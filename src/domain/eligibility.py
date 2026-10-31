"""
Decisión única de elegibilidad de un pick, con razones inmutables.

El problema que resuelve
───────────────────────
La publicación se decidía recalculando `is_publishable_pick(v)` en varios
puntos del pipeline, y esa función solo comprobaba la blacklist. Secuencia real
en `compare.py`:

    1. Regla estadística bloquea el pick:
           is_rule_blocked = True
           is_publishable  = False
           quality_score   = -1
    2. Más adelante, `_rate_pick_quality` sobrescribe `quality_score`
       (el centinela -1 desaparece).
    3. `is_publishable = is_publishable_pick(v)` se recalcula y, al no mirar
       `is_rule_blocked`, devuelve True.

Resultado: un pick bloqueado se publicaba. El bloqueo era reversible por
accidente, que es justo lo que no puede pasar en una decisión de dinero.

El modelo
─────────
Se distinguen dos clases de motivo, y esa distinción es la corrección:

  · BLOQUEO DURO (pegajoso, irreversible): una prohibición ya emitida sobre
    este pick — blacklist de liga, regla estadística, correlación con otro
    pick del mismo partido, imposibilidad de liquidar. Recalcular NUNCA puede
    limpiarlo. Se acumula por unión de conjuntos, así que la elegibilidad es
    monótona decreciente: solo puede ir de publicable a no publicable.

  · FILTRO BLANDO (recalculable): un umbral sobre valores que legítimamente
    cambian durante el pipeline — rango de cuota, probabilidad mínima, edge,
    calidad del dato, stake. Si la cuota se actualiza, este filtro debe poder
    reevaluarse en ambos sentidos.

Un pick es publicable si y solo si no tiene ningún bloqueo duro y no falla
ningún filtro blando. Ante un dato ausente que impide decidir, se falla
cerrado: no publicable.

Este módulo es dominio puro: no importa FastAPI, pydantic ni compare.py, para
que sea testeable y reutilizable desde backtest, API y reportes por igual.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Iterable, Mapping

# Versión de la política de publicación. Cambiar un umbral obliga a subirla:
# sin esto no se puede saber con qué reglas se publicó un pick histórico.
POLICY_VERSION = "elig-v2.5"


class BlockReason(str, Enum):
    """Motivos por los que un pick no se publica."""

    # ── Bloqueos DUROS: irreversibles una vez emitidos ──────────────
    BLACKLISTED = "blacklisted"
    RULE_BLOCKED = "rule_blocked"
    CORRELATION_BLOCKED = "correlation_blocked"
    UNSETTLEABLE = "unsettleable"
    MANUAL_BLOCK = "manual_block"
    EXPOSURE_LIMIT = "exposure_limit"
    SEGMENT_GOVERNANCE_BLOCKED = "segment_governance_blocked"

    # ── Filtros BLANDOS: recalculables ──────────────────────────────
    ODDS_MISSING = "odds_missing"
    ODDS_TOO_LOW = "odds_too_low"
    ODDS_TOO_HIGH = "odds_too_high"
    PROB_MISSING = "prob_missing"
    PROB_BELOW_THRESHOLD = "prob_below_threshold"
    EDGE_TOO_LOW = "edge_too_low"
    EDGE_TOO_HIGH = "edge_too_high"
    EDGE_MISSING = "edge_missing"
    DATA_QUALITY_TOO_LOW = "data_quality_too_low"
    STAKE_TOO_LOW = "stake_too_low"
    H2H_ZERO_HIT_RATE = "h2h_zero_hit_rate"
    H2H_LOW_HIT_RATE = "h2h_low_hit_rate"
    EMPIRICAL_HIT_RATE_TOO_LOW = "empirical_hit_rate_too_low"
    QUALITY_SCORE_TOO_LOW = "quality_score_too_low"


HARD_BLOCKS: frozenset[BlockReason] = frozenset({
    BlockReason.BLACKLISTED,
    BlockReason.RULE_BLOCKED,
    BlockReason.CORRELATION_BLOCKED,
    BlockReason.UNSETTLEABLE,
    BlockReason.MANUAL_BLOCK,
    BlockReason.EXPOSURE_LIMIT,
    BlockReason.SEGMENT_GOVERNANCE_BLOCKED,
})


def is_hard(reason: BlockReason | str) -> bool:
    try:
        return BlockReason(reason) in HARD_BLOCKS
    except ValueError:
        # Un motivo desconocido se trata como duro: fallar cerrado.
        return True


# Texto legible por humanos. La UI y los reportes no deben inventar el suyo.
REASON_LABELS: dict[BlockReason, str] = {
    BlockReason.BLACKLISTED: "Mercado en blacklist para esta liga",
    BlockReason.RULE_BLOCKED: "Bloqueado por regla estadística",
    BlockReason.CORRELATION_BLOCKED: "Correlacionado con otro pick del partido",
    BlockReason.UNSETTLEABLE: "No se puede liquidar: falta la estadística necesaria",
    BlockReason.MANUAL_BLOCK: "Bloqueado manualmente",
    BlockReason.EXPOSURE_LIMIT: "Supera el límite de exposición del evento",
    BlockReason.SEGMENT_GOVERNANCE_BLOCKED: "Bloqueado por gobernanza de segmento (deterioro/drift)",
    BlockReason.ODDS_MISSING: "Sin cuota disponible",
    BlockReason.ODDS_TOO_LOW: "Cuota por debajo del mínimo",
    BlockReason.ODDS_TOO_HIGH: "Cuota por encima del máximo",
    BlockReason.PROB_MISSING: "Sin probabilidad calculada",
    BlockReason.PROB_BELOW_THRESHOLD: "Probabilidad por debajo del umbral del mercado",
    BlockReason.EDGE_TOO_LOW: "Edge insuficiente",
    BlockReason.EDGE_TOO_HIGH: "Edge implausible (probable error de dato)",
    BlockReason.EDGE_MISSING: "Sin edge calculado",
    BlockReason.DATA_QUALITY_TOO_LOW: "Calidad de dato insuficiente",
    BlockReason.STAKE_TOO_LOW: "Stake por debajo del mínimo",
    BlockReason.H2H_ZERO_HIT_RATE: "0% de acierto en H2H con muestra disponible",
    BlockReason.H2H_LOW_HIT_RATE: "H2H con acierto bajo y muestra suficiente (riesgo elevado)",
    BlockReason.EMPIRICAL_HIT_RATE_TOO_LOW: "Hit rate histórico empírico insuficiente para ser pick de calidad",
    BlockReason.QUALITY_SCORE_TOO_LOW: "Score de calidad del pick por debajo del umbral mínimo de categoría",
}


def describe(reason: BlockReason | str) -> str:
    try:
        return REASON_LABELS.get(BlockReason(reason), str(reason))
    except ValueError:
        return str(reason)


# ═══════════════════════════════════════════════════════════════════════
# POLÍTICA DE PUBLICACIÓN
# ═══════════════════════════════════════════════════════════════════════

# Familias con resultado binario claro: se exige probabilidad alta.
BINARY_FAMILIES: frozenset[str] = frozenset({"result", "btts", "goals"})
# Familias de conteo con varianza alta: el umbral de probabilidad es menor
# porque la magnitud es grande y el over/under se reparte distinto.
HIGH_VARIANCE_FAMILIES: frozenset[str] = frozenset(
    {"cards", "shots", "shots_target", "fouls", "corners"}
)


@dataclass(frozen=True)
class PublicationThresholds:
    """Umbrales de publicación, versionados y en un solo sitio."""

    min_odds: float = 1.30
    max_odds: float = 2.80
    min_prob_binary: float = 50.0
    min_prob_high_variance: float = 25.0
    min_prob_default: float = 25.0
    min_edge: float = 2.0
    min_edge_high_threshold: float = 10.0
    max_edge: float = 25.0  # Techo global de edge
    max_edge_high_prob_threshold: float = 67.0  # Excepción: prob calibrada >= 67% permite edge > 25%
    min_data_quality: float = 50.0
    min_stake_units: float = 0.0
    # H2H: nunca bloquear con n < 8 (requisito del planning). Con n >= 8 se aplica
    # shrinkage Beta-Binomial y solo se usa como penalización de fiabilidad, no bloqueo duro.
    block_on_zero_h2h: bool = True
    block_on_low_h2h: bool = True
    min_h2h_hit_rate_block: float = 25.0
    # Aumentado a 8: el planning exige nunca bloquear por H2H bruto con n < 8.
    min_h2h_samples_for_block: int = 8
    low_h2h_families: frozenset[str] = frozenset({"double_chance", "doublechance"})

    # ── Hit Rate Empírico Mínimo ──
    # Si hay muestra histórica suficiente de la temporada (ej. n >= 5),
    # el pick se descarta si su tasa de acierto real es inferior al 35% (o menor que la cuota amerite).
    min_empirical_hit_rate: float = 35.0
    min_empirical_samples: int = 5

    # ── Score de Calidad Mínimo Diferenciado por Categoría ──
    min_quality_score_standard: float = 33.0
    min_quality_score_underdog: float = 22.0
    version: str = "elig-v2.5"

    def min_prob_for(self, market_family: str | None) -> float:
        fam = (market_family or "generic").lower()
        if fam in {"result", "btts", "goals"}:
            return self.min_prob_binary
        if fam in {"cards", "shots", "shots_target", "fouls", "corners"}:
            return self.min_prob_high_variance
        return self.min_prob_default

    def min_edge_for(self, market_family: str | None) -> float:
        fam = (market_family or "generic").lower()
        if fam in {"double_chance", "corners"}:
            return self.min_edge_high_threshold
        return self.min_edge


DEFAULT_THRESHOLDS = PublicationThresholds()


# ═══════════════════════════════════════════════════════════════════════
# ENTRADA
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PickSnapshot:
    """
    Los datos mínimos para decidir elegibilidad.

    Es un DTO plano en lugar de `ValueIndicator` para que el dominio no dependa
    de pydantic ni de la capa API, y para poder evaluar picks que vienen como
    dict desde la BD histórica.
    """

    market_family: str = "generic"
    odds: float | None = None
    prob: float | None = None
    edge: float | None = None
    data_quality_score: float | None = None
    stake_units: float | None = None
    h2h_hit_rate: float | None = None
    h2h_raw_hit_rate: float | None = None
    h2h_hits: int | None = None
    h2h_samples: int = 0
    selection: str = ""
    empirical_hit_rate: float | None = None
    hit_rate_samples: int = 0
    quality_score: float | None = None
    is_underdog: bool = False
    min_edge_add: float = 0.0

    @staticmethod
    def _get(src: Any, *names: str, default=None):
        for n in names:
            if isinstance(src, Mapping):
                if n in src and src[n] is not None:
                    return src[n]
            else:
                v = getattr(src, n, None)
                if v is not None:
                    return v
        return default

    @classmethod
    def from_pick(cls, src: Any, market_family: str | None = None) -> "PickSnapshot":
        """
        Construye el snapshot desde un `ValueIndicator` o un dict.

        La probabilidad usada prioriza `final_prob` (mezcla calibrada + mercado),
        luego `calibrated_prob` y finalmente `model_prob`.
        El edge prioriza `edge_final` > `edge_calibrated` > `edge`.
        Esto garantiza que la elegiblidad usa la mejor estimación disponible.
        """
        # final_prob = calibración + blend de mercado; es la estimación más informada
        prob = cls._get(src, "final_prob", "finalProb")
        if prob is None:
            prob = cls._get(src, "calibrated_prob", "calibratedProb")
        if prob is None:
            prob = cls._get(src, "model_prob", "modelProb")

        # edge_final > edge_calibrated > edge (mismo principio de prioridad)
        edge = cls._get(src, "edge_final", "edgeFinal")
        if edge is None:
            edge = cls._get(src, "edge_calibrated", "edgeCalibrated")
        if edge is None:
            edge = cls._get(src, "edge")

        fam = market_family or cls._get(src, "market_family", "marketFamily") or "generic"
        raw_hits = cls._get(src, "h2h_hits", "h2hHits")

        # Hit rate empírico (combinado o promedio home/away si viene)
        emp_hr = cls._get(src, "empirical_hit_rate", "empiricalHitRate")
        if emp_hr is None:
            h_hr = cls._get(src, "home_hit_rate", "homeHitRate")
            a_hr = cls._get(src, "away_hit_rate", "awayHitRate")
            if h_hr is not None and a_hr is not None:
                emp_hr = (float(h_hr) + float(a_hr)) / 2.0
            elif h_hr is not None:
                emp_hr = float(h_hr)
            elif a_hr is not None:
                emp_hr = float(a_hr)

        emp_samples = cls._get(src, "hit_rate_samples", "hitRateSamples", default=0)
        if not emp_samples:
            h_cnt = cls._get(src, "home_matches_count", "homeMatchesCount", default=0) or 0
            a_cnt = cls._get(src, "away_matches_count", "awayMatchesCount", default=0) or 0
            emp_samples = (int(h_cnt) if h_cnt else 0) + (int(a_cnt) if a_cnt else 0)

        # Determinar si es underdog para aplicar el umbral diferenciado
        is_und = bool(cls._get(src, "is_underdog", "isUnderdog", default=False))
        if not is_und:
            odds_val = _as_float(cls._get(src, "odds"))
            if odds_val is not None and odds_val > 2.50:
                is_und = True

        return cls(
            market_family=str(fam),
            odds=_as_float(cls._get(src, "odds")),
            prob=_as_float(prob),
            edge=_as_float(edge),
            data_quality_score=_as_float(cls._get(src, "data_quality_score", "dataQualityScore")),
            stake_units=_as_float(cls._get(src, "stake_units", "stakeUnits")),
            h2h_hit_rate=_as_float(cls._get(src, "h2h_hit_rate", "h2hHitRate")),
            h2h_raw_hit_rate=_as_float(cls._get(src, "h2h_raw_hit_rate", "h2hRawHitRate")),
            h2h_hits=int(_as_float(raw_hits)) if raw_hits is not None else None,
            h2h_samples=int(_as_float(cls._get(src, "h2h_samples", "h2hSamples", default=0)) or 0),
            selection=str(cls._get(src, "selection", default="") or ""),
            empirical_hit_rate=_as_float(emp_hr),
            hit_rate_samples=int(_as_float(emp_samples) or 0),
            quality_score=_as_float(cls._get(src, "quality_score", "qualityScore")),
            is_underdog=is_und,
            min_edge_add=float(cls._get(src, "min_edge_add", "minEdgeAdd", default=0.0) or 0.0),
        )


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════════════
# DECISIÓN
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EligibilityDecision:
    """
    Resultado inmutable de evaluar la elegibilidad.

    `hard_blocks` solo puede CRECER: es la garantía de que un bloqueo no se
    revierte. `soft_failures` se recalcula en cada evaluación.
    """

    hard_blocks: frozenset[BlockReason] = frozenset()
    soft_failures: frozenset[BlockReason] = frozenset()
    policy_version: str = POLICY_VERSION

    # ── consulta ────────────────────────────────────────────────────
    @property
    def publishable(self) -> bool:
        return not self.hard_blocks and not self.soft_failures

    @property
    def is_hard_blocked(self) -> bool:
        return bool(self.hard_blocks)

    @property
    def blocks(self) -> frozenset[BlockReason]:
        return self.hard_blocks | self.soft_failures

    @property
    def reasons(self) -> tuple[str, ...]:
        """Motivos ordenados de forma estable: duros primero, luego blandos."""
        return tuple(
            r.value for r in
            sorted(self.hard_blocks, key=lambda r: r.value)
            + sorted(self.soft_failures, key=lambda r: r.value)
        )

    @property
    def descriptions(self) -> tuple[str, ...]:
        return tuple(describe(r) for r in self.reasons)

    # ── composición monótona ────────────────────────────────────────
    def with_hard_block(self, *reasons: BlockReason | str) -> "EligibilityDecision":
        """Añade bloqueos duros. Nunca quita ninguno."""
        added = {_coerce_reason(r) for r in reasons}
        return replace(self, hard_blocks=self.hard_blocks | added)

    def merge(self, other: "EligibilityDecision") -> "EligibilityDecision":
        """
        Une dos decisiones sobre el mismo pick.

        Los bloqueos duros se unen (nunca se pierden). Los filtros blandos se
        toman de `other`, que es la evaluación más reciente.
        """
        return EligibilityDecision(
            hard_blocks=self.hard_blocks | other.hard_blocks,
            soft_failures=other.soft_failures,
            policy_version=other.policy_version,
        )

    def quality_score_sentinel(self, computed: int | float | None) -> int | float | None:
        """
        Devuelve el `quality_score` que corresponde publicar.

        Un pick con bloqueo duro conserva el centinela -1 aunque el pipeline
        recalcule su calidad más adelante. Ese sobrescribir era la mitad del
        bug original.
        """
        return -1 if self.is_hard_blocked else computed

    # ── serialización ───────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "publishable": self.publishable,
            "hard_blocks": sorted(r.value for r in self.hard_blocks),
            "soft_failures": sorted(r.value for r in self.soft_failures),
            "reasons": list(self.reasons),
            "descriptions": list(self.descriptions),
            "policy_version": self.policy_version,
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "EligibilityDecision":
        return cls(
            hard_blocks=frozenset(_coerce_reason(r) for r in d.get("hard_blocks", [])),
            soft_failures=frozenset(_coerce_reason(r) for r in d.get("soft_failures", [])),
            policy_version=str(d.get("policy_version", POLICY_VERSION)),
        )

    @classmethod
    def from_reasons(cls, reasons: Iterable[BlockReason | str]) -> "EligibilityDecision":
        """
        Reconstruye una decisión desde una lista plana de motivos, separando
        duros de blandos. Útil para rehidratar desde la BD.
        """
        hard: set[BlockReason] = set()
        soft: set[BlockReason] = set()
        for r in reasons:
            reason = _coerce_reason(r)
            (hard if reason in HARD_BLOCKS else soft).add(reason)
        return cls(hard_blocks=frozenset(hard), soft_failures=frozenset(soft))


def _coerce_reason(r: BlockReason | str) -> BlockReason:
    if isinstance(r, BlockReason):
        return r
    try:
        return BlockReason(str(r))
    except ValueError:
        # Motivo desconocido -> se conserva como bloqueo duro genérico en vez
        # de descartarlo silenciosamente.
        return BlockReason.MANUAL_BLOCK


# ═══════════════════════════════════════════════════════════════════════
# EVALUACIÓN
# ═══════════════════════════════════════════════════════════════════════

def evaluate_soft_filters(
    snapshot,  # PickSnapshot
    thresholds: PublicationThresholds = DEFAULT_THRESHOLDS,
) -> frozenset:
    """Aplica los umbrales recalculables. No conoce los bloqueos duros."""
    from src.domain.eligibility import BlockReason  # evitar import circular en el snippet

    fails: set = set()

    if snapshot.odds is None:
        fails.add(BlockReason.ODDS_MISSING)
    elif snapshot.odds < thresholds.min_odds:
        fails.add(BlockReason.ODDS_TOO_LOW)
    elif snapshot.odds > thresholds.max_odds:
        fails.add(BlockReason.ODDS_TOO_HIGH)

    if snapshot.prob is None:
        fails.add(BlockReason.PROB_MISSING)
    elif snapshot.prob < thresholds.min_prob_for(snapshot.market_family):
        fails.add(BlockReason.PROB_BELOW_THRESHOLD)

    if snapshot.edge is None:
        fails.add(BlockReason.EDGE_MISSING)
    else:
        required_min_edge = thresholds.min_edge_for(snapshot.market_family) + (snapshot.min_edge_add or 0.0)
        if snapshot.edge < required_min_edge:
            fails.add(BlockReason.EDGE_TOO_LOW)
        elif snapshot.edge > thresholds.max_edge:
            # Edge > 25% se descarta por alto riesgo a menos que la probabilidad (calibrada) sea >= 67%
            prob_val = snapshot.prob if snapshot.prob is not None else 0.0
            prob_pct = prob_val * 100.0 if 0.0 < prob_val <= 1.0 else prob_val
            if prob_pct < thresholds.max_edge_high_prob_threshold:
                fails.add(BlockReason.EDGE_TOO_HIGH)

    if (
        snapshot.data_quality_score is not None
        and snapshot.data_quality_score < thresholds.min_data_quality
    ):
        fails.add(BlockReason.DATA_QUALITY_TOO_LOW)

    if (
        snapshot.stake_units is not None
        and snapshot.stake_units < thresholds.min_stake_units
    ):
        fails.add(BlockReason.STAKE_TOO_LOW)

    # H2H: aplicar shrinkage Beta-Binomial y respetar umbral mínimo de muestras (n >= 8).
    # Nunca bloquear por H2H bruto con n < 8: shrunk_h2h_rate absorbe la incertidumbre.
    from src.models.h2h_shrinkage import shrunk_h2h_rate

    effective_h2h_hr = snapshot.h2h_hit_rate if snapshot.h2h_hit_rate is not None else snapshot.h2h_raw_hit_rate
    if (
        thresholds.block_on_zero_h2h
        and effective_h2h_hr is not None
        and snapshot.h2h_samples >= thresholds.min_h2h_samples_for_block
    ):
        if effective_h2h_hr == 0.0 or (snapshot.h2h_hits is not None and snapshot.h2h_hits == 0):
            fails.add(BlockReason.H2H_ZERO_HIT_RATE)

    # H2H bajo (no cero) en familias específicas: requiere n >= 8 obligatoriamente
    fam = (snapshot.market_family or "generic").lower()
    if (
        thresholds.block_on_low_h2h
        and fam in thresholds.low_h2h_families
        and effective_h2h_hr is not None
        and effective_h2h_hr > 0.0
        and effective_h2h_hr <= thresholds.min_h2h_hit_rate_block
        and snapshot.h2h_samples >= thresholds.min_h2h_samples_for_block  # nunca con n < 8
    ):
        fails.add(BlockReason.H2H_LOW_HIT_RATE)

    # ── Hit Rate Empírico de Temporada (Filtro de Calidad Real) ──
    # Si hay muestra suficiente (n >= min_empirical_samples), el pick no puede
    # tener un hit rate ridículamente bajo (ej. 5% - 30%) que contradiga la calidad del pick.
    if (
        snapshot.empirical_hit_rate is not None
        and snapshot.hit_rate_samples >= thresholds.min_empirical_samples
        and snapshot.empirical_hit_rate < thresholds.min_empirical_hit_rate
    ):
        fails.add(BlockReason.EMPIRICAL_HIT_RATE_TOO_LOW)

    # ── Score de Calidad Integral ──
    # NOTA: quality_score ya NO bloquea picks. Se calcula y almacena únicamente
    # como métrica de análisis de datos posterior. Los picks solo se bloquean
    # por blacklist, correlación o ausencia de valor (EV/edge/stake).
    # La verificación QUALITY_SCORE_TOO_LOW se ha eliminado intencionadamente.

    return frozenset(fails)


def evaluate_eligibility(
    snapshot: PickSnapshot,
    previous: EligibilityDecision | None = None,
    hard_blocks: Iterable[BlockReason | str] = (),
    thresholds: PublicationThresholds = DEFAULT_THRESHOLDS,
) -> EligibilityDecision:
    """
    Decisión única de elegibilidad.

    `previous` es la decisión anterior sobre el MISMO pick: sus bloqueos duros
    se arrastran siempre. `hard_blocks` son bloqueos nuevos que se emiten en
    esta pasada. El resultado nunca puede ser más permisivo que `previous`.
    """
    carried = previous.hard_blocks if previous else frozenset()
    new_hard = frozenset(_coerce_reason(r) for r in hard_blocks)

    return EligibilityDecision(
        hard_blocks=carried | new_hard,
        soft_failures=evaluate_soft_filters(snapshot, thresholds),
        policy_version=thresholds.version,
    )


# ═══════════════════════════════════════════════════════════════════════
# APLICACIÓN GENÉRICA SOBRE UN PICK (dict u objeto)
# ═══════════════════════════════════════════════════════════════════════

_FLAG_FOR_REASON: dict[BlockReason, str] = {
    BlockReason.BLACKLISTED: "is_blacklisted",
    BlockReason.RULE_BLOCKED: "is_rule_blocked",
    BlockReason.CORRELATION_BLOCKED: "correlation_blocked",
}


def _pget(pick: Any, key: str, default=None):
    if isinstance(pick, dict):
        return pick.get(key, default)
    return getattr(pick, key, default)


def _pset(pick: Any, key: str, value) -> None:
    if isinstance(pick, dict):
        pick[key] = value
    else:
        setattr(pick, key, value)


def read_hard_blocks(pick: Any) -> frozenset[BlockReason]:
    """
    Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.

    Consulta el registro explícito Y los flags booleanos legacy, para que un
    bloqueo emitido por código que solo movía el flag no se pierda.
    """
    recorded = EligibilityDecision.from_reasons(
        _pget(pick, "eligibility_hard_blocks", []) or []
    ).hard_blocks
    return recorded | hard_blocks_from_flags(
        is_blacklisted=bool(_pget(pick, "is_blacklisted", False)),
        is_rule_blocked=bool(_pget(pick, "is_rule_blocked", False)),
        correlation_blocked=bool(_pget(pick, "correlation_blocked", False)),
    )


def record_hard_block(
    pick: Any,
    *reasons: BlockReason | str,
    detail: str | None = None,
) -> frozenset[BlockReason]:
    """
    Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible.

    Escribe el registro acumulado, sincroniza los flags legacy y apaga las
    marcas de publicación. Pensado para capas que no pueden importar
    `compare.py` (motor de reglas, backtest) sin crear un ciclo.

    Devuelve el conjunto completo de bloqueos duros tras la operación.
    """
    blocks = read_hard_blocks(pick) | {_coerce_reason(r) for r in reasons}

    _pset(pick, "eligibility_hard_blocks", sorted(r.value for r in blocks))
    for reason in blocks:
        flag = _FLAG_FOR_REASON.get(reason)
        if flag:
            _pset(pick, flag, True)

    _pset(pick, "is_publishable", False)
    _pset(pick, "is_value", False)
    _pset(pick, "is_underdog", False)
    _pset(pick, "quality_score", -1)
    if detail:
        _pset(pick, "rule_blocked_reason", detail)

    return blocks


def is_hard_blocked(pick: Any) -> bool:
    """True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse."""
    return bool(read_hard_blocks(pick))


def hard_blocks_from_flags(
    is_blacklisted: bool = False,
    is_rule_blocked: bool = False,
    correlation_blocked: bool = False,
    unsettleable: bool = False,
    exposure_limited: bool = False,
) -> frozenset[BlockReason]:
    """
    Traduce los flags booleanos legacy a motivos de bloqueo.

    Permite adoptar `EligibilityDecision` sin migrar de golpe los campos
    booleanos que ya persisten en BD y consume el frontend.
    """
    out: set[BlockReason] = set()
    if is_blacklisted:
        out.add(BlockReason.BLACKLISTED)
    if is_rule_blocked:
        out.add(BlockReason.RULE_BLOCKED)
    if correlation_blocked:
        out.add(BlockReason.CORRELATION_BLOCKED)
    if unsettleable:
        out.add(BlockReason.UNSETTLEABLE)
    if exposure_limited:
        out.add(BlockReason.EXPOSURE_LIMIT)
    return frozenset(out)