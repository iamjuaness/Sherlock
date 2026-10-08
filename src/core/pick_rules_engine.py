"""
Motor único de reglas de picks para Sherlock.

────────────────────────────────────────────────────────────────────────
CORRELACIÓN ENTRE PICKS: de heurística de texto a evidencia medida
────────────────────────────────────────────────────────────────────────
`sherlock_picks_audit_notebook.ipynb` mide el coeficiente phi empírico entre
picks sobre el histórico real en `sherlock.db` y lo exporta a
`data/market_correlation.json`. La clave de cada par en ese JSON NO es solo
la familia de mercado ("goals", "btts") — es familia + lado
("goals_over", "btts_yes", "result_home", "doublechance_home_draw"). Mezclar
Over y Under (o Sí/No) bajo la misma clave colapsaba la varianza real y
producía correlaciones en NaN; separarlas por lado lo corrigió y además
reveló correlaciones cruzadas reales que a nivel de familia agregada se
diluían (ej. goals_over↔btts_yes ≈ 0.41, antes ≈ invisible).

Este módulo replica esa misma clave familia_lado con `market_group()`, para
que la búsqueda en `data/market_correlation.json` encuentre exactamente lo
que el notebook midió. Dos particularidades a tener en cuenta:

  · Los NOMBRES de familia no son idénticos entre este módulo y el notebook
    (aquí "double_chance" / "shots_target" con guión bajo; en el notebook
    "doublechance" / "shotstarget" sin él, por historia de cada codebase).
    `_NOTEBOOK_FAMILY_ALIASES` traduce de un lado al otro SOLO para la
    búsqueda en la matriz de correlación — `market_family()` en sí no
    cambia, para no romper nada que ya dependa de su valor exacto
    (pick_rules.json, _LINE_MARKETS de StatSource, etc.).
  · Regla A (máximo 1 pick por mercado) sigue operando sobre la familia
    gruesa (`market_family()`), no sobre familia_lado: Over 2.5 y Under 2.5
    de goles deben seguir excluyéndose entre sí aunque sean "grupos"
    distintos, porque son apuestas contradictorias sobre el mismo mercado.
    Regla B (correlación cruzada) es la que ahora usa la clave fina.

  · Si hay `rho` medido con muestra confiable para el par de grupos:
      - |rho| >= block_above_abs_rho      -> bloqueo duro (como antes)
      - |rho| >= penalize_above_abs_rho   -> penalización de stake, NO bloqueo
      - en otro caso                      -> sin restricción
  · Si NO hay `rho` medido (grupo sin datos suficientes todavía): se usa
    `fallback_exclusive_groups`, evaluado sobre la familia gruesa (no tiene
    sentido pedirle al fallback una granularidad que no tiene evidencia).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

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

from src.domain.market_taxonomy import (
    normalize_market_family,
    normalize_market_side,
    line_bucket as canonical_line_bucket,
    market_canonical_group_key,
)

def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def market_family(text: str) -> str:
    """Wrapper para la taxonomía canónica."""
    return normalize_market_family(text)


def market_side(text: str) -> str:
    """Wrapper para la taxonomía canónica."""
    return normalize_market_side(text)


def market_line(text: str) -> Optional[float]:
    """
    Extrae la línea numérica de la selección (ej. 2.5 de "Over 2.5 goles").
    Devuelve None si no se encuentra un valor numérico explícito.
    """
    s = normalize_text(text)
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


_NOTEBOOK_FAMILY_ALIASES: dict[str, str] = {
    "double_chance": "doublechance",
    "shots_target": "shotstarget",
    "generic": "otro",
}


def market_group(text: str) -> str:
    """
    Clave familia_lado usada para consultar data/market_correlation.json.
    """
    fam = market_family(text)
    fam_alias = _NOTEBOOK_FAMILY_ALIASES.get(fam, fam)
    side = market_side(text)
    if side and side != "none":
        return f"{fam_alias}_{side}"
    return fam_alias


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
# Correlación basada en evidencia: carga de data/market_correlation.json
# ─────────────────────────────────────────────────────────────

# Solo los pares (a nivel de familia gruesa) que aún NO se pueden confirmar
# ni descartar con datos. Con la matriz familia_lado ya poblada, casi todo
# lo que antes vivía aquí (goals+btts, shots+shots_target) ahora tiene rho
# medido y se decide por número, no por esta lista — el fallback solo se usa
# si classify_correlation_severity no encuentra el par en la matriz.
DEFAULT_FALLBACK_EXCLUSIVE_GROUPS: list[list[str]] = [
    ["goals", "btts"],
    ["shots", "shots_target"],
]

DEFAULT_CORRELATION_RULES: dict[str, Any] = {
    # Nueva fuente de verdad: matriz medida sobre el histórico real, con
    # claves familia_lado (ver market_group()).
    "correlation_matrix_path": "data/market_correlation.json",
    "block_above_abs_rho": 0.3,
    "penalize_above_abs_rho": 0.2,
    # Factor por el que se multiplica el stake cuando el par cae en zona de
    # penalización (no de bloqueo). 0.25 = recorta el stake a 25%.
    "penalty_stake_factor": 0.25,
    # Se usa solo cuando NO hay rho medido con muestra confiable para el par
    # (evaluado sobre la familia gruesa, no sobre familia_lado).
    "fallback_exclusive_groups": DEFAULT_FALLBACK_EXCLUSIVE_GROUPS,
    # Se mantiene por compatibilidad hacia atrás: si algún caller viejo lee
    # "exclusive_groups" directamente, sigue viendo la lista conservadora.
    "exclusive_groups": DEFAULT_FALLBACK_EXCLUSIVE_GROUPS,
}


_correlation_matrix_cache: dict[str, tuple[float, dict[tuple[str, str], float]]] = {}

def _resolve_data_path(relative_or_abs_path: Optional[str]) -> str:
    if relative_or_abs_path and os.path.isabs(relative_or_abs_path) and os.path.exists(relative_or_abs_path):
        return relative_or_abs_path

    # Posibles rutas relativas al proyecto Sherlock
    candidates = [
        relative_or_abs_path,
        os.path.join(os.path.dirname(__file__), "..", "..", relative_or_abs_path or "data/market_correlation.json"),
        os.path.join(os.path.dirname(__file__), "..", relative_or_abs_path or "data/market_correlation.json"),
        os.path.join(os.getcwd(), relative_or_abs_path or "data/market_correlation.json"),
        os.path.join(os.getcwd(), "data", "market_correlation.json"),
    ]

    for cand in candidates:
        if cand and os.path.exists(cand):
            return os.path.abspath(cand)

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "market_correlation.json"))


def load_market_correlation_matrix(path: Optional[str] = None) -> dict[tuple[str, str], float]:
    resolved_path = _resolve_data_path(path)
    cache_key = resolved_path

    mtime = 0.0
    if os.path.exists(resolved_path):
        try:
            mtime = os.path.getmtime(resolved_path)
        except Exception:
            pass

    if cache_key in _correlation_matrix_cache:
        cached_mtime, cached_matrix = _correlation_matrix_cache[cache_key]
        if cached_mtime == mtime:
            return cached_matrix

    matrix: dict[tuple[str, str], float] = {}
    if os.path.exists(resolved_path):
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for pair in data.get("pairs", []):
                rho = pair.get("rho")
                fam_a = pair.get("family_a")
                fam_b = pair.get("family_b")
                if rho is None or not fam_a or not fam_b:
                    continue
                matrix[(fam_a, fam_b)] = float(rho)
                matrix[(fam_b, fam_a)] = float(rho)
        except Exception as e:
            logger.error("Error cargando matriz de correlación desde %s: %s", resolved_path, e)
    else:
        logger.warning(
            "pick_rules: no se encontró archivo de correlación en %s. Usando fallback_exclusive_groups.",
            resolved_path,
        )

    _correlation_matrix_cache[cache_key] = (mtime, matrix)
    return matrix


def clear_correlation_matrix_cache() -> None:
    """Útil en tests / tras regenerar market_correlation.json en caliente."""
    _correlation_matrix_cache.clear()


def market_correlation_rho(group_a: str, group_b: str, matrix: dict[tuple[str, str], float]) -> Optional[float]:
    if group_a == group_b:
        return 1.0
    return matrix.get((group_a, group_b))


def classify_correlation_severity(
    group_a: str,
    group_b: str,
    family_a: str,
    family_b: str,
    matrix: dict[tuple[str, str], float],
    fallback_exclusive_groups: list[list[str]],
    block_above_abs_rho: float = 0.3,
    penalize_above_abs_rho: float = 0.2,
) -> tuple[str, Optional[float]]:
    rho = market_correlation_rho(group_a, group_b, matrix)

    if rho is not None:
        abs_rho = abs(rho)
        if abs_rho >= block_above_abs_rho:
            return "block", rho
        if abs_rho >= penalize_above_abs_rho:
            return "penalize", rho
        return "ok", rho

    # Fallback por familia si no hay correlación empírica calculada
    for group in fallback_exclusive_groups:
        if family_a in group and family_b in group and family_a != family_b:
            return "block", None

    return "ok", None

    # Sin dato confiable a nivel fino: cae en la lista de familias aún no
    # confirmadas/descartadas con datos (evaluada a nivel de familia gruesa).
    for group in fallback_exclusive_groups:
        if family_a in group and family_b in group and family_a != family_b:
            return "block", None

    return "ok", None


def load_pick_rules_data(rules_path: Optional[str] = None) -> tuple[list[dict], dict]:
    """
    Carga el archivo pick_rules.json y devuelve tuple (rules_list, correlation_rules_dict).
    Soporta formato antiguo (lista de reglas) y formato nuevo (objeto con "rules" y "correlation_rules").
    """
    import os
    import json

    if rules_path is None:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pick_rules.json")

    rules_list: list[dict] = []
    correlation_rules: dict = dict(DEFAULT_CORRELATION_RULES)

    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    rules_list = data
                elif isinstance(data, dict):
                    rules_list = data.get("rules", [])
                    corr = data.get("correlation_rules")
                    if isinstance(corr, dict):
                        correlation_rules.update(corr)
        except Exception as e:
            logger.error("Error loading pick rules from %s: %s", rules_path, e)

    return rules_list, correlation_rules


def _risk_imports():
    from src.domain.eligibility import BlockReason, is_hard_blocked, record_hard_block
    from src.domain.risk import load_risk_limits
    return BlockReason, is_hard_blocked, record_hard_block, load_risk_limits



def resolve_match_picks_correlation(
    candidates: list[Any],
    correlation_rules: Optional[dict] = None,
    max_picks_per_match: Optional[int] = None,
    max_total_stake: Optional[float] = None,
) -> list[Any]:
    if not candidates:
        return candidates

    if correlation_rules is None:
        _, correlation_rules = load_pick_rules_data()

    BlockReason, is_hard_blocked, record_hard_block, load_risk_limits = _risk_imports()

    limits = load_risk_limits(correlation_rules)

    fallback_exclusive_groups = correlation_rules.get(
        "fallback_exclusive_groups",
        correlation_rules.get("exclusive_groups", DEFAULT_FALLBACK_EXCLUSIVE_GROUPS),
    )
    # Umbrales consistentes con DEFAULT_CORRELATION_RULES (0.3 y 0.2)
    block_above_abs_rho = float(correlation_rules.get("block_above_abs_rho", 0.3))
    penalize_above_abs_rho = float(correlation_rules.get("penalize_above_abs_rho", 0.2))
    penalty_stake_factor = float(correlation_rules.get("penalty_stake_factor", 0.25))

    correlation_matrix = load_market_correlation_matrix(
        correlation_rules.get("correlation_matrix_path")
    )

    if not limits.allows_publication:
        for pick in candidates:
            record_hard_block(
                pick,
                BlockReason.MANUAL_BLOCK,
                detail="Publicación detenida por kill switch",
            )
        return candidates

    def get_attr(item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    def set_attr(item: Any, key: str, value: Any) -> None:
        if isinstance(item, dict):
            item[key] = value
        else:
            try:
                setattr(item, key, value)
            except (AttributeError, ValueError):
                pass

    def is_candidate_valid(v: Any) -> bool:
        if is_hard_blocked(v):
            return False
        pub = get_attr(v, "is_publishable", False)
        und = get_attr(v, "is_underdog", False)
        val = get_attr(v, "is_value", False)
        return bool(pub or und or val)

    valid_picks = [v for v in candidates if is_candidate_valid(v)]
    if len(valid_picks) <= 1:
        return candidates

    def pick_merit_score(x: Any) -> tuple[float, float, float, float, str]:
        ds = get_attr(x, "display_score") or 0.0
        ev = get_attr(x, "edge_ev") or 0.0
        edge = get_attr(x, "edge") or 0.0
        qs = get_attr(x, "quality_score") or 0.0
        sel = str(get_attr(x, "selection", ""))
        return (float(ds), float(ev), float(edge), float(qs), sel)

    valid_picks.sort(key=pick_merit_score, reverse=True)

    selected_families: set[str] = set()
    selected_items: list[tuple[str, str, str, Optional[float]]] = []  # (family, group, side, line)
    accepted_picks: list[Any] = []
    current_stake: float = 0.0

    for pick in valid_picks:
        selection = get_attr(pick, "selection", "")
        family = market_family(selection)
        group = market_group(selection)
        side = market_side(selection)
        line = market_line(selection)
        stake = float(get_attr(pick, "stake_units") or 1.0)

        # Regla A: Misma línea, lado opuesto o duplicidad en la misma familia
        is_same_line_opposite = False
        for sfam, sgrp, sside, sline in selected_items:
            if family == sfam:
                if line is not None and sline is not None and line == sline:
                    opposite_pairs = {
                        ("over", "under"), ("under", "over"),
                        ("yes", "no"), ("no", "yes"),
                        ("home", "away"), ("away", "home"),
                    }
                    if (side, sside) in opposite_pairs:
                        is_same_line_opposite = True
                        break

        if family in selected_families or is_same_line_opposite:
            record_hard_block(
                pick,
                BlockReason.CORRELATION_BLOCKED,
                detail=f"Correlación: Bloqueo en misma línea/familia '{family}'",
            )
            continue

        # Regla B: Correlación cruzada entre picks
        is_excluded = False
        excluded_reason = ""
        applied_penalty = False
        worst_penalize_rho: Optional[float] = None
        worst_penalize_group = ""

        for sfam, sgrp, sside, sline in selected_items:
            severity, rho = classify_correlation_severity(
                group,
                sgrp,
                family,
                sfam,
                correlation_matrix,
                fallback_exclusive_groups,
                block_above_abs_rho=block_above_abs_rho,
                penalize_above_abs_rho=penalize_above_abs_rho,
            )
            if severity == "block":
                is_excluded = True
                if rho is not None:
                    excluded_reason = (
                        f"Correlación medida alta entre '{group}' y '{sgrp}' "
                        f"(rho={rho:.2f} >= {block_above_abs_rho:.2f})"
                    )
                else:
                    excluded_reason = (
                        f"Correlación: '{family}' y '{sfam}' sin dato confiable "
                        f"todavía; tratado como excluyente por precaución (fallback)"
                    )
                break
            if severity == "penalize":
                applied_penalty = True
                if rho is not None and (worst_penalize_rho is None or abs(rho) > abs(worst_penalize_rho)):
                    worst_penalize_rho = rho
                    worst_penalize_group = sgrp

        if is_excluded:
            record_hard_block(
                pick, BlockReason.CORRELATION_BLOCKED, detail=excluded_reason
            )
            continue

        if applied_penalty:
            penalized_stake = round(stake * penalty_stake_factor, 4)
            set_attr(pick, "stake_units", penalized_stake)
            set_attr(pick, "correlation_penalty_applied", True)
            set_attr(
                pick,
                "correlation_penalty_reason",
                f"Correlación moderada con '{worst_penalize_group}' "
                f"(rho={worst_penalize_rho:.2f})" if worst_penalize_rho is not None else
                "Correlación moderada detectada",
            )
            stake = penalized_stake

        selected_families.add(family)
        selected_items.append((family, group, side, line))
        accepted_picks.append(pick)
        current_stake += stake

    return candidates


# ─────────────────────────────────────────────────────────────
# Evaluador principal
# ─────────────────────────────────────────────────────────────

def evaluate_pick_rules(
    selection: str | list[Any],
    stats: Optional[StatSource] = None,
    rules: Union[list[dict], dict, None] = None,
) -> Any:
    """
    Devuelve (is_blocked, reason) si selection es una string.
    Si selection es una lista de picks de un partido, evalúa cada pick contra reglas
    y luego aplica resolve_match_picks_correlation.

    rules: puede ser una lista de reglas o un dict con {"rules": [...], "correlation_rules": {...}}.
    """
    rules_list: list[dict] = []
    correlation_rules: dict = dict(DEFAULT_CORRELATION_RULES)

    if isinstance(rules, dict):
        rules_list = rules.get("rules", [])
        corr = rules.get("correlation_rules")
        if isinstance(corr, dict):
            correlation_rules.update(corr)
    elif isinstance(rules, list):
        rules_list = rules

    # Caso 1: Se proporciona una lista completa de picks del partido
    if isinstance(selection, list):
        if stats is not None:
            # Evaluar reglas estadísticas a nivel individual
            for pick in selection:
                sel_text = getattr(pick, "selection", None) if not isinstance(pick, dict) else pick.get("selection")
                if sel_text:
                    blocked, reason = evaluate_pick_rules(sel_text, stats, rules_list)
                    if blocked:
                        record_hard_block(pick, BlockReason.RULE_BLOCKED, detail=reason)
        # Aplicar resolución de correlaciones entre picks del partido
        return resolve_match_picks_correlation(selection, correlation_rules=correlation_rules)

    # Caso 2: Evaluación individual de una string de selección
    if not isinstance(rules_list, list) or not stats:
        return False, None

    family = market_family(selection)
    side = market_side(selection)

    for rule in rules_list:
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
