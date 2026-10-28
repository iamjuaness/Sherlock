"""
Módulo para la separación entre prediction_universe y selected_portfolio.

Expone dos funciones de scaling de exposición:
  · filter_selected_portfolio  → opera sobre PredictionRecord (dominio puro)
  · apply_portfolio_exposure_cap → opera sobre ValueIndicator (pipeline compare.py)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    # Importación tardía para evitar dependencias circulares con compare.py
    from src.ui.api.compare import ValueIndicator

logger = logging.getLogger("sherlock.portfolio")


@dataclass
class PredictionRecord:
    """Registro completo de una predicción evaluada en el universo de predicciones."""

    analysis_id: str
    match_id: str
    prediction_timestamp: str
    kickoff_timestamp: str
    league: str
    league_normalized: str
    home_team: str
    away_team: str
    market_family: str
    market_side: str
    selection: str
    model_prob_raw: float
    model_prob_calibrated: float
    final_prob: float
    edge_raw: float
    edge_calibrated: float
    edge_final: float
    expected_value: float
    kelly_raw: float
    stake_pre_risk: float
    stake_final: float
    publishable: bool
    eligibility_decision: str

    settlement_timestamp: Optional[str] = None
    market_line: Optional[float] = None
    line_bucket: Optional[str] = None
    odds_open: Optional[float] = None
    odds_close: Optional[float] = None
    market_prob_no_vig: Optional[float] = None

    block_reasons: List[str] = field(default_factory=list)
    data_quality_score: float = 1.0
    reliability_score: float = 1.0
    reliability_components: Dict[str, float] = field(default_factory=dict)
    calibration_version: str = "v1"
    policy_version: str = "v1"
    model_version: str = "v1"
    outcome: Optional[str] = None
    profit_units: Optional[float] = None
    legacy_selected_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "match_id": self.match_id,
            "prediction_timestamp": self.prediction_timestamp,
            "kickoff_timestamp": self.kickoff_timestamp,
            "settlement_timestamp": self.settlement_timestamp,
            "league": self.league,
            "league_normalized": self.league_normalized,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "market_family": self.market_family,
            "market_side": self.market_side,
            "market_line": self.market_line,
            "line_bucket": self.line_bucket,
            "selection": self.selection,
            "odds_open": self.odds_open,
            "odds_close": self.odds_close,
            "model_prob_raw": self.model_prob_raw,
            "model_prob_calibrated": self.model_prob_calibrated,
            "market_prob_no_vig": self.market_prob_no_vig,
            "final_prob": self.final_prob,
            "edge_raw": self.edge_raw,
            "edge_calibrated": self.edge_calibrated,
            "edge_final": self.edge_final,
            "expected_value": self.expected_value,
            "kelly_raw": self.kelly_raw,
            "stake_pre_risk": self.stake_pre_risk,
            "stake_final": self.stake_final,
            "publishable": self.publishable,
            "eligibility_decision": self.eligibility_decision,
            "block_reasons": self.block_reasons,
            "data_quality_score": self.data_quality_score,
            "reliability_score": self.reliability_score,
            "reliability_components": self.reliability_components,
            "calibration_version": self.calibration_version,
            "policy_version": self.policy_version,
            "model_version": self.model_version,
            "outcome": self.outcome,
            "profit_units": self.profit_units,
            "legacy_selected_only": self.legacy_selected_only,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionRecord":
        return cls(
            analysis_id=data["analysis_id"],
            match_id=data["match_id"],
            prediction_timestamp=data["prediction_timestamp"],
            kickoff_timestamp=data["kickoff_timestamp"],
            settlement_timestamp=data.get("settlement_timestamp"),
            league=data["league"],
            league_normalized=data.get("league_normalized", data["league"].lower()),
            home_team=data["home_team"],
            away_team=data["away_team"],
            market_family=data["market_family"],
            market_side=data["market_side"],
            market_line=data.get("market_line"),
            line_bucket=data.get("line_bucket"),
            selection=data["selection"],
            odds_open=data.get("odds_open"),
            odds_close=data.get("odds_close"),
            model_prob_raw=float(data["model_prob_raw"]),
            model_prob_calibrated=float(data["model_prob_calibrated"]),
            market_prob_no_vig=float(data["market_prob_no_vig"]) if data.get("market_prob_no_vig") is not None else None,
            final_prob=float(data["final_prob"]),
            edge_raw=float(data["edge_raw"]),
            edge_calibrated=float(data["edge_calibrated"]),
            edge_final=float(data["edge_final"]),
            expected_value=float(data["expected_value"]),
            kelly_raw=float(data.get("kelly_raw", 0.0)),
            stake_pre_risk=float(data.get("stake_pre_risk", 0.0)),
            stake_final=float(data.get("stake_final", 0.0)),
            publishable=bool(data["publishable"]),
            eligibility_decision=data["eligibility_decision"],
            block_reasons=data.get("block_reasons", []),
            data_quality_score=float(data.get("data_quality_score", 1.0)),
            reliability_score=float(data.get("reliability_score", 1.0)),
            reliability_components=data.get("reliability_components", {}),
            calibration_version=data.get("calibration_version", "v1"),
            policy_version=data.get("policy_version", "v1"),
            model_version=data.get("model_version", "v1"),
            outcome=data.get("outcome"),
            profit_units=float(data["profit_units"]) if data.get("profit_units") is not None else None,
            legacy_selected_only=bool(data.get("legacy_selected_only", False)),
        )


def filter_selected_portfolio(
    records: List[PredictionRecord],
    max_total_exposure: float = 0.25,
    min_stake_threshold: float = 0.005,
) -> List[PredictionRecord]:
    """
    Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.

    1. Filtra las predicciones individuales marcadas como publishable y con stake > 0.
    2. Si la suma total de stakes supera max_total_exposure (e.g. 25% del bankroll),
       aplica Simultaneous Kelly Scaling lineal a todos los picks concurrentes.
    3. Si tras el recorte algún pick queda por debajo de min_stake_threshold (0.5%),
       se descarta de forma segura para no asumir micro-posiciones con fricción.
    """
    candidates = [r for r in records if r.publishable and r.stake_final > 0.0]
    if not candidates:
        return []

    total_stake = sum(r.stake_final for r in candidates)

    # Si la suma de stakes está dentro del límite de riesgo del portafolio, se conserva intacta
    if total_stake <= max_total_exposure:
        return candidates

    scale = max_total_exposure / total_stake
    selected: List[PredictionRecord] = []

    for r in candidates:
        scaled_stake = round(r.stake_final * scale, 5)
        if scaled_stake < min_stake_threshold:
            r.publishable = False
            r.stake_final = 0.0
            r.block_reasons.append(f"portfolio_scaled_below_min_stake ({scaled_stake:.4f})")
            r.eligibility_decision = "blocked_portfolio_scale"
        else:
            r.stake_final = scaled_stake
            selected.append(r)

    return selected


def apply_portfolio_exposure_cap(
    value_indicators: "List[ValueIndicator]",
    max_total_exposure: float = 0.25,
    min_stake_threshold: float = 0.5,
) -> "List[ValueIndicator]":
    """
    Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator publicables.

    Conecta portfolio.py con el pipeline de compare.py resolviendo la sobreexposición
    simultánea por jornada:

    - Usa ``kelly_fraction`` (fracción del bankroll [0–1]) como métrica de exposición
      real. ``stake_units`` es una escala de presentación (0.5–3.0) y no es comparable
      directamente con ``max_total_exposure``.
    - Si la suma de kelly_fractions de todos los picks publicables supera
      ``max_total_exposure``, todos se recortan con el mismo factor de scaling.
    - El mismo factor se aplica a ``stake_units`` para mantener coherencia de display.
    - Picks cuyo ``stake_units`` escaldo quede < ``min_stake_threshold`` se bloquean
      irreversiblemente (``is_publishable=False``, ``quality_score=-1``) y el motivo
      se registra en ``eligibility_hard_blocks`` para trazabilidad completa.

    Esta función es idempotente: si la exposición total ya está dentro del límite,
    devuelve la lista sin modificar.

    Args:
        value_indicators: Lista completa de picks evaluados por ``evaluate_pick_eligibility``.
                          Solo se consideran los que tienen ``is_publishable=True`` y
                          ``kelly_fraction > 0``.
        max_total_exposure: Límite de exposición simultánea como fracción del bankroll
                            (defecto: 0.25 = 25%). Se compara contra la suma de
                            ``kelly_fraction`` de los picks.
        min_stake_threshold: Stake mínimo viable en unidades absolutas tras el scaling.
                             Picks con ``stake_units`` < umbral son bloqueados.
                             (defecto: 0.5 unidades — mínimo de compare.py).

    Returns:
        Lista de ValueIndicator modificados in-place. Los picks bloqueados por el
        scaling se incluyen en la lista (con ``is_publishable=False``) para que
        el caller pueda registrar el motivo del recorte.
    """
    # Solo operamos sobre picks activos y con kelly_fraction positiva
    candidates = [
        v for v in value_indicators
        if getattr(v, "is_publishable", False) and (getattr(v, "kelly_fraction", None) or 0.0) > 0.0
    ]

    if not candidates:
        logger.debug("apply_portfolio_exposure_cap: no hay candidatos publicables con kelly_fraction > 0")
        return value_indicators

    # Exposición total = suma de kelly_fractions (fracción del bankroll)
    total_kelly = sum(getattr(v, "kelly_fraction", 0.0) or 0.0 for v in candidates)

    if total_kelly <= max_total_exposure:
        logger.debug(
            "apply_portfolio_exposure_cap: exposición total kelly=%.4f ≤ límite %.4f — sin scaling",
            total_kelly,
            max_total_exposure,
        )
        return value_indicators

    scale = max_total_exposure / total_kelly
    logger.info(
        "apply_portfolio_exposure_cap: exposición total kelly=%.4f > límite %.4f → scale=%.4f sobre %d picks",
        total_kelly,
        max_total_exposure,
        scale,
        len(candidates),
    )

    for v in candidates:
        original_kelly = getattr(v, "kelly_fraction", 0.0) or 0.0
        original_stake = getattr(v, "stake_units", 0.0) or 0.0
        scaled_kelly = round(original_kelly * scale, 6)
        scaled_stake = round(original_stake * scale, 2)

        if scaled_stake < min_stake_threshold:
            # Bloqueo por micro-stake: no asumir exposición con demasiada fricción
            reason = (
                f"portfolio_scaled_below_min_stake "
                f"(stake={scaled_stake:.2f}u < min={min_stake_threshold:.1f}u, "
                f"kelly={original_kelly:.4f}→{scaled_kelly:.4f})"
            )
            logger.debug(
                "apply_portfolio_exposure_cap: bloqueando pick '%s' — %s",
                getattr(v, "selection", "?"),
                reason,
            )
            v.kelly_fraction = 0.0
            v.stake_units = 0.0
            v.is_publishable = False
            v.is_value = False
            if hasattr(v, "quality_score"):
                v.quality_score = -1
            if hasattr(v, "eligibility_hard_blocks"):
                if reason not in v.eligibility_hard_blocks:
                    v.eligibility_hard_blocks = list(v.eligibility_hard_blocks) + [reason]
            if hasattr(v, "eligibility_reasons"):
                v.eligibility_reasons = list(v.eligibility_reasons) + [reason]
        else:
            v.kelly_fraction = scaled_kelly
            v.stake_units = scaled_stake
            logger.debug(
                "apply_portfolio_exposure_cap: pick '%s' kelly %.4f→%.4f, stake %.2f→%.2f",
                getattr(v, "selection", "?"),
                original_kelly,
                scaled_kelly,
                original_stake,
                scaled_stake,
            )

    return value_indicators
