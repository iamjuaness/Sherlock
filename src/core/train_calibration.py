"""
Entrenamiento del calibrador de Sherlock a partir de picks liquidados.

Flujo
─────
  analysis_history (BD)
      -> picks_calculados (JSON) + columnas final_*
      -> resolución de cada pick con la lógica de mercados YA existente
         (`main.py::_check_pick_success`, no se duplica)
      -> Outcome canónico (motor único de settlement)
      -> muestras de calibración
      -> validación walk-forward out-of-fold
      -> promoción del artefacto SOLO si mejora Brier Y log loss

Regla de promoción
──────────────────
El artefacto NO se publica si no mejora el error out-of-sample. Una calibración
que no mejora es una calibración que sobreajusta, y el coste de sobreajustar
aquí es apostar con probabilidades falsas. Ante la duda, identidad.

Anti-fuga temporal
──────────────────
Cada muestra lleva `match_date` como timestamp y el walk-forward ordena por él,
así que el fold k solo ve partidos anteriores. Los picks sin fecha se descartan
con `--require-timestamp` (recomendado): sin fecha no se puede garantizar que
no haya fuga.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.domain.settlement import Outcome, outcome_from_legacy, outcome_hit_value
from src.domain.market_taxonomy import (
    CATEGORICAL_FAMILIES,
    normalize_market_family,
    normalize_market_side,
    line_bucket_for,
    extract_market_line,
)
from src.models.calibration import (
    DEFAULT_MIN_SAMPLES,
    DEFAULT_PRIOR_STRENGTH,
    CalibrationSample,
    HierarchicalCalibrator,
    WalkForwardResult,
    evaluate,
    walk_forward_calibrate,
)

logger = logging.getLogger("sherlock.train_calibration")

DEFAULT_ARTIFACT_PATH = Path("data/calibration/active.json")
HISTORY_DIRNAME = "history"


def history_dir_for(artifact_path: Path | str) -> Path:
    """
    Directorio de versiones ANTIGUAS, siempre junto al artefacto activo.

    Se deriva de la ruta del artefacto en lugar de una constante global: con una
    constante, entrenar hacia una ruta temporal seguía escribiendo en el repo.
    """
    return Path(artifact_path).resolve().parent / HISTORY_DIRNAME

# Columnas de resultado real que `_check_pick_success` necesita.
RESULT_COLUMNS = (
    "final_score_home", "final_score_away",
    "final_corners_home", "final_corners_away",
    "final_yellow_cards_home", "final_yellow_cards_away",
    "final_red_cards_home", "final_red_cards_away",
    "final_shots_home", "final_shots_away",
    "final_shots_on_target_home", "final_shots_on_target_away",
    "final_fouls_home", "final_fouls_away",
    "final_offsides_home", "final_offsides_away",
)


# ═══════════════════════════════════════════════════════════════════════
# EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionStats:
    """
    Contabilidad auditable de la extracción.

    Separa ausencia de picks de JSON inválido. Una fila sin picks no es
    necesariamente un error: puede corresponder a un partido analizado que
    no produjo recomendaciones publicables.
    """

    rows_seen: int = 0
    rows_without_results: int = 0
    rows_no_picks: int = 0
    rows_empty_picks: int = 0
    rows_bad_json: int = 0

    picks_seen: int = 0
    picks_no_prob: int = 0
    picks_unsettled: int = 0
    picks_push: int = 0
    picks_no_timestamp: int = 0
    picks_accepted: int = 0

    def as_dict(self) -> dict:
        return dict(self.__dict__)

    def summary(self) -> str:
        return (
            f"filas={self.rows_seen} "
            f"(sin_resultado={self.rows_without_results}, "
            f"sin_picks={self.rows_no_picks}, "
            f"picks_vacios={self.rows_empty_picks}, "
            f"json_malo={self.rows_bad_json}) | "
            f"picks={self.picks_seen} "
            f"-> aceptados={self.picks_accepted} "
            f"(sin_prob={self.picks_no_prob}, "
            f"sin_liquidar={self.picks_unsettled}, "
            f"push={self.picks_push}, "
            f"sin_fecha={self.picks_no_timestamp})"
        )


def _row_has_results(row: dict) -> bool:
    """Un partido sirve si tiene al menos el marcador final."""
    return row.get("final_score_home") is not None and row.get("final_score_away") is not None


def _pick_probability(pick: dict) -> float | None:
    """
    Extrae la probabilidad CRUDA del modelo, nunca la ya calibrada.

    Calibrar sobre `calibrated_prob` entrenaría una corrección sobre una
    corrección: el error se compone en vez de cancelarse.
    """
    for key in ("model_prob", "modelProb", "prob_model", "probability"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _coerce_cutoff_datetime(value: Any) -> datetime | None:
    """
    Como `_coerce_datetime` pero si el valor es solo una fecha (YYYY-MM-DD)
    la lleva al final del día (23:59:59.999999 UTC) para incluir todos los
    partidos de ese día completo.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        stripped = value.strip()
        # Fecha pura sin componente horaria
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped):
            try:
                d = datetime.strptime(stripped, "%Y-%m-%d")
                return d.replace(
                    hour=23, minute=59, second=59,
                    microsecond=999999, tzinfo=timezone.utc,
                )
            except ValueError:
                return None
        try:
            dt = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _until_date_label(until_date: "datetime | str | None") -> str:
    """Devuelve 'YYYY-MM-DD' a partir de un until_date para usar en nombres de archivo."""
    if isinstance(until_date, str):
        return until_date.strip()[:10]
    if isinstance(until_date, datetime):
        return until_date.strftime("%Y-%m-%d")
    return "unknown"

# -----------------------------------------------------------------------
# NOTE: _extract_line_bucket, _resolve_market_side y market_family_fn
# fueron reemplazados por la taxonomía canónica de src.domain.market_taxonomy.
# No reutilizar las versiones locales: generaban inconsistencias entre el
# entrenamiento de calibración, las reglas y la generación de picks.
# -----------------------------------------------------------------------


def extract_samples(
    rows: Iterable[dict],
    resolver=None,
    market_family_fn=None,
    require_timestamp: bool = True,
    weight_by_match: bool = False,
    decision_region_only: bool = False,
) -> tuple[list[CalibrationSample], ExtractionStats]:
    """
    Convierte el histórico liquidado en muestras para calibración.

    La probabilidad usada siempre es raw/model_prob, nunca calibrated_prob.
    Se registra familia, dirección y línea para permitir pooling jerárquico
    sin mezclar Under con Over, X2 con 1X ni líneas incompatibles.

    Usa exclusivamente la taxonomía canónica (market_taxonomy) para clasificar
    familia, lado y banda de línea. El parámetro market_family_fn se ignora
    para evitar inconsistencias entre entrenamiento y producción.

    - weight_by_match: Si es True, pondera cada pick por 1 / N_picks_del_partido
      para evitar que partidos con muchos picks dominen la calibración (Issue #35).
    - decision_region_only: Si es True, entrena únicamente sobre picks elegibles/jugables
      en la región de decisión real (Issue #41).
    """
    if resolver is None:
        from src.ui.api.main import _check_pick_success as resolver  # type: ignore

    if market_family_fn is None:
        from src.ui.api.compare import _market_family as market_family_fn  # type: ignore

    stats = ExtractionStats()
    samples: list[CalibrationSample] = []

    for row in rows:
        stats.rows_seen += 1

        if not _row_has_results(row):
            stats.rows_without_results += 1
            continue

        raw_picks = row.get("picks_calculados")

        if raw_picks is None:
            stats.rows_no_picks += 1
            continue

        if isinstance(raw_picks, str):
            raw_picks = raw_picks.strip()

            if not raw_picks:
                stats.rows_no_picks += 1
                continue

            try:
                raw_picks = json.loads(raw_picks)
            except (json.JSONDecodeError, TypeError):
                stats.rows_bad_json += 1
                continue

        if isinstance(raw_picks, dict):
            raw_picks = (
                raw_picks.get("picks")
                or raw_picks.get("value_picks")
                or []
            )

        if not isinstance(raw_picks, list):
            stats.rows_bad_json += 1
            continue

        if not raw_picks:
            stats.rows_empty_picks += 1
            continue

        results = {
            column: row.get(column)
            for column in RESULT_COLUMNS
        }

        timestamp = _coerce_datetime(
            row.get("predicted_at_utc")
            or row.get("date")
            or row.get("match_date")
        )

        result_available_at = _coerce_datetime(
            row.get("result_available_at_utc")
            or row.get("match_date")
        )

        league = (
            row.get("league")
            or row.get("competition")
            or row.get("league_name")
        )

        # Issue #35: Contar picks válidos en el partido para ponderar por partido si está activo
        row_accepted_samples: list[CalibrationSample] = []

        for pick in raw_picks:
            if not isinstance(pick, dict):
                continue

            stats.picks_seen += 1

            # Issue #41: Evaluar en la región de decisión si se solicita
            if decision_region_only:
                # Región de decisión: picks que fueron elegibles, recomendados o con edge positivo
                is_candidate = pick.get("is_value") or pick.get("is_publishable") or (float(pick.get("edge_ev") or 0.0) > 0.0)
                if not is_candidate:
                    continue

            probability = _pick_probability(pick)

            if probability is None:
                stats.picks_no_prob += 1
                continue

            if require_timestamp and timestamp is None:
                stats.picks_no_timestamp += 1
                continue

            # Preservar timestamp de predicción y fecha de resultado
            sample_ts = _coerce_datetime(pick.get("predicted_at_utc")) or timestamp

            if resolver is None:
                from src.ui.api.main import _check_pick_success as resolver  # type: ignore

            try:
                legacy_outcome = resolver(pick, results)
            except Exception as exc:
                logger.debug(
                    "Resolver falló para %s: %s",
                    pick.get("selection"),
                    exc,
                )
                stats.picks_unsettled += 1
                continue

            outcome = outcome_from_legacy(legacy_outcome)

            if outcome is Outcome.UNSETTLED:
                stats.picks_unsettled += 1
                continue

            hit_value = outcome_hit_value(outcome)

            if hit_value is None:
                stats.picks_push += 1
                continue

            selection = str(
                pick.get("selection")
                or pick.get("market")
                or ""
            )

            market_fam = str(normalize_market_family(selection))
            side = str(normalize_market_side(selection, family=market_fam))
            line = None if market_fam in CATEGORICAL_FAMILIES else extract_market_line(selection)
            line_bucket = line_bucket_for(market_fam, line)

            row_accepted_samples.append(
                CalibrationSample(
                    prob=float(probability),
                    hit_value=float(hit_value),
                    market_family=market_fam,
                    side=side,
                    line_bucket=line_bucket,
                    league=str(league).strip() if league else None,
                    timestamp=sample_ts,
                    weight=1.0,
                )
            )

        # Issue #35: Si weight_by_match=True, reponderar cada pick del partido por 1 / N_picks
        if weight_by_match and row_accepted_samples:
            match_w = 1.0 / len(row_accepted_samples)
            row_accepted_samples = [
                CalibrationSample(
                    prob=s.prob,
                    hit_value=s.hit_value,
                    market_family=s.market_family,
                    side=s.side,
                    line_bucket=s.line_bucket,
                    league=s.league,
                    timestamp=s.timestamp,
                    weight=round(s.weight * match_w, 6),
                )
                for s in row_accepted_samples
            ]

        samples.extend(row_accepted_samples)
        stats.picks_accepted += len(row_accepted_samples)

    return samples, stats

def load_rows_from_db(
    session=None,
    limit: int | None = None,
    league_filter: str | None = None,
    include_excluded: bool = False,
    until_date: datetime | str | None = None,
) -> list[dict]:
    """
    Lee `analysis_history` y devuelve dicts planos.

    Solo trae filas con marcador final. Por defecto omite las marcadas con
    `count_in_profitability=False` a menos que `include_excluded=True`.

    `league_filter`: si se especifica, solo devuelve filas cuyo nombre de liga
    o competición coincida (insensible a mayúsculas y espacios).

    `until_date`: si se especifica (datetime o string ISO/YYYY-MM-DD), solo incluye
    partidos cuya fecha (match_date o date) sea menor o igual a esa fecha limite.
    """
    from src.core.domain import AnalysisHistory

    close_after = False
    if session is None:
        from src.core.database import SessionLocal
        session = SessionLocal()
        close_after = True

    normalized_filter = " ".join((league_filter or "").lower().strip().split())

    cutoff_dt = None
    if until_date is not None:
        # Usar end-of-day para que una fecha pura incluya todo el día
        cutoff_dt = _coerce_cutoff_datetime(until_date)

    try:
        q = (
            session.query(AnalysisHistory)
            .filter(AnalysisHistory.final_score_home.isnot(None))
            .filter(AnalysisHistory.final_score_away.isnot(None))
        )

        if cutoff_dt is not None:
            # Filtrar por fecha de partido <= fecha de corte
            q = q.filter(
                (AnalysisHistory.match_date <= cutoff_dt) |
                ((AnalysisHistory.match_date.is_(None)) & (AnalysisHistory.date <= cutoff_dt))
            )

        q = q.order_by(AnalysisHistory.match_date.asc())

        if limit:
            q = q.limit(limit)

        out: list[dict] = []
        for r in q.all():
            if not include_excluded and getattr(r, "count_in_profitability", True) is False:
                continue
            row = {c: getattr(r, c, None) for c in RESULT_COLUMNS}
            row["picks_calculados"] = r.picks_calculados
            row["match_date"] = r.match_date
            row["date"] = r.date
            row["match_title"] = r.match_title
            payload = r.payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
            if isinstance(payload, dict):
                row["league"] = (
                    getattr(r, "competition", None)
                    or payload.get("league")
                    or payload.get("competition")
                    or payload.get("league_name")
                )
            else:
                row["league"] = getattr(r, "competition", None)

            # Aplicar filtro por liga si se especificó
            if normalized_filter:
                row_league = " ".join(
                    str(row.get("league") or "").lower().strip().split()
                )
                if normalized_filter not in row_league:
                    continue

            out.append(row)
        return out
    finally:
        if close_after:
            session.close()

# ═══════════════════════════════════════════════════════════════════════
# COMPARACIÓN CANDIDATO vs ACTIVO
# ═══════════════════════════════════════════════════════════════════════

# Mínimo de muestras OOF posteriores a lo que vio el activo para una comparación 100% justa.
MIN_FAIR_SAMPLES = 150

# Si la comparación es "leaky" (el activo pudo ver las muestras), el candidato puede
# quedar ligeramente peor sin que se rechace, porque el activo juega con ventaja.
LEAK_ALLOWANCE = {"brier": 0.001, "log_loss": 0.003}
# Si True, una mejora cuyo IC95 de ΔBrier incluye 0 (ruido) NO se promueve.
REQUIRE_SIGNIFICANT_VS_ACTIVE = False

_ACTIVE_CUTOFF_KEYS = ("trained_until", "cutoff_date")


def _active_trained_until(active_cal) -> datetime | None:
    """Fecha máxima de datos que vio el calibrador activo (si el artefacto la registra)."""
    md = getattr(active_cal, "metadata", None) or {}
    for key in _ACTIVE_CUTOFF_KEYS:
        dt = _coerce_cutoff_datetime(md.get(key))
        if dt is not None:
            return dt
    return None


def _paired_bootstrap_brier(
    cand_probs: Sequence[float],
    act_probs: Sequence[float],
    outcomes: Sequence[float],
    n_boot: int = 1000,
    seed: int = 7,
) -> dict:
    """
    Bootstrap pareado de (Brier_candidato - Brier_activo) sobre las mismas muestras.
    Si el IC95 incluye 0, la diferencia no se distingue del ruido.
    """
    n = len(outcomes)
    if n == 0:
        nan = float("nan")
        return {"mean_diff": nan, "ci_low": nan, "ci_high": nan, "p_cand_better": nan}

    diffs = [(c - o) ** 2 - (a - o) ** 2 for c, a, o in zip(cand_probs, act_probs, outcomes)]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(n_boot))
    return {
        "mean_diff": sum(diffs) / n,
        "ci_low": boots[int(0.025 * n_boot)],
        "ci_high": boots[min(n_boot - 1, int(0.975 * n_boot))],
        "p_cand_better": sum(1 for b in boots if b < 0) / n_boot,
    }


def compare_with_active(
    wf: WalkForwardResult,
    active_path: Path | str,
    tol_ece: float = 0.002,
    min_fair_samples: int = MIN_FAIR_SAMPLES,
) -> dict:
    """
    Compara candidato vs activo sobre EXACTAMENTE las mismas muestras OOF.

    status:
      'no_active' -> no hay activo entrenado.
      'error'     -> no se pudo cargar/evaluar (no se debe promover sin force).
      'ok'        -> comparación realizada.

    mode (solo si status == 'ok'):
      'fair'            -> solo muestras posteriores a `trained_until` del activo.
      'leaky_no_cutoff' -> el activo no registra `trained_until`: se usan todas las
                           muestras; el activo pudo verlas (sesgo a su favor).
      'leaky_fallback'  -> hay `trained_until`, pero quedan menos de
                           `min_fair_samples` muestras posteriores: se usan todas.

    En modos 'leaky_*' el candidato gana si no es peor que el activo más una holgura
    (LEAK_ALLOWANCE), porque el activo evalúa parcialmente sobre sus datos de entreno.
    """
    path = Path(active_path)
    if not path.exists():
        return {"status": "no_active"}

    try:
        active_cal = HierarchicalCalibrator.load(path)
    except Exception as exc:
        logger.warning("No se pudo cargar el calibrador activo: %s", exc)
        return {"status": "error", "error": f"load: {exc}"}

    if not active_cal.is_trained:
        return {"status": "no_active"}

    n_all = len(wf.outcomes)
    if not (len(wf.samples) == len(wf.raw_probs) == len(wf.calibrated_probs) == n_all):
        return {
            "status": "error",
            "error": (
                f"walk-forward desalineado: samples={len(wf.samples)} "
                f"raw={len(wf.raw_probs)} cal={len(wf.calibrated_probs)} outcomes={n_all}"
            ),
        }

    trained_until = _active_trained_until(active_cal)

    fair_idx: list[int] = []
    if trained_until is not None:
        for i, s in enumerate(wf.samples):
            ts = _coerce_datetime(s.timestamp)
            if ts is not None and ts > trained_until:
                fair_idx.append(i)

    if trained_until is None:
        mode, idx = "leaky_no_cutoff", list(range(n_all))
    elif len(fair_idx) >= min_fair_samples:
        mode, idx = "fair", fair_idx
    else:
        mode, idx = "leaky_fallback", list(range(n_all))

    base = {
        "mode": mode,
        "leaky": mode != "fair",
        "trained_until": trained_until.isoformat() if trained_until else None,
        "n_fair_available": len(fair_idx),
        "n_excluded_seen_by_active": (n_all - len(idx)),
    }

    try:
        outcomes = [wf.outcomes[i] for i in idx]
        raw_probs = [wf.raw_probs[i] for i in idx]
        cand_probs = [wf.calibrated_probs[i] for i in idx]
        act_probs = [
            active_cal.apply(
                prob=wf.samples[i].normalized_prob(),
                market_family=wf.samples[i].market_family,
                side=wf.samples[i].side,
                line_bucket=wf.samples[i].line_bucket,
                league=wf.samples[i].league,
            )
            for i in idx
        ]
    except Exception as exc:
        logger.warning("Fallo al evaluar el calibrador activo: %s", exc)
        return {"status": "error", "error": f"apply: {exc}", **base}

    raw = evaluate(raw_probs, outcomes)
    cand = evaluate(cand_probs, outcomes)
    act = evaluate(act_probs, outcomes)

    deltas = {k: cand[k] - act[k] for k in ("brier", "log_loss", "ece")}

    if mode == "fair":
        wins = {
            "brier": deltas["brier"] < 0,
            "log_loss": deltas["log_loss"] < 0,
            "ece": deltas["ece"] <= tol_ece,
        }
    else:
        wins = {
            "brier": deltas["brier"] <= LEAK_ALLOWANCE["brier"],
            "log_loss": deltas["log_loss"] <= LEAK_ALLOWANCE["log_loss"],
            "ece": deltas["ece"] <= tol_ece,
        }

    boot = _paired_bootstrap_brier(cand_probs, act_probs, outcomes)
    stored = ((getattr(active_cal, "metadata", None) or {}).get("walk_forward") or {}).get("calibrated")

    return {
        "status": "ok",
        "n_compared": len(idx),
        "raw": raw,
        "candidate": cand,
        "active": act,
        "active_stored": stored,
        "deltas": deltas,
        "bootstrap": boot,
        "wins": wins,
        "significant": boot["ci_high"] < 0,
        "candidate_better": bool(wins["brier"] and wins["log_loss"] and wins["ece"]),
        **base,
    }


def format_active_comparison(cmp: dict) -> str:
    status = cmp.get("status")
    if not status:
        return ""
    if status == "no_active":
        return "Comparación vs activo: no hay calibrador activo entrenado."
    if status == "error":
        return f"Comparación vs activo: NO DISPONIBLE ({cmp.get('error')})"

    r, c, a, d, b = cmp["raw"], cmp["candidate"], cmp["active"], cmp["deltas"], cmp["bootstrap"]
    mode_txt = {
        "fair": "justa: solo partidos posteriores a lo que vio el activo",
        "leaky_no_cutoff": "con sesgo a favor del activo (no registra trained_until)",
        "leaky_fallback": (
            f"con sesgo a favor del activo (solo {cmp['n_fair_available']} muestras "
            f"posteriores a {cmp['trained_until']})"
        ),
    }.get(cmp.get("mode"), cmp.get("mode"))

    lines = [
        f"Comparación vs activo sobre las MISMAS {cmp['n_compared']} muestras OOF [{mode_txt}]",
        f"  {'':9}{'crudo':>10}{'activo':>10}{'candidato':>11}{'Δ cand-act':>12}",
        f"  {'Brier':9}{r['brier']:>10.5f}{a['brier']:>10.5f}{c['brier']:>11.5f}{d['brier']:>+12.5f}",
        f"  {'LogLoss':9}{r['log_loss']:>10.5f}{a['log_loss']:>10.5f}{c['log_loss']:>11.5f}{d['log_loss']:>+12.5f}",
        f"  {'ECE':9}{r['ece']:>10.5f}{a['ece']:>10.5f}{c['ece']:>11.5f}{d['ece']:>+12.5f}",
        f"  ΔBrier IC95 [{b['ci_low']:+.5f}, {b['ci_high']:+.5f}]  "
        f"P(candidato mejor)={b['p_cand_better']:.2f}  "
        f"{'significativo' if cmp['significant'] else 'NO significativo (puede ser ruido)'}",
    ]
    if cmp.get("leaky"):
        lines.append(
            f"  Holgura por sesgo: Brier +{LEAK_ALLOWANCE['brier']}, "
            f"LogLoss +{LEAK_ALLOWANCE['log_loss']} (el activo juega con ventaja)."
        )
    st = cmp.get("active_stored")
    if st and st.get("brier") is not None:
        lines.append(
            "  (informativo, otro dataset) guardado en active.json: "
            f"Brier {st.get('brier'):.5f} | LogLoss {st.get('log_loss', float('nan')):.5f} "
            f"| ECE {st.get('ece', float('nan')):.5f}"
        )
    lines.append(
        "  Veredicto: " + ("candidato MEJOR que el activo" if cmp["candidate_better"]
                           else "candidato NO mejora al activo")
    )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════
# ENTRENAMIENTO Y PROMOCIÓN
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TrainingReport:
    """Resultado auditable de un entrenamiento."""

    promoted: bool
    reason: str
    n_samples: int
    extraction: dict = field(default_factory=dict)
    walk_forward: dict = field(default_factory=dict)
    calibrator_version: str | None = None
    artifact_path: str | None = None
    segments: list[str] = field(default_factory=list)
    active_comparison: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "promoted": self.promoted,
            "reason": self.reason,
            "n_samples": self.n_samples,
            "extraction": self.extraction,
            "walk_forward": self.walk_forward,
            "active_comparison": self.active_comparison,
            "calibrator_version": self.calibrator_version,
            "artifact_path": self.artifact_path,
            "segments": self.segments,
        }

    def summary(self) -> str:
        head = "PROMOVIDO" if self.promoted else "NO PROMOVIDO"
        lines = [f"[{head}] {self.reason}", f"muestras: {self.n_samples}"]
        wf = self.walk_forward
        if wf.get("raw") and wf.get("calibrated"):
            r, c = wf["raw"], wf["calibrated"]
            lines.append(f"OOF evaluadas: {r.get('n')}  [crudo (sin calibrar) -> candidato]")
            if r.get("brier") is not None:
                lines.append(f"  Brier    {r['brier']:.5f} -> {c['brier']:.5f}")
            if r.get("log_loss") is not None:
                lines.append(f"  LogLoss  {r['log_loss']:.5f} -> {c['log_loss']:.5f}")
            if r.get("ece") is not None:
                lines.append(f"  ECE      {r['ece']:.5f} -> {c['ece']:.5f}")
        cmp_text = format_active_comparison(self.active_comparison)
        if cmp_text:
            lines.append(cmp_text)
        if self.segments:
            lines.append(f"segmentos: {len(self.segments)}")
        return "\n".join(l for l in lines if l)


def train_calibrator(
    samples: Sequence[CalibrationSample],
    artifact_path: Path | str = DEFAULT_ARTIFACT_PATH,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    min_samples: float = DEFAULT_MIN_SAMPLES,
    n_folds: int = 5,
    force: bool = False,
    dry_run: bool = False,
    extraction_stats: dict | None = None,
    cutoff_label: str | None = None,
) -> TrainingReport:
    """
    Ajusta, valida y (si mejora) promueve el calibrador.

    Promoción: el candidato debe (1) mejorar al crudo en OOF (Brier y log loss)
    y (2) no ser peor que el activo en Brier, log loss y ECE, comparados sobre
    las MISMAS muestras OOF y, si el activo registra `trained_until`, solo sobre
    muestras posteriores a lo que el activo ya vio.

    `force` publica el artefacto aunque no mejore — solo para depuración.
    `dry_run` calcula todo y no escribe nada.
    `cutoff_label`: si se especifica (formato 'YYYY-MM-DD'), la copia en history
    llevará el sufijo `_until_{cutoff_label}` para distinguir calibraciones por
    corte temporal. El archivo `active.json` siempre se sobreescribe con la
    versión más reciente.
    """
    n = len(samples)
    report = TrainingReport(
        promoted=False, reason="", n_samples=n,
        extraction=extraction_stats or {}, artifact_path=str(artifact_path),
    )

    if n < min_samples:
        report.reason = (
            f"Muestra insuficiente: {n} < {min_samples:.0f}. Se mantiene la "
            f"identidad, que es preferible a una curva inventada."
        )
        return report

    min_league_samples = min(min_samples, 40.0)

    wf: WalkForwardResult = walk_forward_calibrate(
        samples=samples,
        n_folds=n_folds,
        prior_strength=prior_strength,
        min_samples=min_samples,
        min_line_samples=120.0,
        min_league_samples=min_league_samples,
        min_train=max(120.0, min_samples * 2.0),
    )
    report.walk_forward = wf.metrics()

    if not wf.outcomes:
        report.reason = (
            "El walk-forward no pudo evaluar ningún fold (falta histórico "
            "previo suficiente). Sin validación no se promueve."
        )
        return report

    improves = wf.improved()

    # Comparación candidato vs activo sobre las mismas muestras OOF.
    # Se calcula siempre (informativa); solo bloquea si no hay `force`.
    cmp = compare_with_active(wf, artifact_path)
    report.active_comparison = cmp
    status = cmp.get("status")

    if status == "not_comparable":
        logger.warning(
            "El activo ya vio todas las muestras OOF (trained_until=%s): "
            "no hay comparación justa; se decide solo contra el crudo.",
            cmp.get("trained_until"),
        )
    elif status == "ok" and cmp.get("leaky"):
        logger.warning(
            "Comparación vs activo con sesgo a su favor (modo=%s, muestras justas "
            "disponibles=%s). Holgura aplicada: %s.",
            cmp.get("mode"), cmp.get("n_fair_available"), LEAK_ALLOWANCE,
        )

    if not force:
        if status == "error":
            report.reason = (
                f"No se pudo comparar contra el activo ({cmp.get('error')}). "
                "Sin comparación válida no se promueve; usa --force para saltarlo."
            )
            return report

        if status == "ok":
            d = cmp["deltas"]
            if not cmp["candidate_better"]:
                report.reason = (
                    "El candidato no supera al activo en las mismas "
                    f"{cmp['n_compared']} muestras OOF: "
                    f"ΔBrier={d['brier']:+.5f}, ΔLogLoss={d['log_loss']:+.5f}, "
                    f"ΔECE={d['ece']:+.5f} (negativo = mejor)."
                )
                return report
            if REQUIRE_SIGNIFICANT_VS_ACTIVE and not cmp["significant"]:
                b = cmp["bootstrap"]
                report.reason = (
                    "La mejora sobre el activo no es estadísticamente distinguible de "
                    f"ruido (ΔBrier IC95 [{b['ci_low']:+.5f}, {b['ci_high']:+.5f}])."
                )
                return report

    if not improves and not force:
        report.reason = (
            "La calibración NO mejora Brier y log loss out-of-sample. "
            "No se promueve: una curva que no mejora está sobreajustando."
        )
        return report

    calibrator = HierarchicalCalibrator.fit(
        samples=samples,
        prior_strength=prior_strength,
        min_samples=min_samples,
        min_line_samples=120.0,
        min_league_samples=min_league_samples,
    )
    calibrator.metadata["walk_forward"] = report.walk_forward
    calibrator.metadata["extraction"] = report.extraction
    calibrator.metadata["forced"] = bool(force and not improves)

    # Fecha máxima de datos vistos: permite que el próximo entrenamiento compare
    # solo sobre muestras que este calibrador NO ha visto.
    stamps = [t for t in (_coerce_datetime(s.timestamp) for s in samples) if t is not None]
    if stamps:
        calibrator.metadata["trained_until"] = max(stamps).isoformat()
    calibrator.metadata["n_train_samples"] = n

    if status == "ok":
        calibrator.metadata["vs_previous_active"] = {
            "n_compared": cmp["n_compared"],
            "deltas": cmp["deltas"],
            "bootstrap": cmp["bootstrap"],
            "leaky": cmp["leaky"],
        }

    if cutoff_label:
        calibrator.metadata["cutoff_date"] = cutoff_label
        try:
            cutoff_dt = datetime.strptime(cutoff_label, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            calibrator.version = cutoff_dt.strftime("cal-v2-%Y%m%dT%H%M%SZ")
        except ValueError:
            pass  # Si el label no es parseable, mantener la versión original

    report.calibrator_version = calibrator.version
    report.segments = sorted(calibrator.curves.keys())

    if dry_run:
        report.reason = "dry-run: validación superada, no se escribió el artefacto."
        return report

    path = Path(artifact_path)
    calibrator.save(path)
    calibrator.save(history_dir_for(path) / f"{calibrator.version}.json")
    logger.info("Artefacto history guardado: 'history/%s.json'", calibrator.version)

    report.promoted = True
    if not improves:
        report.reason = "Promovido por --force (NO mejoró las métricas)."
    elif status == "ok":
        d = cmp["deltas"]
        report.reason = (
            "Promovido: mejora al crudo y al activo en las mismas muestras OOF "
            f"(ΔBrier={d['brier']:+.5f}, ΔLogLoss={d['log_loss']:+.5f}, ΔECE={d['ece']:+.5f})."
        )
    else:
        report.reason = "Promovido: mejora Brier y log loss out-of-sample."
    return report


def _league_already_calibrated(
    artifact_path: Path | str,
    league_name: str,
) -> list[str]:
    """
    Devuelve la lista de segmentos del artefacto activo que pertenecen a la liga.

    Un segmento pertenece a una liga cuando la representación normalizada del
    nombre de la liga aparece en la clave del segmento (que sigue el patrón
    `<familia>|<lado>|<línea>|<liga>`).
    """
    path = Path(artifact_path)
    if not path.exists():
        return []
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    curves: dict = artifact.get("curves", {})
    normalized = " ".join(league_name.lower().strip().split())
    return [
        key for key in curves
        if normalized in key.lower()
    ]


def run_training(
    artifact_path: Path | str = DEFAULT_ARTIFACT_PATH,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    min_samples: float = DEFAULT_MIN_SAMPLES,
    n_folds: int = 5,
    limit: int | None = None,
    require_timestamp: bool = True,
    force: bool = False,
    dry_run: bool = False,
    session=None,
    league_filter: str | None = None,
    include_excluded: bool = False,
    until_date: datetime | str | None = None,
    weight_by_match: bool = False,
    decision_region_only: bool = False,
) -> TrainingReport:
    """
    Pipeline completo: BD -> muestras -> validación -> artefacto.

    `league_filter`: si se especifica, solo se entrenan picks de esa liga.
    Si la liga YA tiene curvas en el artefacto activo, el entrenamiento se
    bloquea para evitar sobreajuste — a menos que se pase `force=True`.

    `until_date`: si se especifica, solo se incluyen picks anteriores o iguales a esa fecha.
    """
    # Guardia de sobreajuste: avisar si la liga ya tiene parámetros.
    if league_filter and not force:
        existing = _league_already_calibrated(artifact_path, league_filter)
        if existing:
            logger.warning(
                "La liga '%s' ya tiene %d segmento(s) calibrado(s) en el "
                "artefacto activo: %s. Re-entrenarla puede provocar "
                "sobreajuste. Usa --force para forzar.",
                league_filter, len(existing), existing[:5],
            )
            report = TrainingReport(
                promoted=False,
                reason=(
                    f"Liga '{league_filter}' ya calibrada ({len(existing)} "
                    f"segmentos). Entrena solo ligas nuevas o usa --force."
                ),
                n_samples=0,
            )
            return report

    # Etiqueta de corte temporal (solo para el nombre en history).
    cutoff_label: str | None = _until_date_label(until_date) if until_date is not None else None
    if cutoff_label:
        logger.info(
            "Calibración con corte temporal: hasta '%s' (23:59:59 UTC).",
            cutoff_label,
        )

    rows = load_rows_from_db(
        session=session,
        limit=limit,
        league_filter=league_filter,
        include_excluded=include_excluded,
        until_date=until_date,
    )

    if league_filter:
        logger.info("Filtrando por liga: '%s' → %d filas.", league_filter, len(rows))
    if until_date:
        logger.info(
            "Filtrando por fecha máxima (corte): '%s' → %d filas.",
            until_date, len(rows),
        )

    samples, stats = extract_samples(
        rows,
        require_timestamp=require_timestamp,
        weight_by_match=weight_by_match,
        decision_region_only=decision_region_only,
    )
    logger.info("Extracción: %s", stats.summary())
    return train_calibrator(
        samples,
        artifact_path=artifact_path,
        prior_strength=prior_strength,
        min_samples=min_samples,
        n_folds=n_folds,
        force=force,
        dry_run=dry_run,
        extraction_stats=stats.as_dict(),
        cutoff_label=cutoff_label,
    )


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Entrena el calibrador de Sherlock desde picks liquidados."
    )
    ap.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH))
    ap.add_argument("--prior-strength", type=float, default=DEFAULT_PRIOR_STRENGTH,
                    help="κ: fuerza del prior. Más alto = más conservador.")
    ap.add_argument("--min-samples", type=float, default=DEFAULT_MIN_SAMPLES)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--until-date",
        "--cutoff-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Entrena solo con partidos jugados/analizados hasta esta fecha (inclusive).",
    )
    ap.add_argument(
        "--league",
        default=None,
        metavar="NOMBRE",
        help=(
            "Entrena solo con picks de esta liga. Si la liga ya tiene curvas "
            "en el artefacto activo el entrenamiento se bloquea (usa --force "
            "para saltarte la guardia). Útil para incorporar ligas nuevas sin "
            "re-ajustar las ya calibradas."
        ),
    )
    ap.add_argument("--allow-missing-timestamp", action="store_true",
                    help="Incluye picks sin fecha (riesgo de fuga temporal).")
    ap.add_argument(
        "--include-excluded",
        action="store_true",
        help="Incluye partidos marcados con count_in_profitability=False.",
    )
    ap.add_argument("--weight-by-match", action="store_true",
                    help="Pondera cada pick por 1 / N_picks del partido (Issue #35).")
    ap.add_argument("--decision-region-only", action="store_true",
                    help="Entrena únicamente en la región de decisión de picks con valor/elegibles (Issue #41).")
    ap.add_argument("--force", action="store_true",
                    help="Promueve aunque no mejore / omite guardia de liga ya calibrada.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true", help="Salida en JSON.")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    report = run_training(
        artifact_path=args.artifact,
        prior_strength=args.prior_strength,
        min_samples=args.min_samples,
        n_folds=args.folds,
        limit=args.limit,
        require_timestamp=not args.allow_missing_timestamp,
        force=args.force,
        dry_run=args.dry_run,
        league_filter=args.league,
        include_excluded=args.include_excluded,
        until_date=args.until_date,
        weight_by_match=args.weight_by_match,
        decision_region_only=args.decision_region_only,
    )

    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False)
          if args.json else report.summary())
    return 0 if report.promoted or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
