"""Grid search de --folds/--prior-strength/--min-samples por corte temporal (solo lectura, no escribe artefactos).

Comparación justa entre n_folds distintos: todas las combinaciones se puntúan sobre la
MISMA ventana OOF común (muestras con timestamp >= cuantil 1/min(folds) del corte).
Criterio: menor log-loss calibrado entre las combinaciones que mejoran al crudo (improved()).
"""
from __future__ import annotations

import argparse
import itertools
import json
import logging
from concurrent.futures import ProcessPoolExecutor

FOLDS = [8, 10, 12, 15]
PRIORS = [35, 60, 100]
MINS = [60]


def run_cutoff(cutoff: str) -> dict:
    logging.disable(logging.CRITICAL)
    from src.core.train_calibration import extract_samples, load_rows_from_db
    from src.models.calibration import evaluate, walk_forward_calibrate

    rows = load_rows_from_db(include_excluded=True, until_date=cutoff)
    samples, _ = extract_samples(rows, require_timestamp=True)
    ts = sorted({s.timestamp for s in samples if s.timestamp is not None})
    common_start = ts[len(ts) // min(FOLDS)] if ts else None
    out = []
    for k, prior, mn in itertools.product(FOLDS, PRIORS, MINS):
        wf = walk_forward_calibrate(samples, n_folds=k, prior_strength=float(prior), min_samples=float(mn))
        idx = [i for i, s in enumerate(wf.samples) if s.timestamp >= common_start]
        if len(idx) < 200:
            continue
        pick = lambda xs: [xs[i] for i in idx]  # noqa: E731
        cal = evaluate(pick(wf.calibrated_probs), pick(wf.outcomes))
        raw = evaluate(pick(wf.raw_probs), pick(wf.outcomes))
        out.append({"folds": k, "prior": prior, "min_samples": mn, "n": cal["n"],
                    "improved": wf.improved(), "cal_ll": cal["log_loss"], "cal_brier": cal["brier"],
                    "cal_ece": cal["ece"], "raw_ll": raw["log_loss"], "raw_brier": raw["brier"]})
    ok = [r for r in out if r["improved"]] or out
    best = min(ok, key=lambda r: (round(r["cal_ll"], 5), r["cal_brier"], r["cal_ece"]))
    return {"cutoff": cutoff, "n_samples": len(samples), "best": best, "all": out}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoffs", nargs="+", default=["2026-07-30", "2026-08-30", "2026-09-30", "2026-10-30"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with ProcessPoolExecutor(max_workers=len(a.cutoffs)) as ex:
        res = list(ex.map(run_cutoff, a.cutoffs))
    json.dump(res, open(a.out, "w"), indent=1)
    for r in res:
        print(r["cutoff"], r["n_samples"], r["best"])
