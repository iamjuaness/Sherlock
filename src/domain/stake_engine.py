"""
Motor de stake y gestión de riesgo.

Implementa el cálculo completo de stake según la política del planning.txt §12:

    stake_final =
        stake_kelly_fractional
        × reliability_score
        × data_quality_factor
        × drift_factor
        × correlation_factor
        × exposure_factor

Con los siguientes límites:
- Stake mínimo / máximo global
- Stake máximo por partido
- Stake máximo por liga
- Stake máximo por segmento
- Stake máximo por cluster correlacionado
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Configuración de política de riesgo
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_POLICY_PATH = "data/risk_policy.json"


@dataclass(frozen=True)
class RiskPolicy:
    """
    Política de riesgo versionada.

    Todos los stakes están en unidades de bankroll (0.0-1.0).
    """

    version: str = "1.0"

    # Kelly fraccional global
    kelly_fraction: float = 0.25

    # Límites globales de stake (unidades de bankroll)
    min_stake: float = 0.005
    max_stake: float = 0.05

    # Límites por contexto
    max_stake_per_match: float = 0.08
    max_stake_per_league: float = 0.12
    max_stake_per_segment: float = 0.06
    max_stake_per_cluster: float = 0.10

    # Umbrales de reliability
    min_reliability_to_publish: float = 0.40
    experimental_stake_cap: float = 0.015

    # Overrides por segmento (cargados desde JSON)
    segment_overrides: Dict[str, Dict] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str = _DEFAULT_POLICY_PATH) -> "RiskPolicy":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            overrides = {k: v for k, v in data.get("segment_overrides", {}).items()}
            return cls(
                version=data.get("version", "1.0"),
                kelly_fraction=data.get("kelly_fraction", 0.25),
                min_stake=data.get("min_stake", 0.005),
                max_stake=data.get("max_stake", 0.05),
                max_stake_per_match=data.get("max_stake_per_match", 0.08),
                max_stake_per_league=data.get("max_stake_per_league", 0.12),
                max_stake_per_segment=data.get("max_stake_per_segment", 0.06),
                max_stake_per_cluster=data.get("max_stake_per_cluster", 0.10),
                min_reliability_to_publish=data.get("min_reliability_to_publish", 0.40),
                experimental_stake_cap=data.get("experimental_stake_cap", 0.015),
                segment_overrides=overrides,
            )
        except Exception:
            return cls()


# ═══════════════════════════════════════════════════════════════════════════
# Edge: raw / calibrado / final
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EdgeResult:
    """Descomposición del edge según probabilidades disponibles."""

    edge_raw: float           # edge con p_model cruda (sin calibrar)
    edge_calibrated: float    # edge con p_calibrated (output del calibrador)
    edge_final: float         # edge con p_final (blend modelo + mercado)
    breakeven_prob: float     # 1/odds
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
    """
    Calcula las tres versiones de edge.

    El edge definitivo (edge_final) usa SIEMPRE p_final, nunca el modelo crudo.
    """
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


# ═══════════════════════════════════════════════════════════════════════════
# Kelly fraccionado
# ═══════════════════════════════════════════════════════════════════════════

def kelly_fractional(
    p: float,
    odds: float,
    fraction: float = 0.25,
) -> float:
    """
    Criterio de Kelly fraccionado.

    stake = fraction * (p * odds - 1) / (odds - 1)

    Retorna 0.0 si Kelly es negativo (sin edge real).
    """
    if odds <= 1.0 or p <= 0.0 or p >= 1.0:
        return 0.0
    b = odds - 1.0
    kelly_full = (p * odds - 1.0) / b
    return max(0.0, kelly_full * fraction)


# ═══════════════════════════════════════════════════════════════════════════
# Factores de ajuste de stake
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StakeFactors:
    """Todos los factores multiplicativos del stake final."""

    kelly_base: float                  # Kelly fraccionado base
    reliability_score: float           # [0, 1]
    data_quality_factor: float         # [0, 1]
    drift_factor: float                # [0, 1] -> 1.0 = sin drift
    correlation_factor: float          # [0, 1] -> 1.0 = sin correlación
    exposure_factor: float             # [0, 1] -> 1.0 = sin exposición
    governance_multiplier: float       # [0, 1] de segment_governance
    segment_status: str = "active"


def compute_stake_final(
    factors: StakeFactors,
    policy: RiskPolicy,
    existing_match_stake: float = 0.0,
    existing_league_stake: float = 0.0,
    existing_segment_stake: float = 0.0,
    existing_cluster_stake: float = 0.0,
) -> Tuple[float, str]:
    """
    Calcula el stake final aplicando todos los factores y límites.

    Retorna (stake_final, reason) donde reason explica si se limitó.
    """
    # 0. Reliability mínima
    if factors.reliability_score < policy.min_reliability_to_publish:
        return 0.0, f"reliability_score ({factors.reliability_score:.3f}) < threshold ({policy.min_reliability_to_publish})"

    # 1. Multiplicación de factores
    raw = (
        factors.kelly_base
        * factors.reliability_score
        * factors.data_quality_factor
        * factors.drift_factor
        * factors.correlation_factor
        * factors.exposure_factor
        * factors.governance_multiplier
    )

    # 2. Cap de segmento experimental
    if factors.segment_status == "experimental":
        raw = min(raw, policy.experimental_stake_cap)

    # 3. Límites por contexto (exposure)
    available_match = max(0.0, policy.max_stake_per_match - existing_match_stake)
    available_league = max(0.0, policy.max_stake_per_league - existing_league_stake)
    available_segment = max(0.0, policy.max_stake_per_segment - existing_segment_stake)
    available_cluster = max(0.0, policy.max_stake_per_cluster - existing_cluster_stake)

    context_cap = min(available_match, available_league, available_segment, available_cluster)
    limited = min(raw, context_cap, policy.max_stake)

    # 4. Límite mínimo
    if limited < policy.min_stake:
        return 0.0, f"stake ({limited:.4f}) < min_stake ({policy.min_stake})"

    reason = "ok"
    if limited < raw:
        reason = f"capped from {raw:.4f} to {limited:.4f} by context/policy"

    return limited, reason


# ═══════════════════════════════════════════════════════════════════════════
# Resultado de riesgo completo
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RiskDecision:
    """
    Resultado completo del motor de riesgo para un pick.

    Incluye todos los campos de trazabilidad requeridos por la Fase 13.
    """

    # Probabilidades
    p_model_raw: Optional[float]
    p_calibrated: Optional[float]
    p_market_no_vig: Optional[float]
    p_final: float

    # Edge
    edge_raw: float
    edge_calibrated: float
    edge_final: float

    # Stake
    kelly_base: float
    stake_pre_risk: float      # antes de factores de ajuste
    stake_final: float
    stake_reason: str

    # Factores
    reliability_score: float
    data_quality_factor: float
    drift_factor: float
    correlation_factor: float
    exposure_factor: float
    governance_multiplier: float

    # Metadatos de decisión
    segment_status: str
    policy_version: str
    is_publishable: bool
    block_reason: Optional[str] = None


def compute_risk_decision(
    p_final: float,
    odds: float,
    policy: RiskPolicy,
    factors: StakeFactors,
    p_model_raw: Optional[float] = None,
    p_calibrated: Optional[float] = None,
    p_market_no_vig: Optional[float] = None,
    existing_match_stake: float = 0.0,
    existing_league_stake: float = 0.0,
    existing_segment_stake: float = 0.0,
    existing_cluster_stake: float = 0.0,
) -> RiskDecision:
    """
    Punto de entrada principal del motor de riesgo.

    Produce un RiskDecision con toda la trazabilidad requerida.
    """
    edge = compute_edge(p_final, odds, p_model_raw, p_calibrated)

    stake_final, reason = compute_stake_final(
        factors=factors,
        policy=policy,
        existing_match_stake=existing_match_stake,
        existing_league_stake=existing_league_stake,
        existing_segment_stake=existing_segment_stake,
        existing_cluster_stake=existing_cluster_stake,
    )

    publishable = (
        stake_final > 0.0
        and edge.edge_final > 0.0
        and factors.governance_multiplier > 0.0
    )

    block_reason = None
    if not publishable:
        if factors.governance_multiplier == 0.0:
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
        kelly_base=factors.kelly_base,
        stake_pre_risk=factors.kelly_base,
        stake_final=stake_final,
        stake_reason=reason,
        reliability_score=factors.reliability_score,
        data_quality_factor=factors.data_quality_factor,
        drift_factor=factors.drift_factor,
        correlation_factor=factors.correlation_factor,
        exposure_factor=factors.exposure_factor,
        governance_multiplier=factors.governance_multiplier,
        segment_status=factors.segment_status,
        policy_version=policy.version,
        is_publishable=publishable,
        block_reason=block_reason,
    )
