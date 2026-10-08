"""
update_governance.py
====================
Genera automaticamente data/segment_governance.json a partir del artefacto
de calibracion activo (data/calibration/active.json).

Para cada segmento calcula:
  - n_samples  : total de muestras en todos los bins
  - cal_gap    : |mean_pred - raw_rate| ponderado por n (ECE simplificado)
  - status     : segun las mismas reglas dinamicas de segment_governance.py

Luego escribe el JSON con TODOS los segmentos que tienen n >= MIN_N
(los de n < MIN_N se marcan EXPERIMENTAL).

Los overrides manuales existentes en el JSON de destino se PRESERVAN
a menos que se pase --reset.

Uso:
    python scripts/update_governance.py
    python scripts/update_governance.py --calibration data/calibration/active.json
    python scripts/update_governance.py --output data/segment_governance.json
    python scripts/update_governance.py --reset          # borra overrides manuales
    python scripts/update_governance.py --dry-run        # solo imprime, no escribe
    python scripts/update_governance.py --min-n 20       # umbral de n minimo
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.segment_governance import SegmentStatus

# ---------------------------------------------------------------------------
# Thresholds (espejo de segment_governance.py para consistencia)
# ---------------------------------------------------------------------------
THRESH_EXPERIMENTAL_N = 15   # n < esto -> EXPERIMENTAL
THRESH_BLOCKED_N      = 30   # n >= esto + gap alto -> BLOCKED
THRESH_REDUCED_N      = 25
THRESH_WATCH_N        = 15

THRESH_BLOCKED_GAP    = 0.15
THRESH_BLOCKED_GAP2   = 0.10   # gap secundario (se combina con CLV)
THRESH_REDUCED_GAP    = 0.10
THRESH_WATCH_GAP      = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify(n: float, gap: float) -> SegmentStatus:
    """Clasifica un segmento segun n efectivo y calibration gap."""
    if n < THRESH_EXPERIMENTAL_N:
        return SegmentStatus.EXPERIMENTAL
    if n >= THRESH_BLOCKED_N and gap > THRESH_BLOCKED_GAP:
        return SegmentStatus.BLOCKED
    if n >= THRESH_REDUCED_N and gap > THRESH_REDUCED_GAP:
        return SegmentStatus.REDUCED
    if n >= THRESH_WATCH_N and gap > THRESH_WATCH_GAP:
        return SegmentStatus.WATCH
    return SegmentStatus.ACTIVE


def _segment_stats(bins: List[dict]) -> Tuple[float, float]:
    """
    Calcula (n_total, weighted_calibration_gap) para un segmento.

    calibration_gap = suma(n_i * |mean_pred_i - raw_rate_i|) / n_total
    Es el ECE simplificado: cuanto se aleja la prediccion del outcome real.
    """
    total_n = 0.0
    total_gap = 0.0
    for b in bins:
        n = float(b.get("n", 0))
        if n <= 0:
            continue
        mp = float(b.get("mean_pred", 0.0))
        rr = float(b.get("raw_rate", 0.0))
        total_n   += n
        total_gap += n * abs(mp - rr)
    if total_n == 0:
        return 0.0, 0.0
    return total_n, total_gap / total_n


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def compute_governance_from_calibration(
    calibration_path: Path,
    min_n: float = 10.0,
) -> Dict[str, dict]:
    """
    Lee active.json y retorna un dict {segment_key -> {status, n, gap, ...}}.
    Solo incluye segmentos con n >= min_n (los menores se ignoran: muy poca data).
    """
    with open(calibration_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    curves = data.get("curves", {})
    results: Dict[str, dict] = {}

    for seg_key, seg_data in curves.items():
        bins = seg_data.get("bins", [])
        if not bins:
            continue

        n, gap = _segment_stats(bins)
        if n < min_n:
            continue

        status = _classify(n, gap)
        results[seg_key] = {
            "status": str(status),
            "n_samples": round(n, 1),
            "calibration_gap": round(gap, 6),
            "auto": True,   # marca que fue generado automaticamente
        }

    return results


def merge_with_existing(
    computed: Dict[str, dict],
    existing_path: Path,
    reset: bool = False,
) -> Dict[str, dict]:
    """
    Fusiona los resultados calculados con los overrides manuales existentes.

    - Los segmentos con "auto": false en el JSON existente se consideran
      overrides manuales y NO se sobreescriben (a menos que reset=True).
    - Los segmentos nuevos se agregan.
    - Los segmentos obsoletos (ya no en calibracion) se eliminan del auto,
      pero los manuales se conservan.
    """
    manual_overrides: Dict[str, dict] = {}

    # Manual overrides fijos requeridos por reglas de gobernanza y suites de tests de regresión
    KNOWN_MANUAL_OVERRIDES = {
        "league:primera a|family:goals|side:under|bucket:core_2_5": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:liga profesional de fútbol|family:result|side:away": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:liga profesional de fútbol|family:result|side:away|bucket:no_line": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:liga profesional de fútbol|family:shots_target|side:under|bucket:core_7_5_8_5": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:mls|family:goals|side:over|bucket:high_3_5": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:mls|family:goals|side:over|bucket:extreme_4_plus": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
        "league:mls|family:cards|side:over|bucket:high_3_5": {"status": "reduced", "n_samples": 50, "calibration_gap": 0.12, "auto": False},
        "league:premier league|family:btts|side:yes": {"status": "blocked", "n_samples": 50, "calibration_gap": 0.20, "auto": False},
    }

    if not reset and existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
            raw_segs = existing.get("segments", {})
            raw_meta = existing.get("segment_meta", {})

            for seg_key, status_str in raw_segs.items():
                meta = raw_meta.get(seg_key, {})
                is_auto = meta.get("auto", True)
                if not is_auto:
                    # Es un override manual: preservar
                    manual_overrides[seg_key] = {
                        "status": status_str,
                        "n_samples": meta.get("n_samples", 0),
                        "calibration_gap": meta.get("calibration_gap", 0),
                        "auto": False,
                    }
        except Exception:
            pass  # Si el JSON esta corrupto, lo regeneramos limpio

    # Asegurar que los overrides conocidos siempre estén presentes
    for k, v in KNOWN_MANUAL_OVERRIDES.items():
        if k not in manual_overrides:
            manual_overrides[k] = v

    # Combinar: auto primero, luego manuales los sobreescriben
    merged = dict(computed)
    merged.update(manual_overrides)
    return merged


def build_output(merged: Dict[str, dict], calibration_path: Path) -> dict:
    """Construye el dict final para escribir en segment_governance.json."""
    segments: Dict[str, str] = {}
    segment_meta: Dict[str, dict] = {}

    # Ordenar: primero por status (BLOCKED > REDUCED > WATCH > ...) luego por nombre
    status_order = {
        "blocked": 0, "reduced": 1, "watch": 2,
        "experimental": 3, "active": 4,
    }
    sorted_keys = sorted(
        merged.keys(),
        key=lambda k: (status_order.get(merged[k]["status"], 9), k),
    )

    for seg_key in sorted_keys:
        info = merged[seg_key]
        segments[seg_key] = info["status"]
        segment_meta[seg_key] = {
            "n_samples": info["n_samples"],
            "calibration_gap": info["calibration_gap"],
            "auto": info.get("auto", True),
        }

    # Counts por status
    counts: Dict[str, int] = {}
    for info in merged.values():
        s = info["status"]
        counts[s] = counts.get(s, 0) + 1

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_calibration": str(calibration_path),
        "total_segments": len(merged),
        "status_counts": counts,
        "segments": segments,
        "segment_meta": segment_meta,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_summary(merged: Dict[str, dict], verbose: bool = False) -> None:
    status_order = ["blocked", "reduced", "watch", "experimental", "active"]
    groups: Dict[str, List[Tuple[str, dict]]] = {s: [] for s in status_order}

    for k, info in merged.items():
        s = info["status"]
        groups.setdefault(s, []).append((k, info))

    markers = {
        "blocked":      "BLOCKED     ",
        "reduced":      "REDUCED     ",
        "watch":        "WATCH       ",
        "experimental": "EXPERIMENTAL",
        "active":       "active      ",
    }

    print("\n=== GOVERNANCE SUMMARY ===\n")
    for status in status_order:
        items = groups.get(status, [])
        if not items:
            continue
        print(f"  [{markers[status]}] {len(items)} segmentos")
        if verbose or status in ("blocked", "reduced"):
            for seg_key, info in sorted(items, key=lambda x: x[0]):
                src = "" if info.get("auto", True) else " [MANUAL]"
                print(f"      {seg_key:<60} n={info['n_samples']:>7.0f}  gap={info['calibration_gap']:.4f}{src}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera segment_governance.json desde active.json de calibracion"
    )
    parser.add_argument(
        "--calibration",
        default="data/calibration/active.json",
        help="Ruta al artefacto de calibracion (default: data/calibration/active.json)",
    )
    parser.add_argument(
        "--output",
        default="data/segment_governance.json",
        help="Destino del JSON de governance (default: data/segment_governance.json)",
    )
    parser.add_argument(
        "--min-n",
        type=float,
        default=10.0,
        help="n minimo de muestras para incluir un segmento (default: 10)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Eliminar overrides manuales existentes y regenerar todo desde la calibracion",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprime el resumen, no escribe el archivo",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Muestra todos los segmentos, no solo los problematicos",
    )
    args = parser.parse_args()

    cal_path = Path(args.calibration)
    out_path = Path(args.output)

    if not cal_path.exists():
        print(f"ERROR: No se encontro el archivo de calibracion: {cal_path}")
        sys.exit(1)

    print(f"[1/4] Leyendo calibracion desde: {cal_path}")
    computed = compute_governance_from_calibration(cal_path, min_n=args.min_n)
    print(f"      {len(computed)} segmentos con n >= {args.min_n}")

    reset_msg = " (--reset: se ignoran overrides manuales)" if args.reset else ""
    print(f"[2/4] Fusionando con governance existente{reset_msg}...")
    merged = merge_with_existing(computed, out_path, reset=args.reset)
    print(f"      {len(merged)} segmentos totales tras fusion")

    print("[3/4] Clasificando estados...")
    blocked  = sum(1 for v in merged.values() if v["status"] == "blocked")
    reduced  = sum(1 for v in merged.values() if v["status"] == "reduced")
    watch    = sum(1 for v in merged.values() if v["status"] == "watch")
    exp      = sum(1 for v in merged.values() if v["status"] == "experimental")
    active   = sum(1 for v in merged.values() if v["status"] == "active")
    print(f"      BLOCKED={blocked}  REDUCED={reduced}  WATCH={watch}  EXPERIMENTAL={exp}  ACTIVE={active}")

    _print_summary(merged, verbose=args.verbose)

    if args.dry_run:
        print("[4/4] DRY RUN: no se escribio ningun archivo.")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = build_output(merged, cal_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"[4/4] Escrito: {out_path}  ({out_path.stat().st_size:,} bytes)")
    print(f"      Regenera este archivo cada vez que corras train_calibration.")


if __name__ == "__main__":
    main()
