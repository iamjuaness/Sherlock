"""A/B del split local/visitante: mismos partidos, mismo motor, con y sin `use_home_away_split`.

Uso: uv run python scripts/backtest_home_away.py --n 800 --out out.json
Solo lectura sobre la BD (mode=ro). Brier/log-loss de la prob. cruda (`raw`) y final, sobre
(a) todos los partidos y (b) solo los que tienen split en AMBOS equipos (cobertura real).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent))
from backtest_replay import outcome  # noqa: E402

from src.core.home_away_stats import compute_team_split  # noqa: E402
from src.core.season_resolver import season_key  # noqa: E402
from src.ui.api.compare_models import FootballCompareRequest  # noqa: E402
from src.ui.api.compare_service import compare_football  # noqa: E402


def prepare_odds(pl: dict) -> bool:
    od = pl.get("odds") or {}
    if od.get("home"):
        return True
    srcs = od.get("sources") or {}
    src = srcs.get("betano") or next((x for x in srcs.values() if x and x.get("home")), None)
    if not src:
        return False
    drop = {"bookmaker", "home_team", "away_team", "over_25", "under_25", "over_15", "under_15"}
    pl["odds"] = {k: v for k, v in src.items() if k not in drop}
    return True


def clip(p):
    return min(max(p, 1e-6), 1 - 1e-6)


def metrics(rs, key):
    if not rs:
        return None
    br = sum((r[key] - r["y"]) ** 2 for r in rs) / len(rs)
    ll = -sum(math.log(clip(r[key] if r["y"] else 1 - r[key])) for r in rs) / len(rs)
    return {"n": len(rs), "brier": round(br, 5), "logloss": round(ll, 5)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/sherlock.db")
    ap.add_argument("--n", type=int, default=150, help="partidos CUBIERTOS a evaluar")
    ap.add_argument("--scan", type=int, default=4000, help="filas recientes a recorrer")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    rows = con.execute(
        "select payload, final_score_home, final_score_away from analysis_history "
        "where has_odds=1 and final_score_home is not null and final_score_away is not null "
        "order by date desc limit ?", (a.scan,)).fetchall()
    eng = create_engine(f"sqlite:///file:{a.db}?mode=ro&uri=true")

    recs = {"base": [], "split": []}
    covered = fails = 0
    with Session(eng) as db:
        for payload, hg, ag in rows:
            if covered >= a.n:
                break
            try:
                pl = json.loads(payload)
                if not prepare_odds(pl):
                    fails += 1
                    continue
                req = FootballCompareRequest(sport="football", **pl)
                kick = req.match_date or req.date
                tgt = season_key(req.season_id, req.season_year, getattr(req, "season", None))
                cov = bool(
                    compute_team_split(db, req.home.name, "home", tgt, kick)
                    and compute_team_split(db, req.away.name, "away", tgt, kick)
                )
                if not cov:  # solo se evalúa donde el split realmente aplica (compare cuesta ~6 s)
                    continue
                resp = {
                    "base": asyncio.run(compare_football(req, db=db)),
                    "split": asyncio.run(
                        compare_football(req.model_copy(update={"use_home_away_split": True}), db=db)
                    ),
                }
            except Exception:
                fails += 1
                continue
            covered += cov
            for arm, r in resp.items():
                for v in r.values:
                    y = outcome(v.selection, hg, ag)
                    if y is None or not v.odds or v.odds <= 1.0:
                        continue
                    recs[arm].append({
                        "k": (id(req), v.selection), "cov": cov, "y": y,
                        "raw": (v.model_prob_raw or 0) / 100.0, "final": (v.final_prob or 0) / 100.0,
                        "mkt": (v.p_market_no_vig or 0) / 100.0,
                    })

    out = {"matches": len(rows), "failed": fails, "covered_matches": covered}  # `matches` = filas con split inaplicable incluidas en el scan
    for name, flt in (("all", lambda r: True), ("covered_only", lambda r: r["cov"])):
        out[name] = {
            arm: {"raw": metrics([r for r in rs if flt(r)], "raw"),
                  "final": metrics([r for r in rs if flt(r)], "final")}
            for arm, rs in recs.items()
        }
    out["market_novig_covered"] = metrics([r for r in recs["base"] if r["cov"] and r["mkt"] > 0], "mkt")
    json.dump(out, open(a.out, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
