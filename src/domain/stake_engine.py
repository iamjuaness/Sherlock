"""
Motor de stake y gestión de riesgo institucional de Sherlock.

Sustituye la aproximación Bernoulli por optimización sobre la distribución
completa de retornos (ReturnDistribution) e implementa escalado de portafolio
simultáneo y contracción estadística del edge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from src.domain.settlement import ReturnDistribution


_DEFAULT_POLICY_PATH = "data/risk_policy.json"


@dataclass(frozen=True)
class RiskPolicy:
    """Política de riesgo profesional con soporte de drawdown y portafolio."""

    version: str = "3.0"
    kelly_fraction: float = 0.25
    min_stake: float = 0.005
    max_stake: float = 0.05
    max_total_exposure: float = 0.25  # Exposición total máxima simultánea
    max_stake_per_match: float = 0.08
    max_stake_per_league: float = 0.12
    max_stake_per_segment: float = 0.06
    max_stake_per_cluster: float = 0.10
    min_reliability_to_publish: float = 0.40
    experimental_stake_cap: float = 0.015
    segment_overrides: Dict[str, Dict] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str = _DEFAULT_POLICY_PATH) -> "RiskPolicy":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            gl = data.get("global_limits", {})
            return cls(
                version=data.get("version", "3.0"),
                kelly_fraction=float(gl.get("kelly_fraction", 0.25)),
                min_stake=float(gl.get("min_stake_units", 0.005)),
                max_stake=float(gl.get("max_stake_units", 0.05)),
                max_total_exposure=float(gl.get("max_total_exposure", 0.25)),
                max_stake_per_match=float(gl.get("max_stake_per_match", 0.08)),
                max_stake_per_league=float(gl.get("max_stake_per_league", 0.12)),
                max_stake_per_segment=float(gl.get("max_stake_per_segment", 0.06)),
                max_stake_per_cluster=float(gl.get("max_stake_per_cluster", 0.06)),
                min_reliability_to_publish=float(gl.get("min_reliability_score", 0.40)),
                experimental_stake_cap=float(gl.get("experimental_stake_cap", 0.015)),
                segment_overrides=data.get("segment_status_overrides", {}),
            )
        except Exception:
            return cls()


@dataclass(frozen=True)
class EdgeResult:
    edge_raw: float
    edge_calibrated: float
    edge_final: float
    breakeven_prob: float
    odds: float
    p_model_raw: Optional[float]
    p_calibrated: Optional[float]
    p_final: float


def compute_edge(
    p_final: float,
    odds: float,
    p_model_raw: Optional[float] = None,
    p_calibrated: Optional[float] = None,
) -> EdgeResult:
    if odds <= 1.0:
        raise ValueError(f"Cuotas inválidas: {odds}")

    be = 1.0 / odds

    def _edge(p: Optional[float]) -> float:
        if p is None:
            return 0.0
        return (p * odds - 1.0) * 100.0

    return EdgeResult(
        edge_raw=_edge(p_model_raw),
        edge_calibrated=_edge(p_calibrated),
        edge_final=_edge(p_final),
        breakeven_prob=be,
        odds=odds,
        p_model_raw=p_model_raw,
        p_calibrated=p_calibrated,
        p_final=p_final,
    )


def compute_distribution_kelly(
    distribution: Optional[ReturnDistribution],
    odds: float,
    p_final: float,
    multiplier: float = 0.25,
    hard_cap: float = 0.25,
) -> float:
    """Calcula Kelly utilizando la distribución completa de outcomes si existe."""
    if odds <= 1.0 or p_final <= 0.0:
        return 0.0

    if distribution is not None:
        return distribution.kelly_fraction(multiplier=multiplier, hard_cap=hard_cap)

    # Fallback si no hay distribución multi-resultado (Bernoulli estándar)
    b = odds - 1.0
    p = p_final
    q = 1.0 - p
    f_star = (b * p - q) / b
    if f_star <= 0.0:
        return 0.0
    return round(min(f_star * multiplier, hard_cap), 6)


def kelly_fractional(p: float, odds: float, fraction: float = 0.25, hard_cap: float = 1.0) -> float:
    """Función directa de Kelly Bernoulli fraccionado."""
    return compute_distribution_kelly(None, odds=odds, p_final=p, multiplier=fraction, hard_cap=hard_cap)



@dataclass(frozen=True)
class StakeFactors:
    kelly_base: float
    reliability_score: float
    data_quality_factor: float = 1.0
    drift_factor: float = 1.0
    correlation_factor: float = 1.0
    exposure_factor: float = 1.0
    governance_multiplier: float = 1.0
    segment_status: str = "active"


def compute_stake_final(
    factors: StakeFactors,
    policy: RiskPolicy,
    existing_match_stake: float = 0.0,
    existing_league_stake: float = 0.0,
    existing_segment_stake: float = 0.0,
    existing_cluster_stake: float = 0.0,
    current_drawdown_pct: float = 0.0,
) -> Tuple[float, str]:
    """
    Calcula el stake final aplicando ajuste de factores, drawdown scale y límites.
    """
    if factors.reliability_score < policy.min_reliability_to_publish:
        return 0.0, (
            f"reliability_score ({factors.reliability_score:.3f}) < "
            f"threshold ({policy.min_reliability_to_publish})"
        )

    if factors.governance_multiplier <= 0.0:
        return 0.0, "governance_blocked"

    # Reducción por Drawdown (Half-Kelly escalado al caer el drawdown)
    dd_scale = 1.0
    if current_drawdown_pct > 0.15:
        dd_scale = max(0.20, 1.0 - (current_drawdown_pct * 2.0))

    # Multiplicación directa de todos los factores: stake = kelly × R × Q × D × C × E × G
    # Cada factor actúa como penalización independiente; la multiplicación directa
    # es fiel al contrato matemático y evita que la media geométrica inflacione el resultado.
    composite_factor = (
        max(0.01, factors.reliability_score)
        * max(0.01, factors.data_quality_factor)
        * max(0.01, factors.drift_factor)
        * max(0.01, factors.correlation_factor)
        * max(0.01, factors.exposure_factor)
    )

    raw = factors.kelly_base * composite_factor * factors.governance_multiplier * dd_scale

    if factors.segment_status == "experimental":
        raw = min(raw, policy.experimental_stake_cap)

    # Límites por contexto
    avail_match = max(0.0, policy.max_stake_per_match - existing_match_stake)
    avail_league = max(0.0, policy.max_stake_per_league - existing_league_stake)
    avail_segment = max(0.0, policy.max_stake_per_segment - existing_segment_stake)
    avail_cluster = max(0.0, policy.max_stake_per_cluster - existing_cluster_stake)

    context_cap = min(avail_match, avail_league, avail_segment, avail_cluster)
    limited = min(raw, context_cap, policy.max_stake)

    if limited < policy.min_stake:
        return 0.0, f"stake ({limited:.4f}) < min_stake ({policy.min_stake})"

    reason = "ok"
    if limited < raw:
        reason = f"capped from {raw:.4f} to {limited:.4f} by context/policy"

    return round(limited, 5), reason


def optimize_simultaneous_portfolio(
    proposals: Sequence[Tuple[RiskDecision, float]],
    policy: RiskPolicy,
) -> List[RiskDecision]:
    """
    Escala proporcionalmente las apuestas simultáneas para respetar la exposición global máxima.

    .. deprecated::
        Esta función opera sobre ``RiskDecision`` y no está conectada al pipeline de
        producción (detectado por graphify: degree=4, sin callers externos).
        Para el pipeline real de ``compare_football()`` usar:
            ``src.domain.portfolio.apply_portfolio_exposure_cap()``
        que opera sobre ``ValueIndicator`` con kelly_fraction como métrica de exposición.

        Se mantiene como API de dominio puro para pipelines de backtesting que construyan
        portfolios a partir de ``RiskDecision`` directamente.
    """
    total_requested = sum(dec.stake_final for dec, _ in proposals)
    if total_requested <= policy.max_total_exposure or total_requested == 0.0:
        return [dec for dec, _ in proposals]

    scale = policy.max_total_exposure / total_requested
    adjusted_decisions: List[RiskDecision] = []

    for dec, _ in proposals:
        scaled_stake = round(dec.stake_final * scale, 5)
        if scaled_stake < policy.min_stake:
            dec.stake_final = 0.0
            dec.is_publishable = False
            dec.block_reason = f"scaled_below_min_stake ({scaled_stake:.4f})"
        else:
            dec.stake_final = scaled_stake
            dec.stake_reason = f"portfolio_scaled (factor: {scale:.3f})"
        adjusted_decisions.append(dec)

    return adjusted_decisions


@dataclass
class RiskDecision:
    p_model_raw: Optional[float]
    p_calibrated: Optional[float]
    p_market_no_vig: Optional[float]
    p_final: float
    edge_raw: float
    edge_calibrated: float
    edge_final: float
    kelly_base: float
    stake_pre_risk: float
    stake_final: float
    stake_reason: str
    reliability_score: float
    data_quality_factor: float
    drift_factor: float
    correlation_factor: float
    exposure_factor: float
    governance_multiplier: float
    segment_status: str
    policy_version: str
    is_publishable: bool
    block_reason: Optional[str] = None


def compute_risk_decision(
    p_final: float,
    odds: float,
    policy: RiskPolicy,
    factors: StakeFactors,
    distribution: Optional[ReturnDistribution] = None,
    p_model_raw: Optional[float] = None,
    p_calibrated: Optional[float] = None,
    p_market_no_vig: Optional[float] = None,
    existing_match_stake: float = 0.0,
    existing_league_stake: float = 0.0,
    existing_segment_stake: float = 0.0,
    existing_cluster_stake: float = 0.0,
    current_drawdown_pct: float = 0.0,
) -> RiskDecision:
    """Punto de entrada principal del motor de riesgo."""
    edge = compute_edge(p_final, odds, p_model_raw, p_calibrated)

    # Si kelly_base no se suministró precalculado, resolverlo con la distribución
    kelly_base = factors.kelly_base
    if kelly_base <= 0.0 and edge.edge_final > 0.0:
        kelly_base = compute_distribution_kelly(
            distribution=distribution,
            odds=odds,
            p_final=p_final,
            multiplier=policy.kelly_fraction,
            hard_cap=policy.max_stake,
        )

    updated_factors = StakeFactors(
        kelly_base=kelly_base,
        reliability_score=factors.reliability_score,
        data_quality_factor=factors.data_quality_factor,
        drift_factor=factors.drift_factor,
        correlation_factor=factors.correlation_factor,
        exposure_factor=factors.exposure_factor,
        governance_multiplier=factors.governance_multiplier,
        segment_status=factors.segment_status,
    )

    stake_final, reason = compute_stake_final(
        factors=updated_factors,
        policy=policy,
        existing_match_stake=existing_match_stake,
        existing_league_stake=existing_league_stake,
        existing_segment_stake=existing_segment_stake,
        existing_cluster_stake=existing_cluster_stake,
        current_drawdown_pct=current_drawdown_pct,
    )

    publishable = (
        stake_final > 0.0
        and edge.edge_final > 0.0
        and updated_factors.governance_multiplier > 0.0
    )

    block_reason = None
    if not publishable:
        if updated_factors.governance_multiplier == 0.0:
            block_reason = "governance_blocked"
        elif stake_final == 0.0:
            block_reason = reason
        elif edge.edge_final <= 0.0:
            block_reason = "no_positive_edge"

    return RiskDecision(
        p_model_raw=p_model_raw,
        p_calibrated=p_calibrated,
        p_market_no_vig=p_market_no_vig,
        p_final=p_final,
        edge_raw=edge.edge_raw,
        edge_calibrated=edge.edge_calibrated,
        edge_final=edge.edge_final,
        kelly_base=updated_factors.kelly_base,
        stake_pre_risk=updated_factors.kelly_base,
        stake_final=stake_final,
        stake_reason=reason,
        reliability_score=updated_factors.reliability_score,
        data_quality_factor=updated_factors.data_quality_factor,
        drift_factor=updated_factors.drift_factor,
        correlation_factor=updated_factors.correlation_factor,
        exposure_factor=updated_factors.exposure_factor,
        governance_multiplier=updated_factors.governance_multiplier,
        segment_status=updated_factors.segment_status,
        policy_version=policy.version,
        is_publishable=publishable,
        block_reason=block_reason,
    )