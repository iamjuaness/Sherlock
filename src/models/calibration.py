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
    Una observación para calibrar.

    `prob` es la probabilidad RAW del modelo en 0-1 (o 0-100, se autodetecta).
    `hit_value` es 1.0 (acierto), 0.5 (half-win) o 0.0 (fallo). Un push debe
    excluirse antes de llegar aquí (usar `outcome_hit_value`, que devuelve None).
    """

    prob: float
    hit_value: float
    market_family: str = "generic"
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
    Ajusta una curva de calibración por Beta-Binomial + isotónica.

    `prior_curve` es el nivel padre de la jerarquía. Si es None se usa la
    identidad, es decir, se asume que el modelo ya está calibrado y solo la
    evidencia puede moverlo.
    """
    if not samples:
        return CalibrationCurve.identity(segment)

    prior_curve = prior_curve or CalibrationCurve.identity()
    probs = [s.normalized_prob() for s in samples]
    edges = _quantile_edges(probs, max_bins, min_bin_samples)

    bins: list[ReliabilityBin] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        last = i == len(edges) - 2
        members = [
            s for s, p in zip(samples, probs)
            if (lo <= p < hi) or (last and abs(p - hi) <= 1e-12)
        ]
        if not members:
            continue

        n = sum(s.weight for s in members)
        hits = sum(s.hit_value * s.weight for s in members)
        mean_pred = sum(s.normalized_prob() * s.weight for s in members) / n if n else (lo + hi) / 2

        prior = prior_curve.apply(mean_pred)
        raw_rate = hits / n if n > 0 else None
        # Media posterior Beta-Binomial: shrinkage hacia el padre.
        calibrated = (hits + prior_strength * prior) / (n + prior_strength)

        bins.append(
            ReliabilityBin(
                lo=lo, hi=hi, n=n, hits=hits, mean_pred=mean_pred,
                raw_rate=raw_rate, prior=prior, calibrated=calibrated,
            )
        )

    if not bins:
        return CalibrationCurve.identity(segment)

    # Monotonía: PAVA ponderado por la evidencia efectiva (n + κ).
    bins.sort(key=lambda b: b.mean_pred)
    smoothed = pava(
        [b.calibrated for b in bins],
        [b.n + prior_strength for b in bins],
    )
    bins = [
        ReliabilityBin(
            lo=b.lo, hi=b.hi, n=b.n, hits=b.hits, mean_pred=b.mean_pred,
            raw_rate=b.raw_rate, prior=b.prior, calibrated=y,
        )
        for b, y in zip(bins, smoothed)
    ]

    xs = [0.0] + [b.mean_pred for b in bins] + [1.0]
    ys = [0.0] + [b.calibrated for b in bins] + [1.0]

    # Fuerza monotonía global incluyendo las anclas.
    for i in range(1, len(ys)):
        if ys[i] < ys[i - 1]:
            ys[i] = ys[i - 1]
    for i in range(1, len(xs)):
        if xs[i] < xs[i - 1]:
            xs[i] = xs[i - 1]

    curve = CalibrationCurve(
        knots_x=tuple(xs), knots_y=tuple(ys),
        n_samples=sum(s.weight for s in samples),
        bins=tuple(bins), segment=segment,
    )
    curve.validate()
    return curve


# ═══════════════════════════════════════════════════════════════════════
# CALIBRADOR JERÁRQUICO
# ═══════════════════════════════════════════════════════════════════════

def family_key(market_family: str) -> str:
    return f"family:{market_family or 'generic'}"


def league_key(league: str | None, market_family: str) -> str:
    return f"league:{league or '?'}|family:{market_family or 'generic'}"


@dataclass
class HierarchicalCalibrator:
    """
    Calibrador de 3 niveles con partial pooling.

    Resolución en `apply`: liga×familia -> familia -> global -> identidad.
    Se usa la curva MÁS ESPECÍFICA que exista; cada nivel ya está encogido
    hacia su padre, así que no hay riesgo de saltos por falta de muestra.
    """

    curves: dict[str, CalibrationCurve] = field(default_factory=dict)
    prior_strength: float = DEFAULT_PRIOR_STRENGTH
    min_samples: float = DEFAULT_MIN_SAMPLES
    version: str = "unversioned"
    fitted_at: str | None = None
    metadata: dict = field(default_factory=dict)

    # ── aplicación ──────────────────────────────────────────────────
    def resolve_curve(
        self, market_family: str | None = None, league: str | None = None
    ) -> CalibrationCurve:
        for key in (
            league_key(league, market_family or "generic") if league else None,
            family_key(market_family or "generic"),
            ROOT_KEY,
        ):
            if key and key in self.curves:
                return self.curves[key]
        return CalibrationCurve.identity()

    def apply(
        self,
        prob: float,
        market_family: str | None = None,
        league: str | None = None,
    ) -> float:
        """
        Calibra una probabilidad. Acepta y devuelve en la misma escala (0-1 o 0-100).

        Sin artefacto entrenado devuelve `prob` sin tocar: degradar a identidad
        es seguro, inventar una corrección no lo es.
        """
        if prob is None:
            return prob
        return self.resolve_curve(market_family, league).apply(prob)

    @property
    def is_trained(self) -> bool:
        return any(not c.is_identity for c in self.curves.values())

    # ── ajuste ──────────────────────────────────────────────────────
    @classmethod
    def fit(
        cls,
        samples: Sequence[CalibrationSample],
        prior_strength: float = DEFAULT_PRIOR_STRENGTH,
        min_samples: float = DEFAULT_MIN_SAMPLES,
        max_bins: int = DEFAULT_MAX_BINS,
        version: str | None = None,
    ) -> "HierarchicalCalibrator":
        """
        Ajusta la jerarquía completa: global -> familia -> liga×familia.

        Un segmento solo recibe curva propia si tiene al menos `min_samples`
        observaciones; en caso contrario hereda la del padre.
        """
        curves: dict[str, CalibrationCurve] = {}

        total_w = sum(s.weight for s in samples)
        global_curve = (
            fit_curve(samples, None, prior_strength, max_bins, segment=ROOT_KEY)
            if total_w >= min_samples
            else CalibrationCurve.identity()
        )
        curves[ROOT_KEY] = global_curve

        # Nivel 2: familia de mercado
        by_family: dict[str, list[CalibrationSample]] = {}
        for s in samples:
            by_family.setdefault(s.market_family or "generic", []).append(s)

        for fam, subset in sorted(by_family.items()):
            key = family_key(fam)
            if sum(s.weight for s in subset) < min_samples:
                continue
            curves[key] = fit_curve(
                subset, global_curve, prior_strength, max_bins, segment=key
            )

        # Nivel 3: liga × familia
        by_league: dict[tuple[str | None, str], list[CalibrationSample]] = {}
        for s in samples:
            if not s.league:
                continue
            by_league.setdefault((s.league, s.market_family or "generic"), []).append(s)

        for (lg, fam), subset in sorted(by_league.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
            if sum(s.weight for s in subset) < min_samples:
                continue
            key = league_key(lg, fam)
            parent = curves.get(family_key(fam), global_curve)
            curves[key] = fit_curve(
                subset, parent, prior_strength, max_bins, segment=key
            )

        return cls(
            curves=curves,
            prior_strength=prior_strength,
            min_samples=min_samples,
            version=version or datetime.now(timezone.utc).strftime("cal-%Y%m%dT%H%M%SZ"),
            fitted_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "n_samples": total_w,
                "n_segments": len(curves),
                "format_version": CALIBRATION_FORMAT_VERSION,
            },
        )

    # ── persistencia ────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "format_version": CALIBRATION_FORMAT_VERSION,
            "version": self.version,
            "fitted_at": self.fitted_at,
            "prior_strength": self.prior_strength,
            "min_samples": self.min_samples,
            "metadata": self.metadata,
            "curves": {k: c.to_dict() for k, c in sorted(self.curves.items())},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HierarchicalCalibrator":
        fmt = int(d.get("format_version", 0))
        if fmt != CALIBRATION_FORMAT_VERSION:
            raise ValueError(
                f"Versión de formato de calibración no soportada: {fmt} "
                f"(esperada {CALIBRATION_FORMAT_VERSION})"
            )
        return cls(
            curves={k: CalibrationCurve.from_dict(v) for k, v in d.get("curves", {}).items()},
            prior_strength=float(d.get("prior_strength", DEFAULT_PRIOR_STRENGTH)),
            min_samples=float(d.get("min_samples", DEFAULT_MIN_SAMPLES)),
            version=str(d.get("version", "unversioned")),
            fitted_at=d.get("fitted_at"),
            metadata=d.get("metadata", {}),
        )

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        return p

    @classmethod
    def load(cls, path: str | Path) -> "HierarchicalCalibrator":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def identity(cls) -> "HierarchicalCalibrator":
        return cls(curves={ROOT_KEY: CalibrationCurve.identity()}, version="identity")


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
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    min_samples: float = DEFAULT_MIN_SAMPLES,
    min_train: float = DEFAULT_MIN_SAMPLES,
) -> WalkForwardResult:
    """
    Evaluación walk-forward estricta, ordenada por tiempo.

    El fold k se calibra SOLO con los datos anteriores a él. Nunca se evalúa
    una predicción con una curva que vio su propio resultado, que es el
    error que invalidaba el ROI histórico del notebook.

    Las muestras sin timestamp se ordenan al final de forma estable, pero para
    una evaluación honesta deberían tener kickoff UTC.
    """
    ordered = sorted(
        samples,
        key=lambda s: (
            s.timestamp is None,
            s.timestamp or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    n = len(ordered)
    res = WalkForwardResult(n_folds=n_folds)
    if n == 0 or n_folds < 2:
        return res

    fold_size = max(1, n // n_folds)
    for k in range(1, n_folds):
        train = ordered[: k * fold_size]
        test = ordered[k * fold_size : (k + 1) * fold_size] if k < n_folds - 1 else ordered[k * fold_size :]
        if not test:
            continue
        if sum(s.weight for s in train) < min_train:
            res.skipped += len(test)
            continue

        cal = HierarchicalCalibrator.fit(
            train, prior_strength=prior_strength, min_samples=min_samples
        )
        for s in test:
            p = s.normalized_prob()
            res.raw_probs.append(p)
            res.calibrated_probs.append(
                cal.apply(p, s.market_family, s.league)
            )
            res.outcomes.append(s.hit_value)

    return res
