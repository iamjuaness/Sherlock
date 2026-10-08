"""
Script de utilidad para listar segmentos por estado de gobernanza.

Uso:
    python scripts/list_governance.py --status blocked
    python scripts/list_governance.py --status reduced
    python scripts/list_governance.py  # lista todos
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.segment_governance import load_governance_config, SegmentStatus


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista segmentos por estado de governance")
    parser.add_argument("--status", choices=["active", "watch", "reduced", "blocked", "experimental"],
                        default=None, help="Filtrar por estado (sin filtro = todos)")
    parser.add_argument("--config", default="data/segment_governance.json",
                        help="Ruta al JSON de governance")
    args = parser.parse_args()

    config = load_governance_config(args.config)

    if not config:
        print(f"WARNING: No se encontro configuracion en {args.config}")
        return

    # Cargar versión del JSON
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version", "desconocida")
    except Exception:
        version = "desconocida"

    print(f"\nGovernance config version {version} -- {args.config}")
    print(f"   Total segmentos configurados: {len(config)}\n")

    # Agrupar por estado
    by_status: dict = {s: [] for s in SegmentStatus}
    for key, st in config.items():
        by_status[st].append(key)

    statuses_to_show = (
        [SegmentStatus(args.status)] if args.status else list(SegmentStatus)
    )

    icons = {
        SegmentStatus.BLOCKED: "[BLOCKED]",
        SegmentStatus.REDUCED: "[REDUCED]",
        SegmentStatus.WATCH: "[WATCH]",
        SegmentStatus.EXPERIMENTAL: "[EXPERIMENTAL]",
        SegmentStatus.ACTIVE: "[ACTIVE]",
    }

    for st in statuses_to_show:
        segs = by_status.get(st, [])
        if not segs:
            continue
        print(f"{icons.get(st, '⚪')} {st.value.upper()} ({len(segs)} segmentos)")
        for seg in sorted(segs):
            print(f"   {seg}")
        print()


if __name__ == "__main__":
    main()
