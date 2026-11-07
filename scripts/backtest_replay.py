"""Replay de partidos con resultado por el motor ACTUAL y métricas (Brier, log-loss, ROI).

Uso: PYTHONPATH=<repo> python scripts/backtest_replay.py --db data/sherlock.db --n 1500 --out out.json
Solo lectura sobre la BD (mode=ro). Compara versiones corriéndolo en dos checkouts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import logging
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.database import Base
from src.ui.api.compare_models import FootballCompareRequest
from src.ui.api.compare_service import compare_football


def outcome(sel: str, hg: int, ag: int) -> int | None:
    s = sel.strip()
    if s == "Local":
        return int(hg > ag)
    if s == "Empate":
        return int(hg == ag)
    if s == "Visitante":
        return int(hg < ag)
    if s.startswith("BTTS S"):
        return int(hg > 0 and ag > 0)
    if s == "BTTS No":
        return int(not (hg > 0 and ag > 0))
    if s.endswith("Goles") and s.split()[0] in ("Over", "Under"):
        line = float(s.split()[1])
        tot = hg + ag
        return int(tot > line) if s.startswith("Over") else int(tot < line)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/sherlock.db")
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dump", help="JSON con los registros por pick (para Monte Carlo)")
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    rows = con.execute(
        "select payload, final_score_home, final_score_away from analysis_history "
        "where has_odds=1 and final_score_home is not null and final_score_away is not null "
        "order by date desc limit ?", (a.n,)).fetchall()
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)

    recs, fails = [], 0
    with Session(eng) as db:
        for payload, hg, ag in rows:
            try:
                pl = json.loads(payload)
                od = pl.get("odds") or {}
                if not od.get("home"):  # cuotas viven en sources[bookmaker]; preferir betano
                    srcs = od.get("sources") or {}
                    src = srcs.get("betano") or next((x for x in srcs.values() if x and x.get("home")), None)
                    if not src:
                        fails += 1
                        continue
                    drop = {"bookmaker", "home_team", "away_team", "over_25", "under_25", "over_15", "under_15"}
                    pl["odds"] = {k: v for k, v in src.items() if k not in drop}
                req = FootballCompareRequest(sport="football", **pl)
                resp = asyncio.run(compare_football(req, db=db))
            except Exception:
                fails += 1
                continue
            for v in resp.values:
                y = outcome(v.selection, hg, ag)
                if y is None or not v.odds or v.odds <= 1.0:
                    continue
                recs.append({
                    "y": y, "odds": v.odds, "raw": (v.model_prob_raw or 0) / 100.0,
                    "final": (v.final_prob or 0) / 100.0,
                    "mkt": (v.p_market_no_vig or 0) / 100.0, "stake": v.stake_units or 0.0,
                    "pub": bool(v.is_publishable), "ev": v.edge_ev or 0.0,
                })

    if a.dump:
        json.dump([r for r in recs if r["pub"] and r["stake"] > 0], open(a.dump, "w"))

    def clip(p): return min(max(p, 1e-6), 1 - 1e-6)
    def metrics(rs, key):
        if not rs: return None
        br = sum((r[key] - r["y"]) ** 2 for r in rs) / len(rs)
        ll = -sum(math.log(clip(r[key] if r["y"] else 1 - r[key])) for r in rs) / len(rs)
        return {"n": len(rs), "brier": round(br, 5), "logloss": round(ll, 5)}
    def roi(rs, flag):
        sel = [r for r in rs if flag(r)]
        if not sel: return {"bets": 0}
        st = sum(r["stake"] for r in sel) or 1.0
        pnl = sum(r["stake"] * ((r["odds"] - 1) if r["y"] else -1) for r in sel)
        flat = sum((r["odds"] - 1) if r["y"] else -1 for r in sel)
        return {"bets": len(sel), "staked_u": round(st, 2), "pnl_u": round(pnl, 2),
                "roi_staked": round(pnl / st, 4), "roi_flat": round(flat / len(sel), 4)}

    res = {"matches": len(rows), "failed": fails, "preds": len(recs),
           "raw": metrics(recs, "raw"), "final": metrics(recs, "final"),
           "market_novig": metrics([r for r in recs if r["mkt"] > 0], "mkt"),
           "model_same_rows": metrics([r for r in recs if r["mkt"] > 0], "final"),
           "value_ev>3%": roi(recs, lambda r: r["ev"] > 0.03),
           "publishable_staked": roi(recs, lambda r: r["pub"] and r["stake"] > 0)}
    json.dump(res, open(a.out, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
