"""
Módulo para la separación entre prediction_universe y selected_portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


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


def filter_selected_portfolio(records: List[PredictionRecord]) -> List[PredictionRecord]:
    """Filtra únicamente las predicciones publicables (cartera seleccionada)."""
    return [r for r in records if r.publishable]
