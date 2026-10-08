"""
Calibración probabilística real de Sherlock con jerarquía de 9 niveles,
pooling parcial Beta-Binomial + isotónica (PAVA), ponderación por recencia temporal
y evaluación OOF desagregada por segmento.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from src.domain.market_taxonomy import (
    line_bucket_for,
    market_group_key,
    normalize_market_family,
    normalize_market_side,
)

CALIBRATION_FORMAT_VERSION = 2

# Nivel raíz de la jerarquía.
ROOT_KEY = "global"

# Thresholds configurables por defecto
DEFAULT_MIN_SAMPLES = 50
DEFAULT_PRIOR_STRENGTH = 25.0
DEFAULT_MIN_SAMPLES_GLOBAL = 60.0
DEFAULT_MIN_SAMPLES_FAMILY = 60.0
DEFAULT_MIN_SAMPLES_FAMILY_SIDE = 60.0
DEFAULT_MIN_SAMPLES_FAMILY_SIDE_BUCKET = 80.0
DEFAULT_MIN_SAMPLES_LEAGUE = 40.0
DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY = 40.0
DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE = 40.0
DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE_BUCKET = 30.0

DEFAULT_MAX_BINS = 8
DEFAULT_MIN_BIN_SAMPLES = 8.0

_EPS = 1e-6


# ═══════════════════════════════════════════════════════════════════════
# HELPER KEYS
# ═══════════════════════════════════════════════════════════════════════

def _clean_val(val: str | None, fallback: str = "generic") -> str:
    text = str(val or fallback).strip().lower()
    return " ".join(text.split()) or fallback


def league_family_side_bucket_key(
    league: str | None,
    market_family: str | None,
    side: str | None,
    line_bucket: str | None,
) -> str | None:
    if not league or not market_family or not side or not line_bucket:
        return None
    lg = _clean_val(league)
    fam = _clean_val(market_family)
    s = _clean_val(side)
    bkt = _clean_val(line_bucket, fallback="no_line")
    return f"league:{lg}|family:{fam}|side:{s}|bucket:{bkt}"


def family_side_bucket_key(
    market_family: str | None,
    side: str | None,
    line_bucket: str | None,
) -> str | None:
    if not market_family or not side or not line_bucket:
        return None
    fam = _clean_val(market_family)
    s = _clean_val(side)
    bkt = _clean_val(line_bucket, fallback="no_line")
    return f"family:{fam}|side:{s}|bucket:{bkt}"


def league_family_side_key(league: str | None, market_family: str | None, side: str | None) -> str | None:
    if not league or not market_family or not side:
        return None
    return f"league:{_clean_val(league)}|family:{_clean_val(market_family)}|side:{_clean_val(side)}"


def league_family_key(league: str | None, market_family: str | None) -> str | None:
    if not league or not market_family:
        return None
    return f"league:{_clean_val(league)}|family:{_clean_val(market_family)}"


def league_key(league: str | None, market_family: str | None = None) -> str | None:
    if not league:
        return None
    if market_family:
        return league_family_key(league, market_family)
    return f"league:{_clean_val(league)}"


def family_side_key(market_family: str | None, side: str | None) -> str | None:
    if not market_family or not side:
        return None
    return f"family:{_clean_val(market_family)}|side:{_clean_val(side)}"


def family_key(market_family: str | None) -> str | None:
    if not market_family:
        return None
    return f"family:{_clean_val(market_family)}"


# ═══════════════════════════════════════════════════════════════════════
# MUESTRAS
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalibrationSample:
    """Una observación histórica para ajustar la calibración."""

    prob: float
    hit_value: float
    market_family: str = "generic"
    side: str = "generic"
    line_bucket: str | None = None
    league: str | None = None
    timestamp: datetime | None = None
    weight: float = 1.0

    def normalized_prob(self) -> float:
        p = self.prob / 100.0 if self.prob > 1.0 else self.prob
        return min(1.0 - _EPS, max(_EPS, p))


def compute_sample_weight(
    ts: datetime | None,
    ref_ts: datetime | None,
    half_life_days: float | None,
    base_weight: float = 1.0,
) -> float:
    """Calcula el peso por recencia temporal con la fórmula: w = 0.5 ** (edad / half_life)."""
    if not half_life_days or half_life_days <= 0 or not ts or not ref_ts:
        return base_weight

    # Protección contra fechas futuras
    if ts > ref_ts:
        age_days = 0.0
    else:
        age_days = (ref_ts - ts).total_seconds() / 86400.0

    decay = 0.5 ** (age_days / half_life_days)
    return max(1e-4, base_weight * decay)


def samples_from_settlements(
    rows: Iterable[dict],
    prob_key: str = "model_prob",
    outcome_key: str = "outcome",
    half_life_days: float | None = None,
    reference_timestamp: datetime | None = None,
) -> list[CalibrationSample]:
    """Construye muestras desde filas liquidadas con soporte para taxonomía y recencia."""
    from src.domain.settlement import Outcome, outcome_hit_value

    ref_ts = reference_timestamp or datetime.now(timezone.utc)
    out: list[CalibrationSample] = []

    for row in rows:
        prob = row.get(prob_key)
        raw_outcome = row.get(outcome_key)
        if prob is None or raw_outcome is None:
            continue
        try:
            outcome = Outcome(raw_outcome)
        except ValueError:
            continue
        hit = outcome_hit_value(outcome)
        if hit is None:  # Push o unsettled -> excluido
            continue

        ts = row.get("kickoff_utc") or row.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                ts = None

        fam = normalize_market_family(str(row.get("market_family") or row.get("market") or ""))
        side = normalize_market_side(str(row.get("side") or row.get("selection") or ""), family=fam)
        bkt = row.get("line_bucket")
        if not bkt:
            line_val = row.get("line") or row.get("market_line")
            bkt = line_bucket_for(fam, line_val) if line_val is not None else "no_line"

        w = compute_sample_weight(ts, ref_ts, half_life_days, base_weight=1.0)

        out.append(
            CalibrationSample(
                prob=float(prob),
                hit_value=float(hit),
                market_family=fam,
                side=side,
                line_bucket=bkt,
                league=row.get("league"),
                timestamp=ts,
                weight=w,
            )
        )
    return out


# ═══════════════════════════════════════════════════════════════════════
# ISOTÓNICA (PAVA)
# ═══════════════════════════════════════════════════════════════════════

def pava(values: Sequence[float], weights: Sequence[float]) -> list[float]:
    """Regresión isotónica ponderada por Pool Adjacent Violators."""
    if not values:
        return []
    blocks: list[list[float]] = [
        [float(v), max(float(w), 0.0), 1] for v, w in zip(values, weights)
    ]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0] + 1e-15:
            v1, w1, c1 = blocks[i]
            v2, w2, c2 = blocks[i + 1]
            w = w1 + w2
            merged = (v1 * w1 + v2 * w2) / w if w > 0 else (v1 + v2) / 2.0
            blocks[i : i + 2] = [[merged, w, c1 + c2]]
            if i > 0:
                i -= 1
        else:
            i += 1

    out: list[float] = []
    for v, _w, c in blocks:
        out.extend([v] * int(c))
    return out


# ═══════════════════════════════════════════════════════════════════════
# CURVA
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReliabilityBin:
    lo: float
    hi: float
    n: float
    hits: float
    mean_pred: float
    raw_rate: float | None
    prior: float
    calibrated: float

    def to_dict(self) -> dict:
        return {
            "lo": round(self.lo, 6),
            "hi": round(self.hi, 6),
            "n": round(self.n, 4),
            "hits": round(self.hits, 4),
            "mean_pred": round(self.mean_pred, 6),
            "raw_rate": None if self.raw_rate is None else round(self.raw_rate, 6),
            "prior": round(self.prior, 6),
            "calibrated": round(self.calibrated, 6),
        }


@dataclass(frozen=True)
class CalibrationCurve:
    knots_x: tuple[float, ...]
    knots_y: tuple[float, ...]
    n_samples: float = 0.0
    bins: tuple[ReliabilityBin, ...] = ()
    segment: str = ROOT_KEY

    @staticmethod
    def identity(segment: str = ROOT_KEY) -> "CalibrationCurve":
        return CalibrationCurve((0.0, 1.0), (0.0, 1.0), 0.0, (), segment)

    @property
    def is_identity(self) -> bool:
        return self.knots_x == (0.0, 1.0) and self.knots_y == (0.0, 1.0)

    def apply(self, prob: float) -> float:
        as_pct = prob > 1.0
        p = prob / 100.0 if as_pct else prob
        p = min(1.0, max(0.0, p))

        y = self._interpolate(p)
        y = min(1.0 - _EPS, max(_EPS, y))
        return y * 100.0 if as_pct else y

    def _interpolate(self, p: float) -> float:
        xs, ys = self.knots_x, self.knots_y

        if p <= xs[0]:
            return ys[0]
        if p >= xs[-1]:
            return ys[-1]

        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            if x0 <= p <= x1:
                if x1 - x0 <= 1e-12:
                    return ys[i + 1]
                t = (p - x0) / (x1 - x0)
                return ys[i] + t * (ys[i + 1] - ys[i])

        return ys[-1]

    def validate(self) -> None:
        if len(self.knots_x) != len(self.knots_y) or len(self.knots_x) < 2:
            raise ValueError("Curva mal formada: nodos insuficientes o desalineados")
        for a, b in zip(self.knots_x, self.knots_x[1:]):
            if b < a - 1e-12:
                raise ValueError("knots_x no es creciente")
        for a, b in zip(self.knots_y, self.knots_y[1:]):
            if b < a - 1e-12:
                raise ValueError("knots_y no es monótona")

    def to_dict(self) -> dict:
        return {
            "segment": self.segment,
            "knots_x": [round(x, 6) for x in self.knots_x],
            "knots_y": [round(y, 6) for y in self.knots_y],
            "n_samples": round(self.n_samples, 4),
            "bins": [b.to_dict() for b in self.bins],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationCurve":
        return cls(
            knots_x=tuple(float(x) for x in d["knots_x"]),
            knots_y=tuple(float(y) for y in d["knots_y"]),
            n_samples=float(d.get("n_samples", 0.0)),
            bins=tuple(ReliabilityBin(**b) for b in d.get("bins", [])),
            segment=str(d.get("segment", ROOT_KEY)),
        )


def _quantile_edges(probs: Sequence[float], max_bins: int, min_bin: float) -> list[float]:
    n = len(probs)
    if n == 0:
        return [0.0, 1.0]
    n_bins = max(1, min(max_bins, int(n // max(1.0, min_bin))))
    if n_bins <= 1:
        return [0.0, 1.0]

    ordered = sorted(probs)
    edges = [0.0]
    for i in range(1, n_bins):
        idx = int(round(i * n / n_bins))
        idx = min(max(idx, 0), n - 1)
        edges.append(ordered[idx])
    edges.append(1.0)

    dedup = [edges[0]]
    for e in edges[1:]:
        if e > dedup[-1] + 1e-9:
            dedup.append(e)
    if len(dedup) < 2:
        return [0.0, 1.0]
    dedup[0], dedup[-1] = 0.0, 1.0
    return dedup


def fit_curve(
    samples: Sequence[CalibrationSample],
    prior_curve: CalibrationCurve | None = None,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    max_bins: int = DEFAULT_MAX_BINS,
    min_bin_samples: float = DEFAULT_MIN_BIN_SAMPLES,
    segment: str = ROOT_KEY,
) -> CalibrationCurve:
    if not samples:
        return CalibrationCurve.identity(segment)

    prior_curve = prior_curve or CalibrationCurve.identity()
    probs = [sample.normalized_prob() for sample in samples]
    edges = _quantile_edges(probs=probs, max_bins=max_bins, min_bin=min_bin_samples)

    bins: list[ReliabilityBin] = []

    for i in range(len(edges) - 1):
        lo = edges[i]
        hi = edges[i + 1]
        is_last_bin = i == len(edges) - 2

        members = [
            sample
            for sample, prob in zip(samples, probs)
            if (lo <= prob < hi) or (is_last_bin and abs(prob - hi) <= 1e-12)
        ]

        if not members:
            continue

        n = sum(sample.weight for sample in members)
        if n <= 0:
            continue

        hits = sum(sample.hit_value * sample.weight for sample in members)
        mean_pred = sum(sample.normalized_prob() * sample.weight for sample in members) / n

        prior = prior_curve.apply(mean_pred)
        raw_rate = hits / n

        calibrated = (hits + prior_strength * prior) / (n + prior_strength)

        bins.append(
            ReliabilityBin(
                lo=lo,
                hi=hi,
                n=n,
                hits=hits,
                mean_pred=mean_pred,
                raw_rate=raw_rate,
                prior=prior,
                calibrated=calibrated,
            )
        )

    if not bins:
        return CalibrationCurve.identity(segment)

    bins.sort(key=lambda item: item.mean_pred)

    smoothed_values = pava(
        values=[item.calibrated for item in bins],
        weights=[item.n + prior_strength for item in bins],
    )

    smoothed_bins = [
        ReliabilityBin(
            lo=item.lo,
            hi=item.hi,
            n=item.n,
            hits=item.hits,
            mean_pred=item.mean_pred,
            raw_rate=item.raw_rate,
            prior=item.prior,
            calibrated=calibrated,
        )
        for item, calibrated in zip(bins, smoothed_values)
    ]

    xs = [item.mean_pred for item in smoothed_bins]
    ys = [item.calibrated for item in smoothed_bins]

    for i in range(1, len(xs)):
        xs[i] = max(xs[i], xs[i - 1])
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1])

    if len(xs) == 1:
        center_x = xs[0]
        center_y = ys[0]
        xs = [max(_EPS, center_x - 1e-6), min(1.0 - _EPS, center_x + 1e-6)]
        ys = [center_y, center_y]

    curve = CalibrationCurve(
        knots_x=tuple(xs),
        knots_y=tuple(ys),
        n_samples=sum(sample.weight for sample in samples),
        bins=tuple(smoothed_bins),
        segment=segment,
    )
    curve.validate()
    return curve


# ═══════════════════════════════════════════════════════════════════════
# CALIBRADOR JERÁRQUICO
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class HierarchicalCalibrator:
    """
    Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.

    Orden de Resolución Estricto:
      1. league + family + side + line_bucket
      2. league + family + side
      3. league + family
      4. family + side + line_bucket
      5. family + side
      6. family
      7. league
      8. global
      9. identidad
    """

    curves: dict[str, CalibrationCurve] = field(default_factory=dict)
    prior_strength: float = DEFAULT_PRIOR_STRENGTH
    min_samples_global: float = DEFAULT_MIN_SAMPLES_GLOBAL
    min_samples_family: float = DEFAULT_MIN_SAMPLES_FAMILY
    min_samples_family_side: float = DEFAULT_MIN_SAMPLES_FAMILY_SIDE
    min_samples_family_side_bucket: float = DEFAULT_MIN_SAMPLES_FAMILY_SIDE_BUCKET
    min_samples_league: float = DEFAULT_MIN_SAMPLES_LEAGUE
    min_samples_league_family: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY
    min_samples_league_family_side: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE
    min_samples_league_family_side_bucket: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE_BUCKET
    calibration_half_life_days: float | None = None
    version: str = "unversioned"
    fitted_at: str | None = None
    activated_at_utc: str | None = None
    deactivated_at_utc: str | None = None
    metadata: dict = field(default_factory=dict)

    def resolve_curve(
        self,
        market_family: str | None = None,
        side: str | None = None,
        line_bucket: str | None = None,
        league: str | None = None,
    ) -> CalibrationCurve:
        # Legacy support: si side no es un lado conocido ("over", "under", "home", "away", "draw", "yes", "no") pero league es None y side tiene valor string, asumir que side es league
        if side is not None and league is None and side.lower() not in ("over", "under", "home", "away", "draw", "yes", "no", "over_under", "1x2"):
            league = side
            side = None
        """Devuelve la curva más específica disponible según el orden de resolución exigido."""
        candidates = (
            league_family_side_bucket_key(league, market_family, side, line_bucket),
            league_family_side_key(league, market_family, side),
            league_family_key(league, market_family),
            family_side_bucket_key(market_family, side, line_bucket),
            family_side_key(market_family, side),
            family_key(market_family),
            league_key(league),
            ROOT_KEY,
        )

        for key in candidates:
            if key and key in self.curves:
                return self.curves[key]

        return CalibrationCurve.identity()

    def apply(
        self,
        prob: float,
        market_family: str | None = None,
        side: str | None = None,
        line_bucket: str | None = None,
        league: str | None = None,
    ) -> float:
        if prob is None:
            return prob

        curve = self.resolve_curve(
            market_family=market_family,
            side=side,
            line_bucket=line_bucket,
            league=league,
        )
        return curve.apply(prob)

    @property
    def is_trained(self) -> bool:
        if not self.curves:
            return self.version not in ("identity", "unversioned")
        return any(not curve.is_identity for curve in self.curves.values())

    @classmethod
    def fit(
        cls,
        samples: Sequence[CalibrationSample],
        prior_strength: float = DEFAULT_PRIOR_STRENGTH,
        min_samples: float | None = None,
        min_line_samples: float | None = None,
        min_league_samples: float | None = None,
        min_market_samples: float | None = None,
        min_samples_global: float = DEFAULT_MIN_SAMPLES_GLOBAL,
        min_samples_family: float = DEFAULT_MIN_SAMPLES_FAMILY,
        min_samples_family_side: float = DEFAULT_MIN_SAMPLES_FAMILY_SIDE,
        min_samples_family_side_bucket: float = DEFAULT_MIN_SAMPLES_FAMILY_SIDE_BUCKET,
        min_samples_league: float = DEFAULT_MIN_SAMPLES_LEAGUE,
        min_samples_league_family: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY,
        min_samples_league_family_side: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE,
        min_samples_league_family_side_bucket: float = DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE_BUCKET,
        calibration_half_life_days: float | None = None,
        max_bins: int = DEFAULT_MAX_BINS,
        version: str | None = None,
        reference_timestamp: datetime | None = None,
    ) -> "HierarchicalCalibrator":
        if min_samples is not None:
            min_samples_global = min_samples
            min_samples_family = min_samples
            min_samples_family_side = min_samples
            min_samples_family_side_bucket = min_samples
            min_samples_league = min_samples
            min_samples_league_family = min_samples
            min_samples_league_family_side = min_samples
            min_samples_league_family_side_bucket = min_samples
        """
        Ajusta la jerarquía en 8 niveles lógicos:
          1. global
          2. family
          3. family + side
          4. family + side + line_bucket
          5. league
          6. league + family
          7. league + family + side
          8. league + family + side + line_bucket
        """
        ref_ts = reference_timestamp or datetime.now(timezone.utc)
        weighted_samples: list[CalibrationSample] = []
        for s in samples:
            # If calibration_half_life_days is provided explicitly in fit, use it; otherwise preserve existing sample.weight
            if calibration_half_life_days is not None:
                w = compute_sample_weight(s.timestamp, ref_ts, calibration_half_life_days, base_weight=1.0)
            else:
                w = s.weight
            weighted_samples.append(
                CalibrationSample(
                    prob=s.prob,
                    hit_value=s.hit_value,
                    market_family=s.market_family,
                    side=s.side,
                    line_bucket=s.line_bucket,
                    league=s.league,
                    timestamp=s.timestamp,
                    weight=w,
                )
            )

        curves: dict[str, CalibrationCurve] = {}
        total_weight = sum(s.weight for s in weighted_samples)

        # 1. Global
        global_curve = (
            fit_curve(
                samples=weighted_samples,
                prior_curve=None,
                prior_strength=prior_strength,
                max_bins=max_bins,
                segment=ROOT_KEY,
            )
            if total_weight >= min_samples_global
            else CalibrationCurve.identity(ROOT_KEY)
        )
        curves[ROOT_KEY] = global_curve

        # Indexar muestras por grupo
        by_family: dict[str, list[CalibrationSample]] = {}
        by_fam_side: dict[tuple[str, str], list[CalibrationSample]] = {}
        by_fam_side_bkt: dict[tuple[str, str, str], list[CalibrationSample]] = {}
        by_league: dict[str, list[CalibrationSample]] = {}
        by_league_fam: dict[tuple[str, str], list[CalibrationSample]] = {}
        by_league_fam_side: dict[tuple[str, str, str], list[CalibrationSample]] = {}
        by_league_fam_side_bkt: dict[tuple[str, str, str, str], list[CalibrationSample]] = {}

        for s in weighted_samples:
            fam = _clean_val(s.market_family)
            side = _clean_val(s.side)
            bkt = _clean_val(s.line_bucket, fallback="no_line")
            lg = _clean_val(s.league) if s.league else None

            by_family.setdefault(fam, []).append(s)
            by_fam_side.setdefault((fam, side), []).append(s)
            by_fam_side_bkt.setdefault((fam, side, bkt), []).append(s)

            if lg:
                by_league.setdefault(lg, []).append(s)
                by_league_fam.setdefault((lg, fam), []).append(s)
                by_league_fam_side.setdefault((lg, fam, side), []).append(s)
                by_league_fam_side_bkt.setdefault((lg, fam, side, bkt), []).append(s)

        # 2. Family
        for fam, sub in sorted(by_family.items()):
            if sum(item.weight for item in sub) >= min_samples_family:
                key = family_key(fam)
                if key:
                    curves[key] = fit_curve(sub, global_curve, prior_strength, max_bins, segment=key)

        # 3. Family + Side
        for (fam, side), sub in sorted(by_fam_side.items()):
            if sum(item.weight for item in sub) >= min_samples_family_side:
                key = family_side_key(fam, side)
                if key:
                    parent = curves.get(family_key(fam), global_curve)
                    curves[key] = fit_curve(sub, parent, prior_strength, max_bins, segment=key)

        # 4. Family + Side + Bucket
        for (fam, side, bkt), sub in sorted(by_fam_side_bkt.items()):
            if sum(item.weight for item in sub) >= min_samples_family_side_bucket:
                key = family_side_bucket_key(fam, side, bkt)
                if key:
                    parent = curves.get(family_side_key(fam, side), curves.get(family_key(fam), global_curve))
                    curves[key] = fit_curve(sub, parent, prior_strength, max_bins, segment=key)

        # 5. League
        for lg, sub in sorted(by_league.items()):
            if sum(item.weight for item in sub) >= min_samples_league:
                key = league_key(lg)
                if key:
                    curves[key] = fit_curve(sub, global_curve, prior_strength, max_bins, segment=key)

        # 6. League + Family
        for (lg, fam), sub in sorted(by_league_fam.items()):
            if sum(item.weight for item in sub) >= min_samples_league_family:
                key = league_family_key(lg, fam)
                if key:
                    parent = curves.get(league_key(lg), curves.get(family_key(fam), global_curve))
                    curves[key] = fit_curve(sub, parent, prior_strength, max_bins, segment=key)

        # 7. League + Family + Side
        for (lg, fam, side), sub in sorted(by_league_fam_side.items()):
            if sum(item.weight for item in sub) >= min_samples_league_family_side:
                key = league_family_side_key(lg, fam, side)
                if key:
                    parent = curves.get(
                        league_family_key(lg, fam),
                        curves.get(league_key(lg), curves.get(family_side_key(fam, side), global_curve)),
                    )
                    curves[key] = fit_curve(sub, parent, prior_strength, max_bins, segment=key)

        # 8. League + Family + Side + Bucket
        for (lg, fam, side, bkt), sub in sorted(by_league_fam_side_bkt.items()):
            if sum(item.weight for item in sub) >= min_samples_league_family_side_bucket:
                key = league_family_side_bucket_key(lg, fam, side, bkt)
                if key:
                    # Cadena de fallback del padre:
                    # 1. league + family + side
                    # 2. family + side + bucket
                    # 3. league + family
                    parent = curves.get(
                        league_family_side_key(lg, fam, side),
                        curves.get(
                            family_side_bucket_key(fam, side, bkt),
                            curves.get(league_family_key(lg, fam), global_curve),
                        ),
                    )
                    curves[key] = fit_curve(sub, parent, prior_strength, max_bins, segment=key)

        fitted_at = datetime.now(timezone.utc).isoformat()

        return cls(
            curves=curves,
            prior_strength=prior_strength,
            min_samples_global=min_samples_global,
            min_samples_family=min_samples_family,
            min_samples_family_side=min_samples_family_side,
            min_samples_family_side_bucket=min_samples_family_side_bucket,
            min_samples_league=min_samples_league,
            min_samples_league_family=min_samples_league_family,
            min_samples_league_family_side=min_samples_league_family_side,
            min_samples_league_family_side_bucket=min_samples_league_family_side_bucket,
            calibration_half_life_days=calibration_half_life_days,
            version=version or datetime.now(timezone.utc).strftime("cal-v2-%Y%m%dT%H%M%SZ"),
            fitted_at=fitted_at,
            metadata={
                "n_samples": total_weight,
                "n_segments": len(curves),
                "format_version": CALIBRATION_FORMAT_VERSION,
                "half_life_days": calibration_half_life_days,
            },
        )

    def to_dict(self) -> dict:
        return {
            "format_version": CALIBRATION_FORMAT_VERSION,
            "version": self.version,
            "fitted_at": self.fitted_at,
            "activated_at_utc": self.activated_at_utc,
            "deactivated_at_utc": self.deactivated_at_utc,
            "prior_strength": self.prior_strength,
            "min_samples_global": self.min_samples_global,
            "min_samples_family": self.min_samples_family,
            "min_samples_family_side": self.min_samples_family_side,
            "min_samples_family_side_bucket": self.min_samples_family_side_bucket,
            "min_samples_league": self.min_samples_league,
            "min_samples_league_family": self.min_samples_league_family,
            "min_samples_league_family_side": self.min_samples_league_family_side,
            "min_samples_league_family_side_bucket": self.min_samples_league_family_side_bucket,
            "calibration_half_life_days": self.calibration_half_life_days,
            "metadata": self.metadata,
            "curves": {key: curve.to_dict() for key, curve in sorted(self.curves.items())},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HierarchicalCalibrator":
        fmt = int(data.get("format_version", 0))
        if fmt not in (1, CALIBRATION_FORMAT_VERSION):
            raise ValueError(f"Versión de calibración no soportada: {fmt}")

        return cls(
            curves={key: CalibrationCurve.from_dict(value) for key, value in data.get("curves", {}).items()},
            prior_strength=float(data.get("prior_strength", DEFAULT_PRIOR_STRENGTH)),
            min_samples_global=float(data.get("min_samples_global", data.get("min_samples", DEFAULT_MIN_SAMPLES_GLOBAL))),
            min_samples_family=float(data.get("min_samples_family", DEFAULT_MIN_SAMPLES_FAMILY)),
            min_samples_family_side=float(data.get("min_samples_family_side", DEFAULT_MIN_SAMPLES_FAMILY_SIDE)),
            min_samples_family_side_bucket=float(data.get("min_samples_family_side_bucket", DEFAULT_MIN_SAMPLES_FAMILY_SIDE_BUCKET)),
            min_samples_league=float(data.get("min_samples_league", data.get("min_league_samples", DEFAULT_MIN_SAMPLES_LEAGUE))),
            min_samples_league_family=float(data.get("min_samples_league_family", DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY)),
            min_samples_league_family_side=float(data.get("min_samples_league_family_side", DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE)),
            min_samples_league_family_side_bucket=float(data.get("min_samples_league_family_side_bucket", DEFAULT_MIN_SAMPLES_LEAGUE_FAMILY_SIDE_BUCKET)),
            calibration_half_life_days=data.get("calibration_half_life_days"),
            version=str(data.get("version", "unversioned")),
            fitted_at=data.get("fitted_at"),
            activated_at_utc=data.get("activated_at_utc"),
            deactivated_at_utc=data.get("deactivated_at_utc"),
            metadata=data.get("metadata", {}),
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "HierarchicalCalibrator":
        source = Path(path)
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))

    @classmethod
    def identity(cls) -> "HierarchicalCalibrator":
        return cls(curves={ROOT_KEY: CalibrationCurve.identity(ROOT_KEY)}, version="identity")


# ═══════════════════════════════════════════════════════════════════════
# MÉTRICAS DE CALIDAD PROBABILÍSTICA Y AUDITORÍA OOF
# ═══════════════════════════════════════════════════════════════════════

def brier_score(probs: Sequence[float], outcomes: Sequence[float]) -> float:
    if not probs:
        return float("nan")
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def log_loss(probs: Sequence[float], outcomes: Sequence[float], eps: float = 1e-12) -> float:
    if not probs:
        return float("nan")
    total = 0.0
    for p, o in zip(probs, outcomes):
        p = min(1.0 - eps, max(eps, p))
        total += -(o * math.log(p) + (1.0 - o) * math.log(1.0 - p))
    return total / len(probs)


def expected_calibration_error(probs: Sequence[float], outcomes: Sequence[float], n_bins: int = 10) -> float:
    if not probs:
        return float("nan")
    total = len(probs)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        idx = [j for j, p in enumerate(probs) if (lo <= p < hi) or (i == n_bins - 1 and abs(p - hi) <= 1e-12)]
        if not idx:
            continue
        conf = sum(probs[j] for j in idx) / len(idx)
        acc = sum(outcomes[j] for j in idx) / len(idx)
        ece += (len(idx) / total) * abs(conf - acc)
    return ece


def reliability_table(probs: Sequence[float], outcomes: Sequence[float], n_bins: int = 10) -> list[dict]:
    if not probs:
        return []
    rows = []
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        idx = [j for j, p in enumerate(probs) if (lo <= p < hi) or (i == n_bins - 1 and abs(p - hi) <= 1e-12)]
        if not idx:
            rows.append({"lo": lo, "hi": hi, "n": 0, "confidence": 0.0, "accuracy": 0.0, "gap": 0.0})
            continue
        conf = sum(probs[j] for j in idx) / len(idx)
        acc = sum(outcomes[j] for j in idx) / len(idx)
        rows.append({"lo": lo, "hi": hi, "n": len(idx), "confidence": conf, "accuracy": acc, "gap": acc - conf})
    return rows




def evaluate(probs: Sequence[float], outcomes: Sequence[float]) -> dict:
    if not probs:
        return {
            "n": 0,
            "brier": float("nan"),
            "log_loss": float("nan"),
            "ece": float("nan"),
            "mean_prob": float("nan"),
            "mean_outcome": float("nan"),
            "calibration_gap": float("nan"),
        }
    mean_p = sum(probs) / len(probs)
    mean_o = sum(outcomes) / len(outcomes)
    return {
        "n": len(probs),
        "brier": brier_score(probs, outcomes),
        "log_loss": log_loss(probs, outcomes),
        "ece": expected_calibration_error(probs, outcomes),
        "mean_prob": mean_p,
        "mean_outcome": mean_o,
        "calibration_gap": mean_o - mean_p,
    }


@dataclass
class SegmentEvaluation:
    segment_key: str
    n: int
    raw_brier: float
    calibrated_brier: float
    raw_log_loss: float
    calibrated_log_loss: float
    raw_ece: float
    calibrated_ece: float
    mean_raw_prob: float
    mean_calibrated_prob: float
    mean_observed_hit_rate: float
    calibration_gap: float


@dataclass
class WalkForwardResult:
    raw_probs: list[float] = field(default_factory=list)
    calibrated_probs: list[float] = field(default_factory=list)
    outcomes: list[float] = field(default_factory=list)
    samples: list[CalibrationSample] = field(default_factory=list)
    n_folds: int = 0
    skipped: int = 0
    segment_metrics: dict[str, SegmentEvaluation] = field(default_factory=dict)

    def metrics(self) -> dict:
        return {
            "raw": evaluate(self.raw_probs, self.outcomes),
            "calibrated": evaluate(self.calibrated_probs, self.outcomes),
            "n_folds": self.n_folds,
            "skipped_no_train": self.skipped,
        }

    def improved(self, max_allowed_segment_brier_degradation: float = 0.05) -> bool:
        if not self.outcomes:
            return False
        raw = evaluate(self.raw_probs, self.outcomes)
        cal = evaluate(self.calibrated_probs, self.outcomes)

        # 1. Mejora global en Brier y Log Loss
        if cal["brier"] > raw["brier"] or cal["log_loss"] > raw["log_loss"]:
            return False

        # 2. Regla de rechazo: ningún segmento de alto volumen (n >= 30) puede empeorar materialmente
        for seg_key, seg_eval in self.segment_metrics.items():
            if seg_eval.n >= 30:
                if seg_eval.calibrated_brier > seg_eval.raw_brier + max_allowed_segment_brier_degradation:
                    return False

        return True


def walk_forward_calibrate(
    samples: Sequence[CalibrationSample],
    n_folds: int = 5,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    min_samples: float | None = None,
    min_line_samples: float | None = None,
    min_league_samples: float | None = None,
    min_market_samples: float | None = None,
    min_samples_global: float = DEFAULT_MIN_SAMPLES_GLOBAL,
    calibration_half_life_days: float | None = None,
    min_train: float = 120.0,
) -> WalkForwardResult:
    if min_samples is not None:
        min_samples_global = min_samples
    if min_line_samples is not None and min_samples is None:
        min_samples_global = min_line_samples
    ordered = sorted([s for s in samples if s.timestamp is not None], key=lambda s: s.timestamp)
    if not ordered and samples:
        ordered = list(samples)

    result = WalkForwardResult(n_folds=n_folds)
    if not ordered or n_folds < 2 or len(ordered) < min_train:
        result.skipped = len(samples) if samples else 0
        return result

    grouped: list[list[CalibrationSample]] = []
    current_ts = None
    current_grp: list[CalibrationSample] = []

    for idx, s in enumerate(ordered):
        ts = s.timestamp if s.timestamp is not None else idx
        if current_ts is None or ts == current_ts:
            current_grp.append(s)
            current_ts = ts
            continue
        grouped.append(current_grp)
        current_grp = [s]
        current_ts = ts

    if current_grp:
        grouped.append(current_grp)

    if len(grouped) < n_folds:
        result.skipped = len(ordered)
        return result

    fold_size = max(1, len(grouped) // n_folds)

    for fold_index in range(1, n_folds):
        train_groups = grouped[: fold_index * fold_size]
        test_groups = grouped[fold_index * fold_size :] if fold_index == n_folds - 1 else grouped[fold_index * fold_size : (fold_index + 1) * fold_size]

        train = [s for grp in train_groups for s in grp]
        test = [s for grp in test_groups for s in grp]

        if not test or sum(s.weight for s in train) < min_train:
            result.skipped += len(test)
            continue

        calibrator = HierarchicalCalibrator.fit(
            samples=train,
            prior_strength=prior_strength,
            min_samples_global=min_samples_global,
            calibration_half_life_days=calibration_half_life_days,
        )

        for s in test:
            raw_p = s.normalized_prob()
            cal_p = calibrator.apply(
                prob=raw_p,
                market_family=s.market_family,
                side=s.side,
                line_bucket=s.line_bucket,
                league=s.league,
            )
            result.raw_probs.append(raw_p)
            result.calibrated_probs.append(cal_p)
            result.outcomes.append(s.hit_value)
            result.samples.append(s)

    # Calcular métricas desagregadas por segmento OOF
    seg_samples: dict[str, list[tuple[float, float, float]]] = {}
    for s, raw_p, cal_p, out in zip(result.samples, result.raw_probs, result.calibrated_probs, result.outcomes):
        seg_key = market_group_key(s.league, s.market_family, s.side, s.line_bucket)
        seg_samples.setdefault(seg_key, []).append((raw_p, cal_p, out))

    for seg_key, data in seg_samples.items():
        raw_ps = [d[0] for d in data]
        cal_ps = [d[1] for d in data]
        outs = [d[2] for d in data]

        raw_eval = evaluate(raw_ps, outs)
        cal_eval = evaluate(cal_ps, outs)

        result.segment_metrics[seg_key] = SegmentEvaluation(
            segment_key=seg_key,
            n=len(data),
            raw_brier=raw_eval["brier"],
            calibrated_brier=cal_eval["brier"],
            raw_log_loss=raw_eval["log_loss"],
            calibrated_log_loss=cal_eval["log_loss"],
            raw_ece=raw_eval["ece"],
            calibrated_ece=cal_eval["ece"],
            mean_raw_prob=raw_eval["mean_prob"],
            mean_calibrated_prob=cal_eval["mean_prob"],
            mean_observed_hit_rate=cal_eval["mean_outcome"],
            calibration_gap=cal_eval["calibration_gap"],
        )

    return result
