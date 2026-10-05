"""
Calibración probabilística real de Sherlock. SIN GLM.

Por qué no GLM / stacking
─────────────────────────
El GLM y el stacking anteriores se retiraron porque con poca muestra y
segmentación pobre amplificaban ruido: aprendían coeficientes por liga con
5-20 observaciones y producían curvas inestables entre recálculos.

Enfoque elegido: Beta-Binomial jerárquica + isotónica
─────────────────────────────────────────────────────
1. Se agrupan las predicciones en bins de probabilidad (cuantiles adaptativos).
2. En cada bin se estima el hit rate real con un prior Beta centrado en la
   predicción del PADRE de la jerarquía:

       p̂ = (aciertos + κ·prior) / (n + κ)

   Con n pequeño, p̂ ≈ prior (no se mueve del padre). Con n grande, p̂ ≈ tasa
   empírica. El ruido no puede dominar: está acotado por construcción.
3. Jerarquía de 3 niveles con partial pooling:

       identidad  →  global  →  familia de mercado  →  liga × familia

   El prior del nivel raíz es la propia predicción del modelo, así que
   "sin datos" degrada exactamente a la identidad actual — nunca empeora.
4. Se impone monotonía con PAVA (pool adjacent violators). Una calibración no
   monótona no tiene sentido: más probabilidad del modelo no puede significar
   menos probabilidad real.
5. El resultado es una curva monótona lineal por tramos, interpolable y
   serializable a JSON, versionada y auditable.

Un segmento solo obtiene curva propia si supera `min_samples`; si no, hereda la
del padre. Esto implementa "calibrar out-of-fold solo con muestra suficiente;
usar priors jerárquicos para segmentos pequeños".

Los half-win cuentan como 0.5 aciertos (el motor de settlement ya lo define
así) y los push se excluyen: no informan sobre la probabilidad del evento.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

CALIBRATION_FORMAT_VERSION = 1

# Nivel raíz de la jerarquía.
ROOT_KEY = "global"

# Defaults conservadores: pensados para que con poca muestra casi no se mueva.
DEFAULT_PRIOR_STRENGTH = 25.0   # κ: nº de observaciones "virtuales" del prior
DEFAULT_MIN_SAMPLES = 40.0      # muestra mínima para que un segmento tenga curva
DEFAULT_MAX_BINS = 8
DEFAULT_MIN_BIN_SAMPLES = 8.0

_EPS = 1e-6


# ═══════════════════════════════════════════════════════════════════════
# MUESTRAS
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalibrationSample:
    """
    Una observación histórica para ajustar la calibración.

    `prob` puede venir en escala 0-1 o 0-100.
    `hit_value` admite 1.0, 0.5 o 0.0. Los push deben excluirse antes.

    La segmentación se conserva separada:
      - market_family: goals, corners, cards, result, double_chance, etc.
      - side: over, under, 1x, x2, home, away, draw, yes, no...
      - line_bucket: línea exacta normalizada, por ejemplo "2.5".
    """

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


def samples_from_settlements(
    rows: Iterable[dict],
    prob_key: str = "model_prob",
    outcome_key: str = "outcome",
) -> list[CalibrationSample]:
    """
    Construye muestras desde filas liquidadas, excluyendo push y unsettled.

    Espera en cada fila: `prob_key`, `outcome_key` (valor de `Outcome`),
    y opcionalmente `market_family`, `league`, `kickoff_utc`.
    """
    from src.domain.settlement import Outcome, outcome_hit_value

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
        if hit is None:                       # push o unsettled -> no informa
            continue
        ts = row.get("kickoff_utc") or row.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                ts = None
        out.append(
            CalibrationSample(
                prob=float(prob),
                hit_value=float(hit),
                market_family=str(row.get("market_family") or "generic"),
                league=row.get("league"),
                timestamp=ts,
            )
        )
    return out


# ═══════════════════════════════════════════════════════════════════════
# ISOTÓNICA (PAVA)
# ═══════════════════════════════════════════════════════════════════════

def pava(values: Sequence[float], weights: Sequence[float]) -> list[float]:
    """
    Regresión isotónica ponderada por Pool Adjacent Violators.

    Devuelve la secuencia no decreciente más cercana a `values` en mínimos
    cuadrados ponderados. Determinista y O(n).
    """
    if not values:
        return []
    # Cada bloque: [media, peso, nº de puntos originales]
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
    """Un bin de la curva de reliability, con su evidencia."""

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
    """
    Mapa monótono lineal por tramos de probabilidad raw -> calibrada.

    Los nodos incluyen anclas en (0,0) y (1,1) para que la curva esté definida
    en todo el dominio sin extrapolar.
    """

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
        """
        Aplica la calibración. Acepta 0-1 o 0-100 y devuelve en la MISMA escala.
        """
        as_pct = prob > 1.0
        p = prob / 100.0 if as_pct else prob
        p = min(1.0, max(0.0, p))

        y = self._interpolate(p)
        y = min(1.0 - _EPS, max(_EPS, y))
        return y * 100.0 if as_pct else y

    def _interpolate(self, p: float) -> float:
        """
        Interpolación lineal entre nodos observados.

        Fuera del rango cubierto por los bins entrenados se mantiene el valor
        del extremo más cercano. No se extrapola hacia (0, 0) ni (1, 1),
        porque hacerlo puede reintroducir confianza artificial en las colas.
        """
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
                raise ValueError("knots_y no es monótona (calibración inválida)")

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


# ═══════════════════════════════════════════════════════════════════════
# AJUSTE DE UNA CURVA
# ═══════════════════════════════════════════════════════════════════════

def _quantile_edges(probs: Sequence[float], max_bins: int, min_bin: float) -> list[float]:
    """Bordes de bin por cuantiles, garantizando ocupación mínima."""
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

    # Elimina bordes duplicados (predicciones muy concentradas)
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
    """
    Ajusta una curva por Beta-Binomial + isotónica PAVA.

    Mejoras frente a la versión anterior:
      - Los nodos de la curva corresponden solamente a evidencia observada.
      - La extrapolación de extremos queda plana y conservadora.
      - No se fuerzan las anclas (0, 0) y (1, 1), que pueden crear
        sobreconfianza artificial fuera del rango de entrenamiento.
    """
    if not samples:
        return CalibrationCurve.identity(segment)

    prior_curve = prior_curve or CalibrationCurve.identity()

    probs = [sample.normalized_prob() for sample in samples]
    edges = _quantile_edges(
        probs=probs,
        max_bins=max_bins,
        min_bin=min_bin_samples,
    )

    bins: list[ReliabilityBin] = []

    for i in range(len(edges) - 1):
        lo = edges[i]
        hi = edges[i + 1]
        is_last_bin = i == len(edges) - 2

        members = [
            sample
            for sample, prob in zip(samples, probs)
            if (lo <= prob < hi)
            or (is_last_bin and abs(prob - hi) <= 1e-12)
        ]

        if not members:
            continue

        n = sum(sample.weight for sample in members)
        if n <= 0:
            continue

        hits = sum(sample.hit_value * sample.weight for sample in members)
        mean_pred = (
            sum(sample.normalized_prob() * sample.weight for sample in members)
            / n
        )

        prior = prior_curve.apply(mean_pred)
        raw_rate = hits / n

        calibrated = (
            hits + prior_strength * prior
        ) / (
            n + prior_strength
        )

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

        xs = [
            max(_EPS, center_x - 1e-6),
            min(1.0 - _EPS, center_x + 1e-6),
        ]
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

def _clean_segment_value(value: str | None, fallback: str = "generic") -> str:
    text = str(value or fallback).strip().lower()
    text = " ".join(text.split())
    return text or fallback


def family_key(market_family: str | None) -> str:
    return f"family:{_clean_segment_value(market_family)}"


def directional_key(market_family: str | None, side: str | None) -> str | None:
    if not side:
        return None
    return (
        f"family:{_clean_segment_value(market_family)}"
        f"|side:{_clean_segment_value(side)}"
    )



def line_key(
    market_family: str | None,
    side: str | None,
    line_bucket: str | None,
) -> str | None:
    if line_bucket is None:
        return None

    line = str(line_bucket).strip().lower()
    if not line:
        return None

    return (
        f"family:{_clean_segment_value(market_family)}"
        f"|side:{_clean_segment_value(side)}"
        f"|line:{line}"
    )


def league_key(
    league: str | None,
    market_family: str | None = None,
    side: str | None = None,
) -> str | None:
    if not league:
        return None

    key = f"league:{str(league).strip()}"
    if market_family:
        key += f"|family:{_clean_segment_value(market_family)}"
    if side:
        key += f"|side:{_clean_segment_value(side)}"
    return key


@dataclass
class HierarchicalCalibrator:
    """
    Calibrador jerárquico que prioriza evidencia de liga manteniendo control conservador.

    Orden de resolución:
      1. league × family × side
      2. league × family
      3. league (overall)
      4. family × side × line
      5. family × side
      6. family
      7. global
      8. identidad
    """

    curves: dict[str, CalibrationCurve] = field(default_factory=dict)
    prior_strength: float = 35.0
    min_samples: float = 60.0
    min_line_samples: float = 120.0
    min_league_samples: float = 40.0
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
        """
        Devuelve la curva más específica disponible.

        Prioriza los datos de la liga sobre curvas globales conservadoras.
        """
        if league is None and side is not None and (side[0].isupper() or " " in side or side.lower() in ("premier", "laliga", "serie a", "bundesliga", "big", "tiny", "l1")):
            league = side
            side = None

        candidates = (
            league_key(league, market_family, side),
            league_key(league, market_family, None) if market_family else None,
            league_key(league, None, None),
            line_key(market_family, side, line_bucket),
            directional_key(market_family, side),
            family_key(market_family),
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
        """
        Calibra una probabilidad y conserva su escala de entrada.

        Entrada 0-1 -> salida 0-1.
        Entrada 0-100 -> salida 0-100.
        """
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
        return any(
            not curve.is_identity
            for curve in self.curves.values()
        )

    @classmethod
    def fit(
        cls,
        samples: Sequence[CalibrationSample],
        prior_strength: float = 35.0,
        min_samples: float = 60.0,
        min_line_samples: float = 120.0,
        min_league_samples: float | None = None,
        max_bins: int = DEFAULT_MAX_BINS,
        version: str | None = None,
    ) -> "HierarchicalCalibrator":
        """
        Ajusta la jerarquía completa con partial pooling.
        """
        if min_league_samples is None:
            min_league_samples = min(min_samples, 40.0)

        # Prior strength más flexible para segmentos de liga, dando protagonismo a la evidencia real de la competición
        league_prior_strength = max(8.0, prior_strength * 0.4)

        curves: dict[str, CalibrationCurve] = {}
        total_weight = sum(sample.weight for sample in samples)

        global_curve = (
            fit_curve(
                samples=samples,
                prior_curve=None,
                prior_strength=prior_strength,
                max_bins=max_bins,
                segment=ROOT_KEY,
            )
            if total_weight >= min_samples
            else CalibrationCurve.identity(ROOT_KEY)
        )

        curves[ROOT_KEY] = global_curve

        by_family: dict[str, list[CalibrationSample]] = {}
        by_direction: dict[tuple[str, str], list[CalibrationSample]] = {}
        by_line: dict[tuple[str, str, str], list[CalibrationSample]] = {}
        by_league_full: dict[tuple[str, str, str], list[CalibrationSample]] = {}
        by_league_family: dict[tuple[str, str], list[CalibrationSample]] = {}
        by_league_overall: dict[str, list[CalibrationSample]] = {}

        for sample in samples:
            family = _clean_segment_value(sample.market_family)
            side = _clean_segment_value(sample.side)

            by_family.setdefault(family, []).append(sample)
            by_direction.setdefault((family, side), []).append(sample)

            if sample.line_bucket:
                line = str(sample.line_bucket).strip().lower()
                by_line.setdefault((family, side, line), []).append(sample)

            if sample.league:
                lg = str(sample.league).strip()
                by_league_full.setdefault((lg, family, side), []).append(sample)
                by_league_family.setdefault((lg, family), []).append(sample)
                by_league_overall.setdefault(lg, []).append(sample)

        for family, subset in sorted(by_family.items()):
            if sum(item.weight for item in subset) < min_samples:
                continue

            key = family_key(family)

            curves[key] = fit_curve(
                samples=subset,
                prior_curve=global_curve,
                prior_strength=prior_strength,
                max_bins=max_bins,
                segment=key,
            )

        for (family, side), subset in sorted(by_direction.items()):
            if sum(item.weight for item in subset) < min_samples:
                continue

            key = directional_key(family, side)
            parent = curves.get(family_key(family), global_curve)

            curves[key] = fit_curve(
                samples=subset,
                prior_curve=parent,
                prior_strength=prior_strength,
                max_bins=max_bins,
                segment=key,
            )

        for (family, side, line), subset in sorted(by_line.items()):
            if sum(item.weight for item in subset) < min_line_samples:
                continue

            key = line_key(family, side, line)
            parent = curves.get(
                directional_key(family, side),
                curves.get(family_key(family), global_curve),
            )

            curves[key] = fit_curve(
                samples=subset,
                prior_curve=parent,
                prior_strength=prior_strength,
                max_bins=max_bins,
                segment=key,
            )

        # Fit League Overall
        for lg, subset in sorted(by_league_overall.items()):
            if sum(item.weight for item in subset) < min_league_samples:
                continue

            key = league_key(lg)
            if key:
                curves[key] = fit_curve(
                    samples=subset,
                    prior_curve=global_curve,
                    prior_strength=league_prior_strength,
                    max_bins=max_bins,
                    segment=key,
                )

        # Fit League x Family
        for (lg, family), subset in sorted(by_league_family.items()):
            if sum(item.weight for item in subset) < min_league_samples:
                continue

            key = league_key(lg, family)
            if key:
                parent = curves.get(
                    league_key(lg),
                    curves.get(family_key(family), global_curve),
                )
                curves[key] = fit_curve(
                    samples=subset,
                    prior_curve=parent,
                    prior_strength=league_prior_strength,
                    max_bins=max_bins,
                    segment=key,
                )

        # Fit League x Family x Side
        for (lg, family, side), subset in sorted(by_league_full.items()):
            if sum(item.weight for item in subset) < min_league_samples:
                continue

            key = league_key(lg, family, side)
            if key:
                parent = curves.get(
                    league_key(lg, family),
                    curves.get(
                        league_key(lg),
                        curves.get(directional_key(family, side), global_curve),
                    ),
                )
                curves[key] = fit_curve(
                    samples=subset,
                    prior_curve=parent,
                    prior_strength=league_prior_strength,
                    max_bins=max_bins,
                    segment=key,
                )

        fitted_at = datetime.now(timezone.utc).isoformat()

        return cls(
            curves=curves,
            prior_strength=prior_strength,
            min_samples=min_samples,
            min_line_samples=min_line_samples,
            min_league_samples=min_league_samples,
            version=version or datetime.now(timezone.utc).strftime(
                "cal-v2-%Y%m%dT%H%M%SZ"
            ),
            fitted_at=fitted_at,
            metadata={
                "n_samples": total_weight,
                "n_segments": len(curves),
                "format_version": CALIBRATION_FORMAT_VERSION,
                "hierarchy": [
                    "global",
                    "family",
                    "family_side",
                    "family_side_line",
                    "league_family_side",
                ],
                "tail_policy": "flat_observed_tail",
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
            "min_samples": self.min_samples,
            "min_line_samples": self.min_line_samples,
            "min_league_samples": self.min_league_samples,
            "metadata": self.metadata,
            "curves": {
                key: curve.to_dict()
                for key, curve in sorted(self.curves.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HierarchicalCalibrator":
        fmt = int(data.get("format_version", 0))

        if fmt != CALIBRATION_FORMAT_VERSION:
            raise ValueError(
                f"Versión de calibración no soportada: {fmt}. "
                f"Esperada: {CALIBRATION_FORMAT_VERSION}"
            )

        return cls(
            curves={
                key: CalibrationCurve.from_dict(value)
                for key, value in data.get("curves", {}).items()
            },
            prior_strength=float(data.get("prior_strength", 35.0)),
            min_samples=float(data.get("min_samples", 60.0)),
            min_line_samples=float(data.get("min_line_samples", 120.0)),
            min_league_samples=float(data.get("min_league_samples", 80.0)),
            version=str(data.get("version", "unversioned")),
            fitted_at=data.get("fitted_at"),
            activated_at_utc=data.get("activated_at_utc"),
            deactivated_at_utc=data.get("deactivated_at_utc"),
            metadata=data.get("metadata", {}),
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return target

    @classmethod
    def load(cls, path: str | Path) -> "HierarchicalCalibrator":
        source = Path(path)

        return cls.from_dict(
            json.loads(source.read_text(encoding="utf-8"))
        )

    @classmethod
    def identity(cls) -> "HierarchicalCalibrator":
        return cls(
            curves={ROOT_KEY: CalibrationCurve.identity(ROOT_KEY)},
            version="identity",
        )

# ═══════════════════════════════════════════════════════════════════════
# MÉTRICAS DE CALIDAD PROBABILÍSTICA
# ═══════════════════════════════════════════════════════════════════════

def brier_score(probs: Sequence[float], outcomes: Sequence[float]) -> float:
    """Error cuadrático medio de la probabilidad. Menor es mejor."""
    if not probs:
        return float("nan")
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def log_loss(probs: Sequence[float], outcomes: Sequence[float], eps: float = 1e-12) -> float:
    """Log loss (entropía cruzada). Penaliza la sobreconfianza con fuerza."""
    if not probs:
        return float("nan")
    total = 0.0
    for p, o in zip(probs, outcomes):
        p = min(1.0 - eps, max(eps, p))
        total += -(o * math.log(p) + (1.0 - o) * math.log(1.0 - p))
    return total / len(probs)


def expected_calibration_error(
    probs: Sequence[float], outcomes: Sequence[float], n_bins: int = 10
) -> float:
    """
    ECE: desvío absoluto medio entre confianza y acierto, ponderado por bin.
    0 = perfectamente calibrado.
    """
    if not probs:
        return float("nan")
    total = len(probs)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        idx = [
            j for j, p in enumerate(probs)
            if (lo <= p < hi) or (i == n_bins - 1 and abs(p - hi) <= 1e-12)
        ]
        if not idx:
            continue
        conf = sum(probs[j] for j in idx) / len(idx)
        acc = sum(outcomes[j] for j in idx) / len(idx)
        ece += (len(idx) / total) * abs(conf - acc)
    return ece


def reliability_table(
    probs: Sequence[float], outcomes: Sequence[float], n_bins: int = 10
) -> list[dict]:
    """Tabla de reliability: confianza declarada vs acierto observado por bin."""
    rows: list[dict] = []
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        idx = [
            j for j, p in enumerate(probs)
            if (lo <= p < hi) or (i == n_bins - 1 and abs(p - hi) <= 1e-12)
        ]
        if not idx:
            rows.append({"lo": lo, "hi": hi, "n": 0, "confidence": None,
                         "accuracy": None, "gap": None})
            continue
        conf = sum(probs[j] for j in idx) / len(idx)
        acc = sum(outcomes[j] for j in idx) / len(idx)
        rows.append({
            "lo": round(lo, 4), "hi": round(hi, 4), "n": len(idx),
            "confidence": round(conf, 4), "accuracy": round(acc, 4),
            "gap": round(acc - conf, 4),
        })
    return rows


def evaluate(probs: Sequence[float], outcomes: Sequence[float]) -> dict:
    """Resumen de calidad probabilística."""
    return {
        "n": len(probs),
        "brier": brier_score(probs, outcomes),
        "log_loss": log_loss(probs, outcomes),
        "ece": expected_calibration_error(probs, outcomes),
        "mean_prob": sum(probs) / len(probs) if probs else float("nan"),
        "mean_outcome": sum(outcomes) / len(outcomes) if outcomes else float("nan"),
    }


# ═══════════════════════════════════════════════════════════════════════
# WALK-FORWARD OUT-OF-FOLD
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class WalkForwardResult:
    """Predicciones OOF y métricas antes/después de calibrar."""

    raw_probs: list[float] = field(default_factory=list)
    calibrated_probs: list[float] = field(default_factory=list)
    outcomes: list[float] = field(default_factory=list)
    n_folds: int = 0
    skipped: int = 0

    def metrics(self) -> dict:
        return {
            "raw": evaluate(self.raw_probs, self.outcomes),
            "calibrated": evaluate(self.calibrated_probs, self.outcomes),
            "n_folds": self.n_folds,
            "skipped_no_train": self.skipped,
        }

    def improved(self) -> bool:
        """
        Regla de promoción: la calibración solo se acepta si mejora Brier Y
        log loss out-of-sample. Si no, se mantiene el baseline.
        """
        if not self.outcomes:
            return False
        raw, cal = evaluate(self.raw_probs, self.outcomes), evaluate(
            self.calibrated_probs, self.outcomes
        )
        return cal["brier"] <= raw["brier"] and cal["log_loss"] <= raw["log_loss"]


def walk_forward_calibrate(
    samples: Sequence[CalibrationSample],
    n_folds: int = 5,
    prior_strength: float = 35.0,
    min_samples: float = 60.0,
    min_line_samples: float = 120.0,
    min_league_samples: float = 80.0,
    min_train: float = 120.0,
) -> WalkForwardResult:
    """
    Walk-forward estricto por grupos temporales.

    Un mismo timestamp se trata como una unidad indivisible: los picks del
    mismo bloque de kickoff no pueden aparecer parcialmente en train y
    parcialmente en test. Así se evita fuga temporal entre partidos
    simultáneos o recomendaciones procesadas en el mismo lote.
    """
    ordered = sorted(
        [sample for sample in samples if sample.timestamp is not None],
        key=lambda sample: sample.timestamp,
    )
    if not ordered and samples:
        ordered = list(samples)

    result = WalkForwardResult(n_folds=n_folds)

    if not ordered or n_folds < 2:
        result.skipped = len(samples) if samples else 0
        return result

    if len(ordered) < min_train:
        result.skipped = len(samples)
        return result

    grouped: list[list[CalibrationSample]] = []
    current_timestamp = None
    current_group: list[CalibrationSample] = []

    for idx, sample in enumerate(ordered):
        ts = sample.timestamp if sample.timestamp is not None else idx
        if current_timestamp is None or ts == current_timestamp:
            current_group.append(sample)
            current_timestamp = ts
            continue

        grouped.append(current_group)
        current_group = [sample]
        current_timestamp = ts

    if current_group:
        grouped.append(current_group)

    if len(grouped) < n_folds:
        result.skipped = len(ordered)
        return result


    fold_size = max(1, len(grouped) // n_folds)

    for fold_index in range(1, n_folds):
        train_groups = grouped[: fold_index * fold_size]

        if fold_index < n_folds - 1:
            test_groups = grouped[
                fold_index * fold_size:
                (fold_index + 1) * fold_size
            ]
        else:
            test_groups = grouped[fold_index * fold_size:]

        train = [
            sample
            for group in train_groups
            for sample in group
        ]

        test = [
            sample
            for group in test_groups
            for sample in group
        ]

        if not test:
            continue

        if sum(sample.weight for sample in train) < min_train:
            result.skipped += len(test)
            continue

        calibrator = HierarchicalCalibrator.fit(
            samples=train,
            prior_strength=prior_strength,
            min_samples=min_samples,
            min_line_samples=min_line_samples,
            min_league_samples=min_league_samples,
        )

        for sample in test:
            raw_prob = sample.normalized_prob()

            result.raw_probs.append(raw_prob)
            result.calibrated_probs.append(
                calibrator.apply(
                    prob=raw_prob,
                    market_family=sample.market_family,
                    side=sample.side,
                    line_bucket=sample.line_bucket,
                    league=sample.league,
                )
            )
            result.outcomes.append(sample.hit_value)

    return result
