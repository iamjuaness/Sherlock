from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from src.core.database import get_db
from src.core.domain import AnalysisHistory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sherlock.train_pipeline")


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _has_odds(h: AnalysisHistory, payload_dict: Optional[Dict[str, Any]]) -> bool:
    """
    Determina si un partido tiene cuotas/mercados de apuestas asociados.
    Retorna True si existen cuotas registradas, False si no tiene cuotas.
    """
    if payload_dict and isinstance(payload_dict, dict):
        # 1. Búsqueda en claves estándar del payload
        odds_keys = ["odds", "cuotas", "bookmakers", "bookmaker_odds", "markets", "lines", "odds_data"]
        for key in odds_keys:
            val = payload_dict.get(key)
            if val and (isinstance(val, (dict, list)) and len(val) > 0 or isinstance(val, (int, float))):
                return True

        # 2. Revisión de cuotas dentro de los sub-objetos de equipos
        for side in ("home", "away"):
            team_info = payload_dict.get(side, {})
            if isinstance(team_info, dict) and any(k in team_info for k in ("odd", "cuota", "price")):
                return True

    # 3. Revisión de snapshots o picks de cuotas calculadas
    for attr in ("compare_response_snapshot", "picks_calculados"):
        attr_val = getattr(h, attr, None)
        if attr_val:
            try:
                parsed = json.loads(attr_val) if isinstance(attr_val, str) else attr_val
                if isinstance(parsed, dict) and (parsed.get("odds") or parsed.get("markets") or parsed.get("cuotas")):
                    return True
            except Exception:
                pass

    return False


def _extract_team_names_and_payload(h: AnalysisHistory) -> Tuple[Optional[str], Optional[str], str, Optional[Dict[str, Any]]]:
    home_name = None
    away_name = None
    sport = "football"
    payload_dict = None

    if h.payload:
        try:
            payload_dict = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
            if isinstance(payload_dict, dict):
                home_name = payload_dict.get("home", {}).get("name")
                away_name = payload_dict.get("away", {}).get("name")
                sport = payload_dict.get("sport", "football")
        except Exception:
            pass

    if (not home_name or not away_name) and h.match_title and " vs " in h.match_title:
        parts = h.match_title.split(" vs ", 1)
        home_name = home_name or parts[0].strip()
        away_name = away_name or parts[1].strip()

    return home_name, away_name, sport, payload_dict


def compute_retrospective_stats(
    team_name: str,
    target_date: datetime,
    all_matches: List[AnalysisHistory]
) -> Optional[Dict[str, Any]]:
    """
    Calcula medias acumuladas de un equipo previas a target_date (evita Data Leakage).
    Utiliza todos los partidos históricos finalizados que ya ocurrieron.
    """
    if not target_date:
        return None

    prior_matches = [
        m for m in all_matches 
        if (m.match_date or m.date) and (m.match_date or m.date) < target_date
    ]

    home_matches: List[AnalysisHistory] = []
    away_matches: List[AnalysisHistory] = []

    for m in prior_matches:
        h_name, a_name, _, _ = _extract_team_names_and_payload(m)
        if h_name == team_name:
            home_matches.append(m)
        elif a_name == team_name:
            away_matches.append(m)

    total_played = len(home_matches) + len(away_matches)
    if total_played == 0:
        return None

    stats = {
        "goals_scored": 0.0,
        "goals_conceded": 0.0,
        "xg_scored": 0.0,
        "xg_conceded": 0.0,
        "corners": 0.0,
        "corners_conceded": 0.0,
        "yellow_cards": 0.0,
        "shots": 0.0,
        "shots_on_target": 0.0,
        "shots_inside_box": 0.0,
        "big_chances": 0.0,
        "touches_opp_box": 0.0,
        "final_third_entries": 0.0,
        "blocked_shots": 0.0,
        "fouls": 0.0,
        "recoveries": 0.0,
        "tackles": 0.0,
        "interceptions": 0.0,
        "possession_sum": 0.0,
    }

    for m in home_matches:
        sh = _safe_float(m.final_score_home)
        sa = _safe_float(m.final_score_away)
        stats["goals_scored"] += sh
        stats["goals_conceded"] += sa
        stats["xg_scored"] += _safe_float(getattr(m, "expected_goals_home", None), sh)
        stats["xg_conceded"] += _safe_float(getattr(m, "expected_goals_away", None), sa)
        stats["corners"] += _safe_float(getattr(m, "final_corners_home", None) or getattr(m, "corner_kicks_home", None))
        stats["corners_conceded"] += _safe_float(getattr(m, "final_corners_away", None) or getattr(m, "corner_kicks_away", None))
        stats["yellow_cards"] += _safe_float(getattr(m, "final_yellow_cards_home", None) or getattr(m, "yellow_cards_home", None))
        stats["shots"] += _safe_float(getattr(m, "final_shots_home", None) or getattr(m, "total_shots_on_goal_home", None))
        stats["shots_on_target"] += _safe_float(getattr(m, "final_shots_on_target_home", None) or getattr(m, "shots_on_goal_home", None))
        stats["shots_inside_box"] += _safe_float(getattr(m, "total_shots_inside_box_home", None))
        stats["big_chances"] += _safe_float(getattr(m, "big_chance_created_home", None))
        stats["touches_opp_box"] += _safe_float(getattr(m, "touches_in_opp_box_home", None))
        stats["final_third_entries"] += _safe_float(getattr(m, "final_third_entries_home", None))
        stats["blocked_shots"] += _safe_float(getattr(m, "blocked_scoring_attempt_home", None))
        stats["fouls"] += _safe_float(getattr(m, "final_fouls_home", None) or getattr(m, "fouls_home", None))
        stats["recoveries"] += _safe_float(getattr(m, "ball_recovery_home", None))
        stats["tackles"] += _safe_float(getattr(m, "total_tackle_home", None))
        stats["interceptions"] += _safe_float(getattr(m, "interception_won_home", None))
        stats["possession_sum"] += _safe_float(getattr(m, "ball_possession_home", None), 50.0)

    for m in away_matches:
        sh = _safe_float(m.final_score_home)
        sa = _safe_float(m.final_score_away)
        stats["goals_scored"] += sa
        stats["goals_conceded"] += sh
        stats["xg_scored"] += _safe_float(getattr(m, "expected_goals_away", None), sa)
        stats["xg_conceded"] += _safe_float(getattr(m, "expected_goals_home", None), sh)
        stats["corners"] += _safe_float(getattr(m, "final_corners_away", None) or getattr(m, "corner_kicks_away", None))
        stats["corners_conceded"] += _safe_float(getattr(m, "final_corners_home", None) or getattr(m, "corner_kicks_home", None))
        stats["yellow_cards"] += _safe_float(getattr(m, "final_yellow_cards_away", None) or getattr(m, "yellow_cards_away", None))
        stats["shots"] += _safe_float(getattr(m, "final_shots_away", None) or getattr(m, "total_shots_on_goal_away", None))
        stats["shots_on_target"] += _safe_float(getattr(m, "final_shots_on_target_away", None) or getattr(m, "shots_on_goal_away", None))
        stats["shots_inside_box"] += _safe_float(getattr(m, "total_shots_inside_box_away", None))
        stats["big_chances"] += _safe_float(getattr(m, "big_chance_created_away", None))
        stats["touches_opp_box"] += _safe_float(getattr(m, "touches_in_opp_box_away", None))
        stats["final_third_entries"] += _safe_float(getattr(m, "final_third_entries_away", None))
        stats["blocked_shots"] += _safe_float(getattr(m, "blocked_scoring_attempt_away", None))
        stats["fouls"] += _safe_float(getattr(m, "final_fouls_away", None) or getattr(m, "fouls_away", None))
        stats["recoveries"] += _safe_float(getattr(m, "ball_recovery_away", None))
        stats["tackles"] += _safe_float(getattr(m, "total_tackle_away", None))
        stats["interceptions"] += _safe_float(getattr(m, "interception_won_away", None))
        stats["possession_sum"] += _safe_float(getattr(m, "ball_possession_away", None), 50.0)

    return {
        "name": team_name,
        "matches_played": total_played,
        "goals_per_game": stats["goals_scored"] / total_played,
        "goals_conceded_per_game": stats["goals_conceded"] / total_played,
        "xg_per_game": stats["xg_scored"] / total_played,
        "xg_conceded_per_game": stats["xg_conceded"] / total_played,
        "corners_per_game": stats["corners"] / total_played,
        "corners_conceded_per_game": stats["corners_conceded"] / total_played,
        "yellow_cards_per_game": stats["yellow_cards"] / total_played,
        "shots_per_game": stats["shots"] / total_played,
        "shots_on_target_per_game": stats["shots_on_target"] / total_played,
        "shots_inside_box_per_game": stats["shots_inside_box"] / total_played,
        "big_chances_per_game": stats["big_chances"] / total_played,
        "touches_opp_box_per_game": stats["touches_opp_box"] / total_played,
        "final_third_entries_per_game": stats["final_third_entries"] / total_played,
        "blocked_shots_per_game": stats["blocked_shots"] / total_played,
        "fouls_per_game": stats["fouls"] / total_played,
        "balls_recovered_per_game": stats["recoveries"] / total_played,
        "tackles_per_game": stats["tackles"] / total_played,
        "interceptions_per_game": stats["interceptions"] / total_played,
        "possession_pct": stats["possession_sum"] / total_played,
    }


def get_training_data() -> List[Dict[str, Any]]:
    db = next(get_db())
    try:
        # Partidos con resultado final confirmado
        all_matches: List[AnalysisHistory] = db.query(AnalysisHistory).filter(
            AnalysisHistory.final_score_home.isnot(None),
            AnalysisHistory.final_score_away.isnot(None)
        ).order_by(AnalysisHistory.match_date.asc(), AnalysisHistory.date.asc()).all()

        logger.info("Total de partidos con estadísticas finales: %d", len(all_matches))
        records: List[Dict[str, Any]] = []

        for h in all_matches:
            try:
                home_name, away_name, _, payload_dict = _extract_team_names_and_payload(h)
                if not home_name or not away_name:
                    continue

                # Filtro estricto: Descartar si el partido posee cuotas registradas
                if _has_odds(h, payload_dict):
                    continue

                target_date = h.match_date or h.date
                if not target_date:
                    continue

                # Cálculo de variables retrospectivas sin fuga de información
                home_stats = compute_retrospective_stats(home_name, target_date, all_matches)
                away_stats = compute_retrospective_stats(away_name, target_date, all_matches)

                if not home_stats or not away_stats:
                    continue

                records.append({
                    "home_stats": home_stats,
                    "away_stats": away_stats,
                    "final_score_home": _safe_float(h.final_score_home),
                    "final_score_away": _safe_float(h.final_score_away),
                    "final_corners_home": _safe_float(getattr(h, "final_corners_home", None) or getattr(h, "corner_kicks_home", None)),
                    "final_corners_away": _safe_float(getattr(h, "final_corners_away", None) or getattr(h, "corner_kicks_away", None)),
                    "final_yellow_cards_home": _safe_float(getattr(h, "final_yellow_cards_home", None) or getattr(h, "yellow_cards_home", None)),
                    "final_yellow_cards_away": _safe_float(getattr(h, "final_yellow_cards_away", None) or getattr(h, "yellow_cards_away", None)),
                    "final_red_cards_home": _safe_float(getattr(h, "final_red_cards_home", None)),
                    "final_red_cards_away": _safe_float(getattr(h, "final_red_cards_away", None)),
                    "final_fouls_home": _safe_float(getattr(h, "final_fouls_home", None) or getattr(h, "fouls_home", None)),
                    "final_fouls_away": _safe_float(getattr(h, "final_fouls_away", None) or getattr(h, "fouls_away", None)),
                    "final_shots_home": _safe_float(getattr(h, "final_shots_home", None) or getattr(h, "total_shots_on_goal_home", None)),
                    "final_shots_away": _safe_float(getattr(h, "final_shots_away", None) or getattr(h, "total_shots_on_goal_away", None)),
                    "final_shots_on_target_home": _safe_float(getattr(h, "final_shots_on_target_home", None) or getattr(h, "shots_on_goal_home", None)),
                    "final_shots_on_target_away": _safe_float(getattr(h, "final_shots_on_target_away", None) or getattr(h, "shots_on_goal_away", None)),
                })

            except Exception as e:
                logger.error("Error al procesar partido ID %s: %s", getattr(h, "id", "desconocido"), e)

        return records

    finally:
        db.close()


def train() -> None:
    logger.info("Iniciando extracción de partidos sin cuotas y con estadísticas finales...")
    records = get_training_data()
    logger.info("Dataset generado: %d partidos válidos para entrenamiento.", len(records))

    if len(records) < 80:
        logger.warning("Menos de 80 partidos válidos. El calibrador se quedará en la identidad.")

    if not records:
        logger.error("No se encontraron partidos que cumplan la condición (sin cuotas y con stats finales).")
        return

    # El endpoint ya no entrena un GLM: reentrena el calibrador a partir de los
    # picks liquidados en la base de datos. El dataset se sigue enviando por
    # compatibilidad, pero el servidor lo ignora a proposito -- entrenar con un
    # dataset externo saltaria el cutoff temporal que protege las features.
    logger.info("Solicitando reentrenamiento del calibrador en /api/v1/ml/train...")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/ml/train",
            json={"records": records},
            timeout=120
        )
        if response.status_code == 200:
            logger.info("Reentrenamiento del calibrador completado.")
            print(json.dumps(response.json(), indent=2))
        else:
            logger.error("Error devuelto por el servidor: HTTP %d", response.status_code)
            logger.error(response.text)
    except requests.exceptions.ConnectionError:
        logger.error("No fue posible conectar con http://localhost:8000")


if __name__ == "__main__":
    train()