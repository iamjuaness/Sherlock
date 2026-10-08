import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class StrEnum(str, Enum):
    """String enum for Python compatibility across versions."""
    def __str__(self) -> str:
        return str(self.value)


class MarketFamily(StrEnum):
    GOALS = "goals"
    BTTS = "btts"
    RESULT = "result"
    DOUBLE_CHANCE = "double_chance"
    CARDS = "cards"
    CORNERS = "corners"
    SHOTS = "shots"
    SHOTS_TARGET = "shots_target"
    FOULS = "fouls"
    GENERIC = "generic"


class MarketSide(StrEnum):
    OVER = "over"
    UNDER = "under"
    YES = "yes"
    NO = "no"
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"
    HOME_DRAW = "home_draw"
    DRAW_AWAY = "draw_away"
    HOME_AWAY = "home_away"
    GENERIC = "generic"


@dataclass(frozen=True)
class MarketKey:
    family: str
    side: str
    line: Optional[float]
    line_bucket: Optional[str]


DEFAULT_LINE_BUCKETS: Dict[str, List[Tuple[Optional[float], Optional[float], str]]] = {
    "goals": [
        (None, 1.5, "low_0_5_1_5"),
        (2.0, 2.5, "core_2_5"),
        (3.0, 3.5, "high_3_5"),
        (4.0, None, "extreme_4_plus"),
    ],
    "cards": [
        (None, 3.5, "low_2_5_3_5"),
        (4.0, 4.5, "core_4_5"),
        (5.0, None, "high_5_5_plus"),
    ],
    "corners": [
        (None, 8.5, "low"),
        (9.0, 10.5, "core"),
        (11.0, None, "high"),
    ],
    "shots_target": [
        (None, 6.5, "low_6_5"),
        (7.0, 8.5, "core_7_5_8_5"),
        (9.0, None, "high_9_plus"),
    ],
    "shots": [
        (None, 22.5, "low"),
        (23.0, 25.5, "core"),
        (26.0, None, "high"),
    ],
}


def load_line_buckets(config_path: Optional[str] = None) -> Dict[str, List[Tuple[Optional[float], Optional[float], str]]]:
    """Carga bandas de línea desde un archivo JSON si existe, o retorna las predeterminadas."""
    if config_path:
        path = Path(config_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    buckets = {}
                    for fam, entries in data.items():
                        buckets[fam] = [
                            (e[0], e[1], e[2]) for e in entries
                        ]
                    return buckets
            except Exception:
                pass
    return DEFAULT_LINE_BUCKETS


def normalize_market_family(raw: str) -> str:
    """Normaliza el nombre de un mercado a una familia de mercado canónica.

    ORDEN DE COMPROBACIÓN IMPORTANTE:
    - BTTS y 1X2 / Double Chance se evalúan prioritariamente.
    - SHOTS_TARGET debe evaluarse SIEMPRE antes de SHOTS para evitar que
      subcadenas como 'tiros' o 'shots' capturen 'tiros a puerta' / 'shots on target'.
    """
    if not raw:
        return MarketFamily.GENERIC

    val = str(raw).strip().lower()

    # BTTS: sin ambigüedad
    if any(k in val for k in ["btts", "ambos marcan", "both teams to score", "marcan ambos", "ambos anotan"]):
        return MarketFamily.BTTS

    # RESULT: 1x2 explícito antes de double_chance
    if (
        any(k in val for k in [
            "resultado final", "match result", "resultado del partido",
            "ganador del partido", "moneyline",
        ])
        or re.search(r"\b1x2\b", val)
    ):
        return MarketFamily.RESULT

    # Double Chance
    if (
        any(k in val for k in ["doble oportunidad", "double chance"])
        or re.search(r"\b(1x|x2|12)\b", val)
    ):
        return MarketFamily.DOUBLE_CHANCE

    # Tarjetas y Córners
    if any(k in val for k in ["tarjetas", "cards", "tarjetas amarillas", "yellow cards"]):
        return MarketFamily.CARDS
    if any(k in val for k in ["corners", "córners", "saques de esquina", "corner"]):
        return MarketFamily.CORNERS

    # SHOTS_TARGET: comprobación estricta ANTES de SHOTS
    if any(k in val for k in [
        "tiros a puerta",
        "tiros al arco",
        "shots on target",
        "shots_target",
        "shot_on_target",
        "remates a puerta",
        "remates al arco",
        "sot"
    ]):
        return MarketFamily.SHOTS_TARGET

    # SHOTS: Remates y tiros totales
    if any(k in val for k in ["tiros totales", "tiros", "shots", "remates totales", "remates"]):
        return MarketFamily.SHOTS

    if any(k in val for k in ["faltas", "fouls"]):
        return MarketFamily.FOULS
    if any(k in val for k in ["gol", "goles", "goals", "over", "under", "total"]):
        return MarketFamily.GOALS
    if any(k in val for k in ["ganador", "visitante", "local", "empate"]):
        return MarketFamily.RESULT

    return MarketFamily.GENERIC


def normalize_market_side(raw: str, family: Optional[str] = None) -> str:
    """Normaliza el lado del mercado (side) a su representación canónica."""
    if not raw:
        return MarketSide.GENERIC

    val = str(raw).strip().lower()

    # Over / Under
    if any(k in val for k in ["over", "más de", "mas de", "más", "mas", "+"]):
        return MarketSide.OVER
    if any(k in val for k in ["under", "menos de", "menos", "-"]):
        return MarketSide.UNDER

    # Result 1X2 (comprobar antes de doble oportunidad si no incluye 'empate' u 'o')
    if ("empate" not in val and " o " not in val) or family in [MarketFamily.RESULT, "result"]:
        if val in ["1", "home", "local", "home win", "victoria local"] or re.search(r"\b(local|home)\b", val):
            return MarketSide.HOME
        if val in ["2", "away", "visitante", "away win", "victoria visitante"] or re.search(r"\b(visitante|away)\b", val):
            return MarketSide.AWAY
        if val in ["x", "draw", "empate"] or re.search(r"\b(empate|draw)\b", val):
            return MarketSide.DRAW

    # BTTS / Yes No
    if val in ["sí", "si", "yes", "btts_yes", "btts sí", "btts si"] or any(k in val for k in ["btts_yes", "yes", "si", "sí"]):
        return MarketSide.YES
    if val in ["no", "btts_no", "btts no"] or any(k in val for k in ["btts_no", "no"]):
        return MarketSide.NO

    # Doble Oportunidad
    if any(k in val for k in ["1x", "home_draw", "local o empate", "local o empate (1x)", "1 o x"]):
        return MarketSide.HOME_DRAW
    if any(k in val for k in ["x2", "draw_away", "empate o visitante", "empate o visitante (x2)", "x o 2"]):
        return MarketSide.DRAW_AWAY
    if any(k in val for k in ["12", "home_away", "local o visitante", "local o visitante (12)", "1 o 2"]):
        return MarketSide.HOME_AWAY

    # Result 1X2 fallback
    if val in ["1", "home", "local", "home win", "victoria local"] or re.search(r"\b(local|home)\b", val):
        return MarketSide.HOME
    if val in ["2", "away", "visitante", "away win", "victoria visitante"] or re.search(r"\b(visitante|away)\b", val):
        return MarketSide.AWAY
    if val in ["x", "draw", "empate"] or re.search(r"\b(empate|draw)\b", val):
        return MarketSide.DRAW

    return MarketSide.GENERIC


def extract_market_line(raw: str) -> Optional[float]:
    """Extrae el número de línea flotante (e.g. 2.5, 3.5) de un texto de mercado o selección."""
    if not raw:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(raw))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


CATEGORICAL_FAMILIES = {MarketFamily.RESULT, MarketFamily.DOUBLE_CHANCE, MarketFamily.BTTS, "result", "double_chance", "btts", "doublechance"}


def line_bucket_for(family: str, line: Optional[float], config_path: Optional[str] = None) -> Optional[str]:
    """Determina la banda de línea (line_bucket) para una familia y número de línea dado."""
    if line is None or family in CATEGORICAL_FAMILIES:
        return "no_line"

    buckets_map = load_line_buckets(config_path)
    rules = buckets_map.get(family)
    if not rules:
        return f"line_{str(line).replace('.', '_')}"

    for min_val, max_val, bucket_name in rules:
        if min_val is not None and line < min_val:
            continue
        if max_val is not None and line > max_val:
            continue
        return bucket_name

    return f"line_{str(line).replace('.', '_')}"


def parse_market(raw_market: str, raw_selection: Optional[str] = None, config_path: Optional[str] = None) -> MarketKey:
    """Parsea un texto de mercado y selección y devuelve una MarketKey canónica."""
    combined = f"{raw_market or ''} {raw_selection or ''}".strip()

    family = normalize_market_family(combined)
    side = normalize_market_side(raw_selection or combined, family=family)
    line = None if family in CATEGORICAL_FAMILIES else extract_market_line(combined)

    line_bucket = line_bucket_for(family, line, config_path=config_path)

    return MarketKey(
        family=family,
        side=side,
        line=line,
        line_bucket=line_bucket,
    )


def market_group_key(league: Optional[str], family: str, side: str, line_bucket: Optional[str] = None) -> str:
    """Genera la clave canónica del grupo/segmento de mercado."""
    clean_league = (league or "global").strip().lower()
    bucket_str = line_bucket or "no_line"
    return f"league:{clean_league}|family:{family}|side:{side}|bucket:{bucket_str}"


# Alias de compatibilidad
line_bucket = line_bucket_for
market_canonical_group_key = market_group_key
