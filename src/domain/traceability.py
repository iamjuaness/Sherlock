"""
Módulo de trazabilidad y reportes por segmento.

Implementa la Fase 13 del planning.txt: campos de trazabilidad completos
y reportes por league + family + side + line_bucket.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Snapshot de trazabilidad (todos los campos del §13)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PickTrace:
    """
    Snapshot inmutable de trazabilidad de un pick para audit y reportes.

    Contiene todos los campos requeridos por la Fase 13.
    """

    # Identificación de segmento
    market_family: str
    market_side: str
    line: Optional[float]
    line_bucket: str
    segment_key: str
    league: Optional[str]

    # Probabilidades
    model_probability_raw: Optional[float]
    calibrated_probability: Optional[float]
    market_probability_no_vig: Optional[float]
    final_probability: float

    # Edge
    edge_raw: float
    edge_calibrated: float
    edge_final: float

    # EV
    ev: float                          # (p_final * odds) - 1

    # Stake
    kelly_base: float
    stake_pre_risk: float
    stake_final: float

    # Fiabilidad
    reliability_score: float
    reliability_components: Dict[str, float] = field(default_factory=dict)

    # Gobernanza
    segment_status: str = "active"
    drift_score: float = 0.0

    # Versiones
    calibration_version: str = "unknown"
    model_version: str = "unknown"
    policy_version: str = "1.0"

    # CLV
    open_odds: Optional[float] = None
    close_odds: Optional[float] = None
    clv_percent: Optional[float] = None

    # Elegibilidad
    hard_blocks: List[str] = field(default_factory=list)
    soft_failures: List[str] = field(default_factory=list)
    rule_block_reason: Optional[str] = None

    # Penalizaciones
    correlation_penalty: float = 0.0
    exposure_limit_status: str = "ok"

    @property
    def is_publishable(self) -> bool:
        return len(self.hard_blocks) == 0 and self.stake_final > 0.0

    def to_dict(self) -> Dict:
        return {
            "market_family": self.market_family,
            "market_side": self.market_side,
            "line": self.line,
            "line_bucket": self.line_bucket,
            "segment_key": self.segment_key,
            "league": self.league,
            "model_probability_raw": self.model_probability_raw,
            "calibrated_probability": self.calibrated_probability,
            "market_probability_no_vig": self.market_probability_no_vig,
            "final_probability": self.final_probability,
            "edge_raw": self.edge_raw,
            "edge_calibrated": self.edge_calibrated,
            "edge_final": self.edge_final,
            "ev": self.ev,
            "kelly_base": self.kelly_base,
            "stake_pre_risk": self.stake_pre_risk,
            "stake_final": self.stake_final,
            "reliability_score": self.reliability_score,
            "reliability_components": self.reliability_components,
            "segment_status": self.segment_status,
            "drift_score": self.drift_score,
            "calibration_version": self.calibration_version,
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "open_odds": self.open_odds,
            "close_odds": self.close_odds,
            "clv_percent": self.clv_percent,
            "hard_blocks": self.hard_blocks,
            "soft_failures": self.soft_failures,
            "rule_block_reason": self.rule_block_reason,
            "correlation_penalty": self.correlation_penalty,
            "exposure_limit_status": self.exposure_limit_status,
            "is_publishable": self.is_publishable,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Reporte por segmento
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SegmentReport:
    """
    Reporte completo de un segmento league+family+side+bucket.

    Incluye: picks, hit rate, ROI, yield, profit, CLV, Brier, log loss,
    ECE, error de calibración, drift, estado y recomendación operativa.
    """

    segment_key: str
    league: Optional[str]
    market_family: str
    market_side: str
    line_bucket: str

    # Conteos
    n_picks: int = 0
    n_settled: int = 0
    n_wins: int = 0

    # Rendimiento
    roi: float = 0.0           # profit / staked
    yield_pct: float = 0.0     # profit / n_picks
    profit: float = 0.0        # suma de profits reales
    staked: float = 0.0        # suma de stakes
    hit_rate: float = 0.0      # n_wins / n_settled

    # Línea de break-even
    avg_odds: float = 0.0
    breakeven_rate: float = 0.0   # 1 / avg_odds

    # CLV
    avg_clv: float = 0.0
    clv_positive_rate: float = 0.0

    # Calibración
    brier_score: float = 0.0
    log_loss: float = 0.0
    ece: float = 0.0             # Expected Calibration Error
    calibration_gap: float = 0.0 # |mean_prob - hit_rate|

    # Drift
    drift_score: float = 0.0
    segment_status: str = "active"

    # Recomendación
    recommendation: str = "maintain"
    recommendation_detail: str = ""

    def to_dict(self) -> Dict:
        return {
            "segment_key": self.segment_key,
            "league": self.league,
            "market_family": self.market_family,
            "market_side": self.market_side,
            "line_bucket": self.line_bucket,
            "n_picks": self.n_picks,
            "n_settled": self.n_settled,
            "n_wins": self.n_wins,
            "roi": round(self.roi * 100, 2),
            "yield_pct": round(self.yield_pct, 4),
            "profit": round(self.profit, 4),
            "staked": round(self.staked, 4),
            "hit_rate": round(self.hit_rate, 4),
            "avg_odds": round(self.avg_odds, 3),
            "breakeven_rate": round(self.breakeven_rate, 4),
            "avg_clv": round(self.avg_clv, 3),
            "clv_positive_rate": round(self.clv_positive_rate, 4),
            "brier_score": round(self.brier_score, 6),
            "log_loss": round(self.log_loss, 6),
            "ece": round(self.ece, 6),
            "calibration_gap": round(self.calibration_gap, 4),
            "drift_score": round(self.drift_score, 4),
            "segment_status": self.segment_status,
            "recommendation": self.recommendation,
            "recommendation_detail": self.recommendation_detail,
        }


def _safe_log(p: float, eps: float = 1e-9) -> float:
    return math.log(max(p, eps))


def compute_segment_report(
    segment_key: str,
    league: Optional[str],
    market_family: str,
    market_side: str,
    line_bucket: str,
    traces: Sequence[PickTrace],
    outcomes: Sequence[Optional[float]],  # 1.0=win, 0.0=loss, None=pending/push
    segment_status: str = "active",
    n_ece_bins: int = 10,
) -> SegmentReport:
    """
    Calcula el reporte completo de un segmento a partir de sus traces y resultados.

    `outcomes` debe tener la misma longitud que `traces`.
    Push/pending (None) se excluyen de los cálculos.
    """
    assert len(traces) == len(outcomes), "traces y outcomes deben tener la misma longitud"

    settled_pairs = [
        (t, o) for t, o in zip(traces, outcomes) if o is not None
    ]

    n_picks = len(traces)
    n_settled = len(settled_pairs)
    n_wins = sum(1 for _, o in settled_pairs if o > 0.5)

    staked = sum(t.stake_final for t in traces)
    profit = sum(
        t.stake_final * (t.open_odds - 1.0) if o > 0.5 else -t.stake_final
        for t, o in settled_pairs
        if t.open_odds is not None
    )

    hit_rate = n_wins / n_settled if n_settled > 0 else 0.0
    roi = profit / staked if staked > 0 else 0.0
    yield_pct = profit / n_picks if n_picks > 0 else 0.0

    odds_list = [t.open_odds for t in traces if t.open_odds is not None]
    avg_odds = sum(odds_list) / len(odds_list) if odds_list else 0.0
    breakeven_rate = 1.0 / avg_odds if avg_odds > 1.0 else 0.0

    # CLV
    clv_values = [t.clv_percent for t in traces if t.clv_percent is not None]
    avg_clv = sum(clv_values) / len(clv_values) if clv_values else 0.0
    clv_positive_rate = sum(1 for v in clv_values if v > 0) / len(clv_values) if clv_values else 0.0

    # Brier score
    brier = 0.0
    ll = 0.0
    if settled_pairs:
        for t, o in settled_pairs:
            p = t.final_probability
            brier += (p - o) ** 2
            ll -= o * _safe_log(p) + (1.0 - o) * _safe_log(1.0 - p)
        brier /= n_settled
        ll /= n_settled

    # ECE
    ece = _compute_ece(
        [(t.final_probability, o) for t, o in settled_pairs],
        n_bins=n_ece_bins,
    )

    calibration_gap = abs(
        (sum(t.final_probability for t, _ in settled_pairs) / n_settled if n_settled > 0 else 0.0)
        - hit_rate
    )

    # Recomendación
    recommendation, detail = _recommend(
        segment_status=segment_status,
        calibration_gap=calibration_gap,
        roi=roi,
        n_settled=n_settled,
        hit_rate=hit_rate,
        breakeven_rate=breakeven_rate,
    )

    return SegmentReport(
        segment_key=segment_key,
        league=league,
        market_family=market_family,
        market_side=market_side,
        line_bucket=line_bucket,
        n_picks=n_picks,
        n_settled=n_settled,
        n_wins=n_wins,
        roi=roi,
        yield_pct=yield_pct,
        profit=profit,
        staked=staked,
        hit_rate=hit_rate,
        avg_odds=avg_odds,
        breakeven_rate=breakeven_rate,
        avg_clv=avg_clv,
        clv_positive_rate=clv_positive_rate,
        brier_score=brier,
        log_loss=ll,
        ece=ece,
        calibration_gap=calibration_gap,
        segment_status=segment_status,
        recommendation=recommendation,
        recommendation_detail=detail,
    )


def _compute_ece(pairs: List[Tuple[float, float]], n_bins: int = 10) -> float:
    """Expected Calibration Error con n_bins bins uniformes."""
    if not pairs:
        return 0.0
    bins: List[List] = [[] for _ in range(n_bins)]
    for p, o in pairs:
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, o))
    ece = 0.0
    n_total = len(pairs)
    for b in bins:
        if not b:
            continue
        avg_conf = sum(p for p, _ in b) / len(b)
        avg_acc = sum(o for _, o in b) / len(b)
        ece += (len(b) / n_total) * abs(avg_conf - avg_acc)
    return ece


def _recommend(
    segment_status: str,
    calibration_gap: float,
    roi: float,
    n_settled: int,
    hit_rate: float,
    breakeven_rate: float,
) -> Tuple[str, str]:
    """Genera recomendación operativa simple basada en métricas."""
    if segment_status == "blocked":
        return "blocked", "Segmento bloqueado por governance. No publicar."

    if n_settled < 10:
        return "observe", "Muestra insuficiente para evaluación confiable."

    if calibration_gap > 0.15:
        return "recalibrate", f"Error de calibración alto ({calibration_gap:.2%}). Recalibrar curva."

    if roi < -0.05 and n_settled >= 20:
        return "review", f"ROI negativo ({roi:.1%}). Revisar modelo y segmento."

    if hit_rate < breakeven_rate * 0.9 and n_settled >= 20:
        return "review", f"Hit rate ({hit_rate:.2%}) por debajo del break-even ({breakeven_rate:.2%})."

    if calibration_gap > 0.07:
        return "watch", f"Error de calibración moderado ({calibration_gap:.2%}). Monitorear."

    return "maintain", "Segmento con métricas aceptables."


# ═══════════════════════════════════════════════════════════════════════════
# Generador de reportes agregados
# ═══════════════════════════════════════════════════════════════════════════

def generate_segment_reports(
    traces: Sequence[PickTrace],
    outcomes: Sequence[Optional[float]],
    segment_statuses: Optional[Dict[str, str]] = None,
) -> Dict[str, SegmentReport]:
    """
    Agrupa traces por segment_key y genera un SegmentReport para cada uno.

    Returns:
        dict mapping segment_key -> SegmentReport
    """
    groups: Dict[str, List[Tuple[PickTrace, Optional[float]]]] = {}
    for t, o in zip(traces, outcomes):
        groups.setdefault(t.segment_key, []).append((t, o))

    reports = {}
    for key, pairs in groups.items():
        ts, os = zip(*pairs)
        t0 = ts[0]
        status = (segment_statuses or {}).get(key, t0.segment_status)
        reports[key] = compute_segment_report(
            segment_key=key,
            league=t0.league,
            market_family=t0.market_family,
            market_side=t0.market_side,
            line_bucket=t0.line_bucket,
            traces=ts,
            outcomes=os,
            segment_status=status,
        )

    return reports
