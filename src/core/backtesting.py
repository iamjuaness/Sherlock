"""
Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.

Implementa la estructura de validación temporal expansiva (rolling-origin)
para evaluar combinaciones de hiperparámetros (half-life de liga, half-life de equipo,
límite de partidos y fuerza de prior) sin data leakage.
"""

from __future__ import annotations

import math
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from src.core.math_engine import (
    LeagueMathEngine,
    calculate_time_decay_weight,
    estimate_nb_dispersion,
    get_league_profile,
    LEAGUE_HISTORY_PROFILES,
)
from src.domain.temporal import parse_utc, record_date

logger = logging.getLogger("sherlock.backtesting")


def compute_log_loss(y_true: List[int], y_prob: List[float], eps: float = 1e-15) -> float:
    """Calcula la pérdida logarítmica (Log Loss) binaria."""
    if not y_true or len(y_true) != len(y_prob):
        return 0.0

    total = 0.0
    n = len(y_true)
    for y, p in zip(y_true, y_prob):
        p_clamped = max(eps, min(1.0 - eps, p))
        total += y * math.log(p_clamped) + (1 - y) * math.log(1.0 - p_clamped)
    return -total / n


def compute_brier_score(y_true: List[int], y_prob: List[float]) -> float:
    """Calcula el Brier Score (error cuadrático medio de la probabilidad)."""
    if not y_true or len(y_true) != len(y_prob):
        return 0.0

    n = len(y_true)
    return sum((p - y) ** 2 for y, p in zip(y_true, y_prob)) / n


def compute_calibration_curve(
    y_true: List[int],
    y_prob: List[float],
    n_bins: int = 10,
) -> List[Dict[str, float]]:
    """
    Calcula la curva de calibración dividiendo [0, 1] en n_bins y evaluando
    la frecuencia observada frente a la probabilidad media predicha.
    """
    if not y_true or len(y_true) != len(y_prob):
        return []

    bins = [{"count": 0, "sum_prob": 0.0, "sum_true": 0} for _ in range(n_bins)]
    bin_width = 1.0 / n_bins

    for y, p in zip(y_true, y_prob):
        idx = min(n_bins - 1, int(p / bin_width))
        bins[idx]["count"] += 1
        bins[idx]["sum_prob"] += p
        bins[idx]["sum_true"] += y

    calibration_result = []
    for i, b in enumerate(bins):
        if b["count"] > 0:
            mean_prob = b["sum_prob"] / b["count"]
            observed_freq = b["sum_true"] / b["count"]
        else:
            mean_prob = (i + 0.5) * bin_width
            observed_freq = 0.0

        calibration_result.append({
            "bin": i,
            "bin_lower": round(i * bin_width, 2),
            "bin_upper": round((i + 1) * bin_width, 2),
            "count": b["count"],
            "mean_predicted_prob": round(mean_prob, 4),
            "observed_frequency": round(observed_freq, 4),
        })

    return calibration_result


def calculate_roi_and_yield(
    predictions: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calcula el ROI y Yield si hay cuotas históricas disponibles.
    `predictions` debe contener: `is_correct` (bool), `odds` (float > 1.0), `stake` (float).
    """
    total_staked = 0.0
    total_returned = 0.0
    bets_count = 0

    for pred in predictions:
        odds = pred.get("odds")
        if odds is None or odds <= 1.0:
            continue

        stake = float(pred.get("stake", 1.0))
        is_correct = bool(pred.get("is_correct", False))

        total_staked += stake
        bets_count += 1
        if is_correct:
            total_returned += stake * float(odds)

    if total_staked <= 0:
        return {"bets_count": 0, "total_staked": 0.0, "total_profit": 0.0, "roi_pct": 0.0, "yield_pct": 0.0}

    profit = total_returned - total_staked
    roi_pct = (profit / total_staked) * 100.0

    return {
        "bets_count": bets_count,
        "total_staked": round(total_staked, 2),
        "total_profit": round(profit, 2),
        "roi_pct": round(roi_pct, 2),
        "yield_pct": round(roi_pct, 2),
    }


class TemporalParameterOptimizer:
    """
    Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de partidos ordenados temporalmente.
    """

    DEFAULT_GRID = {
        "league_prior_half_life_days": [180.0, 270.0, 365.0, 420.0, 540.0, 600.0],
        "team_half_life_matches": [10.0, 12.5, 15.0, 17.5, 20.0, 25.0],
        "team_max_matches": [20, 30, 40, 50],
        "league_prior_strength": [12.0, 18.0, 24.0, 28.0],
    }

    def __init__(self, matches: List[Dict[str, Any]], competition_id: Optional[Any] = None, market: str = "goals"):
        self.raw_matches = matches
        self.competition_id = str(competition_id) if competition_id else "unknown"
        self.market = market

        # Ordenar strictly por fecha
        self.sorted_matches = []
        for m in matches:
            d = record_date(m)
            if d is not None:
                self.sorted_matches.append((d, m))
        self.sorted_matches.sort(key=lambda x: x[0])

    def run_grid_search(
        self,
        grid: Optional[Dict[str, List[Any]]] = None,
        min_history_matches: int = 30,
        limit_combinations: int = 50,
    ) -> Dict[str, Any]:
        """
        Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling origin).
        """
        param_grid = grid or self.DEFAULT_GRID
        
        l_hl_list = param_grid.get("league_prior_half_life_days", [420.0])
        t_hl_list = param_grid.get("team_half_life_matches", [17.5])
        t_max_list = param_grid.get("team_max_matches", [40])
        l_str_list = param_grid.get("league_prior_strength", [18.0])

        combinations = []
        for l_hl in l_hl_list:
            for t_hl in t_hl_list:
                for t_max in t_max_list:
                    for l_str in l_str_list:
                        combinations.append({
                            "league_prior_half_life_days": float(l_hl),
                            "team_half_life_matches": float(t_hl),
                            "team_max_matches": int(t_max),
                            "league_prior_strength": float(l_str),
                        })

        if len(combinations) > limit_combinations:
            combinations = combinations[:limit_combinations]

        results = []
        exec_timestamp = datetime.now(timezone.utc).isoformat()

        for idx, params in enumerate(combinations):
            eval_metrics = self.evaluate_parameters(params, min_history_matches=min_history_matches)
            param_version = f"v{idx + 1}-{int(params['league_prior_half_life_days'])}d-{params['team_half_life_matches']}m"
            
            record = {
                "competition_id": self.competition_id,
                "market": self.market,
                "param_version": param_version,
                "parameters": params,
                "execution_timestamp": exec_timestamp,
                "metrics": eval_metrics,
            }
            results.append(record)

        results.sort(key=lambda r: r["metrics"]["log_loss"])

        best = results[0] if results else None
        return {
            "competition_id": self.competition_id,
            "market": self.market,
            "total_evaluated": len(results),
            "execution_timestamp": exec_timestamp,
            "best_parameters": best["parameters"] if best else None,
            "best_metrics": best["metrics"] if best else None,
            "all_results": results,
        }

    def evaluate_parameters(
        self,
        params: Dict[str, Any],
        min_history_matches: int = 30,
    ) -> Dict[str, Any]:
        """
        Evalúa un conjunto específico de parámetros usando rolling origin sobre `sorted_matches`.
        """
        if len(self.sorted_matches) <= min_history_matches:
            return {
                "sample_size": 0,
                "effective_sample_size": 0.0,
                "log_loss": 99.0,
                "brier_score": 1.0,
                "hit_rate_pct": 0.0,
                "calibration": [],
                "roi": {"bets_count": 0, "roi_pct": 0.0},
            }

        y_true = []
        y_prob = []
        eval_records = []
        math_engine = LeagueMathEngine()

        l_hl = params["league_prior_half_life_days"]
        t_hl = params["team_half_life_matches"]
        t_max = params["team_max_matches"]

        for i in range(min_history_matches, len(self.sorted_matches)):
            ref_dt, current_match = self.sorted_matches[i]
            history = [m for _, m in self.sorted_matches[:i]]

            avgs = math_engine.compute_league_averages(
                historical_matches=history,
                reference_date=ref_dt,
                half_life_days=l_hl,
                min_effective_sample_size=15.0,
            )

            sh = current_match.get("final_score_home")
            sa = current_match.get("final_score_away")
            if sh is None or sa is None:
                continue

            total_goals = float(sh) + float(sa)
            actual_over25 = 1 if total_goals > 2.5 else 0

            l_home = avgs.get("home_goals", 1.45)
            mu_away = avgs.get("away_goals", 1.15)
            expected_total = l_home + mu_away

            p0 = math.exp(-expected_total)
            p1 = p0 * expected_total
            p2 = p1 * expected_total / 2.0
            prob_under25 = p0 + p1 + p2
            prob_over25 = max(0.01, min(0.99, 1.0 - prob_under25))

            y_true.append(actual_over25)
            y_prob.append(prob_over25)

            odds = current_match.get("odds_over25") or current_match.get("closing_odds_over25")
            eval_records.append({
                "is_correct": (actual_over25 == 1 and prob_over25 > 0.5) or (actual_over25 == 0 and prob_over25 <= 0.5),
                "odds": odds,
                "stake": 1.0,
            })

        if not y_true:
            return {
                "sample_size": 0,
                "effective_sample_size": 0.0,
                "log_loss": 99.0,
                "brier_score": 1.0,
                "hit_rate_pct": 0.0,
                "calibration": [],
                "roi": {"bets_count": 0, "roi_pct": 0.0},
            }

        ll = compute_log_loss(y_true, y_prob)
        bs = compute_brier_score(y_true, y_prob)
        cal = compute_calibration_curve(y_true, y_prob)
        roi_stats = calculate_roi_and_yield(eval_records)
        hits = sum(1 for y, p in zip(y_true, y_prob) if (y == 1 and p > 0.5) or (y == 0 and p <= 0.5))

        return {
            "sample_size": len(y_true),
            "effective_sample_size": round((sum(y_prob) ** 2) / max(1e-5, sum(p ** 2 for p in y_prob)), 2),
            "log_loss": round(ll, 4),
            "brier_score": round(bs, 4),
            "hit_rate_pct": round((hits / len(y_true)) * 100.0, 2),
            "calibration": cal,
            "roi": roi_stats,
        }
