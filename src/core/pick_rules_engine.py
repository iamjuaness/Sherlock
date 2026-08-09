"""
Motor único de reglas de picks para Sherlock.

Reemplaza:
  - compare.py :: is_pick_blocked_by_rules()
  - main.py    :: apply_pick_rules() -> eval_cond() / field_map (inline)
  - main.py    :: simulate_pick_rules() -> get_stat_from_payload() (inline)

Objetivo: un único punto de verdad para evaluar pick_rules.json, usado
tanto en el análisis en vivo (compare_football) como en la re-evaluación
histórica (/api/v1/analysis/apply-rules) y en el simulador
(/api/v1/pick-rules/simulate). Así se elimina la incongruencia entre
picks generados en vivo y picks recalculados sobre el historial.

Uso:
    from src.core.pick_rules_engine import evaluate_pick_rules, StatSource

    # Desde compare.py (objetos FootballTeamStats)
    blocked, reason = evaluate_pick_rules(selection, StatSource.from_team_stats(h, a), rules)

    # Desde main.py (dicts guardados en AnalysisHistory)
    blocked, reason = evaluate_pick_rules(selection, StatSource.from_payload(home_stats, away_stats), rules)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger("sherlock.pick_rules")

_OPERATORS: dict[str, Callable[[float, float], bool]] = {
    ">=": lambda a, b: a >= b,
    ">":  lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<":  lambda a, b: a < b,
    "==": lambda a, b: a == b,
}

# ─────────────────────────────────────────────────────────────
# Market family / side extraction (idéntico al de compare.py,
# centralizado aquí para que ambos flujos usen exactamente el mismo)
# ─────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def market_family(text: str) -> str:
    s = normalize_text(text)
    if any(k in s for k in ["btts", "ambos marcan", "both teams to score"]):
        return "btts"
    if any(k in s for k in ["corner", "corners", "córner", "córners"]):
        return "corners"
    if any(k in s for k in ["tarjeta", "tarjetas", "cards", "yellow cards", "amarillas"]):
        return "cards"
    if any(k in s for k in ["foul", "fouls", "faltas"]):
        return "fouls"
    if any(k in s for k in ["pta", "a puerta", "target", "shots_target", "shot_target"]):
        return "shots_target"
    if any(k in s for k in ["shot", "shots", "tiros", "remates"]):
        return "shots"
    if any(k in s for k in ["goal", "goals", "goles"]):
        return "goals"
    if any(k in s for k in ["double chance", "doble oportunidad", "1x", "x2", "12"]):
        return "double_chance"
    if any(k in s for k in ["moneyline", "ml", "1x2", "ganador", "local", "visitante", "empate"]):
        return "result"
    return "generic"


def market_side(text: str) -> str:
    s = normalize_text(text)
    patterns = [
        (r"\b(over|más\s+de|mas\s+de)\b", "over"),
        (r"\b(under|menos\s+de)\b", "under"),
        (r"\b(yes|sí|si)\b", "yes"),
        (r"\bno\b", "no"),
        (r"\b(local|home)\b", "home"),
        (r"\b(visitante|away)\b", "away"),
        (r"\b(empate|draw)\b", "draw"),
        (r"\b(1x|home_draw)\b", "home_draw"),
        (r"\b(x2|draw_away)\b", "draw_away"),
        (r"\b(12|home_away)\b", "home_away"),
    ]
    for pattern, side in patterns:
        if re.search(pattern, s):
            return side
    return "none"


# ─────────────────────────────────────────────────────────────
# StatSource: abstrae de dónde vienen los stats (objeto vivo o
# dict de historial) para que get_stat() sea idéntico en ambos casos.
# ─────────────────────────────────────────────────────────────

@dataclass
class StatSource:
    home: dict[str, Optional[float]]
    away: dict[str, Optional[float]]
    odds: dict[str, Any]  # raw odds dict from payload / FootballOdds

    # Mapeo único de claves de condición -> claves internas normalizadas.
    # Si agregas una stat nueva en rules.html (STAT_OPTIONS), agrégala aquí también.
    _BASE_KEYS = {
        "xg_per_game", "goals_per_game", "goals_conceded_per_game",
        "corners_per_game", "shots_per_game", "shots_on_target_per_game",
        "yellow_cards_per_game", "possession_pct", "xga_per_game",
    }

    @classmethod
    def from_team_stats(cls, home_obj: Any, away_obj: Any, odds_obj: Any = None) -> "StatSource":
        """Build StatSource from live FootballTeamStats objects.
        
        odds_obj: optional FootballOdds (or any object/dict) to expose cuotas as conditions.
        """
        def extract(obj: Any) -> dict[str, Optional[float]]:
            return {
                "xg_per_game": getattr(obj, "xg_per_game", None),
                "xga_per_game": getattr(obj, "xga_per_game", None) or getattr(obj, "goals_conceded_per_game", None),
                "goals_per_game": getattr(obj, "goals_per_game", None),
                "goals_conceded_per_game": getattr(obj, "goals_conceded_per_game", None),
                "corners_per_game": getattr(obj, "corners_per_game", None),
                "shots_per_game": getattr(obj, "shots_per_game", None),
                "shots_on_target_per_game": getattr(obj, "shots_on_target_per_game", None),
                "yellow_cards_per_game": getattr(obj, "yellow_cards_per_game", None),
                "possession_pct": getattr(obj, "possession_pct", None),
            }

        # Normalize odds_obj to a plain dict regardless of whether it's a Pydantic model or dict
        odds_dict: dict[str, Any] = {}
        if odds_obj is not None:
            if hasattr(odds_obj, "model_dump"):
                odds_dict = odds_obj.model_dump()
            elif hasattr(odds_obj, "dict"):
                odds_dict = odds_obj.dict()
            elif isinstance(odds_obj, dict):
                odds_dict = odds_obj

        return cls(home=extract(home_obj), away=extract(away_obj), odds=odds_dict)

    @classmethod
    def from_payload(cls, home_payload: dict, away_payload: dict, odds_payload: dict | None = None) -> "StatSource":
        """Build StatSource from saved payload dicts (AnalysisHistory).
        
        odds_payload: the ``odds`` sub-dict from the stored JSON payload.
        """
        def extract(p: dict) -> dict[str, Optional[float]]:
            p = p or {}
            return {
                "xg_per_game": p.get("xg_per_game"),
                "xga_per_game": p.get("xga_per_game") or p.get("goals_conceded_per_game"),
                "goals_per_game": p.get("goals_per_game"),
                "goals_conceded_per_game": p.get("goals_conceded_per_game"),
                "corners_per_game": p.get("corners_per_game"),
                "shots_per_game": p.get("shots_per_game"),
                "shots_on_target_per_game": p.get("shots_on_target_per_game"),
                "yellow_cards_per_game": p.get("yellow_cards_per_game"),
                "possession_pct": p.get("possession_pct"),
            }
        return cls(home=extract(home_payload), away=extract(away_payload), odds=odds_payload or {})

    def get(self, stat_key: str) -> Optional[float]:
        """
        Resuelve stat_key tal como aparece en pick_rules.json / rules.html:
          - "home_xg_per_game" / "away_xg_per_game"
          - stats compuestas: "xg_xga_diff_max"
          - cuotas: "odds_home", "odds_draw", "odds_away", "odds_btts_yes", "odds_btts_no",
                    "odds_dc_1x", "odds_dc_x2", "odds_dc_12",
                    "odds_goals_over_2.5", "odds_goals_under_2.5",
                    "odds_corners_over_9.5", "odds_cards_under_4.5", etc.
        """
        if stat_key.startswith("home_"):
            base = stat_key[len("home_"):]
            return self.home.get(base)
        if stat_key.startswith("away_"):
            base = stat_key[len("away_"):]
            return self.away.get(base)

        if stat_key == "xg_xga_diff_max":
            return self._xg_xga_diff_max()

        # ── Cuotas ──────────────────────────────────────────────────────────
        if stat_key.startswith("odds_"):
            return self._resolve_odds(stat_key[len("odds_"):])

        logger.warning("pick_rules: stat_key desconocida '%s' — condición ignorada como NO cumplida", stat_key)
        return None

    def _resolve_odds(self, key: str) -> Optional[float]:
        """
        Resuelve una clave de cuota (sin el prefijo 'odds_').

        Claves simples directas (coinciden con campos del payload odds):
          home, draw, away, btts_yes, btts_no, dc_1x, dc_x2, dc_12

        Claves de línea dinámica con formato <mercado>_<over|under>_<linea>:
          goals_over_2.5  → odds["goals_over_odds"]["2.5"]
          corners_under_9.5 → odds["corners_under_odds"]["9.5"]
          cards_over_4.5  → odds["cards_over_odds"]["4.5"]
          shots_over_22.5 → odds["shots_over_odds"]["22.5"]
          shots_target_over_9.5 → odds["shots_target_over_odds"]["9.5"]
        """
        o = self.odds or {}

        # Simple scalar odds
        _SIMPLE_MAP = {
            "home": "home", "draw": "draw", "away": "away",
            "btts_yes": "btts_yes", "btts_no": "btts_no",
            "dc_1x": "dc_1x", "dc_x2": "dc_x2", "dc_12": "dc_12",
        }
        if key in _SIMPLE_MAP:
            val = o.get(_SIMPLE_MAP[key])
            return float(val) if val is not None else None

        # Dynamic line odds: <market>_<over|under>_<line>
        # Supported markets: goals, corners, cards, shots, shots_target
        _LINE_MARKETS = [
            "shots_target",  # must come before "shots" to avoid prefix collision
            "goals", "corners", "cards", "shots",
        ]
        for market in _LINE_MARKETS:
            for direction in ("over", "under"):
                prefix = f"{market}_{direction}_"
                if key.startswith(prefix):
                    line_str = key[len(prefix):]
                    odds_dict_key = f"{market}_{direction}_odds"  # e.g. "goals_over_odds"
                    line_dict = o.get(odds_dict_key, {})
                    if not isinstance(line_dict, dict):
                        return None
                    val = line_dict.get(line_str) or line_dict.get(str(float(line_str)))
                    return float(val) if val is not None else None

        logger.warning("pick_rules: clave de cuota desconocida '%s' — condición ignorada", key)
        return None

    def _xg_xga_diff_max(self) -> Optional[float]:
        """
        Diferencia máxima entre |xG - xGA| de ambos equipos.
        Mide equilibrio ofensivo/defensivo: valores bajos = equipo parejo
        (ataca y defiende similar), valores altos = equipo desbalanceado
        (muy ofensivo o muy defensivo).
        """
        h_xg, h_xga = self.home.get("xg_per_game"), self.home.get("xga_per_game")
        a_xg, a_xga = self.away.get("xg_per_game"), self.away.get("xga_per_game")

        if None in (h_xg, h_xga, a_xg, a_xga):
            logger.warning(
                "pick_rules: xg_xga_diff_max no se pudo calcular por datos faltantes "
                "(h_xg=%s h_xga=%s a_xg=%s a_xga=%s)", h_xg, h_xga, a_xg, a_xga
            )
            return None

        diff_home = abs(h_xg - h_xga)
        diff_away = abs(a_xg - a_xga)
        return max(diff_home, diff_away)


# ─────────────────────────────────────────────────────────────
# Evaluador principal
# ─────────────────────────────────────────────────────────────

def evaluate_pick_rules(
    selection: str,
    stats: StatSource,
    rules: list[dict],
) -> tuple[bool, Optional[str]]:
    """
    Devuelve (is_blocked, reason).

    is_blocked = True si existe una regla ENABLED cuyo market_family/market_side
    coincide con la selección y AL MENOS UNA de sus condiciones no se cumple.

    A diferencia de la implementación anterior:
      - Nunca traga excepciones en silencio: cada fallo se loggea con detalle.
      - Si una condición no se puede evaluar (stat=None), la condición se
        considera NO cumplida -> bloquea el pick (fail-safe, no fail-open).
        Esto es intencional: preferimos un falso bloqueo detectable en logs
        a un pick "de valor" publicado que en realidad no cumple la regla.
    """
    if not isinstance(rules, list):
        return False, None

    family = market_family(selection)
    side = market_side(selection)

    for rule in rules:
        if not rule.get("enabled", False):
            continue

        rule_family = rule.get("market_family", "")
        rule_side = rule.get("market_side", "")

        if rule_family and rule_family != family:
            continue
        if rule_side and rule_side != side:
            continue

        for cond in rule.get("conditions", []):
            stat_key = cond.get("stat")
            operator = cond.get("operator")
            expected = cond.get("value")

            if operator not in _OPERATORS:
                logger.error(
                    "pick_rules: operador inválido '%s' en regla '%s' — bloqueando por seguridad",
                    operator, rule.get("id"),
                )
                return True, f"Regla '{rule.get('name')}': operador inválido '{operator}'"

            actual = stats.get(stat_key)

            if actual is None:
                logger.warning(
                    "pick_rules: no se pudo resolver '%s' para selección '%s' (regla '%s') — "
                    "bloqueando pick por datos insuficientes",
                    stat_key, selection, rule.get("id"),
                )
                return True, f"Regla '{rule.get('name')}': falta stat '{stat_key}'"

            try:
                condition_met = _OPERATORS[operator](actual, expected)
            except TypeError as exc:
                logger.error(
                    "pick_rules: error comparando '%s' %s %s (regla '%s'): %s",
                    stat_key, operator, expected, rule.get("id"), exc,
                )
                return True, f"Regla '{rule.get('name')}': error evaluando '{stat_key}'"

            if not condition_met:
                reason = cond.get("label") or f"{stat_key} {operator} {expected}"
                logger.info(
                    "pick_rules: pick '%s' BLOQUEADO por regla '%s' — condición no cumplida: %s "
                    "(valor real=%s)",
                    selection, rule.get("id"), reason, actual,
                )
                return True, f"Regla '{rule.get('name')}': {reason} (valor real: {actual})"

    return False, None
