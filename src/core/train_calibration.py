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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.domain.settlement import Outcome, outcome_from_legacy, outcome_hit_value
from src.models.calibration import (
    DEFAULT_MIN_SAMPLES,
    DEFAULT_PRIOR_STRENGTH,
    CalibrationSample,
    HierarchicalCalibrator,
    WalkForwardResult,
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
    """Contabilidad de por qué se descarta cada pick. Sin esto no hay auditoría."""

    rows_seen: int = 0
    rows_without_results: int = 0
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
            f"filas={self.rows_seen} (sin resultado={self.rows_without_results}, "
            f"json_malo={self.rows_bad_json}) | picks={self.picks_seen} "
            f"-> aceptados={self.picks_accepted} "
            f"(sin_prob={self.picks_no_prob}, sin_liquidar={self.picks_unsettled}, "
            f"push={self.picks_push}, sin_fecha={self.picks_no_timestamp})"
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


def extract_samples(
    rows: Iterable[dict],
    resolver=None,
    market_family_fn=None,
    require_timestamp: bool = True,
) -> tuple[list[CalibrationSample], ExtractionStats]:
    """
    Convierte filas de analysis_history en muestras de calibración, preservando
    la polaridad direccional (1X vs X2, Over vs Under, Home vs Away).
    """
    if resolver is None:
        from src.ui.api.main import _check_pick_success as resolver  # type: ignore
    if market_family_fn is None:
        from src.ui.api.compare import _market_family as market_family_fn  # type: ignore

    def _resolve_directional_market_family(selection_str: str, base_family: str) -> str:
        sel = selection_str.lower().strip()
        
        # 1. Doble Oportunidad: segregación obligatoria
        if base_family in ("family:double_chance", "family:doublechance") or "doble oportunidad" in sel or "1x" in sel or "x2" in sel:
            if "1x" in sel:
                return "family:double_chance|side:1x"
            elif "x2" in sel:
                return "family:double_chance|side:x2"
            elif "12" in sel:
                return "family:double_chance|side:12"
            return "family:double_chance"

        # 2. Over / Under: segregación por polaridad
        if "under" in sel or "menos de" in sel or "menos" in sel:
            return f"{base_family}|side:under"
        if "over" in sel or "más de" in sel or "mas de" in sel or "más" in sel:
            return f"{base_family}|side:over"

        # 3. 1X2 (Moneyline / Result)
        if base_family in ("family:result", "family:1x2", "family:moneyline"):
            if any(k in sel for k in ("local", "home", "1")):
                return f"{base_family}|side:home"
            if any(k in sel for k in ("visitante", "away", "2")):
                return f"{base_family}|side:away"
            if any(k in sel for k in ("empate", "draw", "x")):
                return f"{base_family}|side:draw"

        return base_family

    stats = ExtractionStats()
    samples: list[CalibrationSample] = []

    for row in rows:
        stats.rows_seen += 1

        if not _row_has_results(row):
            stats.rows_without_results += 1
            continue

        raw_picks = row.get("picks_calculados")
        if isinstance(raw_picks, str):
            try:
                raw_picks = json.loads(raw_picks)
            except (json.JSONDecodeError, TypeError):
                stats.rows_bad_json += 1
                continue
        if isinstance(raw_picks, dict):
            raw_picks = raw_picks.get("picks") or raw_picks.get("value_picks") or []
        if not isinstance(raw_picks, list):
            stats.rows_bad_json += 1
            continue

        results = {k: row.get(k) for k in RESULT_COLUMNS}
        ts = _coerce_datetime(row.get("match_date") or row.get("date"))
        league = row.get("league") or row.get("competition") or row.get("league_name")

        for pick in raw_picks:
            if not isinstance(pick, dict):
                continue
            stats.picks_seen += 1

            prob = _pick_probability(pick)
            if prob is None:
                stats.picks_no_prob += 1
                continue

            if require_timestamp and ts is None:
                stats.picks_no_timestamp += 1
                continue

            try:
                legacy = resolver(pick, results)
            except Exception as exc:
                logger.debug("Resolver falló en pick %s: %s", pick.get("selection"), exc)
                stats.picks_unsettled += 1
                continue

            outcome = outcome_from_legacy(legacy)
            if outcome is Outcome.UNSETTLED:
                stats.picks_unsettled += 1
                continue

            hit = outcome_hit_value(outcome)
            if hit is None:
                stats.picks_push += 1
                continue

            selection = str(pick.get("selection") or pick.get("market") or "")
            base_family = market_family_fn(selection)
            directional_key = _resolve_directional_market_family(selection, base_family)

            samples.append(
                CalibrationSample(
                    prob=prob,
                    hit_value=hit,
                    market_family=directional_key,
                    league=str(league) if league else None,
                    timestamp=ts,
                )
            )
            stats.picks_accepted += 1

    return samples, stats

def load_rows_from_db(session=None, limit: int | None = None) -> list[dict]:
    """
    Lee `analysis_history` y devuelve dicts planos.

    Solo trae filas con marcador final y que cuenten para rentabilidad, para no
    calibrar con partidos marcados como excluidos.
    """
    from src.core.domain import AnalysisHistory

    close_after = False
    if session is None:
        from src.core.database import SessionLocal
        session = SessionLocal()
        close_after = True

    try:
        q = (
            session.query(AnalysisHistory)
            .filter(AnalysisHistory.final_score_home.isnot(None))
            .filter(AnalysisHistory.final_score_away.isnot(None))
            .order_by(AnalysisHistory.match_date.asc())
        )
        if limit:
            q = q.limit(limit)

        out: list[dict] = []
        for r in q.all():
            if getattr(r, "count_in_profitability", True) is False:
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
                    payload.get("league")
                    or payload.get("competition")
                    or payload.get("league_name")
                )
            out.append(row)
        return out
    finally:
        if close_after:
            session.close()


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

    def as_dict(self) -> dict:
        return {
            "promoted": self.promoted,
            "reason": self.reason,
            "n_samples": self.n_samples,
            "extraction": self.extraction,
            "walk_forward": self.walk_forward,
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
            lines.append(f"OOF evaluadas: {r.get('n')}")
            lines.append(
                f"  Brier    {r.get('brier'):.5f} -> {c.get('brier'):.5f}"
                if r.get("brier") is not None else ""
            )
            lines.append(
                f"  LogLoss  {r.get('log_loss'):.5f} -> {c.get('log_loss'):.5f}"
                if r.get("log_loss") is not None else ""
            )
            lines.append(
                f"  ECE      {r.get('ece'):.5f} -> {c.get('ece'):.5f}"
                if r.get("ece") is not None else ""
            )
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
) -> TrainingReport:
    """
    Ajusta, valida y (si mejora) promueve el calibrador.

    `force` publica el artefacto aunque no mejore — solo para depuración.
    `dry_run` calcula todo y no escribe nada.
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

    wf: WalkForwardResult = walk_forward_calibrate(
        samples, n_folds=n_folds, prior_strength=prior_strength,
        min_samples=min_samples, min_train=min_samples,
    )
    report.walk_forward = wf.metrics()

    if not wf.outcomes:
        report.reason = (
            "El walk-forward no pudo evaluar ningún fold (falta histórico "
            "previo suficiente). Sin validación no se promueve."
        )
        return report

    improves = wf.improved()
    if not improves and not force:
        report.reason = (
            "La calibración NO mejora Brier y log loss out-of-sample. "
            "No se promueve: una curva que no mejora está sobreajustando."
        )
        return report

    calibrator = HierarchicalCalibrator.fit(
        samples, prior_strength=prior_strength, min_samples=min_samples
    )
    calibrator.metadata["walk_forward"] = report.walk_forward
    calibrator.metadata["extraction"] = report.extraction
    calibrator.metadata["forced"] = bool(force and not improves)

    report.calibrator_version = calibrator.version
    report.segments = sorted(calibrator.curves.keys())

    if dry_run:
        report.reason = "dry-run: validación superada, no se escribió el artefacto."
        return report

    path = Path(artifact_path)
    calibrator.save(path)
    # Copia versionada junto al artefacto, para poder auditar y revertir.
    calibrator.save(history_dir_for(path) / f"{calibrator.version}.json")

    report.promoted = True
    report.reason = (
        f"Promovido: mejora Brier y log loss out-of-sample."
        if improves else "Promovido por --force (NO mejoró las métricas)."
    )
    return report


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
) -> TrainingReport:
    """Pipeline completo: BD -> muestras -> validación -> artefacto."""
    rows = load_rows_from_db(session=session, limit=limit)
    samples, stats = extract_samples(rows, require_timestamp=require_timestamp)
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
    ap.add_argument("--allow-missing-timestamp", action="store_true",
                    help="Incluye picks sin fecha (riesgo de fuga temporal).")
    ap.add_argument("--force", action="store_true",
                    help="Promueve aunque no mejore. Solo depuración.")
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
    )

    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False)
          if args.json else report.summary())
    return 0 if report.promoted or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
