"""
Módulo para el cálculo del score de fiabilidad por segmento (segment_reliability_score).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from src.domain.market_taxonomy import market_group_key


@dataclass
class ReliabilityComponents:
    sample: float
    calibration: float
    drift: float
    data_quality: float
    market_coverage: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "sample": round(self.sample, 4),
            "calibration": round(self.calibration, 4),
            "drift": round(self.drift, 4),
            "data_quality": round(self.data_quality, 4),
            "market_coverage": round(self.market_coverage, 4),
        }


@dataclass
class SegmentReliabilityResult:
    reliability_score: float
    components: ReliabilityComponents
    segment_key: str
    reliability_version: str = "v1"

    def to_dict(self) -> dict:
        return {
            "reliability_score": round(self.reliability_score, 4),
            "reliability_components": self.components.to_dict(),
            "reliability_segment_key": self.segment_key,
            "reliability_version": self.reliability_version,
        }


def compute_sample_factor(effective_sample_size: float, target_n: float = 60.0) -> float:
    """R_sample = 1 - exp(-n / target_n)"""
    if effective_sample_size <= 0:
        return 0.0
    return min(1.0, max(0.0, 1.0 - math.exp(-effective_sample_size / target_n)))


def compute_calibration_factor(ece: float, calibration_gap: float) -> float:
    """R_calibration = exp(- (ece + abs(gap)))"""
    penalty = max(0.0, ece) + abs(calibration_gap)
    return min(1.0, max(0.0, math.exp(-2.5 * penalty)))


def compute_drift_factor(drift_score: float) -> float:
    """R_drift = 1 / (1 + drift_score)"""
    return min(1.0, max(0.0, 1.0 / (1.0 + max(0.0, drift_score))))


def compute_segment_reliability(
    league: Optional[str],
    market_family: str,
    side: str,
    line_bucket: Optional[str],
    effective_sample_size: float,
    ece: float = 0.05,
    calibration_gap: float = 0.02,
    drift_score: float = 0.0,
    data_completeness: float = 1.0,
    market_coverage: float = 1.0,
    reliability_version: str = "v1",
) -> SegmentReliabilityResult:
    """Calcula el score de fiabilidad global R = R_sample * R_calibration * R_drift * R_data * R_market."""
    seg_key = market_group_key(league, market_family, side, line_bucket)

    r_sample = compute_sample_factor(effective_sample_size)
    r_cal = compute_calibration_factor(ece, calibration_gap)
    r_drift = compute_drift_factor(drift_score)
    r_data = min(1.0, max(0.0, data_completeness))
    r_mkt = min(1.0, max(0.0, market_coverage))

    r_total = r_sample * r_cal * r_drift * r_data * r_mkt

    comp = ReliabilityComponents(
        sample=r_sample,
        calibration=r_cal,
        drift=r_drift,
        data_quality=r_data,
        market_coverage=r_mkt,
    )

    return SegmentReliabilityResult(
        reliability_score=r_total,
        components=comp,
        segment_key=seg_key,
        reliability_version=reliability_version,
    )
