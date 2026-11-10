"""Rutas results de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime
import json
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.core.database import get_db
from src.core.domain import Sport, AnalysisHistory

from src.ui.api.shared import (
    _check_payload_has_odds,
    _check_pick_success,
    _extract_bookmaker,
    _extract_competition,
    _invalidate_stats_cache,
    _is_pick_hit,
)
from fastapi import APIRouter

router = APIRouter()

# ---------------------------------------------------------------------------
# Results endpoint — used by browser extensions to push match results
# ---------------------------------------------------------------------------
_result_store: dict | None = None
_in_leagues_window: bool = False


@router.post("/api/v1/leagues/active-state", tags=["Leagues"])
def set_leagues_active_state(active: bool = Query(...)):
    global _in_leagues_window
    _in_leagues_window = active
    return {"status": "ok", "in_leagues_window": _in_leagues_window}


def _normalize_season_year(value):
    """'26/27' -> '2026/2027'; otros formatos (p. ej. '2025') quedan igual."""
    import re

    m = re.fullmatch(r"\s*(\d{2}|\d{4})\s*[/-]\s*(\d{2}|\d{4})\s*", str(value or ""))
    if not m:
        return value
    return "/".join(g if len(g) == 4 else f"20{g}" for g in m.groups())


def _event_id_equals(event_id):
    """event_id EXACTO del payload. `payload.contains(id)` daba falsos positivos
    (ej. 16671672 dentro de start_timestamp 1667167200) y mezclaba datos entre partidos."""
    from sqlalchemy import String, cast, func

    return cast(func.json_extract(AnalysisHistory.payload, "$.event_id"), String) == str(event_id)


@router.post("/api/v1/result", tags=["Results"])
async def push_result(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Browser extension pushes match results here (e.g. from flashscore).
    Tries to find matching AnalysisHistory record and auto-update it,
    and also buffers it in memory for the UI to consume.
    """
    global _result_store, _in_leagues_window
    is_historical = payload.get("season_year") is not None
    if not _in_leagues_window and not is_historical:
        return {
            "status": "ignored",
            "message": "Ignored because user is not in the leagues window.",
        }

    _result_store = payload

    sport = payload.get("sport", "football")
    home_name = payload.get("home_team") or payload.get("home", {}).get("name")
    away_name = payload.get("away_team") or payload.get("away", {}).get("name")

    if home_name and away_name:
        try:
            sport_enum = Sport(sport)
            h_name_lower = home_name.lower()
            a_name_lower = away_name.lower()

            # ── ESTRATEGIA 1: Busqueda directa por event_id (la mas rapida) ──
            event_id = payload.get("event_id")
            matched = None
            if event_id:
                matched = (
                    db.query(AnalysisHistory)
                    .filter(
                        AnalysisHistory.sport == sport_enum,
                        _event_id_equals(event_id),
                    )
                    .first()
                )

            if not matched:
                # ── ESTRATEGIA 2: Búsqueda por título exacto + fecha ──
                match_date_val = None
                if payload.get("start_timestamp"):
                    try:
                        match_date_val = datetime.utcfromtimestamp(payload["start_timestamp"])
                    except Exception:
                        pass
                if not match_date_val and payload.get("match_date"):
                    try:
                        match_date_val = datetime.fromisoformat(
                            str(payload["match_date"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        pass
                if not match_date_val and payload.get("date"):
                    try:
                        match_date_val = datetime.fromisoformat(
                            str(payload["date"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                # 2a. Intento exacto: título con orden correcto + fecha cercana (+/- 2 días)
                exact_title = f"{home_name} vs {away_name}"
                query = db.query(AnalysisHistory).filter(
                    AnalysisHistory.sport == sport_enum,
                    AnalysisHistory.match_title == exact_title,
                )
                if match_date_val:
                    from datetime import timedelta

                    query = query.filter(
                        or_(
                            and_(
                                AnalysisHistory.match_date.isnot(None),
                                AnalysisHistory.match_date >= match_date_val - timedelta(days=2),
                                AnalysisHistory.match_date <= match_date_val + timedelta(days=2),
                            ),
                            and_(
                                AnalysisHistory.match_date.is_(None),
                                AnalysisHistory.date >= match_date_val - timedelta(days=2),
                                AnalysisHistory.date <= match_date_val + timedelta(days=2),
                            ),
                        )
                    )
                matched = query.order_by(AnalysisHistory.date.desc()).first()

                # 2b. Si no hay exacto, buscar candidatos con ambos nombres PERO
                #    filtrar estrictamente por fecha y respetar el orden (local primero, visitante segundo)
                if not matched:
                    candidates_query = db.query(AnalysisHistory).filter(
                        AnalysisHistory.sport == sport_enum,
                        AnalysisHistory.match_title.ilike(f"%{home_name}%"),
                        AnalysisHistory.match_title.ilike(f"%{away_name}%"),
                    )
                    if match_date_val:
                        from datetime import timedelta

                        candidates_query = candidates_query.filter(
                            or_(
                                and_(
                                    AnalysisHistory.match_date.isnot(None),
                                    AnalysisHistory.match_date
                                    >= match_date_val - timedelta(days=2),
                                    AnalysisHistory.match_date
                                    <= match_date_val + timedelta(days=2),
                                ),
                                and_(
                                    AnalysisHistory.match_date.is_(None),
                                    AnalysisHistory.date >= match_date_val - timedelta(days=2),
                                    AnalysisHistory.date <= match_date_val + timedelta(days=2),
                                ),
                            )
                        )
                    candidates = candidates_query.order_by(AnalysisHistory.date.desc()).all()

                    for h in candidates:
                        title_lower = h.match_title.lower()
                        # Issue #15: emparejamiento estricto por nombre completo del equipo (no prefijo de 5 letras)
                        home_match = h_name_lower in title_lower
                        away_match = a_name_lower in title_lower
                        if not (home_match and away_match):
                            continue

                        # Diferenciación estricta por fecha: si el candidato es de otra fecha (+/- 2 días), omitir
                        rec_date = h.match_date or h.date
                        if match_date_val and rec_date:
                            if abs((rec_date - match_date_val).total_seconds()) > 2 * 86400:
                                continue

                        home_idx = title_lower.find(h_name_lower)
                        away_idx = title_lower.find(a_name_lower)
                        if home_idx != -1 and away_idx != -1 and home_idx < away_idx:
                            matched = h
                            break

            # ── Si encontramos el partido, actualizamos ──
            if matched:
                h = matched

                # Guardar la identidad SofaScore en el payload para que el diff lo reconozca
                try:
                    _p = json.loads(str(h.payload))
                    _changed = False
                    for _k in ("event_id", "season_id"):
                        if payload.get(_k) and not _p.get(_k):
                            _p[_k] = payload[_k]
                            _changed = True
                    _sy = _normalize_season_year(payload.get("season_year"))
                    if _sy and not _p.get("season_year"):
                        _p["season_year"] = _sy
                        _changed = True
                    if _changed:
                        h.payload = json.dumps(_p)
                except Exception as _e:
                    print(f"No se pudo actualizar identidad en payload: {_e}")

                # Histórico de Watson: alinear el nombre de competición, si no
                # /history/matches (filtra por competition) no ve la fila y la da por faltante.
                if is_historical and payload.get("competition"):
                    h.competition = payload["competition"]

                # Update fields
                h.final_score_home = payload.get("final_score_home")
                h.final_score_away = payload.get("final_score_away")

                # Optional extra stats
                optional_fields = [
                    "final_corners_home",
                    "final_corners_away",
                    "final_yellow_cards_home",
                    "final_yellow_cards_away",
                    "final_red_cards_home",
                    "final_red_cards_away",
                    "final_shots_home",
                    "final_shots_away",
                    "final_shots_on_target_home",
                    "final_shots_on_target_away",
                    "final_fouls_home",
                    "final_fouls_away",
                    "final_offsides_home",
                    "final_offsides_away",
                ]
                for field in optional_fields:
                    if field in payload:
                        setattr(h, field, payload.get(field))

                # Detailed stats from SofaScore
                det_fields = [
                    "expected_goals_home",
                    "expected_goals_away",
                    "ball_possession_home",
                    "ball_possession_away",
                    "aerial_duels_percentage_home",
                    "aerial_duels_percentage_away",
                    "ground_duels_percentage_home",
                    "ground_duels_percentage_away",
                    "dribbles_percentage_home",
                    "dribbles_percentage_away",
                    "duel_won_percent_home",
                    "duel_won_percent_away",
                    "won_tackle_percent_home",
                    "won_tackle_percent_away",
                    "goals_prevented_home",
                    "goals_prevented_away",
                    "accurate_cross_home",
                    "accurate_cross_away",
                    "accurate_long_balls_home",
                    "accurate_long_balls_away",
                    "accurate_passes_home",
                    "accurate_passes_away",
                    "accurate_through_ball_home",
                    "accurate_through_ball_away",
                    "ball_recovery_home",
                    "ball_recovery_away",
                    "big_chance_created_home",
                    "big_chance_created_away",
                    "big_chance_missed_home",
                    "big_chance_missed_away",
                    "big_chance_scored_home",
                    "big_chance_scored_away",
                    "blocked_scoring_attempt_home",
                    "blocked_scoring_attempt_away",
                    "corner_kicks_home",
                    "corner_kicks_away",
                    "dispossessed_home",
                    "dispossessed_away",
                    "dive_saves_home",
                    "dive_saves_away",
                    "final_third_entries_home",
                    "final_third_entries_away",
                    "final_third_phase_statistic_home",
                    "final_third_phase_statistic_away",
                    "fouled_final_third_home",
                    "fouled_final_third_away",
                    "fouls_home",
                    "fouls_away",
                    "free_kicks_home",
                    "free_kicks_away",
                    "goal_kicks_home",
                    "goal_kicks_away",
                    "goalkeeper_saves_home",
                    "goalkeeper_saves_away",
                    "high_claims_home",
                    "high_claims_away",
                    "hit_woodwork_home",
                    "hit_woodwork_away",
                    "interception_won_home",
                    "interception_won_away",
                    "offsides_home",
                    "offsides_away",
                    "passes_home",
                    "passes_away",
                    "punches_home",
                    "punches_away",
                    "shots_off_goal_home",
                    "shots_off_goal_away",
                    "shots_on_goal_home",
                    "shots_on_goal_away",
                    "throw_ins_home",
                    "throw_ins_away",
                    "total_clearance_home",
                    "total_clearance_away",
                    "total_shots_inside_box_home",
                    "total_shots_inside_box_away",
                    "total_shots_on_goal_home",
                    "total_shots_on_goal_away",
                    "total_shots_outside_box_home",
                    "total_shots_outside_box_away",
                    "total_tackle_home",
                    "total_tackle_away",
                    "touches_in_opp_box_home",
                    "touches_in_opp_box_away",
                    "yellow_cards_home",
                    "yellow_cards_away",
                ]
                for field in det_fields:
                    if field in payload:
                        setattr(h, field, payload.get(field))

                # Calculate Accuracy
                if h.picks_calculados:
                    try:
                        picks = json.loads(str(h.picks_calculados))
                        if isinstance(picks, list) and len(picks) > 0:
                            results_dict = {
                                "final_score_home": h.final_score_home,
                                "final_score_away": h.final_score_away,
                                "final_corners_home": h.final_corners_home,
                                "final_corners_away": h.final_corners_away,
                                "final_yellow_cards_home": h.final_yellow_cards_home,
                                "final_yellow_cards_away": h.final_yellow_cards_away,
                                "final_red_cards_home": h.final_red_cards_home,
                                "final_red_cards_away": h.final_red_cards_away,
                                "final_shots_home": h.final_shots_home,
                                "final_shots_away": h.final_shots_away,
                                "final_shots_on_target_home": h.final_shots_on_target_home,
                                "final_shots_on_target_away": h.final_shots_on_target_away,
                                "final_fouls_home": h.final_fouls_home,
                                "final_fouls_away": h.final_fouls_away,
                                "final_offsides_home": h.final_offsides_home,
                                "final_offsides_away": h.final_offsides_away,
                            }
                            hits = 0
                            total = 0
                            for pick in picks:
                                if pick.get("is_blacklisted"):
                                    continue
                                if not (pick.get("is_publishable", pick.get("is_value", False))):
                                    continue
                                success = _check_pick_success(pick, results_dict)
                                if success is not None and success != "void":
                                    total += 1
                                    if _is_pick_hit(success):
                                        hits += 1
                            if total > 0:
                                h.accuracy_percentage = (hits / total) * 100
                    except Exception as e:
                        print(f"Error calculating accuracy in push_result: {e}")

                db.commit()
                db.refresh(h)

                return {
                    "status": "ok",
                    "message": f"Resultado recibido y auto-asociado al partido en BD: '{h.match_title}'",
                    "auto_updated": True,
                }

        except Exception as ex:
            print(f"Error auto-matching result payload: {ex}")

    # ── Si llegamos aca, NO se encontro en toda la BD: crear nuevo registro ──
    try:
        sport_enum = Sport(sport)
        competition_name = (
            payload.get("tournament.name") or payload.get("competition") or "Desconocida"
        )
        match_title = f"{home_name} vs {away_name}"

        # Reconstruct cleanup payload for storage
        cleaned_payload = {
            "sport": sport,
            "home": {"name": home_name},
            "away": {"name": away_name},
            "competition": competition_name,
            "season_year": _normalize_season_year(payload.get("season_year")),
            "season_id": payload.get("season_id"),
            "tournament_id": payload.get("tournament_id"),
            "round": payload.get("round"),
            "start_timestamp": payload.get("start_timestamp"),
            "event_id": payload.get("event_id"),
        }

        print(f"Reconstruido payload: {cleaned_payload}")

        # ── Tarea 1: extraer fecha explícita; warning si falta ──
        match_date_val = None
        if payload.get("start_timestamp"):
            try:
                match_date_val = datetime.utcfromtimestamp(payload["start_timestamp"])
            except Exception as _e:
                import logging as _logging

                _logging.getLogger("sherlock").warning(
                    "[push_result] start_timestamp inválido id=%s payload=%s err=%s",
                    payload.get("event_id"),
                    payload,
                    _e,
                )
        if not match_date_val and payload.get("match_date"):
            try:
                match_date_val = datetime.fromisoformat(
                    str(payload["match_date"]).replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except Exception:
                pass
        if not match_date_val and payload.get("date"):
            try:
                match_date_val = datetime.fromisoformat(
                    str(payload["date"]).replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except Exception:
                pass
        if not match_date_val:
            import logging as _logging

            _logging.getLogger("sherlock").warning(
                "[push_result] Partido sin fecha: event_id=%s home=%s away=%s payload_keys=%s",
                payload.get("event_id"),
                home_name,
                away_name,
                list(payload.keys()),
            )
            match_date_val = datetime.utcnow()

        # ── Deduplicacion CORREGIDA: ahora SI usa event_id ──
        event_id_str = str(payload.get("event_id")) if payload.get("event_id") else None

        existing = None
        if event_id_str:
            # Buscar por event_id en el payload JSON o en el match_title exacto + fecha
            existing = (
                db.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.sport == sport_enum,
                    AnalysisHistory.match_date == match_date_val,
                    or_(
                        _event_id_equals(event_id_str),
                        AnalysisHistory.match_title == match_title,
                    ),
                )
                .first()
            )
        else:
            # Sin event_id, buscar por titulo exacto + fecha
            existing = (
                db.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.sport == sport_enum,
                    AnalysisHistory.match_title == match_title,
                    AnalysisHistory.match_date == match_date_val,
                )
                .first()
            )

        if existing:
            return {
                "status": "ok",
                "message": f"Evento ya existe — omitido",
                "auto_updated": False,
                "skipped_duplicate": True,
            }

        history = AnalysisHistory(
            sport=sport_enum,
            match_title=match_title,
            payload=json.dumps(cleaned_payload),
            date=match_date_val,
            match_date=match_date_val,
            picks_calculados=None,
            has_odds=_check_payload_has_odds(cleaned_payload),
            needs_recalc=True,
            has_real_stats=True,
            count_in_profitability=False,
            competition=_extract_competition(cleaned_payload),
            bookmaker=_extract_bookmaker(cleaned_payload),
            final_score_home=payload.get("final_score_home"),
            final_score_away=payload.get("final_score_away"),
            final_corners_home=payload.get("final_corners_home"),
            final_corners_away=payload.get("final_corners_away"),
            final_yellow_cards_home=payload.get("final_yellow_cards_home"),
            final_yellow_cards_away=payload.get("final_yellow_cards_away"),
            final_red_cards_home=payload.get("final_red_cards_home"),
            final_red_cards_away=payload.get("final_red_cards_away"),
            final_shots_home=payload.get("final_shots_home"),
            final_shots_away=payload.get("final_shots_away"),
            final_shots_on_target_home=payload.get("final_shots_on_target_home"),
            final_shots_on_target_away=payload.get("final_shots_on_target_away"),
            final_fouls_home=payload.get("final_fouls_home"),
            final_fouls_away=payload.get("final_fouls_away"),
            final_offsides_home=payload.get("final_offsides_home"),
            final_offsides_away=payload.get("final_offsides_away"),
        )

        # Detailed stats from SofaScore
        det_fields = [
            "expected_goals_home",
            "expected_goals_away",
            "ball_possession_home",
            "ball_possession_away",
            "aerial_duels_percentage_home",
            "aerial_duels_percentage_away",
            "ground_duels_percentage_home",
            "ground_duels_percentage_away",
            "dribbles_percentage_home",
            "dribbles_percentage_away",
            "duel_won_percent_home",
            "duel_won_percent_away",
            "won_tackle_percent_home",
            "won_tackle_percent_away",
            "goals_prevented_home",
            "goals_prevented_away",
            "accurate_cross_home",
            "accurate_cross_away",
            "accurate_long_balls_home",
            "accurate_long_balls_away",
            "accurate_passes_home",
            "accurate_passes_away",
            "accurate_through_ball_home",
            "accurate_through_ball_away",
            "ball_recovery_home",
            "ball_recovery_away",
            "big_chance_created_home",
            "big_chance_created_away",
            "big_chance_missed_home",
            "big_chance_missed_away",
            "big_chance_scored_home",
            "big_chance_scored_away",
            "blocked_scoring_attempt_home",
            "blocked_scoring_attempt_away",
            "corner_kicks_home",
            "corner_kicks_away",
            "dispossessed_home",
            "dispossessed_away",
            "dive_saves_home",
            "dive_saves_away",
            "final_third_entries_home",
            "final_third_entries_away",
            "final_third_phase_statistic_home",
            "final_third_phase_statistic_away",
            "fouled_final_third_home",
            "fouled_final_third_away",
            "fouls_home",
            "fouls_away",
            "free_kicks_home",
            "free_kicks_away",
            "goal_kicks_home",
            "goal_kicks_away",
            "goalkeeper_saves_home",
            "goalkeeper_saves_away",
            "high_claims_home",
            "high_claims_away",
            "hit_woodwork_home",
            "hit_woodwork_away",
            "interception_won_home",
            "interception_won_away",
            "offsides_home",
            "offsides_away",
            "passes_home",
            "passes_away",
            "punches_home",
            "punches_away",
            "shots_off_goal_home",
            "shots_off_goal_away",
            "shots_on_goal_home",
            "shots_on_goal_away",
            "throw_ins_home",
            "throw_ins_away",
            "total_clearance_home",
            "total_clearance_away",
            "total_shots_inside_box_home",
            "total_shots_inside_box_away",
            "total_shots_on_goal_home",
            "total_shots_on_goal_away",
            "total_shots_outside_box_home",
            "total_shots_outside_box_away",
            "total_tackle_home",
            "total_tackle_away",
            "touches_in_opp_box_home",
            "touches_in_opp_box_away",
            "yellow_cards_home",
            "yellow_cards_away",
        ]
        for field in det_fields:
            if field in payload:
                setattr(history, field, payload.get(field))

        db.add(history)
        db.commit()
        _invalidate_stats_cache()

        return {
            "status": "ok",
            "message": f"Resultado guardado como nuevo registro historico para {home_name} vs {away_name}.",
            "auto_updated": False,
            "created_new": True,
        }
    except Exception as create_ex:
        print(f"Error creating historical record: {create_ex}")
        return {
            "status": "error",
            "message": f"Error al crear registro historico: {str(create_ex)}",
            "auto_updated": False,
        }


@router.get("/api/v1/result", tags=["Results"])
async def consume_result() -> dict:
    """
    Dashboard/comparator polls this to detect pending match results.
    Returns the payload once and clears the slot (single-use).
    """
    global _result_store
    if _result_store is None:
        return {"pending": False}
    data = _result_store
    _result_store = None
    return {"pending": True, "payload": data}
