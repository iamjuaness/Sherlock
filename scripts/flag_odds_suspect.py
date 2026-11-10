"""Marca picks con cuota/prob incoherentes: odds=None, edge=None, odds_suspect=True.

Criterio: |model_prob - prob_implicita_sin_vig| > 0.30 sobre picks con |edge| > 50 pp
(las anomalias extreme_edge). Uso: uv run python scripts/flag_odds_suspect.py [IDS.txt] [--apply]
(IDS.txt opcional: un analysis_id por linea; sin el, se revisan todos los analisis)
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.core.database import SessionLocal  # noqa: E402
from src.core.domain import AnalysisHistory  # noqa: E402

DIVERGENCE = 0.30
CLEAR = ("odds", "edge", "edge_ev", "kelly_fraction", "stake_units", "fair_odds")


def _pct(v):
    v = float(v)
    return v / 100.0 if v > 1.0 else v


def _flag(node) -> int:
    n = 0
    if isinstance(node, list):
        return sum(_flag(x) for x in node)
    if not isinstance(node, dict):
        return 0
    if "selection" in node and node.get("odds") and node.get("model_prob") is not None and node.get("edge") is not None:
        odds = float(node["odds"])
        implied = _pct(node["implied_prob_no_vig"]) if node.get("implied_prob_no_vig") else 1.0 / odds
        if abs(float(node["edge"])) > 50 and abs(_pct(node["model_prob"]) - implied) > DIVERGENCE:
            for k in CLEAR:
                if k in node:
                    node[k] = None
            node["is_value"] = False
            node["odds_suspect"] = True
            return 1
    return sum(_flag(v) for v in node.values())


def main(ids_file: str | None, apply: bool) -> None:
    db = SessionLocal()
    total = rows = 0
    q = db.query(AnalysisHistory)
    if ids_file:
        ids = {l.split("|")[0].strip() for l in Path(ids_file).read_text(encoding="utf-8").splitlines() if l.strip()}
        q = q.filter(AnalysisHistory.id.in_(ids))
    for ah in q:
        changed = 0
        for col in ("picks_calculados", "compare_response_snapshot"):
            raw = getattr(ah, col)
            if not raw:
                continue
            data = json.loads(raw)
            c = _flag(data)
            if c:
                changed += c
                if apply:
                    setattr(ah, col, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        if changed:
            rows += 1
            total += changed
    print(f"picks marcados (suma de columnas): {total} en {rows} analisis")
    if apply:
        db.commit()
    else:
        db.rollback()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else None, "--apply" in sys.argv)
