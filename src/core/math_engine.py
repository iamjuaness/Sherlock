"""
Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).

Sustituye la dependencia de entrenamiento GLM con bajo número de muestras 
por cálculos deterministas:
  - Dixon-Coles (Ajuste de fuerza ofensiva/defensiva + tau para marcadores de baja anotación).
  - Ponderación por reciencia exponencial (decay por fecha/partido).
  - Segmentación por liga (promedios específicos de liga y factor de localía).
  - Método de momentos para estimar dispersión Binomial Negativa (corners, tarjetas, tiros).
"""

from __future__ import annotations

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger("sherlock.math_engine")


# ---------------------------------------------------------------------------
# Funciones Estadísticas Base
# ---------------------------------------------------------------------------

def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def dixon_coles_tau(x: int, y: int, lambda_home: float, mu_away: float, rho: float = -0.05) -> float:
    """
    Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0, 0-1, 1-1).
    rho típico para fútbol suele ser entre -0.03 y -0.08.
    """
    if x == 0 and y == 0:
        return max(0.0001, 1.0 - lambda_home * mu_away * rho)
    elif x == 0 and y == 1:
        return max(0.0001, 1.0 + lambda_home * rho)
    elif x == 1 and y == 0:
        return max(0.0001, 1.0 + mu_away * rho)
    elif x == 1 and y == 1:
        return max(0.0001, 1.0 - rho)
    return 1.0


def calculate_dixon_coles_matrix(
    lambda_home: float, 
    mu_away: float, 
    max_goals: int = 8, 
    rho: float = -0.05
) -> List[List[float]]:
    """
    Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste Dixon-Coles.
    """
    matrix = [[0.0 for _ in range(max_goals + 1)] for _ in range(max_goals + 1)]
    total_prob = 0.0

    for x in range(max_goals + 1):
        p_x = _poisson_pmf(x, lambda_home)
        for y in range(max_goals + 1):
            p_y = _poisson_pmf(y, mu_away)
            tau = dixon_coles_tau(x, y, lambda_home, mu_away, rho)
            prob = max(0.0, p_x * p_y * tau)
            matrix[x][y] = prob
            total_prob += prob

    # Normalizar para asegurar sum(P) = 1.0
    if total_prob > 0:
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                matrix[x][y] /= total_prob

    return matrix


def calculate_weighted_average(values: List[float], half_life: float = 5.0) -> float:
    """
    Calcula el promedio con decay exponencial según antigüedad.
    half_life: número de partidos para que la importancia caiga al 50%.
    values: ordenados del más reciente al más antiguo.
    """
    if not values:
        return 0.0

    alpha = math.log(2) / max(1.0, half_life)
    weights = [math.exp(-alpha * i) for i in range(len(values))]
    sum_w = sum(weights)

    if sum_w <= 0:
        return sum(values) / len(values)

    return sum(v * w for v, w in zip(values, weights)) / sum_w


def estimate_nb_dispersion(values: List[float]) -> float:
    """
    Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método de Momentos.
    Var(X) = mu + alpha * mu^2  =>  alpha = (Var - mu) / mu^2
    """
    if len(values) < 3:
        return 0.05 # Dispersión baja por defecto

    mu = sum(values) / len(values)
    if mu <= 0:
        return 0.05

    var = sum((x - mu) ** 2 for x in values) / (len(values) - 1)
    if var <= mu:
        return 0.001  # Casi Poisson puro

    alpha = (var - mu) / (mu ** 2)
    return max(0.001, min(0.5, alpha))


# ---------------------------------------------------------------------------
# Motor Predictor Matemático por Liga
# ---------------------------------------------------------------------------

class LeagueMathEngine:
    """
    Calcula probabilidades de partido integrando promedios por liga, fuerza relativa
    de equipo (Local / Visitante / Reciente) y distribuciones Poisson / Dixon-Coles / NB.
    """

    def __init__(self, league_defaults: Optional[Dict[str, float]] = None):
        # Promedios estándar por defecto si la liga no tiene datos históricos suficientes
        self.defaults = {
            "home_goals": 1.45,
            "away_goals": 1.15,
            "home_corners": 5.2,
            "away_corners": 4.1,
            "home_cards": 2.1,
            "away_cards": 2.3,
            "home_shots": 12.5,
            "away_shots": 9.8,
            "home_shots_target": 4.5,
            "away_shots_target": 3.6,
            "home_fouls": 11.5,
            "away_fouls": 12.0,
        }
        if league_defaults:
            self.defaults.update(league_defaults)

    @classmethod
    def compute_league_averages(cls, historical_matches: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calcula los promedios específicos de la liga basándose en los partidos históricos jugados.
        """
        if not historical_matches:
            return cls().defaults

        total_home_goals, total_away_goals = 0.0, 0.0
        total_home_corners, total_away_corners = 0.0, 0.0
        total_home_cards, total_away_cards = 0.0, 0.0
        total_home_shots, total_away_shots = 0.0, 0.0
        total_home_shots_target, total_away_shots_target = 0.0, 0.0
        total_home_fouls, total_away_fouls = 0.0, 0.0
        count = 0

        for m in historical_matches:
            sh = m.get("final_score_home")
            sa = m.get("final_score_away")
            if sh is not None and sa is not None:
                total_home_goals += float(sh)
                total_away_goals += float(sa)
                count += 1

            ch = m.get("final_corners_home")
            ca = m.get("final_corners_away")
            if ch is not None and ca is not None:
                total_home_corners += float(ch)
                total_away_corners += float(ca)

            yh = m.get("final_yellow_cards_home")
            ya = m.get("final_yellow_cards_away")
            if yh is not None and ya is not None:
                total_home_cards += float(yh)
                total_away_cards += float(ya)

            sth = m.get("final_shots_home")
            sta = m.get("final_shots_away")
            if sth is not None and sta is not None:
                total_home_shots += float(sth)
                total_away_shots += float(sta)

            stth = m.get("final_shots_on_target_home")
            stta = m.get("final_shots_on_target_away")
            if stth is not None and stta is not None:
                total_home_shots_target += float(stth)
                total_away_shots_target += float(stta)

            fh = m.get("final_fouls_home")
            fa = m.get("final_fouls_away")
            if fh is not None and fa is not None:
                total_home_fouls += float(fh)
                total_away_fouls += float(fa)

        if count == 0:
            return cls().defaults

        return {
            "home_goals": total_home_goals / count,
            "away_goals": total_away_goals / count,
            "home_corners": total_home_corners / count if total_home_corners > 0 else 5.2,
            "away_corners": total_away_corners / count if total_away_corners > 0 else 4.1,
            "home_cards": total_home_cards / count if total_home_cards > 0 else 2.1,
            "away_cards": total_away_cards / count if total_away_cards > 0 else 2.3,
            "home_shots": total_home_shots / count if total_home_shots > 0 else 12.5,
            "away_shots": total_away_shots / count if total_away_shots > 0 else 9.8,
            "home_shots_target": total_home_shots_target / count if total_home_shots_target > 0 else 4.5,
            "away_shots_target": total_away_shots_target / count if total_away_shots_target > 0 else 3.6,
            "home_fouls": total_home_fouls / count if total_home_fouls > 0 else 11.5,
            "away_fouls": total_away_fouls / count if total_away_fouls > 0 else 12.0,
        }


    def calculate_expected_goals(
        self,
        home_recent_scored: List[float],
        home_recent_conceded: List[float],
        away_recent_scored: List[float],
        away_recent_conceded: List[float],
        league_home_avg: float = 1.45,
        league_away_avg: float = 1.15,
        half_life: float = 17.5,
        is_home_newly_promoted: bool = False,
        is_away_newly_promoted: bool = False,
    ) -> Tuple[float, float]:
        """
        Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva y defensiva relativa con decay exponencial.
        - half_life: 15-20 partidos (default 17.5) para ponderar reciencia y evitar contaminación por temporadas lejanas.
        - is_home_newly_promoted / is_away_newly_promoted: Equipos recién ascendidos con < 10 partidos en la liga
          cuyo prior Bayesiano se apoya fuertemente en la media de la liga.
        """
        league_home_avg = max(0.5, league_home_avg)
        league_away_avg = max(0.5, league_away_avg)

        # Promedios ponderados de equipos con Half-Life de 15-20 partidos
        home_att_raw = calculate_weighted_average(home_recent_scored, half_life=half_life) if home_recent_scored else league_home_avg
        home_def_raw = calculate_weighted_average(home_recent_conceded, half_life=half_life) if home_recent_conceded else league_away_avg

        away_att_raw = calculate_weighted_average(away_recent_scored, half_life=half_life) if away_recent_scored else league_away_avg
        away_def_raw = calculate_weighted_average(away_recent_conceded, half_life=half_life) if away_recent_conceded else league_home_avg

        # Shrinkage Bayesiano para recién ascendidos (< 10 partidos en categoría)
        if is_home_newly_promoted or len(home_recent_scored) < 8:
            shrinkage_weight = min(1.0, len(home_recent_scored) / 10.0)
            home_att_raw = home_att_raw * shrinkage_weight + league_home_avg * (1.0 - shrinkage_weight)
            home_def_raw = home_def_raw * shrinkage_weight + league_away_avg * (1.0 - shrinkage_weight)

        if is_away_newly_promoted or len(away_recent_scored) < 8:
            shrinkage_weight = min(1.0, len(away_recent_scored) / 10.0)
            away_att_raw = away_att_raw * shrinkage_weight + league_away_avg * (1.0 - shrinkage_weight)
            away_def_raw = away_def_raw * shrinkage_weight + league_home_avg * (1.0 - shrinkage_weight)

        # Fuerza relativa
        home_attack_strength = home_att_raw / league_home_avg
        home_defense_strength = home_def_raw / league_away_avg

        away_attack_strength = away_att_raw / league_away_avg
        away_defense_strength = away_def_raw / league_home_avg

        # Exponentes / Lambdas esperados
        lambda_home = home_attack_strength * away_defense_strength * league_home_avg
        mu_away = away_attack_strength * home_defense_strength * league_away_avg

        # Limitar a rangos razonables de fútbol profesional (0.2 a 4.5 goles)
        lambda_home = max(0.2, min(4.5, lambda_home))
        mu_away = max(0.2, min(4.5, mu_away))

        return lambda_home, mu_away

    def predict_market_totals(
        self,
        home_values: List[float],
        away_values: List[float],
        league_avg_total: float,
        half_life: float = 17.5
    ) -> Tuple[float, float]:
        """
        Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros, etc.)
        aplicando decaimiento exponencial y suavizado de liga.
        """
        h_avg = calculate_weighted_average(home_values, half_life=half_life) if home_values else (league_avg_total * 0.55)
        a_avg = calculate_weighted_average(away_values, half_life=half_life) if away_values else (league_avg_total * 0.45)
        
        # Suavizado con la media de la liga
        total_expected = (h_avg + a_avg) * 0.75 + (league_avg_total) * 0.25
        
        h_prop = h_avg / max(0.1, h_avg + a_avg)
        return total_expected * h_prop, total_expected * (1.0 - h_prop)

    @staticmethod
    def compute_recent_form_windows(matches: List[Dict[str, Any]], team_name: str, windows: List[int] = [5, 10, 15]) -> Dict[str, Dict[str, float]]:
        """
        Capa 3: Calcula estadísticas promedio del equipo `team_name` en ventanas móviles de 5, 10 y 15 partidos
        recientes jugados ANTES del partido actual (sin data leakage).
        """
        team_matches = []
        for m in matches:
            ht = (m.get("home_team") or m.get("match_title", "").split(" vs ")[0]).strip().lower()
            at = (m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")).strip().lower()
            t_lower = team_name.strip().lower()
            
            if t_lower == ht or t_lower in ht:
                team_matches.append((m, "home"))
            elif t_lower == at or t_lower in at:
                team_matches.append((m, "away"))

        results = {}
        for w in windows:
            slice_m = team_matches[:w]
            if not slice_m:
                results[f"last_{w}"] = {
                    "goals_scored": 0.0, "goals_conceded": 0.0,
                    "corners": 0.0, "yellow_cards": 0.0, "shots": 0.0
                }
                continue

            g_scored, g_conceded, corners, cards, shots = 0.0, 0.0, 0.0, 0.0, 0.0
            cnt = len(slice_m)

            for m, role in slice_m:
                if role == "home":
                    g_scored += float(m.get("final_score_home") or 0)
                    g_conceded += float(m.get("final_score_away") or 0)
                    corners += float(m.get("final_corners_home") or 0)
                    cards += float(m.get("final_yellow_cards_home") or 0)
                    shots += float(m.get("final_shots_home") or 0)
                else:
                    g_scored += float(m.get("final_score_away") or 0)
                    g_conceded += float(m.get("final_score_home") or 0)
                    corners += float(m.get("final_corners_away") or 0)
                    cards += float(m.get("final_yellow_cards_away") or 0)
                    shots += float(m.get("final_shots_away") or 0)

            results[f"last_{w}"] = {
                "sample_size": cnt,
                "goals_scored": round(g_scored / cnt, 2),
                "goals_conceded": round(g_conceded / cnt, 2),
                "corners": round(corners / cnt, 2),
                "yellow_cards": round(cards / cnt, 2),
                "shots": round(shots / cnt, 2),
            }

        return results

    @staticmethod
    def _evaluate_match_metric_pick(
        m: Dict[str, Any],
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        team_role: str = "home",
        target_side: str = "home",
    ) -> Optional[bool]:
        """
        Evalúa si un partido específico cumple con el criterio de un pick.
        Soporta: goals, corners, cards, shots, shots_target, fouls, btts, 1x2, double_chance.
        """
        sh = m.get("final_score_home")
        sa = m.get("final_score_away")

        # 1. Ambos marcan (BTTS)
        if market_family in {"btts", "btts_yes"}:
            if sh is None or sa is None:
                return None
            return (float(sh) > 0 and float(sa) > 0)
        if market_family == "btts_no":
            if sh is None or sa is None:
                return None
            return (float(sh) == 0 or float(sa) == 0)

        # 2. Ganador 1X2 (Moneyline / Result)
        if market_family in {"result", "moneyline", "1x2"}:
            if sh is None or sa is None:
                return None
            gh, ga = float(sh), float(sa)
            if target_side in {"home", "local", "1"}:
                # Si se evalúa para el equipo en cuestión según su rol
                return gh > ga if team_role == "home" else False
            elif target_side in {"away", "visitante", "2"}:
                return ga > gh if team_role == "away" else False
            elif target_side in {"draw", "empate", "x"}:
                return gh == ga

        # 3. Doble Oportunidad (Double Chance: 1X, X2, 12)
        if market_family == "double_chance":
            if sh is None or sa is None:
                return None
            gh, ga = float(sh), float(sa)
            if target_side in {"1x", "home_draw"}:
                return (gh >= ga) if team_role == "home" else (gh >= ga)
            elif target_side in {"x2", "draw_away"}:
                return (ga >= gh) if team_role == "away" else (ga >= gh)
            elif target_side in {"12", "home_away"}:
                return gh != ga

        # 4. Totales / Over-Under en métricas cuantitativas
        val = None
        if market_family == "goals":
            if sh is not None and sa is not None:
                val = float(sh) + float(sa)
        elif market_family == "corners":
            ch, ca = m.get("final_corners_home"), m.get("final_corners_away")
            if ch is not None and ca is not None:
                val = float(ch) + float(ca)
        elif market_family == "cards":
            yh, ya = m.get("final_yellow_cards_home"), m.get("final_yellow_cards_away")
            if yh is not None and ya is not None:
                val = float(yh) + float(ya)
        elif market_family in {"shots", "shots_target"}:
            if market_family == "shots_target":
                sth, sta = m.get("final_shots_on_target_home"), m.get("final_shots_on_target_away")
            else:
                sth, sta = m.get("final_shots_home"), m.get("final_shots_away")
            if sth is not None and sta is not None:
                val = float(sth) + float(sta)
        elif market_family == "fouls":
            fh, fa = m.get("final_fouls_home"), m.get("final_fouls_away")
            if fh is not None and fa is not None:
                val = float(fh) + float(fa)

        if val is not None and line is not None:
            return (val > line) if is_over else (val < line)

        return None

    @classmethod
    def compute_pick_hit_rate(
        cls,
        matches: List[Dict[str, Any]],
        team_name: str,
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        role_filter: Optional[str] = None,  # "home", "away", or None (all)
        target_side: str = "home",
        exclude_match_id: Optional[int] = None,
        current_match_date: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.
        Soporta: Líneas Over/Under, BTTS (Sí/No), 1X2 (Gana local/vis/emp) y Doble Oportunidad (1X, X2, 12).
        Previene data-leakage excluyendo partidos en o posteriores a la fecha del partido actual.
        """
        t_lower = team_name.strip().lower()
        matching_count = 0
        hit_count = 0

        ref_dt = None
        if current_match_date:
            try:
                if isinstance(current_match_date, datetime):
                    ref_dt = current_match_date
                else:
                    dt_s = str(current_match_date).replace("Z", "+00:00")
                    if "T" in dt_s:
                        ref_dt = datetime.fromisoformat(dt_s)
                    elif len(dt_s) >= 10:
                        ref_dt = datetime.strptime(dt_s[:10], "%Y-%m-%d")
            except Exception:
                ref_dt = None

        ref_date_only = ref_dt.date() if ref_dt else None

        for m in matches:
            if exclude_match_id is not None:
                m_id = m.get("id") or m.get("match_id")
                if m_id is not None and str(m_id) == str(exclude_match_id):
                    continue

            date_val = m.get("date") or m.get("match_date")
            m_dt = None
            if date_val:
                try:
                    if isinstance(date_val, datetime):
                        m_dt = date_val
                    else:
                        m_s = str(date_val).replace("Z", "+00:00")
                        if "T" in m_s or " " in m_s:
                            m_dt = datetime.fromisoformat(m_s)
                        elif len(m_s) >= 10:
                            m_dt = datetime.strptime(m_s[:10], "%Y-%m-%d")
                except Exception:
                    pass

            if ref_date_only and m_dt and m_dt.date() >= ref_date_only:
                continue

            ht = (m.get("home_team") or m.get("match_title", "").split(" vs ")[0]).strip().lower()
            at = (m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")).strip().lower()

            is_home = t_lower == ht
            is_away = t_lower == at

            if not (is_home or is_away):
                continue

            if role_filter == "home" and not is_home:
                continue
            if role_filter == "away" and not is_away:
                continue

            role = "home" if is_home else "away"
            hit = cls._evaluate_match_metric_pick(
                m, market_family, line=line, is_over=is_over, team_role=role, target_side=target_side
            )

            if hit is not None:
                matching_count += 1
                if hit:
                    hit_count += 1

        hit_rate = (hit_count / matching_count * 100.0) if matching_count > 0 else 0.0
        return {
            "sample_size": matching_count,
            "hits": hit_count,
            "hit_rate_pct": round(hit_rate, 1)
        }

    @classmethod
    def compute_h2h_hit_rate(
        cls,
        matches: List[Dict[str, Any]],
        home_team_name: str,
        away_team_name: str,
        market_family: str,
        line: Optional[float] = None,
        is_over: bool = True,
        target_side: str = "home",
        exclude_match_id: Optional[Any] = None,
        current_match_date: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)
        entre ambos equipos (respetando localía/visitante estricta para 1X2 / Doble Oportunidad).
        Previene data-leakage excluyendo partidos en o posteriores a la fecha del partido actual.
        """
        h_lower = home_team_name.strip().lower()
        a_lower = away_team_name.strip().lower()
        matching_count = 0
        hit_count = 0
        h2h_matches_list = []

        ref_dt = None
        if current_match_date:
            try:
                if isinstance(current_match_date, datetime):
                    ref_dt = current_match_date
                else:
                    dt_s = str(current_match_date).replace("Z", "+00:00")
                    if "T" in dt_s or " " in dt_s:
                        ref_dt = datetime.fromisoformat(dt_s)
                    elif len(dt_s) >= 10:
                        ref_dt = datetime.strptime(dt_s[:10], "%Y-%m-%d")
            except Exception as e:
                ref_dt = None

        ref_date_only = ref_dt.date() if ref_dt else None

        for m in matches:
            m_id = m.get("id") or m.get("match_id")
            m_title = m.get("match_title", "")

            # 1. Validación de Exclusión por ID
            if exclude_match_id is not None and m_id is not None:
                if str(m_id).strip() == str(exclude_match_id).strip():
                    print(f"  ❌ [EXCLUIDO POR ID] match_id={m_id} coincide con exclude_match_id={exclude_match_id}")
                    continue

            # 2. Validación de Exclusión por Fecha
            date_val = m.get("date") or m.get("match_date")
            m_dt = None
            if date_val:
                try:
                    if isinstance(date_val, datetime):
                        m_dt = date_val
                    else:
                        m_s = str(date_val).replace("Z", "+00:00")
                        if "T" in m_s or " " in m_s:
                            m_dt = datetime.fromisoformat(m_s)
                        elif len(m_s) >= 10:
                            m_dt = datetime.strptime(m_s[:10], "%Y-%m-%d")
                except Exception as e:
                    print(f"[DEBUG H2H] Error parseando date_val '{date_val}': {e}")

            # Filtrar si el partido es igual o posterior en fecha/hora
            if ref_dt and m_dt and m_dt >= ref_dt:
                print(f"  ❌ [EXCLUIDO POR FECHA >=] {m_title} ({m_dt} >= {ref_dt})")
                continue
            elif ref_date_only and m_dt and m_dt.date() >= ref_date_only:
                print(f"  ❌ [EXCLUIDO POR DIA >=] {m_title} ({m_dt.date()} >= {ref_date_only})")
                continue

            ht_raw = m.get("home_team") or (m.get("match_title", "").split(" vs ")[0] if " vs " in m.get("match_title", "") else "")
            at_raw = m.get("away_team") or (m.get("match_title", "").split(" vs ")[1] if " vs " in m.get("match_title", "") else "")
            ht = ht_raw.strip().lower()
            at = at_raw.strip().lower()

            is_exact_fixture = (h_lower == ht and a_lower == at)
            is_reverse_fixture = (a_lower == ht and h_lower == at)

            if not (is_exact_fixture or is_reverse_fixture):
                continue

            if market_family in {"result", "moneyline", "1x2", "double_chance"}:
                if not is_exact_fixture:
                    continue

            role = "home" if is_exact_fixture else "away"
            hit = cls._evaluate_match_metric_pick(
                m, market_family, line=line, is_over=is_over, team_role=role, target_side=target_side
            )

            if hit is not None:
                matching_count += 1
                if hit:
                    hit_count += 1

                date_str = str(date_val).replace("T", " ").split(" ")[0] if date_val else ""

                h2h_matches_list.append({
                    "date": date_str,
                    "home_team": ht_raw.strip() if ht_raw else "Home",
                    "away_team": at_raw.strip() if at_raw else "Away",
                    "score_home": m.get("final_score_home"),
                    "score_away": m.get("final_score_away"),
                    "corners_home": m.get("final_corners_home"),
                    "corners_away": m.get("final_corners_away"),
                    "cards_home": m.get("final_yellow_cards_home"),
                    "cards_away": m.get("final_yellow_cards_away"),
                    "hit": bool(hit)
                })

        hit_rate = (hit_count / matching_count * 100.0) if matching_count > 0 else 0.0

        return {
            "sample_size": matching_count,
            "hits": hit_count,
            "hit_rate_pct": round(hit_rate, 1),
            "h2h_matches": h2h_matches_list
        }



