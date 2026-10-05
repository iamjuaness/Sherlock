"""
Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).

Sustituye la dependencia de entrenamiento GLM con bajo número de muestras 
por cálculos deterministas:
  - Dixon-Coles (Ajuste de fuerza ofensiva/defensiva + tau para marcadores de baja anotación).
  - Ponderación por reciencia exponencial (decay por fecha/partido).
  - Segmentación por liga (promedios específicos de liga y factor de localía).
  - Método de momentos para estimar dispersión Binomial Negativa (corners, tarjetas, tiros).
"""

from __future__ import annotations

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from src.domain.temporal import TemporalCutoff, record_date, parse_utc

logger = logging.getLogger("sherlock.math_engine")


# ---------------------------------------------------------------------------
import json
from pathlib import Path

PROFILES_JSON_PATH = Path("data/league_profiles.json")
CALCULATED_PARAMS_JSON_PATH = Path("data/calculated_league_params.json")

DEFAULT_LEAGUE_HISTORY_PROFILES: Dict[str, Dict[str, Any]] = {
    "stable_high_volume": {
        "league_prior_half_life_days": 420.0,
        "team_half_life_matches": 17.5,
        "team_max_matches": 40,
        "league_history_seasons": 4,
        "min_effective_sample_size": 30.0,
        "league_prior_strength": 18.0,
    },
    "small_or_short_format": {
        "league_prior_half_life_days": 600.0,
        "team_half_life_matches": 20.0,
        "team_max_matches": 45,
        "league_history_seasons": 5,
        "min_effective_sample_size": 18.0,
        "league_prior_strength": 28.0,
    },
    "high_turnover_or_structural_change": {
        "league_prior_half_life_days": 270.0,
        "team_half_life_matches": 12.5,
        "team_max_matches": 30,
        "league_history_seasons": 4,
        "min_effective_sample_size": 24.0,
        "league_prior_strength": 24.0,
    },
}

LEAGUE_HISTORY_PROFILES = DEFAULT_LEAGUE_HISTORY_PROFILES
COMPETITION_PROFILE_MAPPING: Dict[str, str] = {}


def load_league_profiles_config() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Carga perfiles y ligas desde data/league_profiles.json si existe.
    """
    profiles = {k: dict(v) for k, v in DEFAULT_LEAGUE_HISTORY_PROFILES.items()}
    leagues_map: Dict[str, Any] = {}

    if PROFILES_JSON_PATH.exists():
        try:
            with open(PROFILES_JSON_PATH, "r", encoding="utf-8") as f:
                content = json.load(f)
            if isinstance(content, dict):
                p_data = content.get("profiles")
                if isinstance(p_data, dict):
                    for pk, pv in p_data.items():
                        if isinstance(pv, dict):
                            profiles[pk] = pv
                l_data = content.get("leagues")
                if isinstance(l_data, dict):
                    leagues_map = l_data
        except Exception as exc:
            logger.warning("No se pudo cargar %s (%s). Usando perfiles base.", PROFILES_JSON_PATH, exc)

    return profiles, leagues_map


def get_league_profile(
    competition_id: Optional[Any] = None,
    profile_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Obtiene los parámetros del perfil de histórico para una competición.
    Carga dinámicamente desde data/league_profiles.json si existe.
    """
    profiles, leagues_map = load_league_profiles_config()

    if profile_name and profile_name in profiles:
        return dict(profiles[profile_name])

    if competition_id is not None:
        comp_key = str(competition_id).strip()
        comp_norm = comp_key.lower()

        for l_name, l_config in leagues_map.items():
            if l_name.lower() == comp_norm or (isinstance(l_config, dict) and str(l_config.get("id", "")).strip() == comp_key):
                p_name = l_config.get("profile") if isinstance(l_config, dict) else str(l_config)
                if p_name in profiles:
                    res = dict(profiles[p_name])
                    if isinstance(l_config, dict) and "overrides" in l_config and isinstance(l_config["overrides"], dict):
                        res.update(l_config["overrides"])
                    return res

    return dict(profiles.get("stable_high_volume", DEFAULT_LEAGUE_HISTORY_PROFILES["stable_high_volume"]))


def load_calculated_league_params(
    competition_id: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Carga los parámetros matemáticos calculados por liga desde data/calculated_league_params.json si existe.
    """
    if not CALCULATED_PARAMS_JSON_PATH.exists():
        return None

    try:
        with open(CALCULATED_PARAMS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return None

        if competition_id is None:
            return data

        comp_key = str(competition_id).strip().lower()

        for l_name, l_params in data.items():
            clean = str(l_name).strip().lower()
            if comp_key == clean or comp_key in clean or clean in comp_key:
                if isinstance(l_params, dict):
                    return l_params
    except Exception as exc:
        logger.warning("No se pudo cargar %s (%s).", CALCULATED_PARAMS_JSON_PATH, exc)

    return None


# ---------------------------------------------------------------------------
# Funciones Estadísticas Base
# ---------------------------------------------------------------------------

def calculate_time_decay_weight(
    match_date: Any,
    reference_date: Optional[Any] = None,
    half_life_days: float = 365.0,
) -> float:
    """
    Calcula el peso temporal de un partido según la distancia entre su fecha y una fecha de referencia.
    Fórmula: w_i = 0.5 ** (d_i / h)
    Donde:
      - d_i: antigüedad del partido en días.
      - h: half_life_days (días para que el peso caiga al 50%).
    
    Reglas:
      - El partido en fecha igual a reference_date tiene peso 1.0 (d_i = 0).
      - Un partido con d_i == half_life_days tiene peso 0.5.
      - Un partido futuro (match_date > reference_date) retorna 0.0.
      - Fechas inválidas o nulas retornan 0.0.
      - half_life_days <= 0 retorna 0.0.
    """
    if half_life_days <= 0:
        return 0.0

    m_dt = parse_utc(match_date)
    if m_dt is None:
        return 0.0

    if reference_date is None:
        ref_dt = datetime.now(timezone.utc)
    else:
        ref_dt = parse_utc(reference_date)

    if ref_dt is None:
        return 0.0

    if m_dt > ref_dt:
        return 0.0

    delta_days = (ref_dt - m_dt).total_seconds() / 86400.0
    if delta_days < 0:
        return 0.0

    weight = 0.5 ** (delta_days / float(half_life_days))
    return max(0.0, min(1.0, float(weight)))


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def dixon_coles_tau(x: int, y: int, lambda_home: float, mu_away: float, rho: float = -0.05) -> float:
    """
    Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0, 0-1, 1-1).
    rho típico para fútbol suele ser entre -0.03 y -0.08.
    """
    if x == 0 and y == 0:
        return max(0.0001, 1.0 - lambda_home * mu_away * rho)
    elif x == 0 and y == 1:
        return max(0.0001, 1.0 + lambda_home * rho)
    elif x == 1 and y == 0:
        return max(0.0001, 1.0 + mu_away * rho)
    elif x == 1 and y == 1:
        return max(0.0001, 1.0 - rho)
    return 1.0


def calculate_dixon_coles_matrix(
    lambda_home: float, 
    mu_away: float, 
    max_goals: int = 8, 
    rho: float = -0.05
) -> List[List[float]]:
    """
    Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste Dixon-Coles.
    """
    matrix = [[0.0 for _ in range(max_goals + 1)] for _ in range(max_goals + 1)]
    total_prob = 0.0

    for x in range(max_goals + 1):
        p_x = _poisson_pmf(x, lambda_home)
        for y in range(max_goals + 1):
            p_y = _poisson_pmf(y, mu_away)
            tau = dixon_coles_tau(x, y, lambda_home, mu_away, rho)
            prob = max(0.0, p_x * p_y * tau)
            matrix[x][y] = prob
            total_prob += prob

    # Normalizar para asegurar sum(P) = 1.0
    if total_prob > 0:
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                matrix[x][y] /= total_prob

    return matrix


def calculate_weighted_average(values: List[float], half_life: float = 5.0) -> float:
    """
    Calcula el promedio con decay exponencial según antigüedad.
    half_life: número de partidos para que la importancia caiga al 50%.
    values: ordenados del más reciente al más antiguo.
    """
    if not values:
        return 0.0

    alpha = math.log(2) / max(1.0, half_life)
    weights = [math.exp(-alpha * i) for i in range(len(values))]
    sum_w = sum(weights)

    if sum_w <= 0:
        return sum(values) / len(values)

    return sum(v * w for v, w in zip(values, weights)) / sum_w


def estimate_nb_dispersion(values: List[float], weights: Optional[List[float]] = None) -> float:
    """
    Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método de Momentos.
    Var(X) = mu + alpha * mu^2  =>  alpha = (Var - mu) / mu^2
    Soporta lista opcional de pesos temporales por observación.
    """
    if len(values) < 3:
        return 0.05  # Dispersión baja por defecto

    if weights is None or len(weights) != len(values):
        weights = [1.0] * len(values)

    sum_w = sum(weights)
    if sum_w <= 0:
        return 0.05

    mu = sum(v * w for v, w in zip(values, weights)) / sum_w
    if mu <= 0:
        return 0.05

    var = sum(w * ((x - mu) ** 2) for x, w in zip(values, weights)) / sum_w
    if var <= mu:
        return 0.001  # Casi Poisson puro

    alpha = (var - mu) / (mu ** 2)
    return max(0.001, min(0.5, alpha))


# ---------------------------------------------------------------------------
# Motor Predictor Matemático por Liga
# ---------------------------------------------------------------------------

class LeagueMathEngine:
    """
    Calcula probabilidades de partido integrando promedios por liga, fuerza relativa
    de equipo (Local / Visitante / Reciente) y distribuciones Poisson / Dixon-Coles / NB.
    """

    def __init__(self, league_defaults: Optional[Dict[str, float]] = None):
        # Promedios estándar por defecto si la liga no tiene datos históricos suficientes
        self.defaults = {
            "home_goals": 1.45,
            "away_goals": 1.15,
            "home_corners": 5.2,
            "away_corners": 4.1,
            "home_cards": 2.1,
            "away_cards": 2.3,
            "home_shots": 12.5,
            "away_shots": 9.8,
            "home_shots_target": 4.5,
            "away_shots_target": 3.6,
            "home_fouls": 11.5,
            "away_fouls": 12.0,
        }
        if league_defaults:
            self.defaults.update(league_defaults)

    @classmethod
    def compute_last_round_corner_averages(cls, matches: List[Dict[str, Any]], reference_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula el promedio de córners de la última jornada completada antes de `reference_date`.
        """
        if not matches:
            return {
                "source": "default",
                "last_round_date": None,
                "home_corners": 5.2,
                "away_corners": 4.1,
                "avg_corners_per_game": 9.3,
            }

        ref_dt = parse_utc(reference_date) if reference_date else None

        past_matches = []
        for m in matches:
            ch = m.get("final_corners_home")
            ca = m.get("final_corners_away")
            if ch is None or ca is None:
                continue

            m_dt = record_date(m)
            if not m_dt:
                continue

            if ref_dt and m_dt >= ref_dt:
                continue

            past_matches.append((m_dt, m))

        if not past_matches:
            return {
                "source": "default",
                "last_round_date": None,
                "home_corners": 5.2,
                "away_corners": 4.1,
                "avg_corners_per_game": 9.3,
            }

        past_matches.sort(key=lambda x: x[0], reverse=True)
        latest_dt = past_matches[0][0]
        latest_date_str = latest_dt.strftime("%Y-%m-%d")

        last_round_matches = [m for m_dt, m in past_matches if m_dt.strftime("%Y-%m-%d") == latest_date_str]

        tot_home = sum(float(m.get("final_corners_home", 0)) for m in last_round_matches)
        tot_away = sum(float(m.get("final_corners_away", 0)) for m in last_round_matches)
        cnt = len(last_round_matches)

        avg_home = tot_home / cnt if cnt > 0 else 5.2
        avg_away = tot_away / cnt if cnt > 0 else 4.1

        return {
            "source": "last_round",
            "last_round_date": latest_date_str,
            "home_corners": avg_home,
            "away_corners": avg_away,
            "avg_corners_per_game": avg_home + avg_away,
            "sample_size": cnt,
        }

    @classmethod
    def compute_league_averages(
        cls,
        historical_matches: List[Dict[str, Any]],
        reference_date: Optional[Any] = None,
        half_life_days: float = 420.0,
        min_effective_sample_size: float = 1.0,
        fallback_defaults: Optional[Dict[str, float]] = None,
        competition_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Calcula los promedios específicos de la liga ponderados por reciencia temporal.
        Respetando reciencia temporal, perfiles de liga y Kish ESS.
        """
        defaults_map = dict(cls().defaults)

        calc_params = load_calculated_league_params(competition_id) if competition_id else None
        if calc_params and isinstance(calc_params.get("averages"), dict):
            for k, v in calc_params["averages"].items():
                if isinstance(v, (int, float)) and v > 0:
                    defaults_map[k] = float(v)

        if fallback_defaults:
            defaults_map.update(fallback_defaults)

        ref_dt = parse_utc(reference_date) if reference_date is not None else None

        metric_keys = [
            ("home_goals", "away_goals", "final_score_home", "final_score_away"),
            ("home_corners", "away_corners", "final_corners_home", "final_corners_away"),
            ("home_cards", "away_cards", "final_yellow_cards_home", "final_yellow_cards_away"),
            ("home_shots", "away_shots", "final_shots_home", "final_shots_away"),
            ("home_shots_target", "away_shots_target", "final_shots_on_target_home", "final_shots_on_target_away"),
            ("home_fouls", "away_fouls", "final_fouls_home", "final_fouls_away"),
        ]

        results: Dict[str, Any] = {}
        metric_sources: Dict[str, str] = {}
        all_included_dates: List[datetime] = []
        metric_stats: Dict[str, Dict[str, float]] = {}

        for key_home, key_away, raw_home_key, raw_away_key in metric_keys:
            total_h_weighted = 0.0
            total_a_weighted = 0.0
            sum_w = 0.0
            sum_w2 = 0.0
            valid_cnt = 0

            for m in historical_matches or []:
                vh = m.get(raw_home_key)
                va = m.get(raw_away_key)
                if vh is None or va is None:
                    continue

                m_date = record_date(m)
                if m_date is None:
                    if reference_date is None:
                        w = 1.0
                    else:
                        continue
                else:
                    if ref_dt is not None and m_date >= ref_dt:
                        continue

                    w = calculate_time_decay_weight(m_date, reference_date=reference_date, half_life_days=half_life_days)
                    if w <= 0:
                        continue

                try:
                    fh = float(vh)
                    fa = float(va)
                except (ValueError, TypeError):
                    continue

                total_h_weighted += fh * w
                total_a_weighted += fa * w
                sum_w += w
                sum_w2 += w * w
                valid_cnt += 1
                all_included_dates.append(m_date)

            ess = (sum_w ** 2) / sum_w2 if sum_w2 > 0 else 0.0

            if valid_cnt > 0 and sum_w > 0 and ess >= min_effective_sample_size:
                results[key_home] = total_h_weighted / sum_w
                results[key_away] = total_a_weighted / sum_w
                metric_sources[key_home] = "history"
                metric_sources[key_away] = "history"
            else:
                results[key_home] = defaults_map.get(key_home, 1.45 if "goals" in key_home else 5.0)
                results[key_away] = defaults_map.get(key_away, 1.15 if "goals" in key_away else 4.0)
                metric_sources[key_home] = "default"
                metric_sources[key_away] = "default"

            metric_stats[key_home] = {"count": valid_cnt, "sum_w": sum_w, "ess": ess}

        goals_stat = metric_stats.get("home_goals", {"count": 0, "sum_w": 0.0, "ess": 0.0})
        sample_size = goals_stat["count"]
        effective_sample_size = round(goals_stat["ess"], 2)
        total_weight = round(goals_stat["sum_w"], 4)

        history_count = sum(1 for src in metric_sources.values() if src == "history")
        total_metrics = len(metric_sources)

        if history_count == total_metrics:
            global_source = "weighted_league_history"
        elif history_count > 0:
            global_source = "mixed_with_defaults"
        else:
            global_source = "defaults"

        valid_dates = [d for d in all_included_dates if d is not None]
        coverage_start = min(valid_dates).strftime("%Y-%m-%d") if valid_dates else None
        coverage_end = max(valid_dates).strftime("%Y-%m-%d") if valid_dates else None

        results.update({
            "sample_size": sample_size,
            "effective_sample_size": effective_sample_size,
            "total_weight": total_weight,
            "reference_date": ref_dt.isoformat() if ref_dt else None,
            "half_life_days": float(half_life_days),
            "source": global_source,
            "coverage_start_date": coverage_start,
            "coverage_end_date": coverage_end,
        })

        return results

    def calculate_expected_goals_with_meta(
        self,
        home_recent_scored: List[float],
        home_recent_conceded: List[float],
        away_recent_scored: List[float],
        away_recent_conceded: List[float],
        league_home_avg: float = 1.45,
        league_away_avg: float = 1.15,
        half_life: float = 17.5,
        is_home_newly_promoted: bool = False,
        is_away_newly_promoted: bool = False,
        home_lower_div_scored: Optional[List[float]] = None,
        home_lower_div_conceded: Optional[List[float]] = None,
        away_lower_div_scored: Optional[List[float]] = None,
        away_lower_div_conceded: Optional[List[float]] = None,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa con decay exponencial
        y shrinkage Bayesiano para recién ascendidos, retornando metadatos estructurados.
        """
        league_home_avg = max(0.5, league_home_avg)
        league_away_avg = max(0.5, league_away_avg)

        home_att_raw = calculate_weighted_average(home_recent_scored, half_life=half_life) if home_recent_scored else league_home_avg
        home_def_raw = calculate_weighted_average(home_recent_conceded, half_life=half_life) if home_recent_conceded else league_away_avg

        away_att_raw = calculate_weighted_average(away_recent_scored, half_life=half_life) if away_recent_scored else league_away_avg
        away_def_raw = calculate_weighted_average(away_recent_conceded, half_life=half_life) if away_recent_conceded else league_home_avg

        home_top_matches = len(home_recent_scored) if home_recent_scored else 0
        away_top_matches = len(away_recent_scored) if away_recent_scored else 0

        home_shrinkage_weight = 1.0
        home_used_aux = False
        if is_home_newly_promoted or home_top_matches < 8:
            home_shrinkage_weight = min(1.0, home_top_matches / 10.0)
            non_top_w = 1.0 - home_shrinkage_weight
            if home_lower_div_scored and home_lower_div_conceded:
                home_used_aux = True
                low_att = calculate_weighted_average(home_lower_div_scored, half_life=half_life)
                low_def = calculate_weighted_average(home_lower_div_conceded, half_life=half_life)
                aux_w = 0.3 * non_top_w
                lg_w = 0.7 * non_top_w
                home_att_raw = home_att_raw * home_shrinkage_weight + low_att * aux_w + league_home_avg * lg_w
                home_def_raw = home_def_raw * home_shrinkage_weight + low_def * aux_w + league_away_avg * lg_w
            else:
                home_att_raw = home_att_raw * home_shrinkage_weight + league_home_avg * non_top_w
                home_def_raw = home_def_raw * home_shrinkage_weight + league_away_avg * non_top_w

        away_shrinkage_weight = 1.0
        away_used_aux = False
        if is_away_newly_promoted or away_top_matches < 8:
            away_shrinkage_weight = min(1.0, away_top_matches / 10.0)
            non_top_w = 1.0 - away_shrinkage_weight
            if away_lower_div_scored and away_lower_div_conceded:
                away_used_aux = True
                low_att = calculate_weighted_average(away_lower_div_scored, half_life=half_life)
                low_def = calculate_weighted_average(away_lower_div_conceded, half_life=half_life)
                aux_w = 0.3 * non_top_w
                lg_w = 0.7 * non_top_w
                away_att_raw = away_att_raw * away_shrinkage_weight + low_att * aux_w + league_away_avg * lg_w
                away_def_raw = away_def_raw * away_shrinkage_weight + low_def * aux_w + league_home_avg * lg_w
            else:
                away_att_raw = away_att_raw * away_shrinkage_weight + league_away_avg * non_top_w
                away_def_raw = away_def_raw * away_shrinkage_weight + league_home_avg * non_top_w

        home_attack_strength = home_att_raw / league_home_avg
        home_defense_strength = home_def_raw / league_away_avg
        away_attack_strength = away_att_raw / league_away_avg
        away_defense_strength = away_def_raw / league_home_avg

        lambda_home = home_attack_strength * away_defense_strength * league_home_avg
        mu_away = away_attack_strength * home_defense_strength * league_away_avg

        lambda_home = max(0.2, min(4.5, lambda_home))
        mu_away = max(0.2, min(4.5, mu_away))

        meta = {
            "home": {
                "is_newly_promoted": is_home_newly_promoted,
                "top_division_matches": home_top_matches,
                "shrinkage_weight": round(home_shrinkage_weight, 4),
                "used_lower_division_auxiliary_signal": home_used_aux,
            },
            "away": {
                "is_newly_promoted": is_away_newly_promoted,
                "top_division_matches": away_top_matches,
                "shrinkage_weight": round(away_shrinkage_weight, 4),
                "used_lower_division_auxiliary_signal": away_used_aux,
            }
        }

        return lambda_home, mu_away, meta

    def calculate_expected_goals(
        self,
        home_recent_scored: List[float],
        home_recent_conceded: List[float],
        away_recent_scored: List[float],
        away_recent_conceded: List[float],
        league_home_avg: float = 1.45,
        league_away_avg: float = 1.15,
        half_life: float = 17.5,
        is_home_newly_promoted: bool = False,
        is_away_newly_promoted: bool = False,
        home_lower_div_scored: Optional[List[float]] = None,
        home_lower_div_conceded: Optional[List[float]] = None,
        away_lower_div_scored: Optional[List[float]] = None,
        away_lower_div_conceded: Optional[List[float]] = None,
    ) -> Tuple[float, float]:
        """
        Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás.
        """
        lambda_h, mu_a, _ = self.calculate_expected_goals_with_meta(
            home_recent_scored=home_recent_scored,
            home_recent_conceded=home_recent_conceded,
            away_recent_scored=away_recent_scored,
            away_recent_conceded=away_recent_conceded,
            league_home_avg=league_home_avg,
            league_away_avg=league_away_avg,
            half_life=half_life,
            is_home_newly_promoted=is_home_newly_promoted,
            is_away_newly_promoted=is_away_newly_promoted,
            home_lower_div_scored=home_lower_div_scored,
            home_lower_div_conceded=home_lower_div_conceded,
            away_lower_div_scored=away_lower_div_scored,
            away_lower_div_conceded=away_lower_div_conceded,
        )
        return lambda_h, mu_a

    def predict_market_totals(
        self,
        home_values: List[float],
        away_values: List[float],
        league_avg_total: float,
        half_life: float = 17.5,
        home_weights: Optional[List[float]] = None,
        away_weights: Optional[List[float]] = None,
    ) -> Tuple[float, float]:
        """
        Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros, etc.)
        aplicando decaimiento exponencial y suavizado de liga.
        """
        if home_weights and len(home_weights) == len(home_values):
            sum_hw = sum(home_weights)
            h_avg = sum(v * w for v, w in zip(home_values, home_weights)) / sum_hw if sum_hw > 0 else (league_avg_total * 0.55)
        else:
            h_avg = calculate_weighted_average(home_values, half_life=half_life) if home_values else (league_avg_total * 0.55)

        if away_weights and len(away_weights) == len(away_values):
            sum_aw = sum(away_weights)
            a_avg = sum(v * w for v, w in zip(away_values, away_weights)) / sum_aw if sum_aw > 0 else (league_avg_total * 0.45)
        else:
            a_avg = calculate_weighted_average(away_values, half_life=half_life) if away_values else (league_avg_total * 0.45)

        total_expected = (h_avg + a_avg) * 0.75 + (league_avg_total) * 0.25
        h_prop = h_avg / max(0.1, h_avg + a_avg)
        return total_expected * h_prop, total_expected * (1.0 - h_prop)

    @staticmethod
    def compute_recent_form_windows(matches: List[Dict[str, Any]], team_name: str, windows: List[int] = [5, 10, 15]) -> Dict[str, Dict[str, float]]:
        """
        Capa 3: Calcula estadísticas promedio del equipo `team_name` en ventanas móviles de 5, 10 y 15 partidos
        recientes jugados ANTES del partido actual (sin data leakage).
        """
        team_matches = []
        for m in matches:
            ht = (m.get("home_team") or m.get("match_title", "").split(" vs ")[0]).strip().lower()
            at = (m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")).strip().lower()
            t_lower = team_name.strip().lower()
            
            if t_lower == ht or t_lower in ht:
                team_matches.append((m, "home"))
            elif t_lower == at or t_lower in at:
                team_matches.append((m, "away"))

        results = {}
        for w in windows:
            slice_m = team_matches[:w]
            if not slice_m:
                results[f"last_{w}"] = {
                    "goals_scored": 0.0, "goals_conceded": 0.0,
                    "corners": 0.0, "yellow_cards": 0.0, "shots": 0.0
                }
                continue

            g_scored, g_conceded, corners, cards, shots = 0.0, 0.0, 0.0, 0.0, 0.0
            cnt = len(slice_m)

            for m, role in slice_m:
                if role == "home":
                    g_scored += float(m.get("final_score_home") or 0)
                    g_conceded += float(m.get("final_score_away") or 0)
                    corners += float(m.get("final_corners_home") or 0)
                    cards += float(m.get("final_yellow_cards_home") or 0)
                    shots += float(m.get("final_shots_home") or 0)
                else:
                    g_scored += float(m.get("final_score_away") or 0)
                    g_conceded += float(m.get("final_score_home") or 0)
                    corners += float(m.get("final_corners_away") or 0)
                    cards += float(m.get("final_yellow_cards_away") or 0)
                    shots += float(m.get("final_shots_away") or 0)

            results[f"last_{w}"] = {
                "sample_size": cnt,
                "goals_scored": round(g_scored / cnt, 2),
                "goals_conceded": round(g_conceded / cnt, 2),
                "corners": round(corners / cnt, 2),
                "yellow_cards": round(cards / cnt, 2),
                "shots": round(shots / cnt, 2),
            }

        return results

    @staticmethod
    def _evaluate_match_metric_pick(
        m: Dict[str, Any],
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        team_role: str = "home",
        target_side: str = "home",
        is_team_specific: bool = False,
    ) -> Optional[bool]:
        """
        Evalúa si un partido específico cumple con el criterio de un pick.
        Soporta: goals, corners, cards, shots, shots_target, fouls, btts, 1x2, double_chance.
        """
        sh = m.get("final_score_home")
        sa = m.get("final_score_away")

        fam = market_family.lower().strip()

        # 1. Ambos marcan (BTTS)
        if fam in {"btts", "btts_yes", "bttsyes"}:
            if sh is None or sa is None:
                return None
            return float(sh) > 0 and float(sa) > 0

        if fam in {"btts_no", "bttsno"}:
            if sh is None or sa is None:
                return None
            return float(sh) == 0 or float(sa) == 0

        # 2. Ganador 1X2 (Moneyline / Result)
        if fam in {"result", "moneyline", "1x2"}:
            if sh is None or sa is None:
                return None
            gh, ga = float(sh), float(sa)
            t_side = target_side.lower().strip()
            if t_side in {"home", "local", "1"}:
                # Local gana: Para el local que gane (gh > ga); para el visitante que pierda (ga < gh)
                return (gh > ga) if team_role == "home" else (ga < gh)
            elif t_side in {"away", "visitante", "2"}:
                # Visitante gana: Para el visitante que gane (ga > gh); para el local que pierda (gh < ga)
                return (ga > gh) if team_role == "away" else (gh < ga)
            elif t_side in {"draw", "empate", "x"}:
                return gh == ga

        # 3. Doble Oportunidad (Double Chance: 1X, X2, 12)
        if fam in {"double_chance", "doublechance"}:
            if sh is None or sa is None:
                return None
            gh, ga = float(sh), float(sa)
            t_side = target_side.lower().strip()
            if t_side in {"1x", "home_draw", "homedraw"}:
                # 1X: Local gana o empata. Para local gh >= ga; para visitante rival no ganar (ga <= gh)
                return (gh >= ga) if team_role == "home" else (ga <= gh)
            elif t_side in {"x2", "draw_away", "drawaway"}:
                # X2: Visitante gana o empata. Para visitante ga >= gh; para local rival no ganar (gh <= ga)
                return (ga >= gh) if team_role == "away" else (gh <= ga)
            elif t_side in {"12", "home_away", "homeaway"}:
                # 12: Gana local o visitante (sin empate)
                return gh != ga

        # 4. Totales / Over-Under en métricas cuantitativas
        val = None
        if fam == "goals":
            if sh is not None and sa is not None:
                val = (float(sh) if team_role == "home" else float(sa)) if is_team_specific else (float(sh) + float(sa))
        elif fam == "corners":
            ch, ca = m.get("final_corners_home"), m.get("final_corners_away")
            if ch is not None and ca is not None:
                val = (float(ch) if team_role == "home" else float(ca)) if is_team_specific else (float(ch) + float(ca))
        elif fam == "cards":
            yh, ya = m.get("final_yellow_cards_home"), m.get("final_yellow_cards_away")
            if yh is not None and ya is not None:
                val = (float(yh) if team_role == "home" else float(ya)) if is_team_specific else (float(yh) + float(ya))
        elif fam in {"shots", "shots_target"}:
            if fam == "shots_target":
                sth, sta = m.get("final_shots_on_target_home"), m.get("final_shots_on_target_away")
            else:
                sth, sta = m.get("final_shots_home"), m.get("final_shots_away")
            if sth is not None and sta is not None:
                val = (float(sth) if team_role == "home" else float(sta)) if is_team_specific else (float(sth) + float(sta))
        elif fam == "fouls":
            fh, fa = m.get("final_fouls_home"), m.get("final_fouls_away")
            if fh is not None and fa is not None:
                val = (float(fh) if team_role == "home" else float(fa)) if is_team_specific else (float(fh) + float(fa))

        if val is not None and line is not None:
            if math.isclose(val, line, abs_tol=1e-5):
                return None  # Push / Void: excluye del total de muestra en líneas enteras
            return (val > line) if is_over else (val < line)

        return None

    @classmethod
    def compute_pick_hit_rate(
        cls,
        matches: List[Dict[str, Any]],
        team_name: str,
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        role_filter: Optional[str] = None,  # "home", "away", or None (all)
        target_side: str = "home",
        exclude_match_id: Optional[int] = None,
        current_match_date: Optional[Any] = None,
        cutoff: Optional[TemporalCutoff] = None,
        is_team_specific: bool = False,
    ) -> Dict[str, Any]:
        """
        Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.
        Soporta: Líneas Over/Under, BTTS (Sí/No), 1X2 (Gana local/vis/emp) y Doble Oportunidad (1X, X2, 12).
        Previene data-leakage excluyendo partidos en o posteriores a la fecha del partido actual.
        """
        t_lower = team_name.strip().lower()
        matching_count = 0
        hit_count = 0

        if cutoff is None:
            cutoff = TemporalCutoff.create(current_match_date)
        if cutoff is None:
            return {"sample_size": 0, "hits": 0, "hit_rate_pct": 0.0, "cutoff_missing": True}

        for m in matches:
            if exclude_match_id is not None:
                m_id = m.get("id") or m.get("match_id")
                if m_id is not None and str(m_id).strip() == str(exclude_match_id).strip():
                    continue

            if not cutoff.allows_record(m):
                continue

            ht = (m.get("home_team") or m.get("match_title", "").split(" vs ")[0]).strip().lower()
            at = (m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")).strip().lower()

            is_home = (t_lower == ht) or (t_lower in ht)
            is_away = (t_lower == at) or (t_lower in at)

            if not (is_home or is_away):
                continue

            if role_filter == "home" and not is_home:
                continue
            if role_filter == "away" and not is_away:
                continue

            role = "home" if is_home else "away"
            hit = cls._evaluate_match_metric_pick(
                m,
                market_family,
                line=line,
                is_over=is_over,
                team_role=role,
                target_side=target_side,
                is_team_specific=is_team_specific,
            )

            if hit is not None:
                matching_count += 1
                if hit:
                    hit_count += 1

        hit_rate = (hit_count / matching_count * 100.0) if matching_count > 0 else 0.0
        return {
            "sample_size": matching_count,
            "hits": hit_count,
            "hit_rate_pct": round(hit_rate, 1)
        }

    @classmethod
    def compute_league_pick_hit_rate(
        cls,
        matches: List[Dict[str, Any]],
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        target_side: str = "home",
        exclude_match_id: Optional[Any] = None,
        current_match_date: Optional[Any] = None,
        cutoff: Optional[TemporalCutoff] = None,
        is_team_specific: bool = False,
    ) -> float:
        """
        Calcula el hit rate global a nivel de liga para un mercado específico
        para servir como prior Bayesiano.
        """
        if cutoff is None:
            cutoff = TemporalCutoff.create(current_match_date)
        if cutoff is None or not matches:
            return 0.50

        total_valid = 0
        hits = 0

        for m in matches:
            if exclude_match_id is not None:
                m_id = m.get("id") or m.get("match_id")
                if m_id is not None and str(m_id).strip() == str(exclude_match_id).strip():
                    continue

            if not cutoff.allows_record(m):
                continue

            if is_team_specific:
                h_home = cls._evaluate_match_metric_pick(
                    m, market_family, line=line, is_over=is_over, team_role="home", target_side=target_side, is_team_specific=True
                )
                if h_home is not None:
                    total_valid += 1
                    if h_home:
                        hits += 1

                h_away = cls._evaluate_match_metric_pick(
                    m, market_family, line=line, is_over=is_over, team_role="away", target_side=target_side, is_team_specific=True
                )
                if h_away is not None:
                    total_valid += 1
                    if h_away:
                        hits += 1
            else:
                h = cls._evaluate_match_metric_pick(
                    m, market_family, line=line, is_over=is_over, team_role="home", target_side=target_side, is_team_specific=False
                )
                if h is not None:
                    total_valid += 1
                    if h:
                        hits += 1

        if total_valid == 0:
            return 0.50
        return hits / total_valid

    @classmethod
    def compute_pick_hit_rate_recency(
        cls,
        matches: List[Dict[str, Any]],
        team_name: str,
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        role_filter: Optional[str] = None,  # "home", "away", or None (all)
        target_side: str = "home",
        exclude_match_id: Optional[Any] = None,
        current_match_date: Optional[Any] = None,
        cutoff: Optional[TemporalCutoff] = None,
        is_team_specific: bool = False,
        half_life: float = 10.0,
        prior_rate: Optional[float] = None,
        prior_strength: float = 12.0,
    ) -> Dict[str, Any]:
        """
        Calcula el hit rate enriquecido con ponderación por reciencia exponencial,
        suavizado Bayesiano Beta-Binomial y ventanas fijas de forma reciente (5, 10, 15).
        """
        p_rate = prior_rate if prior_rate is not None else 0.50
        p_strength = max(0.1, prior_strength)

        if cutoff is None:
            cutoff = TemporalCutoff.create(current_match_date)
        if cutoff is None:
            return {
                "sample_size": 0,
                "hits": 0,
                "hit_rate_pct": 0.0,
                "ewma_hit_rate_pct": 0.0,
                "bayesian_ewma_hit_rate_pct": round(p_rate * 100.0, 1),
                "weighted_hits": 0.0,
                "effective_sample_size": 0.0,
                "half_life": half_life,
                "prior_rate_pct": round(p_rate * 100.0, 1),
                "prior_strength": p_strength,
                "windows": {
                    "last_5": {"sample_size": 0, "hits": 0, "hit_rate_pct": 0.0},
                    "last_10": {"sample_size": 0, "hits": 0, "hit_rate_pct": 0.0},
                    "last_15": {"sample_size": 0, "hits": 0, "hit_rate_pct": 0.0},
                },
                "trend_delta_pp": 0.0,
                "trend_label": "insufficient_data",
                "cutoff_missing": True,
            }

        t_lower = team_name.strip().lower()
        valid_evaluations: List[Tuple[Any, bool]] = []

        for m in matches:
            if exclude_match_id is not None:
                m_id = m.get("id") or m.get("match_id")
                if m_id is not None and str(m_id).strip() == str(exclude_match_id).strip():
                    continue

            if not cutoff.allows_record(m):
                continue

            ht = (m.get("home_team") or m.get("match_title", "").split(" vs ")[0]).strip().lower()
            at = (m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")).strip().lower()

            is_home = (t_lower == ht) or (t_lower in ht)
            is_away = (t_lower == at) or (t_lower in at)

            if not (is_home or is_away):
                continue

            if role_filter == "home" and not is_home:
                continue
            if role_filter == "away" and not is_away:
                continue

            role = "home" if is_home else "away"
            hit = cls._evaluate_match_metric_pick(
                m,
                market_family,
                line=line,
                is_over=is_over,
                team_role=role,
                target_side=target_side,
                is_team_specific=is_team_specific,
            )

            if hit is not None:
                d_val = record_date(m)
                valid_evaluations.append((d_val, bool(hit)))

        def get_match_datetime(item):
            d = item[0]
            if d is None:
                return datetime.min
            if isinstance(d, datetime):
                return d
            if isinstance(d, str):
                try:
                    return datetime.fromisoformat(d.replace("Z", "+00:00"))
                except Exception:
                    pass
            return datetime.min

        # Ordenar del más reciente al más antiguo
        valid_evaluations.sort(key=get_match_datetime, reverse=True)

        sample_size = len(valid_evaluations)
        hits = sum(1 for _, h in valid_evaluations if h)
        season_hit_rate = (hits / sample_size) if sample_size > 0 else 0.0
        season_hit_rate_pct = round(season_hit_rate * 100.0, 1)

        half_life_val = max(1.0, half_life)
        alpha_decay = math.log(2) / half_life_val

        weighted_hits = 0.0
        effective_sample_size = 0.0

        for i, (_, hit) in enumerate(valid_evaluations):
            w = math.exp(-alpha_decay * i)
            effective_sample_size += w
            if hit:
                weighted_hits += w

        if effective_sample_size > 0:
            ewma_hit_rate = weighted_hits / effective_sample_size
        else:
            ewma_hit_rate = season_hit_rate

        ewma_hit_rate_pct = round(ewma_hit_rate * 100.0, 1)

        alpha_prior = p_rate * p_strength
        beta_prior = (1.0 - p_rate) * p_strength

        posterior_rate = (alpha_prior + weighted_hits) / (alpha_prior + beta_prior + effective_sample_size)
        bayesian_ewma_hit_rate_pct = round(posterior_rate * 100.0, 1)

        windows = {}
        for w_size in [5, 10, 15]:
            slice_w = valid_evaluations[:w_size]
            w_sample = len(slice_w)
            w_hits = sum(1 for _, h in slice_w if h)
            w_pct = round((w_hits / w_sample * 100.0), 1) if w_sample > 0 else 0.0
            windows[f"last_{w_size}"] = {
                "sample_size": w_sample,
                "hits": w_hits,
                "hit_rate_pct": w_pct,
            }

        base_ref_rate = season_hit_rate if sample_size > 0 else p_rate
        trend_delta_pp = round((posterior_rate - base_ref_rate) * 100.0, 1)

        if sample_size < 5:
            trend_label = "insufficient_data"
        elif trend_delta_pp >= 10.0:
            trend_label = "improving"
        elif trend_delta_pp <= -10.0:
            trend_label = "deteriorating"
        else:
            trend_label = "stable"

        return {
            "sample_size": sample_size,
            "hits": hits,
            "hit_rate_pct": season_hit_rate_pct,
            "ewma_hit_rate_pct": ewma_hit_rate_pct,
            "bayesian_ewma_hit_rate_pct": bayesian_ewma_hit_rate_pct,
            "weighted_hits": round(weighted_hits, 2),
            "effective_sample_size": round(effective_sample_size, 1),
            "half_life": float(half_life),
            "prior_rate_pct": round(p_rate * 100.0, 1),
            "prior_strength": float(p_strength),
            "windows": windows,
            "trend_delta_pp": trend_delta_pp,
            "trend_label": trend_label,
        }

    @classmethod
    def compute_h2h_hit_rate(
        cls,
        matches: List[Dict[str, Any]],
        home_team_name: str,
        away_team_name: str,
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        target_side: str = "home",
        exclude_match_id: Optional[Any] = None,
        current_match_date: Optional[Any] = None,
        cutoff: Optional[TemporalCutoff] = None,
        strict_venue: bool = True,
    ) -> Dict[str, Any]:
        """
        Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)
        entre ambos equipos (respetando localía/visitante estricta para 1X2 / Doble Oportunidad si strict_venue=True).
        Previene data-leakage excluyendo partidos en o posteriores a la fecha del partido actual.
        """
        h_lower = home_team_name.strip().lower()
        a_lower = away_team_name.strip().lower()
        matching_count = 0
        hit_count = 0
        total_any_venue_count = 0
        h2h_matches_list = []

        if cutoff is None:
            cutoff = TemporalCutoff.create(current_match_date)
        if cutoff is None:
            return {
                "sample_size": 0,
                "hits": 0,
                "hit_rate_pct": None,
                "h2h_matches": [],
                "cutoff_missing": True,
                "total_any_venue_count": 0,
                "strict_venue_applied": False,
            }

        fam = market_family.lower().strip()
        is_strict_venue_market = bool(strict_venue and fam in {"result", "moneyline", "1x2", "double_chance", "doublechance"})

        for m in matches:
            m_id = m.get("id") or m.get("match_id")

            if exclude_match_id is not None and m_id is not None:
                if str(m_id).strip() == str(exclude_match_id).strip():
                    continue

            if not cutoff.allows_record(m):
                continue

            date_val = record_date(m)

            ht_raw = m.get("home_team") or (m.get("match_title", "").split(" vs ")[0] if " vs " in m.get("match_title", "") else "")
            at_raw = m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")
            ht = ht_raw.strip().lower()
            at = at_raw.strip().lower()

            is_exact_fixture = ((h_lower == ht) or (h_lower in ht)) and ((a_lower == at) or (a_lower in at))
            is_reverse_fixture = ((a_lower == ht) or (a_lower in ht)) and ((h_lower == at) or (h_lower in at))

            if not (is_exact_fixture or is_reverse_fixture):
                continue

            total_any_venue_count += 1

            # Si el mercado depende estrictamente del estadio (1X2, Doble Oportunidad)
            if is_strict_venue_market and not is_exact_fixture:
                continue

            role = "home" if is_exact_fixture else "away"
            hit = cls._evaluate_match_metric_pick(
                m,
                market_family,
                line=line,
                is_over=is_over,
                team_role=role,
                target_side=target_side,
                is_team_specific=False,
            )

            if hit is not None:
                matching_count += 1
                if hit:
                    hit_count += 1

                date_str = str(date_val).replace("T", " ").split(" ")[0] if date_val else ""

                h2h_matches_list.append({
                    "date": date_str,
                    "home_team": ht_raw.strip() if ht_raw else "Home",
                    "away_team": at_raw.strip() if at_raw else "Away",
                    "score_home": m.get("final_score_home"),
                    "score_away": m.get("final_score_away"),
                    "corners_home": m.get("final_corners_home"),
                    "corners_away": m.get("final_corners_away"),
                    "cards_home": m.get("final_yellow_cards_home"),
                    "cards_away": m.get("final_yellow_cards_away"),
                    "hit": bool(hit)
                })

        hit_rate = (hit_count / matching_count * 100.0) if matching_count > 0 else None

        return {
            "sample_size": matching_count,
            "hits": hit_count,
            "hit_rate_pct": round(hit_rate, 1) if hit_rate is not None else None,
            "h2h_matches": h2h_matches_list,
            "total_any_venue_count": total_any_venue_count,
            "strict_venue_applied": is_strict_venue_market,
        }