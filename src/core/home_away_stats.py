"""Promedios de un equipo SOLO como local o SOLO como visitante, dentro de una temporada.

Fuente: columnas `final_*` de `analysis_history` (una fila por partido). El "contra" del
equipo es la columna del rival en la misma fila. Corte temporal fail-closed (solo partidos
estrictamente anteriores al kickoff) y temporada exacta (ver season_resolver).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func

from src.core.domain import AnalysisHistory, Sport
from src.core.season_resolver import same_season, season_key
from src.domain.temporal import TemporalCutoff

# campo del split -> (columna propia, columna del rival)  [sufijos _home/_away se agregan]
_METRICS = {
    "goals": ("final_score", "final_score"),
    "corners": ("final_corners", "final_corners"),
    "yellow": ("final_yellow_cards", "final_yellow_cards"),
    "shots": ("final_shots", "final_shots"),
    "sot": ("final_shots_on_target", "final_shots_on_target"),
    "fouls": ("final_fouls", "final_fouls"),
    "offsides": ("final_offsides", "final_offsides"),
}
# xG excluido a propósito: expected_goals_* en la BD promedia ~0.6 vs ~1.4 goles (otra escala
# que el xG de temporada de SofaScore), mezclarlo sesgaría w_xg en _compute_team_goals_lambda.

_SEASON_ID = AnalysisHistory.season_id
_SEASON_YEAR = AnalysisHistory.season_year
_SEASON = AnalysisHistory.season_label


def _norm(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


# (clave del split, campo por juego propio, campo por juego "contra" o None)
_PER_GAME = (
    ("goals", "goals_per_game", "goals_conceded_per_game"),
    ("corners", "corners_per_game", "corners_conceded_per_game"),
    ("yellow", "yellow_cards_per_game", None),
    ("shots", "shots_per_game", "shots_against_per_game"),
    ("sot", "shots_on_target_per_game", "shots_on_target_against_per_game"),
    ("fouls", "fouls_per_game", None),
    ("offsides", "offside_per_game", None),
)


def apply_split(team: Any, split: dict, role: str, min_n: int = 5) -> Any:
    """Copia de `team` con los promedios del split; lo no calculable queda con la stat general.

    `matches_played` y el conteo del rol pasan a ser `n` (el shrinkage de lambdas depende de ellos);
    los totales que los lambdas dividen por partidos se reescalan para conservar su tasa por juego.
    """
    n = split["n"]
    old_n = max(team.matches_played, 1)
    upd: dict = {"matches_played": n, f"matches_{role}": n}
    for key, own_f, opp_f in _PER_GAME:
        if split.get(f"{key}_n", 0) < min_n:
            continue
        upd[own_f] = split[key]
        if opp_f:
            upd[opp_f] = split[f"{key}_against"]
    if "yellow_cards_per_game" in upd and split.get("yellow_n", 0) >= min_n:
        upd["yellow_cards_against"] = split["yellow_against"] * n
    # rojas: sin dato fiable antes de 2026 -> conserva la tasa general, reescalada a n
    for f in ("red_cards_total", "red_cards_against"):
        upd[f] = getattr(team, f) / old_n * n
    return team.model_copy(update=upd)


def compute_team_split(
    db: Any,
    team_name: str,
    role: str,
    target_season: tuple | None,
    before: Any,
    min_n: int = 5,
) -> dict | None:
    """Promedios por partido de `team_name` jugando de `role` ('home'|'away').

    Devuelve None si falta temporada/cutoff/nombre o hay menos de `min_n` partidos.
    Resultado: {"n": int, "<metric>": media propia, "<metric>_against": media del rival}
    (cada métrica solo sobre filas con dato en ambas columnas; "<metric>_n" = filas usadas).
    """
    cutoff = TemporalCutoff.create(before)
    team = _norm(team_name)
    if role not in ("home", "away") or not team or cutoff is None or target_season is None:
        return None

    own, opp = ("home", "away") if role == "home" else ("away", "home")
    cols = [AnalysisHistory.match_title, AnalysisHistory.match_date]
    for own_col, _ in _METRICS.values():
        cols += [getattr(AnalysisHistory, f"{own_col}_{own}"), getattr(AnalysisHistory, f"{own_col}_{opp}")]
    cols += [_SEASON_ID, _SEASON_YEAR, _SEASON]

    from src.core.entity_resolver import find_team_id

    team_id = find_team_id(db, team_name)
    if team_id:
        # Índice por id del equipo en su rol; evita ILIKE '%x%' sobre todos los títulos.
        name_filter = (AnalysisHistory.home_team_id if role == "home" else AnalysisHistory.away_team_id) == team_id
    else:
        name_filter = AnalysisHistory.match_title.ilike(f"%{team_name.strip()}%")
    rows = (
        db.query(*cols)
        .filter(
            AnalysisHistory.sport == Sport.FOOTBALL,
            AnalysisHistory.final_score_home.isnot(None),
            AnalysisHistory.final_score_away.isnot(None),
            name_filter,
        )
        .all()
    )

    sums: dict[str, list[float]] = {k: [0.0, 0.0, 0] for k in _METRICS}
    n = 0
    for r in rows:
        title, mdate = r[0], r[1]
        parts = (title or "").split(" vs ")
        if len(parts) != 2 or _norm(parts[0 if role == "home" else 1]) != team:
            continue
        if not cutoff.allows(mdate):
            continue
        sid, syear, sseason = r[-3:]
        if not same_season(target_season, season_key(sid, syear, sseason)):
            continue
        n += 1
        vals = r[2:-3]
        for i, k in enumerate(_METRICS):
            a, b = vals[2 * i], vals[2 * i + 1]
            if a is None or b is None:
                continue
            sums[k][0] += float(a)
            sums[k][1] += float(b)
            sums[k][2] += 1

    if n < min_n:
        return None
    out: dict = {"n": n}
    for k, (s_own, s_opp, c) in sums.items():
        if c:
            out[k] = s_own / c
            out[f"{k}_against"] = s_opp / c
            out[f"{k}_n"] = c
    return out
