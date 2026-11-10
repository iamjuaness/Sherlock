"""Recalibra con corte el dia 30 de cada mes (desde 2026-07) y recalcula todo tras cada calibracion.

Flujo: borra las calibraciones actuales (copia en data/backups/calibration_<ts>/), recalcula todo,
y para cada corte busca los mejores parametros solo (sin pasarlos por consola), calibra y recalcula.
Uso: uv run python scripts/calibrate_monthly.py [--start 2026-07] [--day 30] [--no-recalc]
"""
import argparse
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, ".")

CAL_DIR = Path("data/calibration")


def cutoffs(start: str, day: int, today: date) -> list[str]:
    y, m = (int(x) for x in start.split("-"))
    out = []
    while date(y, m, 1) <= today:
        try:
            d = date(y, m, day)
        except ValueError:  # mes sin ese dia
            d = None
        if d and d <= today:
            out.append(d.isoformat())
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-07")
    ap.add_argument("--day", type=int, default=30)
    ap.add_argument("--no-recalc", action="store_true")
    args = ap.parse_args()

    from fastapi.testclient import TestClient

    from src.core.train_calibration import run_training
    from src.ui.api.compare import reset_calibrator_cache
    from src.ui.api.main import app

    def recalc(client, label: str) -> None:
        if args.no_recalc:
            return
        t = time.perf_counter()
        r = client.post("/api/v1/analysis/recalculate-all?use_general_stats=false&parallel=true", timeout=None)
        print(f"[{label}] recalculate-all HTTP {r.status_code} en {time.perf_counter() - t:.0f}s {r.json()}", flush=True)
        if r.status_code != 200:
            raise SystemExit(1)

    if CAL_DIR.exists():
        bk = Path("data/backups") / f"calibration_{datetime.now():%Y%m%dT%H%M%S}"
        shutil.copytree(CAL_DIR, bk)
        print(f"backup calibraciones -> {bk}")
        (CAL_DIR / "active.json").unlink(missing_ok=True)
        for f in (CAL_DIR / "history").glob("*.json"):
            f.unlink()
    reset_calibrator_cache()

    cuts = cutoffs(args.start, args.day, date.today())
    print("cortes:", cuts, flush=True)
    with TestClient(app) as client:
        recalc(client, "sin calibracion")
        for cut in cuts:
            t = time.perf_counter()
            rep = run_training(until_date=cut)  # prior_strength/min_samples=None -> busqueda automatica
            tun = rep.tuning or {}
            print(f"[{cut}] {rep.reason} | muestras={rep.n_samples} | "
                  f"prior_strength={tun.get('prior_strength')} min_samples={tun.get('min_samples')} "
                  f"({time.perf_counter() - t:.0f}s)", flush=True)
            reset_calibrator_cache()
            recalc(client, cut)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
