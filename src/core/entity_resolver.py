"""Resuelve nombre de equipo/competencia -> id en `teams`/`competitions`.

analysis_history conserva match_title y competition (texto) por compatibilidad;
los *_id son la clave normalizada. Match por lower(trim(nombre)), sin importar mayúsculas.
Competencias: una fila por liga (season NULL); la temporada queda en el payload.
"""
import json
import re
import uuid

from sqlalchemy import text

_SEP = " vs "
_STAGE_RE = re.compile(r"^(.*?)\s*,\s*(Apertura|Clausura)\s*$", re.IGNORECASE)
# Nombres con los que llegaron partidos antiguos -> nombre canónico de la competencia.
LEGACY_ALIASES = {"Liga DIMAYOR": "Primera A"}


def split_stage(name: str | None) -> tuple[str, str | None]:
    """'Liga MX, Apertura' -> ('Liga MX', 'Apertura'); sin torneo -> (name, None)."""
    name = (name or "").strip()
    m = _STAGE_RE.match(name)
    return (m.group(1).strip(), m.group(2).capitalize()) if m else (name, None)


def extract_stage(payload, competition: str | None = None) -> str | None:
    """Torneo (Apertura/Clausura) del partido: payload['stage'] o sufijo del nombre de competencia."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = None
    st = payload.get("stage") if isinstance(payload, dict) else None
    st = split_stage(f"x, {st}")[1] if st else None
    return st or split_stage(competition)[1]


def split_title(title: str | None) -> tuple[str | None, str | None]:
    if not title or _SEP not in title:
        return None, None
    h, a = (p.strip() for p in title.split(_SEP, 1))
    return h or None, a or None


def _name_key(name: str | None) -> str:
    # shortcut: SQLite lower() es solo ASCII ("Ñ" no baja a "ñ"); casefold en Python evita duplicados UNIQUE(sport, name).
    return " ".join((name or "").split()).casefold()


def _find_id_by_name(conn, table: str, sport: str, name: str) -> str | None:
    key = _name_key(name)
    for _id, existing in conn.execute(text(f"SELECT id, name FROM {table} WHERE sport=:s"), {"s": sport}).fetchall():
        if _name_key(existing) == key:
            return _id
    return None


def _find_competition_id(conn, sport: str, name: str | None) -> str | None:
    """Por nombre, por nombre sin torneo ('Liga MX, Apertura' -> 'Liga MX') o por alias."""
    name = (name or "").strip()
    if not name:
        return None
    group = split_stage(name)[0]
    for n in (name, group):
        _id = _find_id_by_name(conn, "competitions", sport, n)
        if _id:
            return _id
    keys = {_name_key(name), _name_key(group)}
    for _id, aliases in conn.execute(
        text("SELECT id, aliases FROM competitions WHERE sport=:s AND aliases IS NOT NULL"), {"s": sport}
    ).fetchall():
        try:
            if keys & {_name_key(a) for a in json.loads(aliases)}:
                return _id
        except Exception:
            continue
    return None


def _get_or_create(conn, table: str, sport: str, name: str | None, cache: dict | None) -> str | None:
    name = (name or "").strip()
    if not name:
        return None
    if table == "competitions":
        name = split_stage(name)[0]  # la liga es una; el torneo va en analysis_history.stage
    key = (table, sport, _name_key(name))
    if cache is not None and key in cache:
        return cache[key]
    _id = (_find_competition_id(conn, sport, name) if table == "competitions"
           else _find_id_by_name(conn, table, sport, name))
    if _id is None:
        _id = str(uuid.uuid4())
        conn.execute(
            text(f"INSERT INTO {table} (id, sport, name) VALUES (:i, :s, :n)"),
            {"i": _id, "s": sport, "n": name},
        )
    if cache is not None:
        cache[key] = _id
    return _id


def resolve_entities(conn, sport: str, title: str | None, competition: str | None, cache: dict | None = None):
    """-> (competition_id, home_team_id, away_team_id); crea filas faltantes."""
    h, a = split_title(title)
    return (
        _get_or_create(conn, "competitions", sport, competition, cache),
        _get_or_create(conn, "teams", sport, h, cache),
        _get_or_create(conn, "teams", sport, a, cache),
    )


def backfill_entity_ids(conn) -> int:
    """Idempotente: llena los *_id NULL. Equipos nuevos usan la grafía más frecuente."""
    rows = conn.execute(text(
        "SELECT id, sport, match_title, competition FROM analysis_history "
        "WHERE home_team_id IS NULL OR away_team_id IS NULL OR competition_id IS NULL"
    )).fetchall()
    if not rows:
        return 0
    # Grafía más frecuente primero, para que sea la canónica al crear.
    freq: dict[str, int] = {}
    for _, _, t, _c in rows:
        for n in split_title(t):
            if n:
                freq[n] = freq.get(n, 0) + 1
    cache: dict = {}
    for n in sorted(freq, key=lambda k: -freq[k]):
        for sp in {r[1] for r in rows}:
            _get_or_create(conn, "teams", sp, n, cache)
    n_upd = 0
    for _id, sport, title, comp in rows:
        c, h, a = resolve_entities(conn, sport, title, comp, cache)
        conn.execute(
            text("UPDATE analysis_history SET competition_id=:c, home_team_id=:h, away_team_id=:a WHERE id=:i"),
            {"c": c, "h": h, "a": a, "i": _id},
        )
        n_upd += 1
    return n_upd


# ── Búsquedas de solo lectura (ORM) para filtrar por id en vez de LIKE sobre texto ──
def find_team_id(db, name: str | None, sport: str = "FOOTBALL") -> str | None:
    if not _name_key(name):
        return None
    return _find_id_by_name(db, "teams", sport, name)


def sync_sofascore_team(db, t: dict, sport: str = "FOOTBALL") -> bool:
    """Completa un equipo YA existente con datos de SofaScore. No crea filas ni renombra `name`.

    Match: external_id (sofascore) -> nombre/shortName -> aliases guardados. False si no existe.
    """
    import json

    full = " ".join((t.get("name") or "").split())
    short = " ".join((t.get("shortName") or "").split())
    ext = str(t["id"]) if t.get("id") is not None else None
    names = [n.lower() for n in {full, short} if n]
    if not names and not ext:
        return False

    row = None
    if ext:
        row = db.execute(
            text("SELECT id, aliases FROM teams WHERE sport=:s AND source='sofascore' AND external_id=:e LIMIT 1"),
            {"s": sport, "e": ext},
        ).fetchone()
    if not row and names:
        ph = ",".join(f":n{i}" for i in range(len(names)))
        params = {"s": sport, **{f"n{i}": n for i, n in enumerate(names)}}
        row = db.execute(
            text(
                f"SELECT id, aliases FROM teams WHERE sport=:s AND (lower(trim(name)) IN ({ph}) "
                f"OR EXISTS (SELECT 1 FROM json_each(COALESCE(aliases,'[]')) WHERE lower(value) IN ({ph}))) LIMIT 1"
            ),
            params,
        ).fetchone()
    if not row:
        return False

    try:
        aliases = json.loads(row[1] or "[]")
    except Exception:
        aliases = []
    for n in (full, short):
        if n and n.lower() not in {a.lower() for a in aliases}:
            aliases.append(n)

    db.execute(
        text(
            "UPDATE teams SET full_name=COALESCE(:full, full_name), short_name=COALESCE(:short, short_name), "
            "slug=COALESCE(:slug, slug), name_code=COALESCE(:code, name_code), gender=COALESCE(:g, gender), "
            "country=COALESCE(:c, country), team_colors=COALESCE(:col, team_colors), "
            "external_id=COALESCE(:e, external_id), source=CASE WHEN :e IS NULL THEN source ELSE 'sofascore' END, "
            "aliases=:al WHERE id=:i"
        ),
        {
            "full": full or None, "short": short or None, "slug": t.get("slug"),
            "code": t.get("nameCode"), "g": t.get("gender"),
            "c": (t.get("country") or {}).get("name"),
            "col": json.dumps(t["teamColors"]) if t.get("teamColors") else None,
            "e": ext, "al": json.dumps(aliases, ensure_ascii=False), "i": row[0],
        },
    )
    return True


def get_team_names(db, ext_id: str | None, name: str | None, sport: str = "FOOTBALL") -> dict | None:
    """Todos los nombres conocidos de un equipo (name, full_name, short_name, aliases), por
    external_id de SofaScore y, si no, por nombre o alias. None si no existe."""
    import json

    row = None
    if ext_id:
        row = db.execute(
            text("SELECT name, full_name, short_name, aliases FROM teams WHERE sport=:s AND source='sofascore' AND external_id=:e LIMIT 1"),
            {"s": sport, "e": str(ext_id)},
        ).fetchone()
    n = " ".join((name or "").strip().lower().split())
    if not row and n:
        row = db.execute(
            text(
                "SELECT name, full_name, short_name, aliases FROM teams WHERE sport=:s AND (lower(trim(name))=:n "
                "OR lower(trim(full_name))=:n OR lower(trim(short_name))=:n "
                "OR EXISTS (SELECT 1 FROM json_each(COALESCE(aliases,'[]')) WHERE lower(value)=:n)) LIMIT 1"
            ),
            {"s": sport, "n": n},
        ).fetchone()
    if not row:
        return None
    try:
        aliases = json.loads(row[3] or "[]")
    except Exception:
        aliases = []
    names = []
    for v in (row[2], row[1], row[0], *aliases):  # corto, largo, nombre en DB, aliases
        if v and v.strip().lower() not in {x.lower() for x in names}:
            names.append(v.strip())
    return {"name": row[0], "full_name": row[1], "short_name": row[2], "aliases": names}


_SRC_FIELDS = (
    "name", "slug", "tier", "grade", "user_count", "primary_color", "secondary_color", "logo_id",
    "teams_count", "rounds_count", "games_count", "tables_count", "relegating_teams_count",
    "frequency", "season_id", "season_name", "season_year", "current_round",
)


def _merge_aliases(conn, comp_id: str, names) -> None:
    """Agrega nombres a competitions.aliases (sin duplicar ni repetir el nombre canónico)."""
    row = conn.execute(text("SELECT name, aliases FROM competitions WHERE id=:i"), {"i": comp_id}).fetchone()
    try:
        cur = json.loads(row[1] or "[]")
    except Exception:
        cur = []
    known = {_name_key(row[0])} | {_name_key(a) for a in cur}
    for n in names:
        n = (n or "").strip()
        if n and _name_key(n) not in known:
            cur.append(n)
            known.add(_name_key(n))
    conn.execute(text("UPDATE competitions SET aliases=:a WHERE id=:i"),
                 {"a": json.dumps(cur, ensure_ascii=False) if cur else None, "i": comp_id})


def refresh_competition_mirror(conn, comp_id: str) -> None:
    """Copia a `competitions` los datos de la fuente vigente (activa y enriquecida, temporada más nueva)."""
    best = None
    for r in conn.execute(
        text("SELECT external_id, slug, tier, user_count, primary_color, secondary_color, logo_id, season_id, "
             "season_name, season_year, synced_at FROM competition_sources "
             "WHERE competition_id=:i AND active=1 AND synced_at IS NOT NULL"),
        {"i": comp_id},
    ).fetchall():
        sid = int(r[7]) if str(r[7] or "").isdigit() else -1
        if best is None or sid > best[0]:
            best = (sid, r)
    if not best:
        return
    r = best[1]
    conn.execute(
        text("UPDATE competitions SET external_id=:e, slug=:sl, tier=:t, user_count=:u, primary_color=:p, "
             "secondary_color=:s, logo_id=:l, season_id=:si, season_name=:sn, season_year=:sy, synced_at=:y, "
             "source='sofascore' WHERE id=:i"),
        {"e": r[0], "sl": r[1], "t": r[2], "u": r[3], "p": r[4], "s": r[5], "l": r[6],
         "si": r[7], "sn": r[8], "sy": r[9], "y": r[10], "i": comp_id},
    )


def sync_sofascore_competition(db, c: dict, sport: str = "FOOTBALL") -> str:
    """Upsert de un unique-tournament de SofaScore. Devuelve 'created', 'updated' o 'skipped'.

    `c` = {id, name, alias?, slug, tier, userCount, category, country, countryCode, primaryColor,
    secondaryColor, logoId, grade, teamsCount, roundsCount, gamesCount, tablesCount,
    relegatingTeamsCount, frequency, otherNames?, currentRound?, season: {id, name, year}, active?,
    discovered?}.
    Una competencia (liga) tiene N fuentes (Liga MX: Apertura y Clausura). La liga se busca por
    fuente (external_id) -> nombre -> nombre sin torneo -> alias. Nunca renombra filas existentes.
    `discovered` = solo descubierta (sin enriquecer): se crea inactiva y no pisa nada existente.
    """
    from datetime import datetime

    ext = str(c["id"])
    discovered = bool(c.get("discovered"))
    group, stage = split_stage(c["name"])
    src = db.execute(text("SELECT id, competition_id FROM competition_sources WHERE external_id=:e"),
                     {"e": ext}).fetchone()
    if src and discovered:
        return "skipped"

    comp_id = src[1] if src else None
    for n in (c.get("name"), c.get("alias")):
        if comp_id or not n:
            break
        comp_id = _find_competition_id(db, sport, n)

    s = c.get("season") or {}
    now = None if discovered else datetime.utcnow()
    vals = {
        "name": c["name"], "slug": c.get("slug"), "tier": c.get("tier"), "grade": c.get("grade"),
        "user_count": c.get("userCount"), "primary_color": c.get("primaryColor"),
        "secondary_color": c.get("secondaryColor"), "logo_id": c.get("logoId"),
        "teams_count": c.get("teamsCount"), "rounds_count": c.get("roundsCount"),
        "games_count": c.get("gamesCount"), "tables_count": c.get("tablesCount"),
        "relegating_teams_count": c.get("relegatingTeamsCount"), "frequency": c.get("frequency"),
        "season_id": str(s["id"]) if s.get("id") is not None else None,
        "season_name": s.get("name"), "season_year": s.get("year"),
        "current_round": c.get("currentRound"),
    }
    created = comp_id is None
    if created:
        comp_id = str(uuid.uuid4())
        db.execute(
            text("INSERT INTO competitions (id, sport, name, active, source) VALUES (:i, :s, :n, :a, 'sofascore')"),
            {"i": comp_id, "s": sport, "n": group, "a": 0 if discovered else (1 if c.get("active", True) else 0)},
        )
    if src:
        sets = ", ".join(f"{k}=COALESCE(:{k}, {k})" for k in _SRC_FIELDS)  # campo ausente no pisa lo guardado
        extra = ", synced_at=:now" + (", active=:a" if "active" in c else "")
        db.execute(text(f"UPDATE competition_sources SET {sets}, stage=COALESCE(:stage, stage){extra} WHERE id=:i"),
                   {**vals, "stage": stage, "now": now, "a": 1 if c.get("active", True) else 0, "i": src[0]})
    else:
        cols = ", ".join(_SRC_FIELDS)
        ph = ", ".join(f":{k}" for k in _SRC_FIELDS)
        db.execute(
            text(f"INSERT INTO competition_sources (id, competition_id, external_id, stage, active, synced_at, {cols}) "
                 f"VALUES (:i, :c, :e, :stage, :a, :now, {ph})"),
            {**vals, "i": str(uuid.uuid4()), "c": comp_id, "e": ext, "stage": stage, "now": now,
             "a": 0 if discovered else (1 if c.get("active", True) else 0)},
        )

    _merge_aliases(db, comp_id, [c.get("alias"), c.get("name") if group != c["name"] else None,
                                 *(c.get("otherNames") or [])])
    db.execute(
        text("UPDATE competitions SET category=COALESCE(:cat, category), country=COALESCE(:cn, country), "
             "country_code=COALESCE(:cc, country_code) WHERE id=:i"),
        {"cat": c.get("category"), "cn": c.get("country"), "cc": c.get("countryCode"), "i": comp_id},
    )
    refresh_competition_mirror(db, comp_id)
    return "created" if created or not src else "updated"


def merge_competitions(conn, keep_id: str, drop_id: str) -> None:
    """Pasa picks, partidos y fuentes de `drop` a `keep`; el nombre de `drop` queda como alias."""
    if keep_id == drop_id:
        return
    drop = conn.execute(text("SELECT name, aliases, category, country, country_code FROM competitions WHERE id=:i"),
                        {"i": drop_id}).fetchone()
    conn.execute(text("UPDATE competitions SET category=COALESCE(category, :c), country=COALESCE(country, :n), "
                      "country_code=COALESCE(country_code, :cc) WHERE id=:k"),
                 {"c": drop[2], "n": drop[3], "cc": drop[4], "k": keep_id})
    try:
        drop_aliases = json.loads(drop[1] or "[]")
    except Exception:
        drop_aliases = []
    for tbl in ("analysis_history", "matches", "competition_sources"):
        conn.execute(text(f"UPDATE {tbl} SET competition_id=:k WHERE competition_id=:d"), {"k": keep_id, "d": drop_id})
    _merge_aliases(conn, keep_id, [drop[0], *drop_aliases])
    conn.execute(text("DELETE FROM competitions WHERE id=:d"), {"d": drop_id})
    refresh_competition_mirror(conn, keep_id)


def consolidate_competitions(conn, sport: str = "FOOTBALL") -> int:
    """Idempotente. (1) crea la fuente de cada competencia que ya tenía external_id, (2) une filas por
    torneo ('Liga MX, Apertura') en su liga, (3) une nombres legacy (LEGACY_ALIASES). Devuelve nº de uniones."""
    from datetime import datetime

    for r in conn.execute(text(
        "SELECT c.id, c.name, c.external_id, c.slug, c.tier, c.user_count, c.primary_color, c.secondary_color, "
        "c.logo_id, c.season_id, c.season_name, c.season_year, c.active, c.synced_at FROM competitions c "
        "WHERE c.sport=:s AND c.external_id IS NOT NULL AND NOT EXISTS "
        "(SELECT 1 FROM competition_sources x WHERE x.external_id=c.external_id)"), {"s": sport},
    ).fetchall():
        conn.execute(
            text("INSERT INTO competition_sources (id, competition_id, external_id, name, stage, slug, tier, "
                 "user_count, primary_color, secondary_color, logo_id, season_id, season_name, season_year, "
                 "active, synced_at) VALUES (:i, :c, :e, :n, :st, :sl, :t, :u, :p, :s2, :l, :si, :sn, :sy, :a, :y)"),
            {"i": str(uuid.uuid4()), "c": r[0], "e": r[2], "n": r[1], "st": split_stage(r[1])[1], "sl": r[3],
             "t": r[4], "u": r[5], "p": r[6], "s2": r[7], "l": r[8], "si": r[9], "sn": r[10], "sy": r[11],
             "a": r[12], "y": r[13] or datetime.utcnow()},
        )

    merged = 0
    for cid, name in conn.execute(text("SELECT id, name FROM competitions WHERE sport=:s"), {"s": sport}).fetchall():
        group = split_stage(name)[0]
        target = None
        if group != name:
            target = _find_id_by_name(conn, "competitions", sport, group)
            if target is None:  # nadie llamado 'Liga MX': esta fila pasa a ser la liga
                conn.execute(text("UPDATE competitions SET name=:n WHERE id=:i"), {"n": group, "i": cid})
                _merge_aliases(conn, cid, [name])
                continue
        elif name in LEGACY_ALIASES:
            target = _find_id_by_name(conn, "competitions", sport, LEGACY_ALIASES[name])
        if target and target != cid:
            merge_competitions(conn, target, cid)
            merged += 1
    return merged


def find_competition_id(db, name: str | None, sport: str = "FOOTBALL") -> str | None:
    return _find_competition_id(db, sport, name)


def purge_orphans(db) -> None:
    """Borra teams/competitions sin ninguna fila de analysis_history que los use."""
    db.execute(text(
        "DELETE FROM teams WHERE id NOT IN (SELECT home_team_id FROM analysis_history WHERE home_team_id IS NOT NULL) "
        "AND id NOT IN (SELECT away_team_id FROM analysis_history WHERE away_team_id IS NOT NULL) "
        "AND id NOT IN (SELECT home_team_id FROM matches WHERE home_team_id IS NOT NULL) "
        "AND id NOT IN (SELECT away_team_id FROM matches WHERE away_team_id IS NOT NULL)"
    ))
    db.execute(text(
        "DELETE FROM competitions WHERE id NOT IN (SELECT competition_id FROM analysis_history WHERE competition_id IS NOT NULL) "
        "AND id NOT IN (SELECT competition_id FROM matches WHERE competition_id IS NOT NULL)"
    ))


def competition_filter(db, name: str | None):
    """Cláusula para AnalysisHistory: por competition_id si la liga existe; si no, por texto."""
    from src.core.domain import AnalysisHistory

    cid = find_competition_id(db, name)
    return AnalysisHistory.competition_id == cid if cid else AnalysisHistory.competition == name
