"""
audit_calibration_tail.py

Diagnóstico de calibración probabilística de Sherlock, enfocado en detectar
en qué segmento (mercado / liga) se concentra la sobreconfianza del bin
90-100%, y cuánto la corrige el HierarchicalCalibrator ya existente.

Reutiliza exactamente la misma extracción que usa el entrenamiento oficial
(`src.core.train_calibration`), para no duplicar lógica de resolución de
mercados ni de settlement.

Uso:
    python audit_calibration_tail.py
    python audit_calibration_tail.py --limit 5000 --tail-threshold 0.9
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from src.core.train_calibration import load_rows_from_db, extract_samples
from src.models.calibration import (
    CalibrationSample,
    HierarchicalCalibrator,
    reliability_table,
    walk_forward_calibrate,
)


def print_reliability_table(title: str, probs, outcomes, n_bins: int = 10) -> None:
    print(f"\n=== {title} ===")
    table = reliability_table(probs, outcomes, n_bins=n_bins)
    print(f"{'bin':<12}{'n':>6}{'confianza':>12}{'acierto real':>14}{'gap':>10}")
    for row in table:
        if row["n"] == 0:
            continue
        bin_label = f"({row['lo']*100:.0f},{row['hi']*100:.0f}]"
        print(
            f"{bin_label:<12}{row['n']:>6}{row['confidence']*100:>11.1f}%"
            f"{row['accuracy']*100:>13.1f}%{row['gap']*100:>9.1f}pp"
        )


def top_bin_breakdown_by_family(samples: list[CalibrationSample], lo: float = 0.90) -> None:
    """
    Descompone el bin de probabilidad >= `lo` por market_family, para ver si
    la sobreconfianza se concentra en un mercado puntual (ej. favoritos en
    'result' o 'double_chance') o es transversal a todos los mercados.
    """
    by_family: dict[str, list[CalibrationSample]] = defaultdict(list)
    for s in samples:
        if s.normalized_prob() >= lo:
            by_family[s.market_family or "generic"].append(s)

    print(f"\n=== Desglose del bin >= {lo*100:.0f}% por market_family ===")
    print(f"{'family':<18}{'n':>6}{'confianza':>12}{'acierto real':>14}{'gap':>10}")
    rows = []
    for fam, subset in by_family.items():
        n = len(subset)
        conf = sum(s.normalized_prob() for s in subset) / n
        acc = sum(s.hit_value for s in subset) / n
        rows.append((fam, n, conf, acc))
    rows.sort(key=lambda r: -r[1])
    for fam, n, conf, acc in rows:
        gap = acc - conf
        print(f"{fam:<18}{n:>6}{conf*100:>11.1f}%{acc*100:>13.1f}%{gap*100:>9.1f}pp")


def top_bin_breakdown_by_league(samples: list[CalibrationSample], lo: float = 0.90) -> None:
    """
    Igual que arriba pero por liga: si son 3-4 ligas las que concentran el
    problema, la corrección debería ir a nivel liga×familia, no global.
    """
    by_league: dict[str, list[CalibrationSample]] = defaultdict(list)
    for s in samples:
        if s.normalized_prob() >= lo:
            by_league[s.league or "?"].append(s)

    print(f"\n=== Desglose del bin >= {lo*100:.0f}% por liga ===")
    print(f"{'liga':<28}{'n':>6}{'confianza':>12}{'acierto real':>14}{'gap':>10}")
    rows = []
    for lg, subset in by_league.items():
        n = len(subset)
        conf = sum(s.normalized_prob() for s in subset) / n
        acc = sum(s.hit_value for s in subset) / n
        rows.append((lg, n, conf, acc))
    rows.sort(key=lambda r: -r[1])
    for lg, n, conf, acc in rows:
        gap = acc - conf
        print(f"{lg:<28}{n:>6}{conf*100:>11.1f}%{acc*100:>13.1f}%{gap*100:>9.1f}pp")


def main() -> None:
    ap = argparse.ArgumentParser(description="Audita la calibración en la cola 90-100%.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--allow-missing-timestamp", action="store_true")
    ap.add_argument("--tail-threshold", type=float, default=0.90,
                     help="Umbral de probabilidad RAW que define 'la cola alta' (0-1).")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--prior-strength", type=float, default=25.0)
    ap.add_argument("--min-samples", type=float, default=40.0)
    args = ap.parse_args()

    print("Cargando picks liquidados desde analysis_history...")
    rows = load_rows_from_db(limit=args.limit)
    samples, stats = extract_samples(rows, require_timestamp=not args.allow_missing_timestamp)
    print(stats.summary())

    if not samples:
        print("Sin muestras suficientes para auditar. Revisa la extracción.")
        return

    raw_probs = [s.normalized_prob() for s in samples]
    outcomes = [s.hit_value for s in samples]

    # 1. Tabla de reliability cruda (equivalente a la tabla que ya calculaste).
    print_reliability_table("Reliability cruda (sin calibrar), 10 bins", raw_probs, outcomes)

    # 2. Desglose del bin problemático por mercado y por liga.
    top_bin_breakdown_by_family(samples, lo=args.tail_threshold)
    top_bin_breakdown_by_league(samples, lo=args.tail_threshold)

    # 3. Validación walk-forward: ¿el calibrador jerárquico corrige la cola
    #    fuera de muestra, sin fuga temporal?
    print("\n=== Walk-forward out-of-fold (curva entrenada solo con datos previos) ===")
    wf = walk_forward_calibrate(
        samples, n_folds=args.folds,
        prior_strength=args.prior_strength, min_samples=args.min_samples,
        min_train=args.min_samples,
    )
    metrics = wf.metrics()
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    if wf.outcomes:
        print_reliability_table(
            "Reliability CALIBRADA out-of-fold, 10 bins",
            wf.calibrated_probs, wf.outcomes,
        )

    # 4. Curva final ajustada con TODO el histórico (solo para inspección;
    #    la promoción real a producción la hace src/core/train_calibration.py
    #    con su propia regla de mejora Brier + log loss).
    calibrator = HierarchicalCalibrator.fit(
        samples, prior_strength=args.prior_strength, min_samples=args.min_samples,
    )
    print("\n=== Segmentos con curva propia (>= min_samples) ===")
    for key in sorted(calibrator.curves):
        curve = calibrator.curves[key]
        if curve.is_identity:
            continue
        print(f"  {key}  (n={curve.n_samples:.0f})")

    print("\n=== Ejemplo: aplicar calibración a un pick con prob=0.95 ===")
    for fam in ("result", "double_chance", "goals", "generic"):
        corrected = calibrator.apply(0.95, market_family=fam, league=None)
        print(f"  familia={fam:<15} 95% -> {corrected*100:.1f}%")


if __name__ == "__main__":
    main()