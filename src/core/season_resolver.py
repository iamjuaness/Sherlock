"""Identidad de temporada de un partido (liga + temporada), fallando cerrado.

Prioridad: `season_id` de SofaScore (único por liga+temporada, también separa
Apertura/Clausura) > `season_year` normalizado. Sin ninguno -> None: no se adivina.
"""

from __future__ import annotations

import re
from typing import Any


def norm_season_year(value: Any) -> str | None:
    """'26/27' -> '2026/2027'; '2025' queda igual; vacío -> None."""
    if value is None or str(value).strip() == "":
        return None
    m = re.fullmatch(r"\s*(\d{2}|\d{4})\s*[/-]\s*(\d{2}|\d{4})\s*", str(value))
    if not m:
        return str(value).strip()
    return "/".join(g if len(g) == 4 else f"20{g}" for g in m.groups())


def season_key(season_id: Any = None, season_year: Any = None, season: Any = None) -> tuple | None:
    """Clave comparable de temporada. ('id', '70681') o ('year', '2025/2026') o None."""
    if season_id not in (None, "", 0, "0"):
        return ("id", str(season_id).strip())
    year = norm_season_year(season_year) or norm_season_year(season)
    return ("year", year) if year else None


def same_season(a: tuple | None, b: tuple | None) -> bool:
    """Misma temporada solo si ambas son conocidas y del mismo tipo de clave e igual valor."""
    return a is not None and b is not None and a == b


def extract_season_columns(payload: Any) -> tuple[str | None, str | None, str | None]:
    """(season_id, season_year, season_label) crudos del payload, como texto; para las columnas indexadas."""
    import json

    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except ValueError:
            return None, None, None
    if not isinstance(payload, dict):
        return None, None, None
    return tuple(None if payload.get(k) is None else str(payload[k]) for k in ("season_id", "season_year", "season"))  # type: ignore[return-value]
