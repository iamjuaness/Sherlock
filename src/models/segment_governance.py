"""
Módulo para el monitor de drift y la gobernanza automática de segmentos.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from src.domain.market_taxonomy import market_group_key


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)


class SegmentStatus(StrEnum):
    ACTIVE = "active"
    WATCH = "watch"
    REDUCED = "reduced"
    BLOCKED = "blocked"
    EXPERIMENTAL = "experimental"


def load_governance_config(config_path: str = "data/segment_governance.json") -> Dict[str, SegmentStatus]:
    """Carga la configuración persistida de gobernanza de segmentos."""
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            segments = data.get("segments", {})
            res = {}
            for k, v in segments.items():
                try:
                    res[k] = SegmentStatus(v.lower())
                except ValueError:
                    pass
            return res
    except Exception:
        return {}


def evaluate_segment_status(
    league: Optional[str],
    market_family: str,
    side: str,
    line_bucket: Optional[str],
    effective_n: float,
    calibration_gap_abs: float = 0.0,
    recent_clv: float = 0.0,
    config_path: str = "data/segment_governance.json",
) -> SegmentStatus:
    """Evalúa el estado de gobernanza de un segmento según evidencia y configuración manual de seguridad."""
    seg_key = market_group_key(league, market_family, side, line_bucket)

    # 1. Check override manual/config de seguridad
    configured_states = load_governance_config(config_path)
    if configured_states:
        candidates = []
        clean_league = (league or "").strip().lower()
        if clean_league:
            candidates.extend([
                f"league:{clean_league}|family:{market_family}|side:{side}|bucket:{line_bucket or 'no_line'}",
                f"league:{clean_league}|family:{market_family}|side:{side}",
                f"league:{clean_league}|family:{market_family}",
                f"league:{clean_league}",
            ])
        candidates.extend([
            f"family:{market_family}|side:{side}|bucket:{line_bucket or 'no_line'}",
            f"family:{market_family}|side:{side}",
            f"family:{market_family}",
        ])
        for cand in candidates:
            if cand in configured_states:
                return configured_states[cand]

    # 2. Reglas dinámicas automáticas
    if effective_n < 15:
        return SegmentStatus.EXPERIMENTAL

    if effective_n >= 30 and (calibration_gap_abs > 0.15 or (calibration_gap_abs > 0.10 and recent_clv < -0.05)):
        return SegmentStatus.BLOCKED

    if effective_n >= 25 and (calibration_gap_abs > 0.10 or recent_clv < -0.02):
        return SegmentStatus.REDUCED

    if effective_n >= 15 and (calibration_gap_abs > 0.05 or recent_clv < 0.0):
        return SegmentStatus.WATCH

    return SegmentStatus.ACTIVE


def get_governance_multipliers(status: SegmentStatus) -> dict:
    """Retorna los multiplicadores de stake y ajustes de edge según el estado de gobernanza."""
    if status == SegmentStatus.BLOCKED:
        return {"stake_multiplier": 0.0, "min_edge_add": 1.0, "publishable": False}
    elif status == SegmentStatus.REDUCED:
        return {"stake_multiplier": 0.25, "min_edge_add": 0.04, "publishable": True}
    elif status == SegmentStatus.WATCH:
        return {"stake_multiplier": 0.50, "min_edge_add": 0.02, "publishable": True}
    elif status == SegmentStatus.EXPERIMENTAL:
        return {"stake_multiplier": 0.30, "min_edge_add": 0.03, "publishable": True}
    else:  # ACTIVE
        return {"stake_multiplier": 1.0, "min_edge_add": 0.0, "publishable": True}
