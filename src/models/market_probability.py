"""
Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),
Closing Line Value (CLV), combinación ponderada por fiabilidad y guardrails de divergencia.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


def implied_probability(odds: float) -> float:
    """Calcula la probabilidad implícita de una cuota decimal (1 / odds)."""
    if odds <= 1.0:
        raise ValueError("Las cuotas deben ser mayores a 1.0")
    return 1.0 / float(odds)


def remove_vig_two_way(odds_a: float, odds_b: float) -> Tuple[float, float]:
    """Elimina el margen (vigorish) de un mercado de 2 opciones por método proporcional."""
    if odds_a <= 1.0 or odds_b <= 1.0:
        raise ValueError("Cuotas inválidas para mercado 2-way")
    p_a = implied_probability(odds_a)
    p_b = implied_probability(odds_b)
    overround = p_a + p_b
    if overround <= 0:
        raise ValueError("Overround nulo o negativo")
    return p_a / overround, p_b / overround


def remove_vig_three_way(home: float, draw: float, away: float) -> Tuple[float, float, float]:
    """Elimina el margen (vigorish) de un mercado 1X2 por método proporcional."""
    if home <= 1.0 or draw <= 1.0 or away <= 1.0:
        raise ValueError("Cuotas inválidas para mercado 3-way")
    p_h = implied_probability(home)
    p_d = implied_probability(draw)
    p_a = implied_probability(away)
    overround = p_h + p_d + p_a
    if overround <= 0:
        raise ValueError("Overround nulo o negativo")
    return p_h / overround, p_d / overround, p_a / overround


@dataclass(frozen=True)
class CLVResult:
    open_odds: float
    close_odds: float
    clv_percent: float  # (close_odds / open_odds - 1) * 100
    clv_log: float      # log(open_prob / close_prob)
    market_prob_open_no_vig: Optional[float] = None
    market_prob_close_no_vig: Optional[float] = None
    market_margin_open: Optional[float] = None
    market_margin_close: Optional[float] = None


def compute_clv(
    open_odds: float,
    close_odds: float,
    open_opposite_odds: Optional[float] = None,
    close_opposite_odds: Optional[float] = None,
) -> CLVResult:
    """Calcula las métricas de Closing Line Value (CLV)."""
    if open_odds <= 1.0 or close_odds <= 1.0:
        raise ValueError("Cuotas de apertura y cierre deben ser mayores a 1.0")

    clv_pct = ((open_odds / close_odds) - 1.0) * 100.0
    p_open_raw = implied_probability(open_odds)
    p_close_raw = implied_probability(close_odds)
    clv_log = math.log(p_open_raw / p_close_raw) if (p_open_raw > 0 and p_close_raw > 0) else 0.0

    p_open_novig = None
    margin_open = None
    if open_opposite_odds and open_opposite_odds > 1.0:
        p_open_novig, _ = remove_vig_two_way(open_odds, open_opposite_odds)
        margin_open = (implied_probability(open_odds) + implied_probability(open_opposite_odds)) - 1.0

    p_close_novig = None
    margin_close = None
    if close_opposite_odds and close_opposite_odds > 1.0:
        p_close_novig, _ = remove_vig_two_way(close_odds, close_opposite_odds)
        margin_close = (implied_probability(close_odds) + implied_probability(close_opposite_odds)) - 1.0

    return CLVResult(
        open_odds=open_odds,
        close_odds=close_odds,
        clv_percent=clv_pct,
        clv_log=clv_log,
        market_prob_open_no_vig=p_open_novig,
        market_prob_close_no_vig=p_close_novig,
        market_margin_open=margin_open,
        market_margin_close=margin_close,
    )


@dataclass(frozen=True)
class BlendResult:
    final_prob: float
    reliability_weight: float
    market_prob: Optional[float]
    divergence: float
    divergence_warning: bool
    divergence_blocked: bool
    stake_multiplier: float


def blend_model_and_market_probability(
    p_calibrated: float,
    p_market_no_vig: Optional[float],
    reliability_score: float,
    data_quality_factor: float = 1.0,
    calibration_confidence: float = 1.0,
    divergence_warn_threshold: float = 0.15,
    divergence_block_threshold: float = 0.25,
    has_strong_oof_evidence: bool = False,
) -> BlendResult:
    """
    Mezcla controlada: p_final = r * p_calibrated + (1 - r) * p_market
    donde r = reliability_score * data_quality_factor * calibration_confidence
    """
    p_cal = min(1.0, max(0.0, p_calibrated))

    if p_market_no_vig is None:
        # Sin mercado, se usa la calibrada reduciendo el peso/fiabilidad
        r = max(0.0, min(1.0, reliability_score * 0.7 * data_quality_factor))
        return BlendResult(
            final_prob=p_cal,
            reliability_weight=r,
            market_prob=None,
            divergence=0.0,
            divergence_warning=False,
            divergence_blocked=False,
            stake_multiplier=0.8,
        )

    p_mkt = min(1.0, max(0.0, p_market_no_vig))
    r = max(0.0, min(1.0, reliability_score * data_quality_factor * calibration_confidence))

    p_final = r * p_cal + (1.0 - r) * p_mkt
    divergence = abs(p_cal - p_mkt)

    warn = divergence > divergence_warn_threshold
    block = divergence > divergence_block_threshold and not has_strong_oof_evidence

    multiplier = 1.0
    if block:
        multiplier = 0.0
    elif warn:
        multiplier = max(0.25, 1.0 - (divergence - divergence_warn_threshold) * 3.0)

    return BlendResult(
        final_prob=p_final,
        reliability_weight=r,
        market_prob=p_mkt,
        divergence=divergence,
        divergence_warning=warn,
        divergence_blocked=block,
        stake_multiplier=multiplier,
    )
