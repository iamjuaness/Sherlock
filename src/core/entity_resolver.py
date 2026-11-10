"""Resuelve nombre de equipo/competencia -> id en `teams`/`competitions`.

analysis_history conserva match_title y competition (texto) por compatibilidad;
los *_id son la clave normalizada. Match por lower(trim(nombre)), sin importar mayúsculas.
Competencias: una fila por liga (season NULL); la temporada queda en el payload.
"""
import uuid

from sqlalchemy import text

_SEP = " vs "


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


def _get_or_create(conn, table: str, sport: str, name: str | None, cache: dict | None) -> str | None:
    name = (name or "").strip()
    if not name:
        return None
    key = (table, sport, _name_key(name))
    if cache is not None and key in cache:
        return cache[key]
    _id = _find_id_by_name(conn, table, sport, name)
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


def find_competition_id(db, name: str | None, sport: str = "FOOTBALL") -> str | None:
    n = (name or "").strip().lower()
    if not n:
        return None
    row = db.execute(
        text("SELECT id FROM competitions WHERE sport=:s AND lower(trim(name))=:n LIMIT 1"),
        {"s": sport, "n": n},
    ).fetchone()
    return row[0] if row else None


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
