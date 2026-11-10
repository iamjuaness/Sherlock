"""Agrega season_id (y season_year normalizado) a analysis_history para la última
temporada de cada liga en data/competitions.json.

Uso:
    uv run python scripts/backfill_season_ids.py          # dry-run
    uv run python scripts/backfill_season_ids.py --apply  # escribe (crea backup .bak)

Criterio: para cada liga con "season", la temporada objetivo es la season_year de las filas
que ya tienen ese season_id; si no hay, la más reciente presente en la DB. Se etiquetan las
filas SIN season_id cuyo año de inicio coincide con el de la temporada objetivo.
"""

import argparse
import json
import re
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sherlock.db"
COMPS = ROOT / "data" / "competitions.json"


def norm_season(value):
    """'26/27' -> '2026/2027'; '2025' queda igual."""
    m = re.fullmatch(r"\s*(\d{2}|\d{4})\s*[/-]\s*(\d{2}|\d{4})\s*", str(value or ""))
    if not m:
        return str(value).strip() if value else None
    return "/".join(g if len(g) == 4 else f"20{g}" for g in m.groups())


def start_year(season):
    m = re.match(r"\d{4}", season or "")
    return int(m.group()) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    comps = [c for c in json.loads(COMPS.read_text(encoding="utf-8")) if c.get("season")]
    con = sqlite3.connect(DB)
    updates = []  # (id, new_payload_json)

    for c in comps:
        sid = str(c["season"])
        rows = con.execute(
            "select id, payload from analysis_history where competition = ?", (c["name"],)
        ).fetchall()
        parsed = []
        for rid, pl in rows:
            try:
                p = json.loads(pl)
            except Exception:
                continue
            parsed.append((rid, p, norm_season(p.get("season_year") or p.get("season"))))

        labeled = {s for _, p, s in parsed if str(p.get("season_id") or "") == sid and s}
        if labeled:
            target = max(labeled, key=lambda s: start_year(s) or 0)
        else:
            seasons = [s for _, _, s in parsed if s and start_year(s)]
            if not seasons:
                continue
            target = max(seasons, key=start_year)
        ty = start_year(target)

        todo = [
            (rid, p)
            for rid, p, s in parsed
            if not p.get("season_id") and s and start_year(s) == ty
        ]
        for rid, p in todo:
            p["season_id"] = sid
            p["season_year"] = target
            updates.append((rid, json.dumps(p)))
        if todo:
            print(f"{c['name']}: {len(todo)} filas -> season_id={sid} ({target})")

    print(f"Total filas a corregir: {len(updates)}")
    if not args.apply:
        print("Dry-run. Usa --apply para escribir.")
        return
    shutil.copy2(DB, DB.with_suffix(".db.bak"))
    con.executemany(
        "update analysis_history set payload = ?, season_id = ?, season_year = ? where id = ?",
        [(p, str(json.loads(p)["season_id"]), str(json.loads(p)["season_year"]), i) for i, p in updates],
    )
    con.commit()
    print(f"Aplicado. Backup: {DB.with_suffix('.db.bak')}")


if __name__ == "__main__":
    main()
