"""Quita del payload las cuotas de los picks marcados odds_suspect, para que recalculate-all no las regenere.

Over/Under: borra la linea en ambos lados (Over y Under) del mercado, en odds y en odds.sources.*
(la pareja se usa para quitar el vig, una cuota sola no sirve). 1X2: pone la cuota a None.
Uso: uv run python scripts/strip_suspect_odds_payload.py [--apply]
"""
import json
import re
import sys

sys.path.insert(0, ".")
from src.core.database import SessionLocal  # noqa: E402
from src.core.domain import AnalysisHistory  # noqa: E402

FAMILY = {"corners": "corners", "goles": "goals", "tarjetas": "cards"}
ONE_X_TWO = {"local": "home", "empate": "draw", "visitante": "away"}
OU = re.compile(r"^(over|under)\s+([\d.]+)\s+(\w+)", re.I)
unmatched: list[str] = []


def _suspect(node, out: set) -> None:
    if isinstance(node, list):
        for x in node:
            _suspect(x, out)
    elif isinstance(node, dict):
        if node.get("odds_suspect") and node.get("selection"):
            out.add(str(node["selection"]).strip())
        for v in node.values():
            _suspect(v, out)


def _strip(odds: dict, selection: str) -> int:
    """Quita la cuota de `selection` en un dict de cuotas; devuelve cuantas entradas borro."""
    n = 0
    m = OU.match(selection)
    if m and m.group(3).lower() in FAMILY:
        fam, line = FAMILY[m.group(3).lower()], m.group(2)
        for side in ("Over", "Under"):
            d = odds.get(f"{fam}{side}Odds")
            if isinstance(d, dict) and line in d:
                del d[line]
                n += 1
        return n
    key = ONE_X_TWO.get(selection.lower())
    if key and odds.get(key) is not None:
        odds[key] = None
        return 1
    return n


def main(apply: bool) -> None:
    db = SessionLocal()
    entries = analyses = 0
    for ah in db.query(AnalysisHistory):
        sels: set[str] = set()
        for col in ("picks_calculados", "compare_response_snapshot"):
            raw = getattr(ah, col)
            if raw:
                _suspect(json.loads(raw), sels)
        if not sels:
            continue
        payload = json.loads(ah.payload)
        odds = payload.get("odds")
        if not isinstance(odds, dict):
            continue
        n = 0
        for sel in sels:
            k = _strip(odds, sel)
            for src in (odds.get("sources") or {}).values():
                if isinstance(src, dict):
                    k += _strip(src, sel)
            if not k:
                unmatched.append(f"{ah.id}|{sel}")
            n += k
        if n:
            analyses += 1
            entries += n
            if apply:
                ah.payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    print(f"cuotas quitadas: {entries} en {analyses} analisis; sin match: {len(unmatched)}")
    for u in unmatched[:20]:
        print("  sin match:", u)
    if apply:
        db.commit()
    else:
        db.rollback()


if __name__ == "__main__":
    main("--apply" in sys.argv)
