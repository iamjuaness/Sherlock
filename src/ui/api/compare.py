from __future__ import annotations

from typing import Optional
import json
import os, math
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Iterable
from src.core.pick_rules_engine import (
    evaluate_pick_rules,
    resolve_match_picks_correlation as engine_resolve_match_picks_correlation,
    load_pick_rules_data,
    StatSource,
)
from datetime import datetime, timezone
from src.domain.settlement import ReturnDistribution
from src.domain.eligibility import (
    DEFAULT_THRESHOLDS,
    BlockReason,
    EligibilityDecision,
    PickSnapshot,
    evaluate_eligibility,
    hard_blocks_from_flags,
)
from src.models.count_negative_binomial import (
    under_over_probabilities as _nb_under_over_probabilities,
)
# ── Nueva Arquitectura: Stake Engine, Trazabilidad, Taxonomía de Mercado ──
from src.domain.stake_engine import (
    compute_edge,
)
from src.domain.market_taxonomy import (
    parse_market,
    market_group_key,
    normalize_market_family,
)
# ── Portfolio: control de sobreexposición simultánea por jornada ──
from src.models.market_probability import blend_model_and_market_probability

load_dotenv()


from src.core.prediction.score_matrix import (  # usado internamente (definido en src/core/prediction)
    _poisson_over_under,
)

from src.ui.api.compare_models import (
    FootballTeamStats,
    LeagueStats,
    FootballCompareRequest,
    ValueIndicator,
    StatComparison,
    ProjectedLine,
)

logger = logging.getLogger("sherlock.compare")

MIN_STAKE = 1
MAX_STAKE = 3

# ───────────────────────────────────────────────────────────────
def _use_general_stats(req: FootballCompareRequest) -> bool:
    return req.use_general_stats


def _sanitize_and_fill_team_stats(team: FootballTeamStats) -> FootballTeamStats:
    """Preprocesa y sanea las estadísticas del equipo para garantizar consistencia entre totales y promedios."""
    t = team.model_copy()
    n = max(t.matches_played, 1)

    # 1. Goles
    if t.goals_per_game <= 0.0 and t.goals_scored > 0.0:
        t.goals_per_game = t.goals_scored / n
    elif t.goals_scored <= 0.0 and t.goals_per_game > 0.0:
        t.goals_scored = t.goals_per_game * n

    if t.goals_conceded_per_game <= 0.0 and t.goals_conceded > 0.0:
        t.goals_conceded_per_game = t.goals_conceded / n
    elif t.goals_conceded <= 0.0 and t.goals_conceded_per_game > 0.0:
        t.goals_conceded = t.goals_conceded_per_game * n

    # 2. Tiros
    if t.shots_per_game <= 0.0 and t.shots > 0.0:
        t.shots_per_game = t.shots / n
    elif t.shots <= 0.0 and t.shots_per_game > 0.0:
        t.shots = t.shots_per_game * n

    if t.shots_on_target_per_game <= 0.0 and t.shots_on_target > 0.0:
        t.shots_on_target_per_game = t.shots_on_target / n
    elif t.shots_on_target <= 0.0 and t.shots_on_target_per_game > 0.0:
        t.shots_on_target = t.shots_on_target_per_game * n

    if t.shots_off_target_per_game <= 0.0 and t.shots_off_target > 0.0:
        t.shots_off_target_per_game = t.shots_off_target / n
    elif t.shots_off_target <= 0.0 and t.shots_off_target_per_game > 0.0:
        t.shots_off_target = t.shots_off_target_per_game * n

    if t.shots_inside_box <= 0.0 and t.shots_inside_box_per_game > 0.0:
        t.shots_inside_box = t.shots_inside_box_per_game
    elif t.shots_inside_box_per_game <= 0.0 and t.shots_inside_box > 0.0:
        t.shots_inside_box_per_game = t.shots_inside_box
        
    if t.shots_outside_box <= 0.0 and t.shots_outside_box_per_game > 0.0:
        t.shots_outside_box = t.shots_outside_box_per_game
    elif t.shots_outside_box_per_game <= 0.0 and t.shots_outside_box > 0.0:
        t.shots_outside_box_per_game = t.shots_outside_box

    # 3. Corners
    if t.corners_per_game <= 0.0 and t.corners > 0.0:
        t.corners_per_game = t.corners / n
    elif t.corners <= 0.0 and t.corners_per_game > 0.0:
        t.corners = t.corners_per_game * n

    if t.corners_conceded_per_game <= 0.0 and t.corners_against > 0.0:
        t.corners_conceded_per_game = t.corners_against / n
    elif t.corners_against <= 0.0 and t.corners_conceded_per_game > 0.0:
        t.corners_against = t.corners_conceded_per_game * n

    # 4. Faltas y Offsides
    if t.fouls_per_game <= 0.0 and t.fouls > 0.0:
        t.fouls_per_game = t.fouls / n
    elif t.fouls <= 0.0 and t.fouls_per_game > 0.0:
        t.fouls = t.fouls_per_game * n

    if t.offside_per_game <= 0.0 and t.offsides > 0.0:
        t.offside_per_game = t.offsides / n
    elif t.offsides <= 0.0 and t.offside_per_game > 0.0:
        t.offsides = t.offside_per_game * n

    # 5. Tarjetas
    if t.yellow_cards_per_game <= 0.0 and t.yellow_cards > 0.0:
        t.yellow_cards_per_game = t.yellow_cards / n
    elif t.yellow_cards <= 0.0 and t.yellow_cards_per_game > 0.0:
        t.yellow_cards = t.yellow_cards_per_game * n

    # 6. Portería y Saves
    if t.save_pct > 1.0:
        t.save_pct /= 100.0

    if t.save_pct <= 0.0:
        actual_saves = t.saves if t.saves > 0.0 else (t.saves_per_game * n)
        actual_conceded = t.goals_conceded if t.goals_conceded > 0.0 else (t.goals_conceded_per_game * n)
        total_shots_on_target_faced = actual_saves + actual_conceded
        if total_shots_on_target_faced > 0.0:
            t.save_pct = actual_saves / total_shots_on_target_faced

    # 7. Big Chances
    if t.big_chances_per_game <= 0.0 and t.big_chances > 0.0:
        t.big_chances_per_game = t.big_chances / n
    elif t.big_chances <= 0.0 and t.big_chances_per_game > 0.0:
        t.big_chances = t.big_chances_per_game * n

    if t.big_chances_created_per_game <= 0.0 and t.big_chances_created > 0.0:
        t.big_chances_created_per_game = t.big_chances_created / n
    elif t.big_chances_created <= 0.0 and t.big_chances_created_per_game > 0.0:
        t.big_chances_created = t.big_chances_created_per_game * n

    # 8. Tiros en contra del oponente
    if t.shots_against_per_game <= 0.0 and t.shots_against > 0.0:
        t.shots_against_per_game = t.shots_against / n
    elif t.shots_against <= 0.0 and t.shots_against_per_game > 0.0:
        t.shots_against = t.shots_against_per_game * n

    if t.shots_on_target_against_per_game <= 0.0 and t.shots_on_target_against > 0.0:
        t.shots_on_target_against_per_game = t.shots_on_target_against / n
    elif t.shots_on_target_against <= 0.0 and t.shots_on_target_against_per_game > 0.0:
        t.shots_on_target_against = t.shots_on_target_against_per_game * n

    # 9. Conversión de gol
    if t.goal_conversion_pct <= 0.0 and t.goals_per_game > 0.0 and t.shots_per_game > 0.0:
        t.goal_conversion_pct = (t.goals_per_game / t.shots_per_game) * 100.0

    # 10. Correcciones menores de xg / xga si están ausentes (Issue #4)
    if t.xg_per_game is None or t.xg_per_game <= 0.0:
        t.xg_per_game = max(t.goals_per_game, 0.1)
        t.xg_is_imputed = True
    if t.xga_per_game is None or t.xga_per_game <= 0.0:
        t.xga_per_game = max(t.goals_conceded_per_game, 0.1)

    return t


def _implied_probability(odds: float | None) -> float:
    if odds is None or odds <= 0: return 0.0
    return (1.0 / odds) * 100.0


def _stat_comparison(label: str, key: str, hv: Optional[float], av: Optional[float],
                     higher_is_better: bool = True) -> StatComparison:
    if hv is None and av is None:
        adv = "even"
    elif hv is None:
        adv = "away" if higher_is_better else "home"
    elif av is None:
        adv = "home" if higher_is_better else "away"
    elif abs(hv - av) < 0.01:
        adv = "even"
    elif higher_is_better:
        adv = "home" if hv > av else "away"
    else:
        adv = "home" if hv < av else "away"
    return StatComparison(key=key, label=label, home_value=hv, away_value=av, advantage=adv)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza un datetime a naive-UTC para permitir comparaciones seguras
    entre fechas que pueden venir con o sin zona horaria."""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt









def get_nbinom_under_over_prob(
    line: float,
    h_mu: float,
    h_r: float,
    a_mu: float,
    a_r: float,
    num_sim: int | None = None,
) -> tuple[float, float, float]:
    """
    Probabilidades Under/Over/Push para un mercado de conteo. DETERMINISTA.

    Antes usaba `np.random.negative_binomial` sin semilla, por lo que dos
    recálculos idénticos podían producir probabilidades (y picks) distintos.
    Ahora delega en la convolución exacta de PMF de
    `src.models.count_negative_binomial`, que además liquida correctamente las
    líneas de cuarto (un Over 2.25 con total 2 es half-loss, no pérdida total).

    `num_sim` se conserva solo por compatibilidad de firma y se ignora.

    Devuelve (p_under, p_over, p_push) en porcentaje (0-100).
    """
    return _nb_under_over_probabilities(line, h_mu, h_r, a_mu, a_r)





def _fair_probabilities_from_odds(*odds_list: float | None) -> list[float]:
    valid_odds = [o for o in odds_list if o and o > 1.0]
    if not valid_odds:
        return [0.0] * len(odds_list)

    k = 1.0
    raw_probs = [1.0/o for o in valid_odds]

    for _ in range(10):
        current_sum = sum(p**k for p in raw_probs)
        if abs(current_sum - 1.0) < 0.0001:
            break
        k = k * (math.log(current_sum) / math.log(sum(raw_probs)) if sum(raw_probs) > 1 else 1)

    normalized = [(p**k) * 100.0 for p in raw_probs]

    result = []
    idx = 0
    for o in odds_list:
        if o and o > 1.0:
            result.append(normalized[idx])
            idx += 1
        else:
            result.append(0.0)
    return result

# ───────────────────────────────────────────────────────────────
# League Reliability Score
# ───────────────────────────────────────────────────────────────

def _compute_league_reliability_score(league: "LeagueStats") -> float:
    """
    Calcula un score de confiabilidad de la liga (LRS) en rango [0.15, 1.0].

    1. Base del LRS (LRS_base in [0.15, 0.85]): Determinado exclusivamente por volumen
       de partidos e integridad de datos:
       - Volumen de partidos (S_matches in [0.0, 0.50]):
         S_matches = 0.50 / (1 + exp(-(matches - 150) / 50))
         (Para matches >= 300, satura cerca de 0.50; con 0 partidos, tiende a ~0.02).
       - Integridad de datos de la competicion (S_integrity in [0.0, 0.35]):
         Porcentaje promedio de metricas no nulas disponibles en la liga
         (xG, tiros a puerta, corners, faltas, tarjetas).
       - LRS_base = max(0.15, S_matches + S_integrity)

    2. Ajuste Fino por Desempeno Historico (A_perf in [-0.10, +0.10]):
       - Condicion estricta: Solo se activa si league.historical_picks >= 50.
         Si no se cumple, A_perf = 0.0.
       - Si picks >= 50:
         A_perf = clip(0.5 * roi, -0.10, +0.10)
         donde roi se normaliza en escala decimal [-1.0, 1.0+].

    3. Formula final:
       LRS = clip(LRS_base + A_perf, 0.15, 1.00)
    """
    matches = int(getattr(league, "historical_matches", 0) or 0)
    picks = int(getattr(league, "historical_picks", 0) or 0)

    # -- 1. S_matches: Sigmoide centrada en 150 con escala 50 --
    z = (matches - 150.0) / 50.0
    z = max(-50.0, min(50.0, z))
    s_matches = 0.50 / (1.0 + math.exp(-z))
    s_matches = max(0.0, min(0.50, s_matches))

    # -- 2. S_integrity: Integridad de metricas de la competicion [0.0, 0.35] --
    def _is_valid_metric(val: Any) -> bool:
        if val is None:
            return False
        try:
            f = float(val)
            return not math.isnan(f) and f > 0.0
        except (ValueError, TypeError):
            return False

    has_xg = _is_valid_metric(getattr(league, "avg_xg_per_game", None)) or _is_valid_metric(getattr(league, "avg_xg", None))
    has_shots_target = _is_valid_metric(getattr(league, "avg_shots_target_per_game", None))
    has_corners = _is_valid_metric(getattr(league, "avg_corners_per_game", None))
    has_fouls = _is_valid_metric(getattr(league, "avg_fouls_per_game", None))
    has_cards = (
        _is_valid_metric(getattr(league, "avg_cards_per_game", None))
        or _is_valid_metric(getattr(league, "avg_yellow_cards_per_game", None))
    )

    metrics_status = [has_xg, has_shots_target, has_corners, has_fouls, has_cards]
    pct_available = sum(1.0 for m in metrics_status if m) / float(len(metrics_status))
    s_integrity = max(0.0, min(0.35, 0.35 * pct_available))

    lrs_base = max(0.15, min(0.85, s_matches + s_integrity))

    # -- 3. A_perf: Ajuste fino por desempeno historico [-0.10, +0.10] --
    a_perf = 0.0
    if picks >= 50:
        raw_roi = getattr(league, "roi", None)
        if raw_roi is not None and abs(float(raw_roi)) > 1e-6:
            roi_val = float(raw_roi)
            if abs(roi_val) > 1.0:
                roi_val = roi_val / 100.0
        else:
            profit = float(getattr(league, "historical_profit", 0.0) or 0.0)
            roi_val = profit / picks

        a_perf = max(-0.10, min(0.10, 0.50 * roi_val))

    lrs = max(0.15, min(1.00, lrs_base + a_perf))
    return round(lrs, 3)


MIN_PICKS_FOR_EMPIRICAL = 10
FULL_WEIGHT_PICKS = 60.0

MARKET_REF_ACCURACY = {
    "corners": 0.52, "cards": 0.52, "shots": 0.52, "shots_target": 0.52, "fouls": 0.52,
    "goals": 0.55, "btts": 0.54, "result": 0.55,
    "double_chance": 0.57, "generic": 0.53,
}


# ── Calibración probabilística real (Beta-Binomial jerárquica, sin GLM) ──
# El artefacto se entrena offline con picks liquidados y se valida walk-forward.
# Si no existe, `apply_calibration` degrada a la identidad: nunca inventa una
# corrección que no esté respaldada por evidencia.
CALIBRATION_ARTIFACT_PATH = os.getenv(
    "SHERLOCK_CALIBRATION_PATH", "data/calibration/active.json"
)


# ── Gobernanza de Segmentos ─────────────────────────────────────────────
# Ruta configurable; fallback al JSON generado por update_governance.py.
GOVERNANCE_PATH = os.getenv("SHERLOCK_GOVERNANCE_PATH", "data/segment_governance.json")

_governance_cache: "dict[str, Any]" = {"mtime": None, "data": None}

# Factores de stake por status de gobernanza (unificados con src.models.segment_governance)
_STATUS_MULTIPLIERS: "dict[str, float]" = {
    "blocked":      0.0,   # bloqueo duro: stake cero -> SEGMENT_GOVERNANCE_BLOCKED
    "reduced":      0.25,  # stake reducido a 25% (unificado con get_governance_multipliers)
    "watch":        0.50,  # stake en vigilancia al 50%
    "experimental": 0.30,  # segmento nuevo con muy poca muestra
    "active":       1.0,   # sin restriccion
}


def get_segment_governance() -> "dict":
    """
    Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.

    Nunca lanza: un artefacto ausente o corrupto degrada a dict vacio (sin restricciones).
    """
    path = Path(GOVERNANCE_PATH)
    try:
        mtime = path.stat().st_mtime if path.exists() else None
    except OSError:
        mtime = None

    if _governance_cache["data"] is not None and _governance_cache["mtime"] == mtime:
        return _governance_cache["data"]

    if mtime is None:
        data: "dict" = {}
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(
                "Gobernanza cargada: %d segmentos (active=%s blocked=%s reduced=%s watch=%s).",
                data.get("total_segments", 0),
                data.get("status_counts", {}).get("active", 0),
                data.get("status_counts", {}).get("blocked", 0),
                data.get("status_counts", {}).get("reduced", 0),
                data.get("status_counts", {}).get("watch", 0),
            )
        except Exception as exc:
            logger.warning("Error cargando gobernanza desde %s (%s). Sin restricciones.", path, exc)
            data = {}

    _governance_cache["mtime"] = mtime
    _governance_cache["data"] = data
    return data


def _get_governance_multiplier(
    segment_key: "str",
    league: "str | None" = None,
    family: "str | None" = None,
    side: "str | None" = None,
    bucket: "str | None" = None,
) -> "tuple[str, float, float, float]":
    """
    Resuelve el status de gobernanza y el multiplicador de stake para un segmento.

    Busca en orden jerarquico decreciente (mas especifico primero):
      1. segment_key completo (league+family+side+bucket)
      2. league+family+side+bucket
      3. league+family+side
      4. league+family
      5. league (solo)
      6. family+side+bucket
      7. family+side
      8. family (solo)

    Devuelve (status, governance_multiplier, drift_score).
    Si el segmento no esta en el artefacto, devuelve ('active', 1.0, 0.0).
    """
    gov = get_segment_governance()
    segments: "dict" = gov.get("segments", {})
    segment_meta: "dict" = gov.get("segment_meta", {})

    if not segments:
        return "active", 1.0, 0.0

    # Construir las claves a buscar en orden de especificidad
    candidates: "list[str]" = []
    if segment_key:
        candidates.append(segment_key)

    # Variantes jerarquicas parciales
    if league and family and side and bucket:
        candidates.append(f"league:{league}|family:{family}|side:{side}|bucket:{bucket}")
    if league and family and side:
        candidates.append(f"league:{league}|family:{family}|side:{side}")
    if league and family:
        candidates.append(f"league:{league}|family:{family}")
    if league:
        candidates.append(f"league:{league}")
    if family and side and bucket:
        candidates.append(f"family:{family}|side:{side}|bucket:{bucket}")
    if family and side:
        candidates.append(f"family:{family}|side:{side}")
    if family:
        candidates.append(f"family:{family}")

    for key in candidates:
        status = segments.get(key)
        if status is not None:
            status_str = str(status).lower()
            meta = segment_meta.get(key, {})
            drift = float(meta.get("drift_score", 0.0) or meta.get("calibration_gap", 0.0))

            if status_str == "reduced":
                # Si segment_meta especifica un stake_multiplier o un factor basado en calibration_gap/drift, lo usamos
                if "stake_multiplier" in meta and meta["stake_multiplier"] is not None:
                    multiplier = float(meta["stake_multiplier"])
                elif "calibration_gap" in meta and meta["calibration_gap"] is not None:
                    gap = abs(float(meta["calibration_gap"]))
                    # Cuanto mayor sea el gap de calibración, mayor la reducción (mínimo 0.2, máximo 0.8)
                    multiplier = max(0.2, min(0.8, round(1.0 - (gap * 2.0), 2)))
                elif drift > 0:
                    multiplier = max(0.2, min(0.8, round(1.0 - drift, 2)))
                else:
                    multiplier = _STATUS_MULTIPLIERS.get("reduced", 0.25)
            else:
                multiplier = _STATUS_MULTIPLIERS.get(status_str, 1.0)

            # Extraer min_edge_add canónico de segment_governance
            min_edge_add = 0.0
            if "min_edge_add" in meta and meta["min_edge_add"] is not None:
                min_edge_add = float(meta["min_edge_add"])
            else:
                try:
                    from src.models.segment_governance import SegmentStatus, get_governance_multipliers
                    gov_dict = get_governance_multipliers(SegmentStatus(status_str))
                    # min_edge_add viene en porcentaje si el edge se mide en % (ej. 4.0% para 0.04) o en puntos
                    # get_governance_multipliers da 0.04 para REDUCED, 0.02 para WATCH -> 4.0pp y 2.0pp
                    min_edge_add = float(gov_dict.get("min_edge_add", 0.0)) * 100.0
                except Exception:
                    pass

            return status_str, multiplier, drift, min_edge_add

    return "active", 1.0, 0.0, 0.0


def reset_governance_cache() -> None:
    """Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)."""
    _governance_cache["mtime"] = None
    _governance_cache["data"] = None


_calibrator_cache: "dict[str, Any]" = {"mtime": None, "obj": None}


def get_calibrator():
    """
    Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.

    Nunca lanza: un artefacto corrupto o ausente degrada a identidad y se
    registra en el log. Fallar cerrado aquí significa no tocar la probabilidad.
    """
    from src.models.calibration import HierarchicalCalibrator

    path = Path(CALIBRATION_ARTIFACT_PATH)
    try:
        mtime = path.stat().st_mtime if path.exists() else None
    except OSError:
        mtime = None

    if _calibrator_cache["obj"] is not None and _calibrator_cache["mtime"] == mtime:
        return _calibrator_cache["obj"]

    if mtime is None:
        cal = HierarchicalCalibrator.identity()
    else:
        try:
            cal = HierarchicalCalibrator.load(path)
            logger.info(
                "Calibrador cargado: version=%s segmentos=%d n=%s",
                cal.version, len(cal.curves), cal.metadata.get("n_samples"),
            )
        except Exception as exc:  # artefacto corrupto o versión incompatible
            logger.warning(
                "Artefacto de calibración inválido en %s (%s). Usando identidad.",
                path, exc,
            )
            cal = HierarchicalCalibrator.identity()

    _calibrator_cache["mtime"] = mtime
    _calibrator_cache["obj"] = cal
    return cal


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


_version_cache: "dict[str, Any]" = {"mtime": None, "versions": []}

# Caché para get_calibrator_for_timestamp: evita cargar todos los archivos
# de history en cada llamada (crítico en recalculate-all paralelo).
# La clave es un frozenset de (path, mtime) de los archivos cargados.
_history_cal_cache: "dict[str, Any]" = {"key": None, "cals": None}


def _build_history_cache_key(artifacts: list) -> frozenset:
    """Clave de caché basada en los paths y mtimes de los artefactos."""
    items = []
    for p in artifacts:
        try:
            items.append((str(p), p.stat().st_mtime))
        except OSError:
            items.append((str(p), None))
    return frozenset(items)


def get_calibrator_for_timestamp(predicted_at: "datetime | str | None"):
    """
    Devuelve el calibrador activo en el momento predicted_at según el historial
    de activaciones.

    IMPORTANTE: la lista de calibradores se cachea a nivel de proceso y solo
    se recarga si cambian los archivos en disco (mtime). Esto es crítico para
    el rendimiento en recalculate-all paralelo, donde se llama miles de veces.
    """
    from src.models.calibration import HierarchicalCalibrator
    if predicted_at is None:
        return HierarchicalCalibrator.identity()

    dt = _coerce_datetime(predicted_at)
    if dt is None:
        return HierarchicalCalibrator.identity()

    # Resolver los artefactos disponibles.
    # IMPORTANTE: se usa CALIBRATION_ARTIFACT_PATH (variable de módulo) en vez de
    # os.getenv(...) directamente para que el monkeypatch de tests funcione correctamente.
    active_path_str = os.getenv("SHERLOCK_CALIBRATION_PATH", CALIBRATION_ARTIFACT_PATH)
    base_dir = Path(active_path_str).parent
    history_dir = base_dir / "history"
    artifacts: list = []

    if history_dir.exists():
        for f in history_dir.glob("*.json"):
            # Ignorar archivos legacy con sufijo _until_ (no son versiones independientes)
            if "_until_" in f.name:
                continue
            artifacts.append(f)
    active_p = Path(active_path_str)
    if active_p.exists() and active_p not in artifacts:
        artifacts.append(active_p)

    # Verificar si el caché sigue vigente
    cache_key = _build_history_cache_key(artifacts)
    if _history_cal_cache["key"] == cache_key and _history_cal_cache["cals"] is not None:
        loaded_cals = _history_cal_cache["cals"]
    else:
        # Recargar desde disco
        loaded_cals = []
        for p in artifacts:
            try:
                cal = HierarchicalCalibrator.load(p)
                act_str = cal.activated_at_utc or cal.fitted_at or cal.metadata.get("fitted_at")
                act_dt = _coerce_datetime(act_str)
                if act_dt:
                    loaded_cals.append((act_dt, cal))
            except Exception:
                continue
        loaded_cals.sort(key=lambda x: x[0])
        _history_cal_cache["key"] = cache_key
        _history_cal_cache["cals"] = loaded_cals
        logger.debug(
            "Cache de calibradores reconstruida: %d versiones cargadas.",
            len(loaded_cals),
        )

    if not loaded_cals:
        return get_calibrator()

    # Si dt es anterior a la primera activación válida, no había calibración activa
    if dt < loaded_cals[0][0]:
        return HierarchicalCalibrator.identity()

    # Seleccionar la última versión cuya fecha de activación <= dt
    selected = None
    for act_dt, cal in loaded_cals:
        if act_dt <= dt:
            selected = cal
        else:
            break

    return selected or HierarchicalCalibrator.identity()


def get_calibration_version_for_timestamp(predicted_at: datetime | str | None) -> str:
    """Retorna la versión de la calibración para un timestamp dado o 'unverified'."""
    cal = get_calibrator_for_timestamp(predicted_at)
    if not cal.is_trained:
        return "unverified"
    return cal.version or "unverified"


def reset_calibrator_cache() -> None:
    """Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)."""
    _calibrator_cache["mtime"] = None
    _calibrator_cache["obj"] = None
    _version_cache["mtime"] = None
    _history_cal_cache["key"] = None
    _history_cal_cache["cals"] = None
    _version_cache["versions"] = []


def apply_calibration(
    raw_prob: float,
    odds: float,
    market_family: str,
    selection: str | None = None,
    league: "LeagueStats | None" = None,
    league_name: str | None = None,
    predicted_at_utc: datetime | str | None = None,
) -> float:
    """
    Aplica la curva jerárquica de calibración al pick según la versión activa en predicted_at_utc.

    La cuota se mantiene en la firma por compatibilidad con llamadas
    existentes, pero no altera la probabilidad del evento. La calibración
    usa exclusivamente evidencia histórica de probabilidad vs resultado.

    La segmentación efectiva es:
      global -> familia -> familia/dirección -> línea -> liga/dirección.
    """
    if raw_prob is None:
        return raw_prob

    resolved_league = league_name

    if resolved_league is None and league is not None:
        resolved_league = (
            getattr(league, "name", None)
            or getattr(league, "league_name", None)
        )

    resolved_selection = selection or market_family
    # Issue #31: Usar la taxonomía canónica (parse_market) idéntica a train_calibration.py
    mk = parse_market(resolved_selection, resolved_selection)
    resolved_family = str(mk.family)
    resolved_side = str(mk.side)
    resolved_line = mk.line_bucket

    try:
        calibrator = get_calibrator_for_timestamp(predicted_at_utc) if predicted_at_utc is not None else get_calibrator()
        return calibrator.apply(
            prob=raw_prob,
            market_family=resolved_family,
            side=resolved_side,
            line_bucket=resolved_line,
            league=resolved_league,
        )
    except Exception as exc:
        logger.warning(
            "Fallo al calibrar %s (%s). Se conserva la probabilidad raw.",
            resolved_selection,
            exc,
        )
        return raw_prob


def calibration_is_active() -> bool:
    """True si hay una curva entrenada gobernando las probabilidades."""
    try:
        return get_calibrator().is_trained
    except Exception:
        return False

def get_market_confidence_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals", "double_chance"}:
        return "segmented"
    if family == "corners":
        return "hybrid"
    return "global"

def get_market_variance_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals"}:
        return "low"
    return "high"

def get_data_quality_score(selection: str, h: FootballTeamStats, a: FootballTeamStats) -> float:
    """
    Score objetivo de calidad de datos (0 a 100 pts) como suma ponderada lineal:
    1. xG / xGA Data (25 pts): 25 pts si ambos disponen de xG/xGA reales > 0; 12.5 si solo uno.
    2. Estadísticas de conteo y presión (35 pts):
       - Shots & Shots on Target: 15 pts
       - Córners: 10 pts
       - Faltas y Tarjetas: 10 pts
    3. Muestra y segmentación Local/Visitante (25 pts):
       - min(matches_home, matches_away) >= 5: 25 pts
       - Entre 2 y 4 partidos: 15 pts
       - < 2 partidos: 5 pts
    4. Métricas secundarias / contexto (15 pts):
       - Posesión, ratings o forma reciente.
    """
    if not h or not a:
        return 0.0

    # 1. xG / xGA Data (25 pts)
    has_xg_h = not getattr(h, "xg_is_imputed", False) and (h.xg_per_game or 0.0) > 0 and (h.xga_per_game or 0.0) > 0
    has_xg_a = not getattr(a, "xg_is_imputed", False) and (a.xg_per_game or 0.0) > 0 and (a.xga_per_game or 0.0) > 0
    if has_xg_h and has_xg_a:
        xg_pts = 25.0
    elif has_xg_h or has_xg_a:
        xg_pts = 12.5
    else:
        xg_pts = 0.0

    # 2. Conteo y presión (35 pts)
    shots_pts = 15.0 if (h.shots_per_game > 0 and a.shots_per_game > 0 and h.shots_on_target_per_game > 0 and a.shots_on_target_per_game > 0) else 0.0
    corners_pts = 10.0 if (h.corners_per_game > 0 and a.corners_per_game > 0) else 0.0
    fouls_cards_pts = 10.0 if (h.fouls_per_game > 0 and a.fouls_per_game > 0 and h.yellow_cards_per_game > 0 and a.yellow_cards_per_game > 0) else 0.0
    count_pts = shots_pts + corners_pts + fouls_cards_pts

    # 3. Muestra y segmentación Local/Visitante (25 pts)
    m_split = min(h.matches_home or 0, a.matches_away or 0)
    if m_split >= 5:
        split_pts = 25.0
    elif m_split >= 2:
        split_pts = 15.0
    else:
        split_pts = 5.0

    # 4. Métricas secundarias / contexto (15 pts)
    has_possession = (h.possession_pct is not None and a.possession_pct is not None)
    has_rating = ((h.avg_rating or 0.0) > 0 and (a.avg_rating or 0.0) > 0)
    has_form = bool(getattr(h, "recent_form", None) or getattr(h, "recent_form_stats", None) or getattr(a, "recent_form", None) or getattr(a, "recent_form_stats", None))
    sec_pts = 0.0
    if has_possession:
        sec_pts += 5.0
    if has_rating:
        sec_pts += 5.0
    if has_form or (h.pass_accuracy > 0 and a.pass_accuracy > 0):
        sec_pts += 5.0
    sec_pts = min(15.0, sec_pts)

    total_dq = xg_pts + count_pts + split_pts + sec_pts
    return round(max(0.0, min(100.0, total_dq)), 1)

def _calculate_display_score(v: ValueIndicator) -> float:
    if v.calibrated_prob is None or v.edge_ev is None:
        return 0.0

    s_prob = v.calibrated_prob * 0.4

    edge_capped = max(0, min(0.15, v.edge_ev))
    s_edge = (edge_capped * 100) * 2.0

    s_data = (v.data_quality_score or 50.0) * 0.1

    sample_w = v.sample_size_weight if v.sample_size_weight is not None else 0.5
    s_stability = 40.0 + (sample_w * 50.0)
    if v.odds:
        if v.odds < 1.60: s_stability = min(100.0, s_stability + 10.0)
        elif v.odds > 2.50: s_stability = max(20.0, s_stability - 20.0)

    final_score = s_prob + s_edge + s_data + (s_stability * 0.2)
    return round(min(100.0, final_score), 1)

def current_eligibility(v: ValueIndicator) -> EligibilityDecision:
    """
    Reconstruye la decisión de elegibilidad ya acumulada sobre este pick.

    Une dos fuentes para no perder bloqueos durante la migración:
      · el registro explícito `eligibility_hard_blocks`;
      · los flags booleanos legacy (`is_blacklisted`, `is_rule_blocked`,
        `correlation_blocked`), que siguen persistiendo en BD y usa el frontend.

    Así un pick bloqueado por código antiguo que solo movía el flag continúa
    bloqueado al pasar por la decisión nueva.
    """
    return EligibilityDecision(
        hard_blocks=frozenset(
            EligibilityDecision.from_reasons(v.eligibility_hard_blocks).hard_blocks
        )
        | hard_blocks_from_flags(
            is_blacklisted=bool(v.is_blacklisted),
            is_rule_blocked=bool(v.is_rule_blocked),
            correlation_blocked=bool(v.correlation_blocked),
        )
    )


def evaluate_pick_eligibility(
    v: ValueIndicator,
    new_hard_blocks: "Iterable[BlockReason | str]" = (),
) -> EligibilityDecision:
    """
    Evalúa la elegibilidad y ESCRIBE el resultado en el pick.

    Es el único punto que decide publicabilidad. Mantiene sincronizados los
    flags legacy y el registro inmutable, y conserva el centinela
    `quality_score = -1` de los picks con bloqueo duro.

    Invariante: llamar a esta función repetidamente nunca puede hacer
    publicable un pick que ya estaba bloqueado.
    """
    decision = evaluate_eligibility(
        PickSnapshot.from_pick(v, market_family=_market_family(v.selection)),
        previous=current_eligibility(v),
        hard_blocks=new_hard_blocks,
        thresholds=DEFAULT_THRESHOLDS,
    )

    v.eligibility_hard_blocks = sorted(r.value for r in decision.hard_blocks)
    v.eligibility_soft_failures = sorted(r.value for r in decision.soft_failures)
    v.eligibility_reasons = list(decision.reasons)
    v.eligibility_policy_version = decision.policy_version

    # Reflejar los bloqueos duros en los flags legacy (nunca al revés).
    if BlockReason.BLACKLISTED in decision.hard_blocks:
        v.is_blacklisted = True
    if BlockReason.RULE_BLOCKED in decision.hard_blocks:
        v.is_rule_blocked = True
    if BlockReason.CORRELATION_BLOCKED in decision.hard_blocks:
        v.correlation_blocked = True

    v.is_publishable = decision.publishable
    if decision.is_hard_blocked:
        v.is_value = False
        v.quality_score = -1

    return decision


def block_pick(
    v: ValueIndicator,
    *reasons: "BlockReason | str",
    detail: "str | None" = None,
) -> EligibilityDecision:
    """
    Emite uno o más bloqueos duros sobre un pick. Operación irreversible.

    Sustituye al patrón disperso de asignar a mano
    `is_rule_blocked = True; is_publishable = False; quality_score = -1`,
    que se deshacía en cuanto otro tramo recalculaba esos campos.
    """
    if detail:
        v.rule_blocked_reason = detail
    return evaluate_pick_eligibility(v, new_hard_blocks=reasons)


def is_publishable_pick(v: ValueIndicator) -> bool:
    """
    True si el pick es publicable AHORA, respetando todo bloqueo previo.

    Antes esta función solo comprobaba `is_blacklisted`, así que recalcularla
    tras un bloqueo por regla o correlación devolvía True y resucitaba el pick.
    Ahora delega en la decisión única, que arrastra los bloqueos duros.
    """
    return evaluate_pick_eligibility(v).publishable


def score_pick_quality(v: Any) -> int:
    """
    Score de Calidad Multidimensional (0 a 100) para clasificar y filtrar picks.

    Evalúa 5 pilares fundamentales:
      1. Edge EV real (hasta 30 pts): Valor matemático medible sobre el mercado.
      2. Calidad de Datos del evento (hasta 25 pts): Cobertura estadística y muestra.
      3. Confiabilidad de Liga / LRS (hasta 20 pts): Estabilidad y muestra real de la liga.
      4. Respaldo Empírico / H2H (hasta 15 pts): Coherencia entre modelo y realidad histórica.
      5. Consistencia de Probabilidad (hasta 10 pts): Solidez de la probabilidad estimada.
    """
    if isinstance(v, dict):
        ev = _safe_num(v.get("edge_ev"), 0.0)
        cal_p = _safe_num(v.get("calibrated_prob") or v.get("model_prob"), 0.0)
        dq = _safe_num(v.get("data_quality_score"), 50.0)
        lrs = _safe_num(v.get("league_reliability_score"), 0.50)
        emp_hr = _safe_num(v.get("empirical_hit_rate"), None)
        emp_samples = int(_safe_num(v.get("hit_rate_samples"), 0) or 0)
        h2h_hr = _safe_num(v.get("h2h_hit_rate") or v.get("h2h_raw_hit_rate"), None)
        h2h_samples = int(_safe_num(v.get("h2h_samples"), 0) or 0)
    else:
        ev = _safe_num(getattr(v, "edge_ev", 0.0), 0.0)
        cal_p = _safe_num(getattr(v, "calibrated_prob", None) or getattr(v, "model_prob", 0.0), 0.0)
        dq = _safe_num(getattr(v, "data_quality_score", None), 50.0)
        lrs = _safe_num(getattr(v, "league_reliability_score", None), 0.50)
        emp_hr = _safe_num(getattr(v, "empirical_hit_rate", None), None)
        emp_samples = int(_safe_num(getattr(v, "hit_rate_samples", None), 0) or 0)
        h2h_hr = _safe_num(getattr(v, "h2h_hit_rate", None) or getattr(v, "h2h_raw_hit_rate", None), None)
        h2h_samples = int(_safe_num(getattr(v, "h2h_samples", None), 0) or 0)

    if ev <= 0.005:
        return 0

    # 1. Edge EV (hasta 30 pts)
    ev_score = min(ev * 200.0, 30.0)

    # 2. Calidad de Datos (hasta 25 pts)
    dq_score = min(max(dq, 0.0) * 0.25, 25.0)

    # 3. Confiabilidad de Liga / LRS (hasta 20 pts)
    lrs_score = min(max(lrs, 0.0) * 20.0, 20.0)

    # 4. Respaldo Empírico y H2H (hasta 15 pts)
    emp_score = 7.5  # base neutral si no hay muestra
    if emp_hr is not None and emp_samples >= 3:
        # Relación entre tasa de acierto real y probabilidad proyectada
        gap = cal_p - emp_hr
        if gap <= 0:
            emp_score = 15.0  # El equipo acierta incluso más que el modelo
        elif gap <= 10.0:
            emp_score = 12.0
        elif gap <= 20.0:
            emp_score = 8.0
        elif gap <= 30.0:
            emp_score = 4.0
        else:
            emp_score = 0.0  # Enorme discrepancia (modelo 65% vs real 25%)

    # Ajuste por H2H si hay partidos directos previos (#46: n >= 8 para significancia)
    if h2h_hr is not None and h2h_samples >= 8:
        if h2h_hr == 0.0:
            emp_score = max(0.0, emp_score - 5.0)
        elif h2h_hr >= 50.0:
            emp_score = min(15.0, emp_score + 2.0)

    # 5. Probabilidad / Estabilidad (hasta 10 pts)
    prob_score = min(max(cal_p, 0.0) / 10.0, 10.0)

    total = int(round(ev_score + dq_score + lrs_score + emp_score + prob_score))
    return min(max(total, 0), 100)


def is_value_pick(v: Any) -> bool:
    is_blk = v.get("is_blacklisted", False) if isinstance(v, dict) else getattr(v, "is_blacklisted", False)
    is_blk_rule = v.get("is_rule_blocked", False) if isinstance(v, dict) else getattr(v, "is_rule_blocked", False)
    if is_blk or is_blk_rule:
        return False
    # Filtro Crítico H2H: Solo se bloquea si hay >= 8 partidos H2H evaluados Y el hit rate fue 0.0%.
    # Con menos de 8 muestras el dato es ruido, no evidencia (#46).
    h2h_samp = (v.get("h2h_samples", 0) or 0) if isinstance(v, dict) else (getattr(v, "h2h_samples", 0) or 0)
    h2h_hr = v.get("h2h_hit_rate") if isinstance(v, dict) else getattr(v, "h2h_hit_rate", None)
    if h2h_hr is None:
        h2h_hr = v.get("h2h_raw_hit_rate") if isinstance(v, dict) else getattr(v, "h2h_raw_hit_rate", None)
    if h2h_samp >= 8 and h2h_hr is not None and h2h_hr == 0.0:
        return False

    odds = v.get("odds") if isinstance(v, dict) else getattr(v, "odds", None)
    if odds is None or odds < 1.30 or odds > 3.50:
        return False
    ev = v.get("edge_ev") if isinstance(v, dict) else getattr(v, "edge_ev", None)
    ev_val = ev if ev is not None else 0.0
    stake = v.get("stake_units") if isinstance(v, dict) else getattr(v, "stake_units", None)
    stake_val = stake if stake is not None else 0.0

    # Requisito de Edge Prob diferenciado por mercado (planning.txt punto 2):
    # Doble Oportunidad y Corners exigen edge prob >= 10.0 (10%).
    sel = v.get("selection", "") if isinstance(v, dict) else getattr(v, "selection", "")
    fam = _market_family(sel)
    edge_val = (v.get("edge") if isinstance(v, dict) else getattr(v, "edge", 0.0)) or 0.0
    if fam in {"double_chance", "corners"} and edge_val < 10.0:
        return False

    # Umbral EV 0.020 para estabilidad entre recálculos.
    # stake > 0 (no 1.0) porque #52 permite stakes fraccionados (0.25u mínimo).
    return ev_val >= 0.020 and stake_val > 0.0


def is_underdog_pick(v: Any) -> bool:
    if isinstance(v, dict):
        odds = v.get("odds")
        edge = v.get("edge", 0)
        edge_ev = v.get("edge_ev")
        dq = v.get("data_quality_score")
        stake = v.get("stake_units")
        h2h_hr = v.get("h2h_hit_rate")
        if h2h_hr is None:
            h2h_hr = v.get("h2h_raw_hit_rate")
        h2h_samp = v.get("h2h_samples", 0) or 0
    else:
        odds = getattr(v, "odds", None)
        edge = getattr(v, "edge", 0)
        edge_ev = getattr(v, "edge_ev", None)
        dq = getattr(v, "data_quality_score", None)
        stake = getattr(v, "stake_units", None)
        h2h_hr = getattr(v, "h2h_hit_rate", None)
        if h2h_hr is None:
            h2h_hr = getattr(v, "h2h_raw_hit_rate", None)
        h2h_samp = getattr(v, "h2h_samples", 0) or 0

    # Filtro Crítico H2H: Solo se bloquea si hay >= 8 partidos H2H evaluados Y el hit rate fue 0.0%.
    # Con menos de 8 muestras el dato es ruido, no evidencia (#46).
    if h2h_samp >= 8 and h2h_hr is not None and h2h_hr == 0.0:
        return False

    # Filtro de Calidad por Hit Rate Empírico de Temporada (Underdog):
    # Incluso para un underdog, si hay muestra representativa (>= 5 partidos) y su hit rate empírico es < 20%,
    # no tiene sustento real para ser un pick de calidad.
    emp_hr = v.get("empirical_hit_rate") if isinstance(v, dict) else getattr(v, "empirical_hit_rate", None)
    emp_samp = (v.get("hit_rate_samples", 0) or 0) if isinstance(v, dict) else (getattr(v, "hit_rate_samples", 0) or 0)
    if emp_hr is not None and emp_samp >= 5 and emp_hr < 20.0:
        return False

    # Rango de cuotas: (2.80, 8.00]
    if odds is None or odds <= 2.80 or odds > 5.00:
        return False

    # Expected Value (EV): edge_ev >= 0.050 (5%) o edge >= 5.0%
    ev_val = edge_ev if edge_ev is not None else 0.0
    edge_val = edge if edge is not None else 0.0
    if ev_val < 0.050 and edge_val < 5.0:
        return False

    if dq is not None and dq < 50.0:
        return False

    # Permitir stakes fraccionados (>= 0.25)
    if stake is not None and stake < 0.25:
        return False

    return True

def _calculate_stake_units(
    edge_ev: float,
    odds: float,
    kelly_fraction: float,
    market_family: str,
    lrs: float | None,
) -> float:
    """
    Stake cuantitativo basado en Fractional Kelly (máximo 3% del capital = 3.0u).
    Retorna unidades escaladas continuamente entre [0.25, 3.00] unidades si edge_ev >= 0.020.
    Si edge_ev < 0.020, retorna 0.0.
    """
    if edge_ev < 0.020 or kelly_fraction <= 0 or odds <= 1.0:
        return 0.0

    # kelly_fraction ya viene de la distribución completa de retornos (push/cuartos correctos)
    # y ya incorpora la fiabilidad de liga vía kelly_multiplier: no se recalcula ni se re-escala por LRS.
    vol_factor = 0.5 if market_family in {"corners", "cards", "shots", "shots_target", "fouls"} else 1.0
    stake = min(3.0, kelly_fraction * vol_factor * 100.0)  # 1u = 1% del bankroll; tope 3%
    stake = round(stake * 4) / 4
    return stake if stake >= 0.25 else 0.0

def _calculate_kelly_fraction(
    calibrated_prob: float,
    odds: float | None,
    kelly_multiplier: float = 0.25,
    hard_cap: float = 0.25,
    push_prob: float = 0.0,
    distribution: "ReturnDistribution | None" = None,
) -> float:
    """
    Kelly fraccional calculado sobre la DISTRIBUCIÓN COMPLETA de retornos.

    Antes se usaba la fórmula Bernoulli (b·p - q)/b con q = 1 - p, lo que
    contaba los pushes como pérdidas y por tanto subestimaba el stake óptimo.
    Un push devuelve la apuesta: aporta retorno 0, no -1.

    Args:
        calibrated_prob: probabilidad de GANAR (0-1 o 0-100, se autodetecta).
        odds: cuota decimal (>1.0).
        kelly_multiplier: fracción de Kelly completo (0.25 = 1/4 Kelly).
        hard_cap: techo absoluto sobre la fracción de bankroll.
        push_prob: probabilidad de push (0-1 o 0-100). El push no consume banca.
        distribution: si se pasa, se usa tal cual e ignora los tres primeros
            argumentos. Es la vía correcta para líneas de cuarto, donde hay
            masa real en half_win / half_loss.

    Returns:
        Fracción del bankroll a apostar (0.0 si no hay valor o inputs inválidos).
    """
    if distribution is not None:
        try:
            return distribution.kelly_fraction(
                multiplier=kelly_multiplier, hard_cap=hard_cap
            )
        except (ValueError, ZeroDivisionError):
            return 0.0

    if odds is None or odds <= 1.0 or calibrated_prob is None:
        return 0.0

    try:
        dist = ReturnDistribution.simple(
            odds=odds, p_win=calibrated_prob, p_push=push_prob or 0.0
        )
        return dist.kelly_fraction(multiplier=kelly_multiplier, hard_cap=hard_cap)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _value_indicator(
    sel, odds, modelp, h=None, a=None, overround=100.0, push_p=0.0,
    league: "LeagueStats | None" = None, league_name: str | None = None,
    odds_obj: Any = None, match_date: datetime | str | None = None,
    market_novig_pct: float | None = None,
):
    """
    Construye un ValueIndicator con la nueva arquitectura completa:
      1. Calibración jerárquica de 9 niveles
      2. Edge desglosado (raw -> calibrado -> final)
      3. Gobernanza de segmento (segment_governance.json) con bloqueo duro si BLOCKED
      4. Stake Engine (Kelly × LRS × governance_multiplier × data_quality)
      5. Trazabilidad completa (PickTrace con todos los campos Fase 13)
    """
    if odds is None or odds <= 1.0:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1), push_prob=round(push_p, 1))

    # ── 1. Taxonomía Canónica de Mercado ────────────────────────────────
    # family_legacy: usado para calibración, odds, EV (compatibilidad con código existente)
    family = _market_family(sel)
    # mk: taxonomía canónica — determina el segment_key para gobernanza y trazabilidad
    mk = parse_market(sel, sel)           # MarketKey canónica (family, side, line, line_bucket)
    mkt_family = str(mk.family)           # familia canónica (goals, corners, cards, etc.)
    mkt_side   = mk.side
    mkt_bucket = mk.line_bucket or "no_line"
    mkt_line   = mk.line

    resolved_league_name = league_name or (getattr(league, "name", None) if league else None)
    # El segment_key usa la familia CANÓNICA para coincidir con segment_governance.json
    seg_key = market_group_key(resolved_league_name, mkt_family, mkt_side, mkt_bucket)

    pred_ts = match_date if match_date is not None else datetime.now(timezone.utc).isoformat()
    pred_ts_str = pred_ts.isoformat() if isinstance(pred_ts, datetime) else str(pred_ts)

    # ── 2. Calibración Jerárquica ────────────────────────────────────────
    calibrated_p = apply_calibration(
        raw_prob=modelp,
        odds=odds,
        market_family=family,
        selection=sel,
        league=league,
        league_name=league_name,
        predicted_at_utc=pred_ts,
    )

    raw_implied = (1.0 / odds) * 100.0
    if market_novig_pct is not None and market_novig_pct > 0.0:
        implied_no_vig = market_novig_pct
    else:
        margin_factor = (overround / 100.0) if overround > 100 else 1.05
        implied_no_vig = raw_implied / margin_factor

    # ── 3. Edge desglosado (raw → calibrado → final) ────────────────────
    # edge_raw: usando prob. Poisson cruda (sin calibrar)
    # edge_calibrated: usando prob. calibrada (curva jerárquica)
    # edge_final: usando prob. final (blend con mercado; aquí = calibrada hasta blend)
    _p_model_raw_01 = modelp / 100.0 if modelp > 1.0 else modelp
    _p_calibrated_01 = calibrated_p / 100.0 if calibrated_p > 1.0 else calibrated_p

    # Siempre recalcular con la fórmula actualizada; el valor de BD puede estar obsoleto
    lrs = _compute_league_reliability_score(league) if league is not None else 0.7

    # Blend modelo/mercado ponderado por fiabilidad de liga: peso del modelo 0.65-0.90
    # (antes fijo 0.80) + guarda de divergencia (aviso 0.15 / bloqueo 0.25 vía _blend_stake_mult).
    _p_market_01 = (implied_no_vig / 100.0) if implied_no_vig > 0.0 else None
    _blend = blend_model_and_market_probability(
        p_calibrated=_p_calibrated_01,
        p_market_no_vig=_p_market_01,
        reliability_score=0.65 + 0.25 * min(max(lrs, 0.0), 1.0),
    )
    _p_final_01 = _blend.final_prob
    _blend_stake_mult = _blend.stake_multiplier

    try:
        edge_result = compute_edge(
            p_final=_p_final_01,
            odds=odds,
            p_model_raw=_p_model_raw_01,
            p_calibrated=_p_calibrated_01,
        )
        _edge_raw        = edge_result.edge_raw
        _edge_calibrated = edge_result.edge_calibrated
        _edge_final      = edge_result.edge_final
    except Exception:
        _edge_raw = _edge_calibrated = _edge_final = 0.0

    # Prob final en % para el resto del pipeline
    final_prob_pct = _p_final_01 * 100.0

    # ── 4. EV y Edge de display (#42: Una sola probabilidad coherente: final_prob) ──
    ret_dist = ReturnDistribution.simple(
        odds=odds, p_win=final_prob_pct, p_push=push_p or 0.0
    )
    ev = ret_dist.expected_value
    edge_prob = (ret_dist.p_win_effective * 100.0) - raw_implied

    # ── 5. League Reliability Score (calculado antes del blend) ──
    lrs_penalty = 0.0
    p = calibrated_p / 100.0

    # ── 6. Gobernanza de Segmento ────────────────────────────────────────
    gov_status, gov_multiplier, gov_drift, gov_min_edge_add = _get_governance_multiplier(
        segment_key=seg_key,
        league=resolved_league_name,
        family=mkt_family,   # usa familia canónica para lookup en segment_governance.json
        side=mkt_side,
        bucket=mkt_bucket,
    )

    # ── 7. Rating ────────────────────────────────────────────────────────
    conf_tier = get_market_confidence_tier(sel)
    var_tier = get_market_variance_tier(sel)
    dq_score = get_data_quality_score(sel, h, a) if h and a else None

    if   ev > 0.15:  rating = "🔥 STRONG VALUE"
    elif ev > 0.07:  rating = "✅ VALUE"
    elif ev > 0.02:  rating = "⚖️ MARGINAL"
    else:            rating = "❌ NO VALUE"

    # ── 8. Stake Engine ──────────────────────────────────────────────────
    market_lrs_factor = 1.0
    if league is not None and league.market_hit_rates:
        market_rate = league.market_hit_rates.get(family)
        if market_rate is not None and league.historical_picks >= 5:
            MARKET_REF = {
                "corners": 0.52, "cards": 0.52, "shots": 0.52, "shots_target": 0.52, "fouls": 0.52,
                "goals": 0.55,   "btts": 0.54,  "result": 0.55,
                "double_chance": 0.57, "generic": 0.53,
            }
            ref_rate = MARKET_REF.get(family, 0.53)
            market_dev = market_rate - ref_rate
            market_lrs_factor = 1.0 + max(-0.35, min(0.15, market_dev * 1.5))

    if lrs >= 0.65:
        kelly_multiplier = 0.25   # liga consolidada: Kelly completo fraccionado
    elif lrs >= 0.50:
        kelly_multiplier = 0.25   # liga suficiente: mismo multiplier, techo en _calculate_stake_units
    elif lrs >= 0.35:
        kelly_multiplier = 0.20   # liga con poca muestra: Kelly ligeramente reducido
    else:
        kelly_multiplier = 0.15   # liga muy poco probada: Kelly conservador
    kelly_multiplier *= market_lrs_factor

    # #53: Mínimo de muestra (picks >= 20) para juzgar el rendimiento de la liga en Kelly.
    # Evitar castigar prematuramente con solo 5 picks de muestra ruidosa.
    if league is not None and getattr(league, "historical_picks", 0) >= 20:
        hist_profit = getattr(league, "historical_profit", 0.0)
        hist_accuracy = getattr(league, "accuracy", 100.0)
        # 40% es buen acierto para cuotas 2.50+; solo penalizar si hay pérdida neta y acierto bajo
        if hist_profit < 0.0 and hist_accuracy < 42.0:
            kelly_multiplier = min(kelly_multiplier, 0.12)

    kelly_fraction = _calculate_kelly_fraction(
        calibrated_prob=calibrated_p,
        odds=odds,
        kelly_multiplier=kelly_multiplier,
        distribution=ret_dist,
    )

    stake = _calculate_stake_units(
        edge_ev=ev,
        odds=odds or 1.0,
        kelly_fraction=kelly_fraction,
        market_family=family,
        lrs=lrs,
    )

    if _blend_stake_mult < 1.0:
        stake = round(round(stake * _blend_stake_mult * 4) / 4, 2)
        stake = stake if stake >= 0.25 else 0.0

    # Aplicar governance_multiplier al stake (REDUCED→×0.25, BLOCKED→0, WATCH→×0.50)
    if gov_multiplier < 1.0:
        stake = round(stake * gov_multiplier, 2)
        # Redondear a múltiplo de 0.25 respetando mínimo
        stake = round(stake * 4) / 4

    if league_name:
        stake_mod = get_market_stake_modifier_for_league(league_name, sel)
        if stake_mod != 1.0:
            stake = round(stake * stake_mod, 2)

    target_cal = get_calibrator_for_timestamp(pred_ts) if pred_ts is not None else get_calibrator()
    cal_ver = target_cal.version if target_cal.is_trained else "unverified"

    # ── 9. Componentes de fiabilidad (para trazabilidad) ─────────────────
    dq_factor = (dq_score / 100.0) if dq_score is not None else 0.7
    reliability_score = round(lrs * dq_factor, 4)
    reliability_comps = {
        "lrs": round(lrs, 4),
        "data_quality_factor": round(dq_factor, 4),
        "governance_multiplier": round(gov_multiplier, 4),
        "drift_score": round(gov_drift, 4),
    }

    # ── 10. Construir ValueIndicator ─────────────────────────────────────
    v = ValueIndicator(
        selection=sel,
        odds=odds,
        model_prob=round(modelp, 1),
        model_prob_raw=float(modelp),
        calibrated_prob=round(calibrated_p, 1),
        calibration_version=cal_ver,
        predicted_at_utc=pred_ts_str,
        implied_prob=round(raw_implied, 1),
        implied_prob_no_vig=round(implied_no_vig, 1),
        fair_odds=round(ret_dist.fair_odds, 2) if ret_dist.fair_odds else None,
        edge=round(edge_prob, 1),
        edge_ev=round(ev, 3),
        push_prob=round(push_p, 1),
        is_value=ev >= 0.020 and stake > 0 and odds <= 3.50,
        rating=rating,
        data_quality_score=dq_score,
        market_confidence_tier=conf_tier,
        market_variance_tier=var_tier,
        kelly_fraction=round(kelly_fraction, 4),
        stake_units=stake if stake > 0.0 else None,
        sample_size_weight=min(1.0, (h.matches_played + a.matches_played) / 30.0) if h and a else 0.5,
        league_reliability_score=round(lrs, 3),
        league_reliability_penalty=lrs_penalty,
        # ── Nuevos campos de trazabilidad (Fase 13) ──
        market_family=mkt_family,   # familia canónica (goals/corners/cards/...) para trazabilidad
        market_side=mkt_side,
        line_bucket=mkt_bucket,
        segment_key=seg_key,
        final_prob=round(final_prob_pct, 2),
        p_market_no_vig=round(implied_no_vig, 2),
        edge_raw=round(_edge_raw, 2),
        edge_calibrated=round(_edge_calibrated, 2),
        edge_final=round(_edge_final, 2),
        segment_status=gov_status,
        drift_score=round(gov_drift, 4),
        governance_multiplier=round(gov_multiplier, 4),
        min_edge_add=round(gov_min_edge_add, 2) if gov_min_edge_add else 0.0,
        reliability_components=reliability_comps,
    )

    if odds_obj:
        bm = odds_obj.get("bookmaker") if isinstance(odds_obj, dict) else getattr(odds_obj, "bookmaker", None)
        if bm:
            v.bookmaker = str(bm)

    # ── Blacklist de liga: bloqueo duro ──────────────────────────────────
    if league_name and is_market_blacklisted_for_league(league_name, sel):
        block_pick(v, BlockReason.BLACKLISTED)
        v.strategic_score = -1
    else:
        v.quality_score = score_pick_quality(v)
        evaluate_pick_eligibility(v)
        v.is_value = is_value_pick(v) and v.is_publishable
        v.display_score = _calculate_display_score(v)
        v.is_underdog = is_underdog_pick(v)

    # ── Gobernanza de segmento: bloqueo duro si BLOCKED ──────────────────
    # Se aplica DESPUÉS de eligibility para que el bloqueo persista (irreversible).
    if gov_status == "blocked" and not v.is_blacklisted:
        block_pick(v, BlockReason.SEGMENT_GOVERNANCE_BLOCKED,
                   detail=f"Segmento '{seg_key}' bloqueado por gobernanza (drift={gov_drift:.3f}).")
        logger.debug("Gobernanza: pick '%s' bloqueado por segmento '%s'.", sel, seg_key)

    # ── Reglas estadísticas: bloqueo duro ────────────────────────────────
    if not v.is_blacklisted and h is not None and a is not None:
        if is_pick_blocked_by_rules(sel, h, a, odds_obj):
            block_pick(v, BlockReason.RULE_BLOCKED)

    return v



# ───────────────────────────────────────────────────────────────
# Poisson engine (Football)
# ───────────────────────────────────────────────────────────────























# ───────────────────────────────────────────────────────────────
# Dixon-Coles helpers
# ───────────────────────────────────────────────────────────────



























# ── Faltas y Offsides MEJORADOS ─────────────────────────────

















# ───────────────────────────────────────────────────────────────
# Support functions MEJORADAS con stats avanzadas
# ───────────────────────────────────────────────────────────────

def _safe_num(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())

def _calibration_line_bucket(selection: str) -> str | None:
    """
    Extrae y normaliza una línea numérica presente en el texto del pick.
    """
    value = _extract_line_number(selection)

    if value is None:
        return None

    return f"{value:.2f}".rstrip("0").rstrip(".")

def _extract_line_number(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)", text.replace(",", "."))
    return float(match.group(1)) if match else None


def _implied_prob_from_odds(odds: float | None) -> float | None:
    if odds is None or odds <= 1.0:
        return None
    return round((1 / odds) * 100, 2)


def _clip_0_100(x: float) -> float:
    return max(0.0, min(100.0, x))

def _calibration_side(selection: str, market_family: str) -> str:
    """
    Normaliza la polaridad del pick para resolver correctamente la curva
    jerárquica de calibración.
    """
    text = _normalize_text(selection)
    family = _normalize_text(market_family)

    if family == "double_chance":
        if "1x" in text:
            return "1x"
        if "x2" in text:
            return "x2"
        if re.search(r"(?<!\\d)12(?!\\d)", text):
            return "12"
        return "generic"

    if family in {"goals", "corners", "cards", "shots", "shots_target", "fouls"}:
        if "under" in text or "menos" in text:
            return "under"
        if "over" in text or "más" in text or "mas" in text:
            return "over"
        return "generic"

    if family == "result":
        if "local" in text or "home" in text:
            return "home"
        if "visitante" in text or "away" in text:
            return "away"
        if "empate" in text or "draw" in text:
            return "draw"
        return "generic"

    if family == "btts":
        if "sí" in text or "si" in text or "yes" in text:
            return "yes"
        if "no" in text:
            return "no"
        return "generic"

    return "generic"

def _market_family(text: str) -> str:
    """Clasificación canónica de familia de mercado.

    Issue #71: única fuente de clasificación de familia — siempre delega a
    `normalize_market_family` de `market_taxonomy.py`. No duplicar lógica aquí.
    """
    return str(normalize_market_family(text))



def _market_side(text: str) -> str:
    s = _normalize_text(text)
    
    patterns = [
        (r'\b(over|más\s+de|mas\s+de)\b', "over"),
        (r'\b(under|menos\s+de)\b', "under"),
        (r'\b(yes|sí|si)\b', "yes"),
        (r'\bno\b', "no"),
        (r'\b(local|home)\b', "home"),
        (r'\b(visitante|away)\b', "away"),
        (r'\b(empate|draw)\b', "draw"),
        # Doble oportunidad
        (r'\b(1x|home_draw)\b', "home_draw"),
        (r'\b(x2|draw_away)\b', "draw_away"),
        (r'\b(12|home_away)\b', "home_away"),
    ]
    
    for pattern, side in patterns:
        if re.search(pattern, s):
            return side
    
    return "none"


# No esta extrauendo correcta la linea, por ejemplo en MLS, over 0.5, 1.0, 1.5, etc
def _market_line(text: str) -> float | None:
    import re

    s = _normalize_text(text or "")

    pattern = (
        r"(?:\bover\b|\bunder\b|más de|mas de|menos de)"
        r"[^\d]*?([+-]?\d+(?:[.,]\d+)?)"
    )

    match = re.search(pattern, s)

    if not match:
        return None

    return float(match.group(1).replace(",", "."))


def is_pick_blocked_by_rules(selection: str, home: "FootballTeamStats", away: "FootballTeamStats", odds_obj: Any = None) -> bool:
    """
    Checks pick_rules.json using the unified pick_rules_engine.
    If a rule is enabled for this pick's market family/side and any of its
    conditions is NOT met, returns True (the pick should be blocked).
    If all conditions pass, or no matching enabled rule exists, returns False.
    """
    try:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json")
        rules_list, _ = load_pick_rules_data(rules_path)
        if not rules_list:
            return False

        stat_source = StatSource.from_team_stats(home, away, odds_obj)
        blocked, _ = evaluate_pick_rules(selection, stat_source, rules_list)
        return blocked
    except Exception as e:
        import logging
        logging.getLogger("sherlock.pick_rules").error(f"Error evaluating pick rules in compare: {e}")
        return False


def resolve_match_picks_correlation(
    candidates: list[ValueIndicator],
    correlation_rules: Optional[dict] = None
) -> list[ValueIndicator]:
    """
    Filtra picks correlacionados en un mismo evento garantizando
    la máxima expectativa matemática sin sobreexposición de varianza.
    Utiliza el motor de reglas centralizado pick_rules_engine.
    Nota: max_picks_per_match y max_total_stake fueron removidos por completo (#72).
    """
    if correlation_rules is None:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json")
        _, correlation_rules = load_pick_rules_data(rules_path)

    return engine_resolve_match_picks_correlation(
        candidates,
        correlation_rules=correlation_rules
    )

def is_market_blacklisted_for_league(
    league_name: str,
    selection: str,
    category: str | None = None,
    *,
    line: float | str | None = None,
) -> bool:
    """
    Comprueba reglas de blacklist por:
    liga, familia, lado, línea y categoría.

    La línea explícita tiene prioridad sobre la extraída de selection.

    Las reglas sin línea, con línea null o vacía se consideran generales.
    Una regla con línea específica solo coincide con esa línea.
    """
    import json
    import logging
    from decimal import Decimal, InvalidOperation

    def normalize_line(value):
        if value is None or isinstance(value, bool):
            return None

        text = str(value).strip().replace(",", ".")

        if not text:
            return None

        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            return None

        if not number.is_finite():
            return None

        if number == 0:
            return "0"

        result = format(number, "f")

        if "." in result:
            result = result.rstrip("0").rstrip(".")

        return result

    def normalize_category(value):
        if value is None:
            return None

        text = str(value).strip().lower()

        if not text:
            return None

        if text in {"profesional", "publishable"}:
            return "profesional"

        return text

    try:
        data_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "league_penalties.json",
        )

        if not os.path.exists(data_path):
            return False

        with open(data_path, "r", encoding="utf-8") as file:
            content = file.read().strip()

        if not content:
            return False

        penalties = json.loads(content)

        if not isinstance(penalties, list):
            return False

        family = str(
            _market_family(selection) or ""
        ).strip().lower().replace(" ", "_")

        side = str(
            _market_side(selection) or ""
        ).strip().lower().replace(" ", "_")

        pick_line = normalize_line(line)

        if pick_line is None:
            pick_line = normalize_line(_market_line(selection))

        requested_league = str(league_name or "").strip()
        requested_category = normalize_category(category)

        for rule in penalties:
            if not isinstance(rule, dict):
                continue

            rule_league = str(rule.get("league") or "").strip()

            if not rule_league:
                continue

            match_league = (
                rule_league.lower() == requested_league.lower()
                or _normalize_text(rule_league)
                == _normalize_text(requested_league)
            )

            if not match_league:
                continue

            rule_family = str(
                rule.get("market_family") or ""
            ).strip().lower().replace(" ", "_")

            rule_side = str(
                rule.get("market_side") or ""
            ).strip().lower().replace(" ", "_")

            if rule_family and rule_family != family:
                continue

            if rule_side and rule_side != side:
                continue

            raw_rule_line = rule.get("line")

            has_specific_line = (
                raw_rule_line is not None
                and str(raw_rule_line).strip() != ""
            )

            if has_specific_line:
                normalized_rule_line = normalize_line(raw_rule_line)

                # Una línea inválida no debe convertirse
                # accidentalmente en una regla general.
                if normalized_rule_line is None:
                    continue

                if (
                    pick_line is None
                    or normalized_rule_line != pick_line
                ):
                    continue

            rule_category = normalize_category(rule.get("category"))

            if (
                rule_category is not None
                and rule_category != requested_category
            ):
                continue

            # Mantiene el comportamiento anterior:
            # solo blacklist=false explícito desactiva el bloqueo.
            if rule.get("blacklist") is not False:
                return True

        return False

    except Exception:
        logging.getLogger(__name__).exception(
            "Error comprobando blacklist para liga=%r, selection=%r",
            league_name,
            selection,
        )
        return False


def get_market_stake_modifier_for_league(league_name: str, selection: str, category: str | None = None) -> float:
    """
    Obtiene el multiplicador de stake para un mercado en una liga según data/league_penalties.json.
    Si se encuentra una regla con 'stake_modifier', retorna ese valor (ej: 0.5 para reducir a la mitad).
    Si no hay regla o stake_modifier, retorna 1.0 (stake normal).
    """
    try:
        data_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "league_penalties.json")
        if not os.path.exists(data_path):
            return 1.0
        import json
        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return 1.0
            penalties = json.loads(content)

        if not isinstance(penalties, list):
            return 1.0

        family = _market_family(selection)
        side = _market_side(selection)

        for rule in penalties:
            rule_league = (rule.get("league") or "").strip()
            if rule_league and (rule_league.lower() == (league_name or "").strip().lower() or _normalize_text(rule_league) == _normalize_text(league_name)):
                rule_family = rule.get("market_family", "").strip().lower().replace(" ", "_")
                rule_side = rule.get("market_side", "").strip().lower().replace(" ", "_")

                match_family = not rule_family or rule_family == family.lower()
                match_side = not rule_side or rule_side == side.lower()

                if match_family and match_side:
                    rule_cat = rule.get("category")
                    
                    def normalize_cat(c: str | None) -> str | None:
                        if not c:
                            return None
                        c_lower = c.strip().lower()
                        if c_lower in {"profesional", "publishable"}:
                            return "profesional"
                        return c_lower

                    norm_rule_cat = normalize_cat(rule_cat)
                    norm_requested_cat = normalize_cat(category)

                    match_category = True
                    if norm_rule_cat is not None:
                        match_category = (norm_rule_cat == norm_requested_cat)

                    if match_category:
                        if "stake_modifier" in rule:
                            try:
                                return float(rule["stake_modifier"])
                            except (TypeError, ValueError):
                                return 1.0

        return 1.0
    except Exception:
        return 1.0


def _market_risk_weight(selection: str) -> int:
    family = _market_family(selection)

    if family in {"result"}:
        return -14
    if family == "double_chance":
        return -7
    if family == "btts":
        return -10
    if family in {"corners", "cards", "shots", "shots_target", "fouls"}:
        return -4
    if family == "goals":
        return -3

    return -8


def _odds_risk_penalty(odds: float | None) -> int:
    if odds is None:
        return -8
    if odds >= 3.20:
        return -18
    if odds >= 2.80:
        return -13
    if odds >= 2.35:
        return -8
    if odds >= 2.00:
        return -4
    return 0


def _probability_band_score(prob: float) -> int:
    if prob >= 82:
        return 50
    if prob >= 78:
        return 42
    if prob >= 74:
        return 34
    if prob >= 70:
        return 26
    if prob >= 66:
        return 18
    if prob >= 62:
        return 8
    return -20



def _projected_value_by_keywords(proj: list, keywords: list[str]) -> tuple[float | None, float | None, str | None]:
    best = None
    for p in proj:
        label = _normalize_text(getattr(p, "label", "") or "")
        if all(k in label for k in keywords):
            value = _safe_num(getattr(p, "value", None), None)
            prob = _safe_num(getattr(p, "prob", None), None)
            return value, prob, label

        matches = sum(1 for k in keywords if k in label)
        if matches > 0:
            cand = (
                matches,
                _safe_num(getattr(p, "prob", None), 0),
                _safe_num(getattr(p, "value", None), -999),
                label,
                _safe_num(getattr(p, "value", None), None),
                _safe_num(getattr(p, "prob", None), None),
            )
            if best is None or cand > best:
                best = cand

    if best is None:
        return None, None, None

    return best[4], best[5], best[3]


# ── NUEVO: Score de fuerza mejorado con stats avanzadas ──
def _team_strength_score(team) -> float:
    goals = _safe_num(team.goals_per_game)
    xg = _safe_num(team.xg_per_game)
    xga = _safe_num(team.xga_per_game)
    big = _safe_num(team.big_chances_per_game)
    sot = _safe_num(team.shots_on_target_per_game)
    poss = _safe_num(team.possession_pct)
    conceded = _safe_num(team.goals_conceded_per_game)

    # NUEVO: Factores avanzados
    rating = _safe_num(team.avg_rating)
    fast_break = _safe_num(team.fast_break_goals)
    outside_goals = _safe_num(team.goals_outside_box)
    big_created = _safe_num(team.big_chances_created)
    dribble = _safe_num(team.dribble_success_pct)
    duels_pct = _safe_num(team.duels_won_pct)
    if 0.0 < duels_pct <= 1.0:
        duels_pct *= 100.0

    aerial_pct = _safe_num(team.aerial_duels_won_pct)
    if 0.0 < aerial_pct <= 1.0:
        aerial_pct *= 100.0

    errors = _safe_num(team.errors_leading_to_goal)

    base = (
        goals * 10
        + xg * 12
        + big * 8
        + sot * 6
        + poss * 0.12
        - conceded * 8
        - xga * 7
    )

    # Ajustes avanzados
    advanced = (
        (rating - 7.0) * 5.0  # Rating por encima/debajo de 7.0
        + fast_break * 15.0    # Goles en contraataque valen mucho
        + outside_goals * 8.0  # Goles de fuera = impredecibilidad
        + big_created * 6.0    # Creación de chances
        + dribble * 0.15       # Calidad individual
        + (duels_pct - 50.0) * 1.5  # Dominio físico (porcentaje centrado en 50%)
        + (aerial_pct - 50.0) * 1.0  # Dominio aéreo (porcentaje centrado en 50%)
        - errors * 10.0        # Penaliza errores graves
    )

    return base + advanced


# ── Support Over/Under Goals — Determinista ──
def _support_over_goals(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    """
    stat_support con penalización no lineal en colas extremas (Over > 3.5).
    """
    pval, pprob, _ = _projected_value_by_keywords(proj, ["goles", "goals"])

    if pprob is not None:
        model_prob = float(pprob)
    elif pval is not None:
        model_prob = _clip_0_100(55.0 + (pval - line) * 20.0)
    else:
        h_exp = (_safe_num(h.goals_per_game) + _safe_num(h.xg_per_game)) / 2.0
        a_exp = (_safe_num(a.goals_per_game) + _safe_num(a.xg_per_game)) / 2.0
        total_exp = h_exp + a_exp
        model_over, _, _ = _poisson_over_under(total_exp, line)
        model_prob = model_over

    # Amortiguación estricta de colas altas (Over 4.5+ sufre decaimiento de intensidad)
    if line >= 4.5:
        # Penalización por saciedad competitiva
        model_prob *= 0.82
    elif line >= 3.5:
        model_prob *= 0.94

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)
        if empirical is None:
            h_hr = _safe_num(getattr(vi, "home_hit_rate", None), None)
            a_hr = _safe_num(getattr(vi, "away_hit_rate", None), None)
            if h_hr is not None and a_hr is not None:
                empirical = (h_hr + a_hr) / 2.0

    if empirical is not None:
        stat = _clip_0_100(0.55 * model_prob + 0.45 * empirical)
    else:
        stat = _clip_0_100(model_prob)

    proj_score = model_prob if pprob is not None else _clip_0_100(55.0 + (pval - line) * 20.0 if pval else model_prob)
    return stat, _clip_0_100(proj_score)


def _support_under_goals(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    """
    Soporte Under modelado independientemente con factor de ruido de partido (Varianza Residual).
    No asume simetría estricta con el Over para líneas bajas (Under 2.5).
    """
    stat_over, proj_over = _support_over_goals(line, h, a, proj, vi)
    
    raw_under_stat = 100.0 - stat_over
    raw_under_proj = 100.0 - proj_over

    # Descuento por riesgo de varianza tardía en líneas cerradas (Under 1.5, Under 2.5)
    # Un gol en el 85+ rompe Under con mucha más frecuencia que lo proyectado por medias
    variance_discount = 0.0
    if line <= 2.5:
        # Descuento base por entropía del juego (penaltis, rojas, tiempo añadido)
        variance_discount = 5.5
        
        # Si la probabilidad cruda es excesivamente alta (>70%), aplicar contracción (shrinkage)
        if raw_under_stat > 65.0:
            excess = raw_under_stat - 65.0
            variance_discount += excess * 0.35

    adjusted_stat = max(0.0, raw_under_stat - variance_discount)
    adjusted_proj = max(0.0, raw_under_proj - variance_discount)

    return _clip_0_100(adjusted_stat), _clip_0_100(adjusted_proj)


# ── Support BTTS MEJORADO ──
def _support_btts_yes(h, a, proj: list, vi=None) -> tuple[float, float]:
    h_attack = _safe_num(h.goals_per_game) + _safe_num(h.xg_per_game) * 0.4
    a_attack = _safe_num(a.goals_per_game) + _safe_num(a.xg_per_game) * 0.4
    h_defense = _safe_num(h.goals_conceded_per_game) + _safe_num(h.xga_per_game) * 0.4
    a_defense = _safe_num(a.goals_conceded_per_game) + _safe_num(a.xga_per_game) * 0.4

    base = (h_attack * a_defense + a_attack * h_defense) / 2.0
    stat = 50.0 + (base - 1.5) * 14.0

    # Pérdidas de posesión altas en ambos = más transiciones = más probabilidad de BTTS
    h_turnover = _safe_num(h.possession_lost)
    a_turnover = _safe_num(a.possession_lost)
    if h_turnover > 90 and a_turnover > 90:
        stat += 5.0

    # Contraataques de ambos = ambos marcan en transiciones
    h_fb = _safe_num(h.fast_break_goals)
    a_fb = _safe_num(a.fast_break_goals)
    stat += (h_fb + a_fb) * 3.0

    # Errores defensivos de ambos
    h_err = _safe_num(h.errors_leading_to_goal) + _safe_num(h.errors_leading_to_shot) * 0.3
    a_err = _safe_num(a.errors_leading_to_goal) + _safe_num(a.errors_leading_to_shot) * 0.3
    stat += (h_err + a_err) * 2.0

    stat = _clip_0_100(stat)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["btts"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["ambos", "marcan"])

    proj_score = 55.0
    if pprob is not None:
        proj_score = pprob

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)
        if empirical is None:
            h_hr = _safe_num(getattr(vi, "home_hit_rate", None), None)
            a_hr = _safe_num(getattr(vi, "away_hit_rate", None), None)
            if h_hr is not None and a_hr is not None:
                empirical = (h_hr + a_hr) / 2.0

    if empirical is not None:
        stat = _clip_0_100(0.60 * stat + 0.40 * empirical)

    return stat, _clip_0_100(proj_score)


def _support_btts_no(h, a, proj: list, vi=None) -> tuple[float, float]:
    stat_yes, proj_yes = _support_btts_yes(h, a, proj, vi)
    return _clip_0_100(100.0 - stat_yes), _clip_0_100(100.0 - proj_yes)


def _support_home_win(h, a, proj: list, vi=None) -> tuple[float, float]:
    diff = _team_strength_score(h) - _team_strength_score(a)
    stat = _clip_0_100(54 + diff * 0.9)

    pval, pprob, label = _projected_value_by_keywords(proj, ["local"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["home"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["1x2", "local"])

    proj_score = 54.0
    if pprob is not None:
        proj_score += (pprob - 50) * 0.8
    elif label and ("local" in label or "home" in label):
        proj_score += 8

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "home_hit_rate", None), None) or _safe_num(getattr(vi, "empirical_hit_rate", None), None)

    if empirical is not None:
        stat = _clip_0_100(0.60 * stat + 0.40 * empirical)

    return stat, _clip_0_100(proj_score)


def _support_away_win(h, a, proj: list, vi=None) -> tuple[float, float]:
    diff = _team_strength_score(a) - _team_strength_score(h)
    stat = _clip_0_100(54 + diff * 0.9)

    pval, pprob, label = _projected_value_by_keywords(proj, ["visitante"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["away"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["1x2", "visitante"])

    proj_score = 54.0
    if pprob is not None:
        proj_score += (pprob - 50) * 0.8
    elif label and ("visitante" in label or "away" in label):
        proj_score += 8

    return stat, _clip_0_100(proj_score)


def _support_draw(h, a, proj: list, vi=None) -> tuple[float, float]:
    diff = abs(_team_strength_score(h) - _team_strength_score(a))
    stat = _clip_0_100(62 - diff * 0.7)

    pval, pprob, label = _projected_value_by_keywords(proj, ["empate"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["draw"])

    proj_score = 50.0
    if pprob is not None:
        proj_score += (pprob - 50) * 0.7

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)

    if empirical is not None:
        stat = _clip_0_100(0.60 * stat + 0.40 * empirical)

    return stat, _clip_0_100(proj_score)

def _support_double_chance(
    side: str, 
    h, 
    a, 
    proj: list, 
    vi=None
) -> tuple[float, float]:
    """
    Soporte probabilístico estricto y coherente para Doble Oportunidad.
    Evita suelos artificiales y respeta la probabilidad complementaria axiomática:
      - P(1X) = 100 - P(Away)
      - P(X2) = 100 - P(Home)
      - P(12) = 100 - P(Draw)
    """
    stath, projh = _support_home_win(h, a, proj, vi)
    statd, projd = _support_draw(h, a, proj, vi)
    stata, proja = _support_away_win(h, a, proj, vi)

    # Suma directa con acotamiento de coherencia en espacio de probabilidades
    if side in ("1x", "homedraw"):
        # Derivación complementaria cruzada para evitar sobreestimar locales extremos
        direct_stat = stath + statd
        comp_stat = 100.0 - stata
        stat = min(direct_stat, comp_stat)

        direct_proj = projh + projd
        comp_proj = 100.0 - proja
        proj_score = min(direct_proj, comp_proj)

    elif side in ("x2", "drawaway"):
        direct_stat = stata + statd
        comp_stat = 100.0 - stath
        stat = min(direct_stat, comp_stat)

        direct_proj = proja + projd
        comp_proj = 100.0 - projh
        proj_score = min(direct_proj, comp_proj)

    elif side in ("12", "homeaway"):
        direct_stat = stath + stata
        comp_stat = 100.0 - statd
        stat = min(direct_stat, comp_stat)

        direct_proj = projh + proja
        comp_proj = 100.0 - projd
        proj_score = min(direct_proj, comp_proj)

    else:
        stat, proj_score = 50.0, 50.0

    # Ajuste de contracción Bayesiana hacia la cuota de mercado si el ValueIndicator está disponible
    if vi is not None and getattr(vi, "odds", None) is not None:
        try:
            odds_val = float(vi.odds)
            if odds_val > 1.0:
                implied_pct = (1.0 / odds_val) * 100.0
                # Si el modelo proyecta un soporte > 20% sobre la implícita, encoger hacia la implícita
                if stat > implied_pct + 15.0:
                    stat = 0.50 * stat + 0.50 * implied_pct
                if proj_score > implied_pct + 15.0:
                    proj_score = 0.50 * proj_score + 0.50 * implied_pct
        except (ValueError, TypeError):
            pass

    return _clip_0_100(stat), _clip_0_100(proj_score)

# ── Support Shots MEJORADO ──
def _support_under_shots(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    total_shots = _safe_num(h.shots_per_game) + _safe_num(a.shots_per_game)
    total_sot = _safe_num(h.shots_on_target_per_game) + _safe_num(a.shots_on_target_per_game)
    tempo = _safe_num(h.possession_pct) + _safe_num(a.possession_pct)
    base = total_shots + total_sot * 0.35 + max(0, (tempo - 100)) * 0.03

    # NUEVO: Ajustes por calidad de tiros
    h_inside = _safe_num(h.shots_inside_box)
    a_inside = _safe_num(a.shots_inside_box)
    h_created = _safe_num(h.big_chances_created)
    a_created = _safe_num(a.big_chances_created)
    h_dribble = _safe_num(h.dribble_success_pct)
    a_dribble = _safe_num(a.dribble_success_pct)

    quality_bonus = (h_inside + a_inside) * 0.3 + (h_created + a_created) * 0.5 + (h_dribble + a_dribble) * 0.02
    base += quality_bonus

    stat = _clip_0_100(58 + (line - base) * 7)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["tiros"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["shots"])

    proj_score = 55.0
    if pval is not None:
        proj_score += (line - pval) * 9
    if pprob is not None:
        proj_score += (pprob - 50) * 0.45

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)

    if empirical is not None:
        stat = _clip_0_100(0.60 * stat + 0.40 * empirical)

    return stat, _clip_0_100(proj_score)


def _support_over_shots(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    stat_u, proj_u = _support_under_shots(line, h, a, proj, vi)
    return _clip_0_100(100.0 - stat_u), _clip_0_100(100.0 - proj_u)


# ── Support Cards — Determinista ──
def _support_over_cards(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    """stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico."""
    lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["tarjetas totales"])
    if lam_val is None:
        lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["tarjetas"])

    if lam_prob is not None:
        model_prob = float(lam_prob)
    elif lam_val is not None:
        model_prob = _clip_0_100(55.0 + (lam_val - line) * 12)
    else:
        # Estimación por stats
        total_y = _safe_num(h.yellow_cards_per_game) + _safe_num(a.yellow_cards_per_game)
        model_prob = _clip_0_100(55.0 + (total_y - line) * 10)

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)
        if empirical is None:
            h_hr = _safe_num(getattr(vi, "home_hit_rate", None), None)
            a_hr = _safe_num(getattr(vi, "away_hit_rate", None), None)
            if h_hr is not None and a_hr is not None:
                empirical = (h_hr + a_hr) / 2.0

    stat = _clip_0_100(0.60 * model_prob + 0.40 * empirical) if empirical is not None else _clip_0_100(model_prob)
    proj_score = model_prob
    return stat, _clip_0_100(proj_score)


def _support_under_cards(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    stat_o, proj_o = _support_over_cards(line, h, a, proj, vi)
    return _clip_0_100(100 - stat_o), _clip_0_100(100 - proj_o)


# ── Support Corners — Determinista ──
def _support_over_corners(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    """stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico."""
    lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["corners totales"])
    if lam_val is None:
        lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["corners"])

    if lam_prob is not None:
        model_prob = float(lam_prob)
    elif lam_val is not None:
        model_prob = _clip_0_100(55.0 + (lam_val - line) * 12)
    else:
        base = (
            _safe_num(h.corners_per_game) + _safe_num(a.corners_per_game) +
            _safe_num(h.corners_conceded_per_game) + _safe_num(a.corners_conceded_per_game)
        ) / 2
        model_prob = _clip_0_100(55.0 + (base - line) * 10)

    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)
        if empirical is None:
            h_hr = _safe_num(getattr(vi, "home_hit_rate", None), None)
            a_hr = _safe_num(getattr(vi, "away_hit_rate", None), None)
            if h_hr is not None and a_hr is not None:
                empirical = (h_hr + a_hr) / 2.0

    stat = _clip_0_100(0.60 * model_prob + 0.40 * empirical) if empirical is not None else _clip_0_100(model_prob)
    proj_score = model_prob
    return stat, _clip_0_100(proj_score)


def _support_under_corners(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    stat_o, proj_o = _support_over_corners(line, h, a, proj, vi)
    return _clip_0_100(100 - stat_o), _clip_0_100(100 - proj_o)


def _dc_component_weights(h, a) -> tuple[float, float, float]:
    h_str = max(0.1, _team_strength_score(h) + 60.0)
    a_str = max(0.1, _team_strength_score(a) + 60.0)
    total_str = h_str + a_str
    h_w_base = h_str / total_str
    a_w_base = a_str / total_str

    balance = 1.0 - abs(h_w_base - a_w_base)
    d_w = 0.20 + balance * 0.15

    rem = 1.0 - d_w
    h_w = rem * h_w_base
    a_w = rem * a_w_base
    return h_w, d_w, a_w


def _explicit_market_support(selection: str, h, a, proj: list, vi=None) -> tuple[float, float]:
    s = _normalize_text(selection)
    line = _extract_line_number(selection)
    family = _market_family(selection)
    side = _market_side(selection)

    if family == "goals" and side == "over" and line is not None:
        return _support_over_goals(line, h, a, proj, vi)
    if family == "goals" and side == "under" and line is not None:
        return _support_under_goals(line, h, a, proj, vi)

    if family == "btts" and side == "yes":
        return _support_btts_yes(h, a, proj, vi)
    if family == "btts" and side == "no":
        return _support_btts_no(h, a, proj, vi)

    if family == "result" and side == "home":
        return _support_home_win(h, a, proj, vi)
    if family == "result" and side == "away":
        return _support_away_win(h, a, proj, vi)
    if family == "result" and side == "draw":
        return _support_draw(h, a, proj, vi)

    if family == "shots" and side == "under" and line is not None:
        return _support_under_shots(line, h, a, proj, vi)
    if family == "shots" and side == "over" and line is not None:
        return _support_over_shots(line, h, a, proj, vi)

    if family == "cards" and side == "over" and line is not None:
        return _support_over_cards(line, h, a, proj, vi)
    if family == "cards" and side == "under" and line is not None:
        return _support_under_cards(line, h, a, proj, vi)

    if family == "corners" and side == "over" and line is not None:
        return _support_over_corners(line, h, a, proj, vi)
    if family == "corners" and side == "under" and line is not None:
        return _support_under_corners(line, h, a, proj, vi)

    if family in ("double_chance", "doublechance") or "doble oportunidad" in s:
        target_side = "1x" if "1x" in s else ("x2" if "x2" in s else ("12" if "12" in s else side))
        return _support_double_chance(target_side, h, a, proj, vi)

    return 55.0, 55.0


def _canonical_pick_signature(selection: str) -> tuple[str, str, float | None]:
    family = _market_family(selection)
    side = _market_side(selection)
    line = _extract_line_number(selection)
    if line is not None:
        line = round(line, 2)
    return family, side, line


def _deduplicate_correlated_picks(values: list["ValueIndicator"]) -> list["ValueIndicator"]:
    DEDUP_FAMILIES = {"goals", "corners", "cards", "shots", "shots_target"}
    
    # NUEVO: Límite máximo de picks por familia de mercado
    MAX_PICKS_PER_FAMILY = {
        "goals": 1,
        "corners": 1,
        "cards": 1,
        "shots": 1,
        "shots_target": 1
    }

    groups: dict[tuple[str, str], list["ValueIndicator"]] = {}
    non_dedup: list["ValueIndicator"] = []

    for v in values:
        family, side, _ = _canonical_pick_signature(v.selection)
        if family in DEDUP_FAMILIES and v.odds is not None:
            key = (family, side)
            groups.setdefault(key, []).append(v)
        else:
            non_dedup.append(v)

    # Regla de selección por tamaño de grupo:
    #  - 1 pick   → se conserva tal cual
    #  - 2 picks  → solo el de mayor EV
    #  - 3+ picks → los 2 con mayor EV
    best_picks: list["ValueIndicator"] = []
    for (family, side), group in groups.items():
        if not group:
            continue
        sorted_group = sorted(
            group,
            key=lambda v: (
                v.edge if v.edge is not None else -999.0,
                v.display_score or 0.0,
                v.selection or ""
            ),
            reverse=True,
        )
        # Aplicar límite máximo por familia
        max_keep = MAX_PICKS_PER_FAMILY.get(family, 2)
        keep = min(max_keep, 2 if len(sorted_group) >= 3 else 1)
        best_picks.extend(sorted_group[:keep])

    return non_dedup + best_picks


def _are_contradictory(selection_a: str, selection_b: str) -> bool:
    fa, sa, la = _canonical_pick_signature(selection_a)
    fb, sb, lb = _canonical_pick_signature(selection_b)

    if fa != fb:
        return False

    if fa in {"goals", "corners", "cards", "shots", "shots_target", "fouls"}:
        if la is not None and lb is not None and abs(la - lb) <= 0.15 and {sa, sb} == {"over", "under"}:
            return True

    if fa == "btts" and {sa, sb} == {"yes", "no"}:
        return True

    if fa == "result" and sa != "none" and sb != "none" and sa != sb:
        return True

    return False


def _is_too_similar(selection_a: str, selection_b: str) -> bool:
    fa, sa, la = _canonical_pick_signature(selection_a)
    fb, sb, lb = _canonical_pick_signature(selection_b)

    if fa != fb:
        return False

    if sa == sb and la is not None and lb is not None and abs(la - lb) <= 0.5:
        return True

    return _normalize_text(selection_a) == _normalize_text(selection_b)


def _profitability_band_score(odds: float) -> int:
    if 1.50 <= odds <= 2.50:
        return 50
    if 2.50 < odds <= 3.50: 
        return 20
    if 1.40 <= odds < 1.50:
        return -8
    if 1.30 <= odds < 1.40:
        return -18
    return -30


def _is_secondary_market(selection: str) -> bool:
    s = (selection or "").lower()
    return any(k in s for k in ["corner", "corners", "córner", "córners", "tarjeta", "tarjetas", "cards"])


def _frontend_style_strategic_score(v: ValueIndicator) -> int:
    """Score estratégico basado únicamente en EV positivo y Kelly Fraccional.
    No contiene saltos fijos por tipo de mercado.
    """
    if v.is_blacklisted:
        return -1
    edge = _safe_num(v.edge)
    odds = _safe_num(v.odds, 0.0)
    prob = _safe_num(v.model_prob)

    if edge < 2.0 or odds <= 1.01:
        return -1

    # Kelly Fraccional: f* = (p * b - (1-p)) / b, donde b = odds - 1
    b = max(odds - 1.0, 0.01)
    p = prob / 100.0
    kelly_raw = (p * b - (1.0 - p)) / b
    kelly = max(0.0, min(kelly_raw, 0.25))  # Fraccionado al 25% máximo

    if kelly <= 0:
        return -1

    # Score base: Kelly * 200 (0 a 50 puntos) + contribución del edge
    score = int(kelly * 200) + int(edge * 1.5)

    # Banda de rentabilidad: refuerzo de cuotas óptimas (continuo)
    score += _profitability_band_score(odds)

    return max(score, 0)


def _rate_pick_quality(v: ValueIndicator, h, a, proj: list[ProjectedLine]) -> tuple[int, float, float, int]:
    if v.is_blacklisted:
        return -1, 0.0, 0.0, -1
    selection = v.selection or ""
    odds = _safe_num(v.odds, None)
    prob = _safe_num(v.model_prob)
    edge = _safe_num(v.edge)
    implied = _safe_num(v.implied_prob, None)
    if implied is None:
        implied = _implied_prob_from_odds(odds)

    # Pasar el ValueIndicator completo para que las funciones de soporte
    # puedan usar empirical_hit_rate y home/away_hit_rate
    stat_support, proj_support = _explicit_market_support(selection, h, a, proj, vi=v)
    strategic_score = _frontend_style_strategic_score(v)

    # ── SCORE DE CALIDAD (siempre se calcula; NO veta publicación) ──
    # quality_score es puramente métrica analítica. Los umbrales internos
    # (prob, edge, stat_support, proj_support) ahora restan puntos al score
    # en vez de vetar el pick. Solo blacklist, correlación y ausencia de
    # valor (EV/edge/stake) pueden bloquear un pick.
    family = _market_family(selection)

    score = 0
    score += _probability_band_score(prob)

    # Penalizaciones graduales (bajan el score, no vetan)
    if odds is None or odds <= 1.01:
        score -= 20
    if prob < 56:
        score -= max(0, int((56 - prob) * 0.5))
    if edge < 1.8:
        score -= max(0, int((1.8 - edge) * 5))
    min_stat = 53 if family in {"cards", "corners", "shots"} else 52
    score += int((stat_support - 50) * 0.85)
    if stat_support < min_stat:
        score -= 10
    score += int((proj_support - 50) * 0.65)
    if proj_support < 48:
        score -= 8

    score += _market_risk_weight(selection)
    score += _odds_risk_penalty(odds)

    # ── SCORE DE RENTABILIDAD ESTRATÉGICA ──
    score += strategic_score

    # Bonus continuo por EV Edge real sobre implícita (sin descuentos fijos)
    if implied is not None:
        delta = prob - implied
        ev_confidence = min(delta / 12.0, 1.0)  # 0..1 según magnitud del edge
        score += int(ev_confidence * 10)  # hasta +10 pts proporcional

    # Confianza por tamaño de muestra: penalización continua si la liga tiene
    # poca muestra (league_reliability va de 0 a 1)
    league = getattr(v, "_league_ref", None)  # inyectado opcionalmente
    if league is not None:
        reliability = _compute_league_reliability_score(league)
        if reliability < 0.5:
            score = int(score * (0.5 + reliability))  # máx penalización del 50%

    return score, stat_support, proj_support, strategic_score
