"""CLV por familia de mercado desde picks con `closing_odds` (se cargan por /api/v1/closing-odds/submit).

CLV% = odds_tomada / closing_odds - 1  (>0: se batió el cierre). Solo lectura sobre la BD.
"""
import json
import sqlite3
import sys
from collections import defaultdict

from src.core.compressed_text import unpack

db = sys.argv[1] if len(sys.argv) > 1 else "data/sherlock.db"
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
agg = defaultdict(list)
for (pc,) in con.execute("select picks_calculados from analysis_history where picks_calculados is not null"):
    try:
        ps = json.loads(unpack(pc))
    except ValueError:
        continue
    for p in ps if isinstance(ps, list) else ps.get("picks", []):
        if isinstance(p, dict) and p.get("odds") and p.get("closing_odds") and p["closing_odds"] > 1:
            agg[(p.get("selection") or "?").split()[0]].append(p["odds"] / p["closing_odds"] - 1)
if not agg:
    raise SystemExit("0 picks con closing_odds: sin datos para CLV. Cargar cierres vía /api/v1/closing-odds/submit.")
for k, v in sorted(agg.items(), key=lambda kv: -len(kv[1])):
    print(f"{k:12s} n={len(v):5d} CLV medio={sum(v)/len(v):+.2%} batió_cierre={sum(x>0 for x in v)/len(v):.1%}")
