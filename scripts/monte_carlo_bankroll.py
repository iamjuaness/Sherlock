"""Monte Carlo de bankroll: remuestrea (bootstrap) las apuestas publicadas del backtest.

Uso: python scripts/monte_carlo_bankroll.py picks.json [--bankroll 100] [--bets 300] [--sims 5000]
Stake en unidades (1u = 1% del bankroll). Reporta retorno, drawdown máximo y prob. de ruina.
"""
import argparse
import json

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("picks")
ap.add_argument("--bankroll", type=float, default=100.0)
ap.add_argument("--bets", type=int, default=300)
ap.add_argument("--sims", type=int, default=5000)
ap.add_argument("--ruin", type=float, default=0.5, help="ruina = bankroll < ruin*inicial")
a = ap.parse_args()

recs = json.load(open(a.picks))
if not recs:
    raise SystemExit("sin apuestas publicadas")
pnl = np.array([r["stake"] * ((r["odds"] - 1) if r["y"] else -1.0) for r in recs])  # unidades
rng = np.random.default_rng(7)
draw = rng.choice(pnl, size=(a.sims, a.bets), replace=True)
curve = a.bankroll + np.cumsum(draw, axis=1)
peak = np.maximum.accumulate(np.concatenate([np.full((a.sims, 1), a.bankroll), curve], axis=1), axis=1)[:, 1:]
dd = ((peak - curve) / peak).max(axis=1)
final = curve[:, -1]
print(json.dumps({
    "apuestas_base": len(recs), "pnl_medio_por_apuesta_u": round(float(pnl.mean()), 4),
    "final_mediana": round(float(np.median(final)), 2),
    "final_p5_p95": [round(float(np.percentile(final, 5)), 2), round(float(np.percentile(final, 95)), 2)],
    "prob_perdida": round(float((final < a.bankroll).mean()), 3),
    "drawdown_mediano": round(float(np.median(dd)), 3), "drawdown_p95": round(float(np.percentile(dd, 95)), 3),
    "prob_ruina": round(float((curve.min(axis=1) < a.ruin * a.bankroll).mean()), 3),
}, indent=2))
