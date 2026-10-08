"""
Módulo de política de riesgo, Kelly ponderado e inmutable y límites de exposición.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


class PublicationMode:
    PAPER = "PAPER"
    LIVE = "LIVE"
    HALTED = "HALTED"


@dataclass(frozen=True)
class RiskPolicyConfig:
    version: str = "v2.0"
    min_stake_units: float = 0.25
    max_stake_units: float = 3.0
    max_stake_per_match: float = 5.0
    max_stake_per_league: float = 15.0
    max_stake_per_segment: float = 8.0
    max_stake_per_correlated_cluster: float = 6.0
    min_edge_final_pct: float = 2.5
    min_reliability_score: float = 0.35
    publishing_enabled: bool = True
    paper_trading: bool = True
    mode: str = "PAPER"

    @property
    def effective_mode(self) -> str:
        if not self.publishing_enabled or self.mode == PublicationMode.HALTED:
            return PublicationMode.HALTED
        if not self.paper_trading or self.mode == PublicationMode.LIVE:
            return PublicationMode.LIVE
        return PublicationMode.PAPER

    @property
    def allows_publication(self) -> bool:
        return self.publishing_enabled and self.effective_mode != PublicationMode.HALTED

    @property
    def is_live(self) -> bool:
        return self.effective_mode == PublicationMode.LIVE

    def effective_stake(self, stake: float | None) -> float:
        if not self.is_live or stake is None or stake < 0:
            return 0.0
        return stake

    def describe(self) -> str:
        m = self.effective_mode
        if m == PublicationMode.HALTED:
            return "Publicación detenida (Kill Switch activado)."
        if m == PublicationMode.PAPER:
            return "Modo Paper Trading activo."
        return "Modo Real activo."

    def to_dict(self) -> dict:
        return {
            "mode": self.effective_mode.lower(),
            "publishing_enabled": self.allows_publication,
            "paper_trading": self.paper_trading,
            "version": self.version,
        }

    @classmethod
    def load(cls, path: str = "data/risk_policy.json") -> "RiskPolicyConfig":
        p = Path(path)
        if not p.exists():
            return cls()

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                gl = data.get("global_limits", {})
                return cls(
                    version=data.get("version", "v2.0"),
                    min_stake_units=float(gl.get("min_stake_units", 0.25)),
                    max_stake_units=float(gl.get("max_stake_units", 3.0)),
                    max_stake_per_match=float(gl.get("max_stake_per_match", 5.0)),
                    max_stake_per_league=float(gl.get("max_stake_per_league", 15.0)),
                    max_stake_per_segment=float(gl.get("max_stake_per_segment", 8.0)),
                    max_stake_per_correlated_cluster=float(gl.get("max_stake_per_correlated_cluster", 6.0)),
                    min_edge_final_pct=float(gl.get("min_edge_final_pct", 2.5)),
                    min_reliability_score=float(gl.get("min_reliability_score", 0.35)),
                    allows_publication=bool(gl.get("allows_publication", True)),
                )
        except Exception:
            return cls()


def _parse_bool_env(var_name: str, default: bool) -> bool:
    import os
    val = os.environ.get(var_name)
    if val is None:
        return default
    v = val.strip().lower()
    if v in ("true", "1", "yes", "on", "si", "sí"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    return default


def load_risk_limits(config: Optional[dict] = None) -> RiskPolicyConfig:
    cfg = RiskPolicyConfig.load(config["risk_policy"]) if config and "risk_policy" in config else RiskPolicyConfig.load()
    
    paper_trading = _parse_bool_env(ENV_PAPER_TRADING, True)
    publishing_enabled = _parse_bool_env(ENV_PUBLISHING_ENABLED, True)

    if not publishing_enabled:
        mode = PublicationMode.HALTED
        allows_pub = False
    elif paper_trading:
        mode = PublicationMode.PAPER
        allows_pub = cfg.allows_publication
    else:
        mode = PublicationMode.LIVE
        allows_pub = cfg.allows_publication

    return RiskPolicyConfig(
        version=cfg.version,
        min_stake_units=cfg.min_stake_units,
        max_stake_units=cfg.max_stake_units,
        max_stake_per_match=cfg.max_stake_per_match,
        max_stake_per_league=cfg.max_stake_per_league,
        max_stake_per_segment=cfg.max_stake_per_segment,
        max_stake_per_correlated_cluster=cfg.max_stake_per_correlated_cluster,
        min_edge_final_pct=cfg.min_edge_final_pct,
        min_reliability_score=cfg.min_reliability_score,
        publishing_enabled=publishing_enabled,
        paper_trading=paper_trading,
        mode=mode,
    )


def calculate_kelly_stake(
    final_prob: float,
    odds: float,
    fraction: float = 0.25,
) -> float:
    """Calcula la fracción de Kelly base: f* = (b*p - q) / b"""
    if odds <= 1.0 or final_prob <= 0.0 or final_prob >= 1.0:
        return 0.0

    b = odds - 1.0
    p = final_prob
    q = 1.0 - p

    f_star = (b * p - q) / b
    if f_star <= 0:
        return 0.0

    return max(0.0, f_star * fraction * 100.0)  # Convertir a unidades base (scale 1-10)


@dataclass(frozen=True)
class StakeCalculationResult:
    stake_kelly_raw: float
    stake_pre_risk: float
    stake_final: float
    reliability_score: float
    data_quality_factor: float
    drift_factor: float
    correlation_factor: float
    exposure_factor: float


def compute_final_stake(
    final_prob: float,
    odds: float,
    reliability_score: float,
    data_quality_factor: float = 1.0,
    drift_factor: float = 1.0,
    correlation_factor: float = 1.0,
    exposure_factor: float = 1.0,
    config: Optional[RiskPolicyConfig] = None,
) -> StakeCalculationResult:
    """
    stake_final = stake_kelly * reliability_score * data_quality * drift * correlation * exposure
    """
    cfg = config or RiskPolicyConfig.load()

    kelly_raw = calculate_kelly_stake(final_prob, odds)
    stake_base = kelly_raw

    stake_raw = (
        stake_base
        * max(0.0, min(1.0, reliability_score))
        * max(0.0, min(1.0, data_quality_factor))
        * max(0.0, min(1.0, drift_factor))
        * max(0.0, min(1.0, correlation_factor))
        * max(0.0, min(1.0, exposure_factor))
    )

    if stake_raw < cfg.min_stake_units:
        final_stake = 0.0
    else:
        final_stake = min(cfg.max_stake_units, stake_raw)

    return StakeCalculationResult(
        stake_kelly_raw=kelly_raw,
        stake_pre_risk=stake_base,
        stake_final=round(final_stake, 2),
        reliability_score=reliability_score,
        data_quality_factor=data_quality_factor,
        drift_factor=drift_factor,
        correlation_factor=correlation_factor,
        exposure_factor=exposure_factor,
    )


ENV_PAPER_TRADING = "SHERLOCK_PAPER_TRADING"
ENV_PUBLISHING_ENABLED = "SHERLOCK_PUBLISHING_ENABLED"

RiskLimits = RiskPolicyConfig
