from __future__ import annotations
from enum import Enum
from typing import Optional
import os, math
import re
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Optional, Any, Dict, List

load_dotenv()


# ───────────────────────────────────────────────────────────────
# Enums
# ───────────────────────────────────────────────────────────────
class SportType(str, Enum):
    FOOTBALL = "football"

# ───────────────────────────────────────────────────────────────
# Football — modelo limpio
# ───────────────────────────────────────────────────────────────
class FootballTeamStats(BaseModel):
    name: str = Field(..., description="Nombre del equipo")

    # Generales
    matches_home:   int = Field(1,  description="Partidos jugados como local")
    matches_away:   int = Field(1,  description="Partidos jugados como visitante")
    matches_played: int = Field(1,  description="Partidos totales")
    wins:           int = Field(0,  description="Ganados")
    draws:          int = Field(0,  description="Empates")
    losses:         int = Field(0,  description="Perdidos")

    # Goles
    goals_per_game:          float = Field(..., description="Goles por juego")
    goals_conceded_per_game: float = Field(..., description="Goles concedidos por juego")
    goal_conversion_pct:     float = Field(..., description="Conversión de gol %")

    # Ataque
    big_chances_per_game:         float = Field(..., description="Grandes chances por juego")
    big_chances_missed_per_game:  float = Field(..., description="Grandes chances falladas por juego")
    shots_per_game:               float = Field(..., description="Tiros totales por juego")
    shots_on_target_per_game:     float = Field(..., description="Tiros al arco por juego")

    # Posesión / Pases
    possession_pct:         float = Field(..., description="Posesión %")
    passes_completed:       float = Field(0,   description="Pases acertados")
    pass_accuracy:          float = Field(0,   description="Precisión pases %")
    passes_opp_half:        float = Field(0,   description="Pases acertados campo rival")
    pass_accuracy_opp_half: float = Field(0,   description="Precisión pases campo rival %")
    crosses_per_game:       float = Field(0,   description="Centros completos por juego")
    cross_accuracy:         float = Field(0,   description="Precisión de centros %")
    corners_per_game:       float = Field(..., description="Corners por juego")

    # Defensa
    clean_sheets_home:        int   = Field(0,   description="Vallas invictas como local")
    clean_sheets_away:        int   = Field(0,   description="Vallas invictas como visitante")
    clean_sheets:             float = Field(..., description="Vallas invictas totales")
    saves_per_game:           float = Field(0,   description="Saves por juego")
    balls_recovered_per_game: float = Field(..., description="Recuperaciones por juego")

    # Duelos
    duels_won_per_game:        float = Field(0, description="Duelos ganados por juego")
    ground_duels_won_per_game: float = Field(0, description="Duelos en piso ganados por juego")

    # Set pieces
    penalties_conceded: float = Field(0, description="Penales concedidos")

    # Disciplina
    fouls_per_game:        float = Field(..., description="Faltas por juego")
    yellow_cards_per_game: float = Field(..., description="Amarillas promedio por juego")
    red_cards_total:       float = Field(0.0, description="Rojas totales")

    errors_leading_to_goal: float = Field(0, description="Errores que llevan a gol")
    offside_per_game:       float = Field(0, description="Fuera de juego por juego")

    # Extra Advanced
    corners_conceded_per_game:    float = Field(5.0, description="Corners concedidos por juego")
    xg_per_game:                  float = Field(1.5, description="Expected Goals por juego")
    xga_per_game:                 float = Field(1.5, description="Expected Goals Against por juego")
    # Pases / Centros (Totales vs Acertados)
    passes_total_per_game:          float = Field(500.0, description="Pases totales intentados por juego")
    passes_opp_half_total_per_game: float = Field(200.0, description="Pases totales intentados en campo rival")
    crosses_total_per_game:         float = Field(20.0,  description="Centros totales intentados por juego")


class LeagueStats(BaseModel):
    avg_goals_per_game:        float = Field(2.5,  description="Promedio total goles liga")
    avg_corners_per_game:      float = Field(9.5,  description="Promedio corners liga")
    avg_cards_per_game:        float = Field(4.5,  description="Promedio tarjetas liga")
    home_win_pct:              float = Field(45.0, description="% Victoria local liga")
    draw_pct:                 float = Field(25.0, description="% Empate liga")
    away_win_pct:              float = Field(30.0, description="% Victoria visitante liga")
    avg_yellow_cards_per_game: float = Field(4.0,  description="Promedio amarillas liga")
    avg_red_cards_per_game:    float = Field(0.2,  description="Promedio rojas liga")
    avg_shots_per_game:        float = Field(26.0, description="Promedio tiros totales liga")
    avg_shots_target_per_game: float = Field(8.5,  description="Promedio tiros a puerta liga")
    home_advantage_factor:    float = Field(1.20, description="Multiplicador goles local (1.15–1.30)")
    away_disadvantage_factor: float = Field(0.85, description="Factor penalización visitante")
    
    # Referee stats
    referee_avg_yellow:        float = Field(0.0,  description="Promedio amarillas del árbitro")
    referee_avg_red:           float = Field(0.0,  description="Promedio rojas del árbitro")


class FootballOdds(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    home:     float | None = Field(None, gt=1.0)
    draw:     float | None = Field(None, gt=1.0)
    away:     float | None = Field(None, gt=1.0)
    btts_yes: float | None = Field(None, gt=1.0)
    btts_no:  float | None = Field(None, gt=1.0)

    # DC
    dc_1x:    float | None = Field(None, gt=1.0)
    dc_x2:    float | None = Field(None, gt=1.0)
    dc_12:    float | None = Field(None, gt=1.0)

    # DNB
    dnb_home: float | None = Field(None, gt=1.0)
    dnb_away: float | None = Field(None, gt=1.0)

    goals_lines:      list[float]                = [1.5, 2.5, 3.5, 4.5]
    goals_over_odds:  Dict[str, Optional[float]] = Field(default_factory=dict)
    goals_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    corners_lines:      list[float]              = [7.5, 8.5, 9.5, 10.5]
    corners_over_odds:  Dict[str, Optional[float]] = Field(default_factory=dict)
    corners_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    cards_lines:      list[float]                = [2.5, 3.5, 4.5, 5.5]
    cards_over_odds:  Dict[str, Optional[float]] = Field(default_factory=dict)
    cards_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    shots_lines:      list[float]                = [21.5, 22.5, 23.5, 24.5]
    shots_over_odds:  Dict[str, Optional[float]] = Field(default_factory=dict)
    shots_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    shots_target_lines: list[float]                = [7.5, 8.5, 9.5, 10.5]
    shots_target_over_odds:  Dict[str, Optional[float]] = Field(default_factory=dict)
    shots_target_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    
    handicap_lines:     list[float]                = []
    handicap_home_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    handicap_away_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    bookmaker: str = ""


class FootballCompareRequest(BaseModel):
    home: FootballTeamStats
    away: FootballTeamStats
    odds: FootballOdds
    league_stats: LeagueStats = Field(default_factory=LeagueStats)
    competition: str = "Desconocida"
    generate_llm_analysis: bool = False
    user_context: str = Field(default="", description="Contexto adicional proporcionado por el usuario sobre los equipos")

# ───────────────────────────────────────────────────────────────
# Response models
# ───────────────────────────────────────────────────────────────
class ValueIndicator(BaseModel):
    selection:    str
    odds:         float | None = None
    
    # Probabilidades
    model_prob:           float  # Raw Poisson/Bayesian prob
    calibrated_prob:      Optional[float] = None
    implied_prob:         Optional[float] = None # 1/odds (raw)
    implied_prob_no_vig:  Optional[float] = None # Fair market prob
    
    # Métricas de Valor
    edge:         float = 0.0    # Diferencia de prob (legacy/display)
    edge_ev:      float = 0.0    # Expected Value real: (cal_prob * odds) - 1
    fair_odds:    Optional[float] = None
    
    # Status y Calidad
    is_value:     bool  = False
    rating:       str   = "N/A"
    quality_score:   Optional[int] = None
    strategic_score: Optional[int] = None
    stat_support:    Optional[float] = None
    proj_support:    Optional[float] = None
    data_quality_score:     Optional[float] = None
    
    # Clasificación de Mercado
    market_confidence_tier: Optional[str]   = None 
    market_variance_tier:   Optional[str]   = None 
    
    # Flags de Decisión
    is_publishable:        bool = False
    is_high_confidence:    bool = False
    is_underdog:           bool = False
    success:               Optional[bool] = None
    display_score:         Optional[float] = None
    push_prob:             Optional[float] = None
    
    # Staking
    kelly_fraction:        Optional[float] = None
    sample_size_weight:    Optional[float] = None


class StatComparison(BaseModel):
    label:      str
    key:        str
    home_value: float
    away_value: float
    advantage:  str   # "home" | "away" | "even"

class ProjectedLine(BaseModel):
    label: str
    value: float
    type: str  # 'goals', 'corners', 'cards', 'handicap', 'btts'
    prob: Optional[float] = None # Probabilidad (0-100)


class CompareResponse(BaseModel):
    sport:           str
    home_name:       str
    away_name:       str
    h_lam:           Optional[float] = None
    a_lam:           Optional[float] = None
    h_corners_lam:   Optional[float] = None
    a_corners_lam:   Optional[float] = None
    h_cards_lam:     Optional[float] = None
    a_cards_lam:     Optional[float] = None
    h_fouls_lam:     Optional[float] = None
    a_fouls_lam:     Optional[float] = None
    h_offsides_lam:  Optional[float] = None
    a_offsides_lam:  Optional[float] = None
    most_probable_score: Optional[str] = None
    comparisons:     list[StatComparison]
    values:          list[ValueIndicator]
    projected_lines: list[ProjectedLine] = []
    summary:         str
    llm_analysis:    Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Shared helpers
# ───────────────────────────────────────────────────────────────
def _implied_probability(odds: float | None) -> float:
    if odds is None or odds <= 0: return 0.0
    return (1.0 / odds) * 100.0


def _stat_comparison(label: str, key: str, hv: float, av: float,
                     higher_is_better: bool = True) -> StatComparison:
    if abs(hv - av) < 0.01:
        adv = "even"
    elif higher_is_better:
        adv = "home" if hv > av else "away"
    else:
        adv = "home" if hv < av else "away"
    return StatComparison(key=key, label=label, home_value=hv, away_value=av, advantage=adv)


def _poisson_pmf(lam: float, k: int) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def _fair_probabilities_from_odds(*odds_list: float | None) -> list[float]:
    """
    Remueve el overround de un mercado completo usando el Power Method (Shin/Margin Proportional).
    Este método es superior a la normalización simple porque asigna proporcionalmente 
    más margen a las cuotas altas (underdogs), corrigiendo parcialmente el FLB.
    """
    valid_odds = [o for o in odds_list if o and o > 1.0]
    if not valid_odds:
        return [0.0] * len(odds_list)
    
    # Cálculo iterativo de k (Power Method)
    # SUM( (1/odds_i)^k ) = 1
    k = 1.0
    raw_probs = [1.0/o for o in valid_odds]
    
    # Búsqueda simple de k (Newton-Raphson simplificado o aproximación)
    for _ in range(10):
        current_sum = sum(p**k for p in raw_probs)
        if abs(current_sum - 1.0) < 0.0001:
            break
        k = k * (math.log(current_sum) / math.log(sum(raw_probs)) if sum(raw_probs) > 1 else 1)

    normalized = [(p**k) * 100.0 for p in raw_probs]
    
    # Mapear de vuelta a la lista original (preservando None)
    result = []
    idx = 0
    for o in odds_list:
        if o and o > 1.0:
            result.append(normalized[idx])
            idx += 1
        else:
            result.append(0.0)
    return result

def apply_calibration(raw_prob: float, odds: float, market_family: str) -> float:
    """
    Capa de Calibración Post-Hoc.
    Implementa una Beta Calibration heurística para corregir la sobreconfianza de Poisson.
    Penaliza cuotas altas y edges extremos que históricamente rinden mal.
    """
    p = raw_prob / 100.0
    
    # 1. Ajuste Heurístico de Curvatura (Beta Calibration Proxy)
    # p_cal = a * p^b / (a * p^b + (1-p)^b)
    # b < 1 aplana la curva (reduce sobreconfianza en los extremos)
    b = 0.85 
    if market_family in {"corners", "cards", "shots"}:
        b = 0.75 # Más incertidumbre en mercados secundarios
    elif market_family == "double_chance":
        # DC: calibración dinámica según nivel de probabilidad.
        # Alta prob (≥80%): favorito claro → el modelo es más fiable, menos squashing.
        # Prob media (70-80%): ajuste moderado.
        # Baja prob (<70%): mercado equilibrado (ej. DC 12 en partido parejo) → más incertidumbre.
        if p >= 0.80:
            b = 0.78   # DC de alta confianza
        elif p >= 0.70:
            b = 0.74   # DC moderado
        else:
            b = 0.70   # DC balanceado / mercado 12
    elif market_family == "dnb":
        b = 0.82   # DNB suele ser muy predecible
    
    calibrated = (p**b) / (p**b + (1-p)**b)
    
    # Shrinkage adaptativo hacia la media neutral (50%) para DC.
    # Cuanto mayor la incertidumbre (prob más baja), más nos acercamos al 50%.
    if market_family == "double_chance":
        if p >= 0.80:
            shrinkage = 0.07
        elif p >= 0.70:
            shrinkage = 0.09
        else:
            shrinkage = 0.12
        calibrated = (1.0 - shrinkage) * calibrated + shrinkage * 0.50
    elif market_family == "dnb":
        # Shrinkage mínimo para DNB
        calibrated = 0.95 * calibrated + 0.05 * 0.50
    
    # 2. Penalización por cuota (Favorite-Longshot Bias Correction)
    if odds > 3.0:
        calibrated *= 0.90 # Los underdogs suelen estar sobreestimados por el modelo
    elif odds > 2.0:
        calibrated *= 0.94
        
    return calibrated * 100.0

# Y en _value_indicator, pasar el overround del mercado:
def get_market_confidence_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals", "handicap", "double_chance"}:
        return "segmented"
    if family == "corners":
        return "hybrid"
    return "global"

def get_market_variance_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals"}:
        return "low"
    if family in {"handicap", "double_chance"}:
        return "medium"
    return "high"

def get_data_quality_score(selection: str, h: FootballTeamStats, a: FootballTeamStats) -> float:
    tier = get_market_confidence_tier(selection)
    if tier == "segmented":   base = 92.0 
    elif tier == "hybrid":    base = 70.0 # Restaurado a 70
    else:                     base = 45.0 # Restaurado a 45
    
    # Penalización por muestra pequeña (Fuerte regresión si hay poca data)
    min_m = min(h.matches_played, a.matches_played)
    if min_m < 8:
        sample_penalty = (10 - min_m) * 6.0 # Restaurado a 6.0
    elif min_m < 15:
        sample_penalty = (15 - min_m) * 2.0 # Restaurado a 2.0
    else:
        sample_penalty = 0
    
    # Penalización si el mercado es volátil y no hay xG/xGA suficiente
    family = _market_family(selection)
    if family in {"cards", "corners", "shots"}:
        if h.xg_per_game < 0.4 or a.xg_per_game < 0.4:
            base -= 8 # Restaurado a 8
        
    return max(5.0, base - sample_penalty)

def _calculate_display_score(v: ValueIndicator) -> float:
    """
    Calcula un score compuesto para visualización y ranking (0-100).
    Integra probabilidad, edge, calidad de datos y estabilidad.
    """
    if v.calibrated_prob is None or v.edge_ev is None:
        return 0.0
        
    # 1. Probabilidad Calibrada (w=0.4)
    # Una prob del 100% daría 40 puntos
    s_prob = v.calibrated_prob * 0.4
    
    # 2. Edge EV (w=0.3)
    # Un edge del 10% (0.10) daría 30 puntos (0.10 * 100 * 3)
    # Capamos el edge en 15% para el score
    edge_capped = max(0, min(0.15, v.edge_ev))
    s_edge = (edge_capped * 100) * 2.0 # w=0.3 aproximado
    
    # 3. Calidad de Datos (w=0.1)
    s_data = (v.data_quality_score or 50.0) * 0.1
    
    # 4. Estabilidad Histórica del Segmento (w=0.2)
    # Por ahora basado en la cuota (las cuotas bajas son más estables)
    s_stability = 70.0
    if v.odds:
        if v.odds < 1.60: s_stability = 90.0
        elif v.odds > 2.50: s_stability = 40.0
    
    final_score = s_prob + s_edge + s_data + (s_stability * 0.2)
    return round(min(100.0, final_score), 1)

def is_publishable_pick(v: ValueIndicator) -> bool:
    """
    Filtro profesional equilibrado. 
    Relajado para permitir visibilidad manteniendo la ventaja estadística.
    """
    # Prohibit BTTS and Double Chance
    family = _market_family(v.selection)
    if family in {"btts", "double_chance"}:
        return False

    # 1. Ventana de Cuotas (Gestión de Varianza)
    # Rango ampliado: 1.40 - 2.50
    if v.odds is None or v.odds < 1.4 or v.odds > 2.50:
        return False

    # 2. Umbral de Probabilidad Calibrada
    family = _market_family(v.selection)
    is_binary = family in {"result", "btts", "goals"}
    
    prob = v.calibrated_prob if v.calibrated_prob is not None else v.model_prob
    
    # 60% para binarios, 35% para volátiles
    if is_binary and prob < 60.0:
        return False
    if not is_binary and prob < 35.0:
        return False

    # 3. Ventana de Edge Utilizable (ROI Esperado)
    # Bajamos a 2% (0.02) que es el estándar de valor profesional
    if v.edge_ev < 0.02 or v.edge_ev > 0.20:
        return False

    # 4. Calidad de Datos
    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False
        
    return True



def score_pick_quality(v: ValueIndicator) -> int:
    """Rankea la calidad del pick de 0 a 100."""
    if not v.edge_ev: return 0
    
    # Componente principal: EV (60%)
    ev_score = min(v.edge_ev * 200, 60) # 30% EV -> 60 pts
    
    # Componente Probabilidad (20%)
    prob_score = (v.calibrated_prob or v.model_prob) / 5.0
    
    # Componente Calidad Datos (20%)
    dq_score = (v.data_quality_score or 50) / 5.0
    
    total = int(ev_score + prob_score + dq_score)
    return min(max(total, 0), 100)

def is_high_confidence_pick(v: ValueIndicator) -> bool:
    """
    Detecta picks con probabilidad muy alta (>=75%) que NO tienen edge matemático claro (<2%).
    Estos son los picks 'estrella' (⭐) que son muy probables pero no están bien pagados por la casa.
    """
    # Prohibit Double Chance and 1X2
    family = _market_family(v.selection)
    if family in {"double_chance", "result"}:
        return False

    # 1. Umbral de probabilidad alta (>=75%)
    if v.model_prob < 75.0:
        return False
    
    # 2. Restricción de Edge: Solo si NO tiene un edge claro (< 2%)
    # Si tiene un edge >= 2%, debería ser un pick de valor profesional o descartado.
    if v.edge_ev >= 0.02:
        return False
    
    # 3. Filtros básicos de calidad
    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False
        
    return True


def is_underdog_pick(v: ValueIndicator) -> bool:
    """
    Detecta picks underdog: cuotas altas (>2.50) con edge positivo y calidad de datos aceptable.
    Estos picks son mutuamente excluyentes con is_publishable (que requiere odds <= 2.50)
    y con is_high_confidence (que requiere edge < 5%).
    """
    # Prohibit corners
    family = _market_family(v.selection)
    if family == "corners":
        return False

    # 1. Cuota alta (por encima de la ventana profesional)
    if v.odds is None or v.odds <= 2.5 or v.odds > 5.80:
        return False
    
    # 2. Debe tener edge positivo real (>= 5%)
    if v.edge_ev < 0.05:
        return False
    
    # 3. Calidad de datos mínima
    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False
    
    return True



def _value_indicator(sel, odds, modelp, h=None, a=None, overround=100.0, push_p=0.0):
    if odds is None or odds <= 1.0:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1), push_prob=round(push_p, 1))
        
    # 1. Calibración Post-Hoc
    family = _market_family(sel)
    calibrated_p = apply_calibration(modelp, odds, family)
    
    # 2. Mercado y Vig
    raw_implied = (1.0 / odds) * 100.0
    # Nota: Aquí idealmente usaríamos implied_prob_no_vig si tuviéramos el mercado completo.
    # Por ahora aproximamos no-vig asumiendo un margin estándar del 5% si no viene especificado.
    margin_factor = (overround / 100.0) if overround > 100 else 1.05
    implied_no_vig = raw_implied / margin_factor
    
    # 3. Métricas de Valor
    edge_prob = calibrated_p - raw_implied
    ev = (calibrated_p / 100.0 * odds) - 1.0
    
    # Corrección por push/void: en mercados donde la apuesta puede anularse (e.g. Handicap Asiático entero),
    # el EV real debe ponderarse por la fracción de tiempo que el pick es efectivamente resuelto.
    # p_resolve = 1 - (push_p / 100), de modo que ev_efectivo = ev * p_resolve
    if push_p > 0:
        p_resolve = 1.0 - (push_p / 100.0)
        ev = ev * p_resolve
        edge_prob = edge_prob * p_resolve
    
    # 4. Kelly Criterion (Fractional Kelly 1/8 para máxima seguridad)
    kelly = (ev / (odds - 1)) * 0.125 if ev > 0 else 0
    
    # Metadatos de calidad
    conf_tier = get_market_confidence_tier(sel)
    var_tier = get_market_variance_tier(sel)
    dq_score = get_data_quality_score(sel, h, a) if h and a else None
    
    # 5. Sistema de Rating Basado en EV
    if   ev > 0.15:  rating = "🔥 STRONG VALUE"
    elif ev > 0.07:  rating = "✅ VALUE"
    elif ev > 0.02:  rating = "⚖️ MARGINAL"
    else:            rating = "❌ NO VALUE"
    
    v = ValueIndicator(
        selection=sel,
        odds=odds,
        model_prob=round(modelp, 1),
        calibrated_prob=round(calibrated_p, 1),
        implied_prob=round(raw_implied, 1),
        implied_prob_no_vig=round(implied_no_vig, 1),
        fair_odds=round(100.0 / calibrated_p, 2) if calibrated_p > 0 else None,
        edge=round(edge_prob, 1),
        edge_ev=round(ev, 3),
        push_prob=round(push_p, 1),
        is_value=ev > 0.03, # Umbral de explotación real
        rating=rating,
        data_quality_score=dq_score,
        market_confidence_tier=conf_tier,
        market_variance_tier=var_tier,
        kelly_fraction=round(kelly, 4),
        sample_size_weight=min(1.0, (h.matches_played + a.matches_played) / 30.0) if h and a else 0.5
    )
    
    v.is_publishable = is_publishable_pick(v)
    v.quality_score = score_pick_quality(v)
    v.display_score = _calculate_display_score(v)
    v.is_high_confidence = is_high_confidence_pick(v)
    v.is_underdog = is_underdog_pick(v)
    return v


# ───────────────────────────────────────────────────────────────
# Poisson engine (Football)
# ───────────────────────────────────────────────────────────────

def _compute_team_goals_lambda(
    attacker: FootballTeamStats,
    defender: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_team_goals = league.avg_goals_per_game / 2.0

    # ── 1. Determinar Datos Segmentados por Localía ──
    # Los datos ya vienen pre-segmentados desde el frontend:
    #   - El equipo local (attacker cuando is_home=True) entrega sus stats de LOCAL
    #   - El equipo visitante (attacker cuando is_home=False) entrega sus stats de VISITA
    # Por lo tanto, goals_per_game ya es la tasa correcta para cada condición.
    # matches_home / matches_away indican el tamaño de muestra segmentado.
    if is_home:
        # Atacante juega de local → sus goals_per_game son sus goles de local
        att_n = max(attacker.matches_home, 1)
        prior_att_xg = attacker.xg_per_game
        actual_att_g = attacker.goals_per_game

        # Defensor juega de visita → su concedidos son los que recibe de visita
        def_n = max(defender.matches_away, 1)
        prior_def_xga = defender.xga_per_game
        actual_def_g = defender.goals_conceded_per_game
    else:
        # Atacante juega de visita → sus goals_per_game son sus goles de visita
        att_n = max(attacker.matches_away, 1)
        prior_att_xg = attacker.xg_per_game
        actual_att_g = attacker.goals_per_game

        # Defensor juega de local → su concedidos son los que recibe de local
        def_n = max(defender.matches_home, 1)
        prior_def_xga = defender.xga_per_game
        actual_def_g = defender.goals_conceded_per_game

    # beta_prior representa cuántos "partidos de peso" le damos a la estadística subyacente (xG / xGA)
    # Aumentado a 5.0 para ser más conservador/robusto ante varianza
    beta_prior = 5.0 

    # ── 2. Fuerza de Ataque Bayesiana (Poisson-Gamma) ──
    S_att = actual_att_g * att_n
    alpha_att = prior_att_xg * beta_prior
    
    att_g_bayesian = (alpha_att + S_att) / (beta_prior + att_n)
    att_str = att_g_bayesian / max(avg_team_goals, 0.1)

    # ── 3. Debilidad Defensiva Rival Bayesiana ──
    S_def = actual_def_g * def_n
    alpha_def = prior_def_xga * beta_prior
    
    def_g_bayesian = (alpha_def + S_def) / (beta_prior + def_n)
    def_weakness = def_g_bayesian / max(avg_team_goals, 0.1)

    # ── 4. Lambda Base ──
    lam_base = att_str * def_weakness * avg_team_goals

    # ── 5. Señales Tácticas Adicionales (Moderadas) ──
    # Moderamos el impacto de las Big Chances para que no inflen demasiado el lambda
    bc_signal = attacker.big_chances_per_game / max(attacker.big_chances_missed_per_game + 0.5, 0.5)
    tactical_mult = 1.0 + (min(bc_signal, 2.0) - 1.0) * 0.08  # Reducido de 0.12 a 0.08
    lam_adjusted = lam_base * tactical_mult

    # ── 6. Shrinkage Global a la Liga ──
    # Actúa como seguro de "Regresión a la Media" cuando la muestra segmentada es muy pequeña
    total_n = min(att_n, def_n)
    prior_league_n = max(1.0, 4.0 - (total_n / 8.0)) # Prior más fuerte que antes
    shrink_w = prior_league_n / (prior_league_n + total_n)
    
    lam_final = lam_adjusted * (1.0 - shrink_w) + avg_team_goals * shrink_w

    return max(lam_final, 0.10)



def _compute_team_corners_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    """
    Calcula corners esperados por equipo.
    Señales (por orden de precisión según literatura):
    - Cross-completion ratio (crosses_per_game / crosses_total_per_game):
        mejor predictor individual de corner-generation rate.
    - Corners históricos propios (base).
    - Corners concedidos del rival (propensión defensiva).
    - Shrinkage bayesiana por tamaño de muestra segmentado.
    """
    avg_team_corners = league.avg_corners_per_game / 2.0

    # ── 1. Señal de centros: ratio de completud (crosses_per_game / crosses_total)
    # Cuanto más alta la tasa de centros completados, más despejes cerca de línea
    # de fondo → más corners generados. Proxy validado en la literatura.
    cross_total = max(team.crosses_total_per_game, 0.1)
    cross_ratio = team.crosses_per_game / cross_total   # 0.0 – 1.0
    # Convertimos el ratio en un multiplicador centrado en 1.0:
    # ratio promedio de referencia empírica ~0.45 (45% de centros son completados)
    CROSS_REF   = 0.45
    cross_mult  = 1.0 + 1.20 * (cross_ratio - CROSS_REF)  # ±1.2 * desviación
    cross_mult  = max(0.50, min(1.60, cross_mult))         # techo razonable

    # ── 2. Base de generación: corners históricos ajustados por cross_mult
    gen_base = team.corners_per_game * cross_mult

    # ── 3. Capacidad del rival de conceder corners (debilidad defensiva)
    opp_def_weakness = opponent.corners_conceded_per_game / max(avg_team_corners, 1.0)

    # ── 4. Lambda base cruzada (generación × debilidad rival)
    lam = gen_base * opp_def_weakness

    # ── 5. Shrinkage bayesiana segmentada por localía
    m_count = team.matches_home if is_home else team.matches_away
    prior_n = 2.0
    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_corners * shrink_w

    return max(lam, 0.5)


def _compute_team_cards_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    # Usamos 15 partidos de "prior" para evitar que 2 rojas en 3 fechas rompan el modelo
    actual_matches = max(team.matches_played, 1)
    
    # 1. Promedio base del equipo
    # Una roja suele valer 2 amarillas en los mercados de casas de apuestas
    red_card_weight = 2.0 
    team_reds_per_game = (team.red_cards_total / actual_matches) * red_card_weight
    own_cards_avg = team.yellow_cards_per_game + team_reds_per_game

    # 2. Ajuste por agresividad (Faltas)
    foul_deviation = (team.fouls_per_game - 12.5) / 12.5
    foul_modifier = 1.0 + (foul_deviation * 0.15)

    # 3. Ajuste por inducción del rival (Duelos/Posesión)
    poss_deviation = (opponent.possession_pct - 50.0) / 50.0
    duel_deviation = (opponent.ground_duels_won_per_game - 10.0) / 10.0
    
    rival_modifier = 1.0 + (poss_deviation * 0.05) + (duel_deviation * 0.10)
    
    total_modifier = max(0.75, min(1.25, foul_modifier * rival_modifier))
    lam = own_cards_avg * total_modifier

    # 4. Integración del Árbitro (The "Sheriff" Factor)
    # Si tenemos data del árbitro, la usamos para moderar/ajustar la expectativa
    # Determinamos la media de tarjetas de la liga (usando amarillas y rojas separadas si están presentes)
    if league.avg_yellow_cards_per_game > 0 and league.avg_red_cards_per_game > 0:
        league_cards_avg = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0)
    else:
        # Fallback a como se hace hasta ahora (usando avg_cards_per_game)
        league_cards_avg = league.avg_cards_per_game

    if league.referee_avg_yellow > 0:
        # El árbitro es una señal de alta calidad pero externa a los equipos
        ref_baseline = league.referee_avg_yellow + (league.referee_avg_red * 2.0)
        
        # Desviación del árbitro frente a la media de la liga
        ref_dev_ratio = ref_baseline / max(league_cards_avg, 1.0)
        
        # El árbitro influye un 50% en el ajuste (shrinkage hacia 1.0)
        # Esto evita que un árbitro muy 'tarjetero' dispare el lambda si los equipos son limpios
        ref_modifier = 1.0 + (ref_dev_ratio - 1.0) * 0.50
        lam *= ref_modifier

    # 5. Shrinkage (Regresión a la media)
    avg_team_cards = league_cards_avg / 2.0
    prior_n = 5.0
    shrink_w = prior_n / (prior_n + actual_matches)
    
    lam = lam * (1.0 - shrink_w) + avg_team_cards * shrink_w

    return max(lam, 0.5)


def _compute_team_shots_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_team_shots = league.avg_shots_per_game / 2.0
    gen_str = team.shots_per_game
    opp_def_factor = max((100.0 - opponent.possession_pct) / 50.0, 0.5)
    
    lam = gen_str * opp_def_factor
    m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_shots * shrink_w
    return max(lam, 1.0)


def _compute_team_shots_target_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_team_sot = league.avg_shots_target_per_game / 2.0
    gen_str = team.shots_on_target_per_game
    opp_def_factor = max((100.0 - opponent.possession_pct) / 50.0, 0.5)
    
    lam = gen_str * opp_def_factor
    m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_sot * shrink_w
    return max(lam, 0.5)


def split_asian_line(line: float) -> list[float]:
    """Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)."""
    if abs(line * 4 % 2) != 0: # Es .25 o .75
        return [line - 0.25, line + 0.25]
    return [line]

def settle_handicap_outcome(home_goals: int, away_goals: int, line: float) -> str:
    """Liquida una línea simple de handicap."""
    margin = home_goals - away_goals + line
    if margin > 0: return "win"
    if margin < 0: return "loss"
    return "push"

def _compute_asian_handicap_probs(
    h_lam: float,
    a_lam: float,
    line: float,
    max_goals: int = 10
) -> dict[str, float]:
    """
    Calcula probabilidades reales de Asian Handicap usando la matriz de scores.
    Soporta líneas enteras, medias y cuartos.
    """
    matrix, _ = _dc_score_matrix(h_lam, a_lam, max_goals=max_goals)
    lines = split_asian_line(line)
    
    p_w, p_hw, p_p, p_hl, p_l = 0.0, 0.0, 0.0, 0.0, 0.0
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = matrix[i][j]
            res = [settle_handicap_outcome(i, j, l) for l in lines]
            
            if len(res) == 1:
                if res[0] == "win": p_w += p
                elif res[0] == "loss": p_l += p
                else: p_p += p
            else:
                # Caso split (.25 / .75)
                if res[0] == "win" and res[1] == "win": p_w += p
                elif (res[0] == "win" and res[1] == "push") or (res[0] == "push" and res[1] == "win"): p_hw += p
                elif res[0] == "push" and res[1] == "push": p_p += p
                elif (res[0] == "loss" and res[1] == "push") or (res[0] == "push" and res[1] == "loss"): p_hl += p
                elif res[0] == "loss" and res[1] == "loss": p_l += p
                
    return {
        "win": p_w * 100.0,
        "half_win": p_hw * 100.0,
        "push": p_p * 100.0,
        "half_loss": p_hl * 100.0,
        "loss": p_l * 100.0
    }


# ───────────────────────────────────────────────────────────────
# Dixon-Coles helpers
# ───────────────────────────────────────────────────────────────

def _dc_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """
    Corrección Dixon-Coles para scorelines bajos:
    afecta 0-0, 0-1, 1-0 y 1-1.
    """
    if x == 0 and y == 0:
        return 1.0 - (lam * mu * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lam * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def _default_dc_rho(h_lam: float, a_lam: float) -> float:
    """
    Sin entrenamiento histórico, usamos una heurística conservadora
    centrada en valores típicos observados para DC (~ -0.13 en ejemplos publicados).
    Cuanto menor el total esperado de goles, más relevante suele ser la corrección.

    Valores ajustados para favorecer victorias claras y reducir empates excesivos.
    """
    total = h_lam + a_lam
    base = -0.13  # Valor estándar Dixon & Coles 1997
    
    # Ligas bajas en goles = más correlación negativa
    if total < 2.0: return max(-0.18, base - 0.03)
    if total > 3.0: return min(-0.08, base + 0.03)
    return base


def _dc_score_matrix(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> tuple[list[list[float]], float]:
    """
    Construye matriz conjunta P(Home=i, Away=j) usando Poisson marginal
    + corrección Dixon-Coles en marcadores bajos.
    """
    rho_used = _default_dc_rho(h_lam, a_lam) if rho is None else rho

    home_probs = [_poisson_pmf(h_lam, i) for i in range(max_goals + 1)]
    away_probs = [_poisson_pmf(a_lam, j) for j in range(max_goals + 1)]

    matrix: list[list[float]] = []
    for i in range(max_goals + 1):
        row = []
        for j in range(max_goals + 1):
            p = home_probs[i] * away_probs[j]
            p *= _dc_tau(i, j, h_lam, a_lam, rho_used)
            row.append(max(p, 0.0))
        matrix.append(row)

    total = sum(sum(row) for row in matrix)
    if total <= 0:
        # Fallback ultra defensivo
        uniform = 1.0 / ((max_goals + 1) ** 2)
        matrix = [[uniform for _ in range(max_goals + 1)] for _ in range(max_goals + 1)]
        return matrix, rho_used

    matrix = [[p / total for p in row] for row in matrix]
    return matrix, rho_used


def _sum_score_matrix_1x2_and_markets(
    matrix: list[list[float]]
) -> dict[str, float]:
    h_win = 0.0
    draw = 0.0
    a_win = 0.0
    over_25 = 0.0
    under_25 = 0.0
    btts_yes = 0.0

    max_goals = len(matrix) - 1

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = matrix[i][j]

            if i > j:
                h_win += p
            elif i == j:
                draw += p
            else:
                a_win += p

            if i + j >= 3:
                over_25 += p
            else:
                under_25 += p

            if i >= 1 and j >= 1:
                btts_yes += p

    btts_no = max(0.0, 1.0 - btts_yes)

    return {
        "home_win_pct": h_win * 100.0,
        "draw_pct": draw * 100.0,
        "away_win_pct": a_win * 100.0,
        "over_25_pct": over_25 * 100.0,
        "under_25_pct": under_25 * 100.0,
        "btts_yes_pct": btts_yes * 100.0,
        "btts_no_pct": btts_no * 100.0,
    }


def _top_exact_scores(
    matrix: list[list[float]],
    top_n: int = 5,
) -> list[dict[str, float | str]]:
    picks: list[dict[str, float | str]] = []

    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            picks.append({
                "score": f"{i}-{j}",
                "probability_pct": round(p * 100.0, 2)
            })

    picks.sort(key=lambda x: x["probability_pct"], reverse=True)
    return picks[:top_n]


def _dc_match_probs(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> dict[str, Any]:
    matrix, rho_used = _dc_score_matrix(
        h_lam=h_lam,
        a_lam=a_lam,
        max_goals=max_goals,
        rho=rho,
    )

    markets = _sum_score_matrix_1x2_and_markets(matrix)
    top_scores = _top_exact_scores(matrix, top_n=5)

    return {
        **markets,
        "rho_used": round(rho_used, 4),
        "home_lambda": round(h_lam, 4),
        "away_lambda": round(a_lam, 4),
        "top_exact_scores": top_scores,
        "score_matrix": matrix,
    }


def _compute_corners_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    """
    Calcula el lambda total de corners del partido como suma de los lambdas
    por equipo (via _compute_team_corners_lambda).

    Se abandona el proxy de posesión (débil predictor) en favor del
    cross-completion ratio implementado en _compute_team_corners_lambda,
    que la literatura identifica como predictor principal de corner-events.
    """
    # Usamos is_home=True/False para aprovechar la segmentación de muestra
    h_lam_c = _compute_team_corners_lambda(h, a, league, is_home=True)
    a_lam_c = _compute_team_corners_lambda(a, h, league, is_home=False)
    lam_corners = h_lam_c + a_lam_c

    # Fallback de seguridad al promedio de la liga si la data está mal
    if lam_corners < 2.0:
        lam_corners = league.avg_corners_per_game
    return lam_corners


def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    """
    Calcula el lambda total de tarjetas del partido como suma de los lambdas
    por equipo, integrando la agresividad de ambos y el factor del árbitro.
    """
    h_lam_cards = _compute_team_cards_lambda(h, a, league, is_home=True)
    a_lam_cards = _compute_team_cards_lambda(a, h, league, is_home=False)
    
    lam_cards = h_lam_cards + a_lam_cards
    
    # Fallback de seguridad al promedio de la liga
    if lam_cards < 1.0: 
        lam_cards = league.avg_cards_per_game
        
    return lam_cards


def _compute_shots_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    h_s_exp = _compute_team_shots_lambda(h, a, league, is_home=True)
    a_s_exp = _compute_team_shots_lambda(a, h, league, is_home=False)
    lam_shots = h_s_exp + a_s_exp
    return max(lam_shots, league.avg_shots_per_game * 0.5)


def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    h_st_exp = _compute_team_shots_target_lambda(h, a, league, is_home=True)
    a_st_exp = _compute_team_shots_target_lambda(a, h, league, is_home=False)
    lam_shots_target = h_st_exp + a_st_exp
    return max(lam_shots_target, league.avg_shots_target_per_game * 0.5)


def _compute_team_fouls_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    avg_team_fouls = avg_league_fouls / 2.0
    gen_str = team.fouls_per_game if team.fouls_per_game > 0 else avg_team_fouls
    opp_possession = opponent.possession_pct if opponent.possession_pct > 0 else 50.0
    opp_factor = max(opp_possession / 50.0, 0.5)
    
    lam = gen_str * opp_factor
    m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_fouls * shrink_w
    return max(lam, 1.0)


def _compute_fouls_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    h_f_exp = _compute_team_fouls_lambda(h, a, league, is_home=True)
    a_f_exp = _compute_team_fouls_lambda(a, h, league, is_home=False)
    lam_fouls = h_f_exp + a_f_exp
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    return max(lam_fouls, avg_league_fouls * 0.5)


def _compute_team_offsides_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    avg_team_offsides = avg_league_offsides / 2.0
    gen_str = team.offside_per_game if team.offside_per_game > 0 else avg_team_offsides
    team_possession = team.possession_pct if team.possession_pct > 0 else 50.0
    pos_factor = max(team_possession / 50.0, 0.5)
    
    lam = gen_str * pos_factor
    m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_offsides * shrink_w
    return max(lam, 0.1)


def _compute_offsides_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    h_o_exp = _compute_team_offsides_lambda(h, a, league, is_home=True)
    a_o_exp = _compute_team_offsides_lambda(a, h, league, is_home=False)
    lam_offsides = h_o_exp + a_o_exp
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    return max(lam_offsides, avg_league_offsides * 0.5)


def _poisson_over_under(lam: float, line: float, max_k: int = 40) -> tuple[float, float, float]:
    """
    Devuelve (p_over, p_push, p_under) en porcentaje.
    Maneja líneas asiáticas (.25, .75) promediando las líneas adyacentes.
    NO redistribuye el push; lo devuelve explícitamente.
    """
    def _get_single_line_probs(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        for k in range(max_k + 1):
            # Usamos una implementación local de PMF para evitar dependencias circulares si las hubiera
            p = (lam ** k * math.exp(-lam)) / math.factorial(k)
            if k < l: p_u += p
            elif k > l: p_o += p
            else: p_p += p
        return p_o, p_p, p_u

    lines = split_asian_line(line)
    results = [_get_single_line_probs(l) for l in lines]
    
    avg_over = sum(r[0] for r in results) / len(results)
    avg_push = sum(r[1] for r in results) / len(results)
    avg_under = sum(r[2] for r in results) / len(results)
    
    return avg_over * 100.0, avg_push * 100.0, avg_under * 100.0


import os
import asyncio

async def _call_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "Para ver el análisis con IA, configura OPENROUTER_API_KEY en tu .env"

    primary_model = os.environ.get("OPENROUTER_MODEL")
    if not primary_model:
        return "Para generar el análisis con IA, configura OPENROUTER_MODEL en tu .env"

    fallback_model = os.environ.get("OPENROUTER_FALLBACK_MODEL")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    retry_delays = [1.5, 3, 5]
    last_error = None

    def _extract_content(response) -> str | None:
        if response is None:
            return None

        err = getattr(response, "error", None)
        if err:
            return None

        choices = getattr(response, "choices", None)
        if not choices:
            return None

        message = getattr(choices[0], "message", None)
        if message is None:
            return None

        content = getattr(message, "content", None)

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("text"):
                        text_parts.append(part["text"])
                else:
                    txt = getattr(part, "text", None)
                    if txt:
                        text_parts.append(txt)

            joined = "\n".join(x.strip() for x in text_parts if x and str(x).strip())
            if joined:
                return joined

        return None

    def _response_error_info(response):
        err = getattr(response, "error", None)
        if isinstance(err, dict):
            return str(err.get("code", "N/A")), str(err.get("message", "Error desconocido"))
        if err:
            return "N/A", str(err)
        return None, None

    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            extra_body = {}
            if fallback_model and fallback_model != primary_model:
                extra_body["models"] = [fallback_model]

            r = await client.chat.completions.create(
                model=primary_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5000,
                temperature=0.15,
                extra_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "football-analysis",
                },
                extra_body=extra_body if extra_body else None,
            )

            content = _extract_content(r)
            if content:
                return content

            code, msg = _response_error_info(r)
            if code:
                last_error = f"Error del modelo ({code}): {msg}"
            else:
                last_error = "⚠️ El modelo no devolvió contenido válido."

        except Exception as e:
            msg = str(e)
            last_error = msg

            retryable_markers = [
                "429",
                "500",
                "502",
                "503",
                "504",
                "524",
                "529",
                "rate limit",
                "timeout",
                "temporarily unavailable",
                "internal server error",
                "bad gateway",
                "service unavailable",
            ]

            if not any(marker.lower() in msg.lower() for marker in retryable_markers):
                return f"Error al generar análisis IA: {e}"

        if attempt < len(retry_delays):
            await asyncio.sleep(delay)

    return last_error or "⚠️ No se pudo generar el análisis con IA tras varios intentos."


def _safe_num(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


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


def _market_family(text: str) -> str:
    s = _normalize_text(text)

    if any(k in s for k in ["btts", "ambos marcan", "both teams to score"]):
        return "btts"
    if any(k in s for k in ["corner", "corners", "córner", "córners"]):
        return "corners"
    if any(k in s for k in ["tarjeta", "tarjetas", "cards", "yellow cards", "amarillas"]):
        return "cards"
    if any(k in s for k in ["foul", "fouls", "faltas"]):
        return "fouls"
    if any(k in s for k in ["shot", "shots", "tiros", "remates"]):
        return "shots"
    if any(k in s for k in ["goal", "goals", "goles"]):
        return "goals"
    if any(k in s for k in ["handicap", "hándicap", "asian"]):
        return "handicap"

    if any(k in s for k in ["double chance", "doble oportunidad", "1x", "x2", "12"]):
        return "double_chance"
    if any(k in s for k in ["dnb", "draw no bet", "sin empate"]):
        return "dnb"
    if any(k in s for k in ["moneyline", "ml", "1x2", "ganador", "local", "visitante", "empate"]):
        return "result"

    return "generic"


def _market_side(text: str) -> str:
    s = _normalize_text(text)

    if any(k in s for k in ["over", "más de", "mas de"]):
        return "over"
    if any(k in s for k in ["under", "menos de"]):
        return "under"
    if any(k in s for k in ["yes", "sí", "si"]):
        return "yes"
    if " no " in f" {s} " or s.endswith(" no"):
        return "no"
    if any(k in s for k in ["local", "home"]):
        return "home"
    if any(k in s for k in ["visitante", "away"]):
        return "away"
    if "empate" in s or "draw" in s:
        return "draw"

    return "none"


def _market_risk_weight(selection: str) -> int:
    family = _market_family(selection)

    if family in {"result", "handicap"}:
        return -14
    if family == "double_chance":
        return -7
    if family == "btts":
        return -10
    if family in {"corners", "cards", "shots", "fouls"}:
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


def _team_strength_score(team) -> float:
    goals = _safe_num(team.goals_per_game)
    xg = _safe_num(team.xg_per_game)
    xga = _safe_num(team.xga_per_game)
    big = _safe_num(team.big_chances_per_game)
    sot = _safe_num(team.shots_on_target_per_game)
    poss = _safe_num(team.possession_pct)
    conceded = _safe_num(team.goals_conceded_per_game)

    return (
        goals * 10
        + xg * 12
        + big * 8
        + sot * 6
        + poss * 0.12
        - conceded * 8
        - xga * 7
    )


def _support_over_goals(line: float, h, a, proj: list) -> tuple[float, float]:
    h_g = _safe_num(h.goals_per_game)
    a_g = _safe_num(a.goals_per_game)
    h_c = _safe_num(h.goals_conceded_per_game)
    a_c = _safe_num(a.goals_conceded_per_game)
    h_xg = _safe_num(h.xg_per_game)
    a_xg = _safe_num(a.xg_per_game)
    h_xga = _safe_num(h.xga_per_game)
    a_xga = _safe_num(a.xga_per_game)
    h_big = _safe_num(h.big_chances_per_game)
    a_big = _safe_num(a.big_chances_per_game)
    h_sot = _safe_num(h.shots_on_target_per_game)
    a_sot = _safe_num(a.shots_on_target_per_game)

    base_total = (h_g + a_g + h_c + a_c + h_xg + a_xg + h_xga + a_xga) / 4
    attack_bonus = (h_big + a_big) * 1.8 + (h_sot + a_sot) * 0.9
    stat = 56 + (base_total - line) * 18 + attack_bonus
    stat = _clip_0_100(stat)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["goles"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["goals"])

    proj_score = 55.0
    if pval is not None:
        margin = pval - line
        proj_score += margin * 20
    if pprob is not None:
        proj_score += (pprob - 50) * 0.5

    return stat, _clip_0_100(proj_score)


def _support_under_goals(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_over, proj_over = _support_over_goals(line, h, a, proj)
    return _clip_0_100(110 - stat_over), _clip_0_100(110 - proj_over)


def _support_btts_yes(h, a, proj: list) -> tuple[float, float]:
    h_g = _safe_num(h.goals_per_game)
    a_g = _safe_num(a.goals_per_game)
    h_xg = _safe_num(h.xg_per_game)
    a_xg = _safe_num(a.xg_per_game)
    h_c = _safe_num(h.goals_conceded_per_game)
    a_c = _safe_num(a.goals_conceded_per_game)
    h_xga = _safe_num(h.xga_per_game)
    a_xga = _safe_num(a.xga_per_game)

    # Clean sheets segmentados por localía
    h_cs_rate = _safe_num(h.clean_sheets_home) / max(1, _safe_num(h.matches_home, 1))
    a_cs_rate = _safe_num(a.clean_sheets_away) / max(1, _safe_num(a.matches_away, 1))

    # Capacidad de ataque
    h_attack = (h_g + h_xg) / 2.0
    a_attack = (a_g + a_xg) / 2.0
    # Debilidad defensiva rival
    h_def_weakness = (a_c + a_xga) / 2.0
    a_def_weakness = (h_c + h_xga) / 2.0

    # Score por equipo: ataque propio + defensa rival - clean sheets
    h_score = h_attack * 8.0 + h_def_weakness * 5.0 - h_cs_rate * 20.0
    a_score = a_attack * 8.0 + a_def_weakness * 5.0 - a_cs_rate * 20.0

    # BTTS requiere que ambos anoten
    stat = 45.0 + (h_score + a_score) / 2.0
    stat = _clip_0_100(stat)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["btts"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["ambos", "marcan"])

    proj_score = 55.0
    if pprob is not None:
        proj_score = pprob

    return stat, _clip_0_100(proj_score)


def _support_btts_no(h, a, proj: list) -> tuple[float, float]:
    stat_yes, proj_yes = _support_btts_yes(h, a, proj)
    return _clip_0_100(110 - stat_yes), _clip_0_100(110 - proj_yes)


def _support_home_win(h, a, proj: list) -> tuple[float, float]:
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

    return stat, _clip_0_100(proj_score)


def _support_away_win(h, a, proj: list) -> tuple[float, float]:
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


def _support_draw(h, a, proj: list) -> tuple[float, float]:
    diff = abs(_team_strength_score(h) - _team_strength_score(a))
    stat = _clip_0_100(62 - diff * 0.7)

    pval, pprob, label = _projected_value_by_keywords(proj, ["empate"])
    if pval is None:
        pval, pprob, label = _projected_value_by_keywords(proj, ["draw"])

    proj_score = 50.0
    if pprob is not None:
        proj_score += (pprob - 50) * 0.7

    return stat, _clip_0_100(proj_score)


def _support_under_shots(line: float, h, a, proj: list) -> tuple[float, float]:
    total_shots = _safe_num(h.shots_per_game) + _safe_num(a.shots_per_game)
    total_sot = _safe_num(h.shots_on_target_per_game) + _safe_num(a.shots_on_target_per_game)
    tempo = _safe_num(h.possession_pct) + _safe_num(a.possession_pct)
    base = total_shots + total_sot * 0.35 + max(0, (tempo - 100)) * 0.03

    stat = _clip_0_100(58 + (line - base) * 7)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["tiros"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["shots"])

    proj_score = 55.0
    if pval is not None:
        proj_score += (line - pval) * 9
    if pprob is not None:
        proj_score += (pprob - 50) * 0.45

    return stat, _clip_0_100(proj_score)


def _support_over_shots(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_u, proj_u = _support_under_shots(line, h, a, proj)
    return _clip_0_100(110 - stat_u), _clip_0_100(110 - proj_u)


def _support_over_cards(line: float, h, a, proj: list) -> tuple[float, float]:
    total_y = _safe_num(h.yellow_cards_per_game) + _safe_num(a.yellow_cards_per_game)
    total_f = _safe_num(h.fouls_per_game) + _safe_num(a.fouls_per_game)
    # Una roja equivale a 2 amarillas en mercados reales de amonestaciones
    total_r = (_safe_num(h.red_cards_total) + _safe_num(a.red_cards_total)) / max(
        _safe_num(h.matches_played, 1) + _safe_num(a.matches_played, 1), 2
    )
    base = total_y + total_f * 0.10 + total_r * 2.0

    lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["tarjetas totales"])
    if lam_val is None:
         lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["tarjetas"])

    if lam_val is not None:
        stat = _clip_0_100(58 + (lam_val - line) * 12)
    else:
        stat = _clip_0_100(58 + (base - line) * 11)

    proj_score = 55.0
    if lam_prob is not None:
        proj_score = lam_prob
    elif lam_val is not None:
        proj_score = _clip_0_100(55 + (lam_val - line) * 10)

    return stat, _clip_0_100(proj_score)


def _support_under_cards(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_o, proj_o = _support_over_cards(line, h, a, proj)
    return _clip_0_100(110 - stat_o), _clip_0_100(110 - proj_o)


def _support_over_corners(line: float, h, a, proj: list) -> tuple[float, float]:
    lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["corners totales"])
    if lam_val is None:
        lam_val, lam_prob, _ = _projected_value_by_keywords(proj, ["corners"])

    if lam_val is not None:
        stat = _clip_0_100(58 + (lam_val - line) * 12)
    else:
        base = (
            _safe_num(h.corners_per_game) + _safe_num(a.corners_per_game) +
            _safe_num(h.corners_conceded_per_game) + _safe_num(a.corners_conceded_per_game)
        ) / 2
        stat = _clip_0_100(57 + (base - line) * 10)

    # Ajuste por efectividad en centros (cross completion ratio)
    h_cross_ratio = _safe_num(h.crosses_per_game) / max(_safe_num(h.crosses_total_per_game, 20), 1)
    a_cross_ratio = _safe_num(a.crosses_per_game) / max(_safe_num(a.crosses_total_per_game, 20), 1)
    cross_signal = (h_cross_ratio + a_cross_ratio) / 2.0
    stat += (cross_signal - 0.45) * 8
    stat = _clip_0_100(stat)

    proj_score = 55.0
    if lam_prob is not None:
        proj_score = lam_prob
    elif lam_val is not None:
        proj_score = _clip_0_100(55 + (lam_val - line) * 10)

    return stat, _clip_0_100(proj_score)


def _support_under_corners(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_o, proj_o = _support_over_corners(line, h, a, proj)
    return _clip_0_100(110 - stat_o), _clip_0_100(110 - proj_o)


def _dc_component_weights(h, a) -> tuple[float, float, float]:
    """
    Estima pesos relativos (h_weight, d_weight, a_weight) para los componentes
    del Doble Oportunidad basándose en la fuerza relativa de los equipos.
    Los tres pesos suman 1.0 y se usan para ponderar el soporte de cada componente
    en lugar del max() previo, que inflaba artificialmente el score.
    """
    h_str = max(0.1, _team_strength_score(h) + 60.0)  # desplazado al dominio positivo
    a_str = max(0.1, _team_strength_score(a) + 60.0)
    total_str = h_str + a_str
    h_w_base = h_str / total_str
    a_w_base = a_str / total_str

    # El peso del empate crece cuando los equipos son más equilibrados
    balance = 1.0 - abs(h_w_base - a_w_base)  # 0=muy desequilibrado, 1=perfectamente igual
    d_w = 0.20 + balance * 0.15  # rango: 20% (desequilibrado) → 35% (equilibrado)

    # Redistribuir el peso restante proporcionalmente
    rem = 1.0 - d_w
    h_w = rem * h_w_base
    a_w = rem * a_w_base
    return h_w, d_w, a_w


def _explicit_market_support(selection: str, h, a, proj: list) -> tuple[float, float]:
    s = _normalize_text(selection)
    line = _extract_line_number(selection)
    family = _market_family(selection)
    side = _market_side(selection)

    if family == "goals" and side == "over" and line is not None:
        return _support_over_goals(line, h, a, proj)
    if family == "goals" and side == "under" and line is not None:
        return _support_under_goals(line, h, a, proj)

    if family == "btts" and side == "yes":
        return _support_btts_yes(h, a, proj)
    if family == "btts" and side == "no":
        return _support_btts_no(h, a, proj)

    if family == "result" and side == "home":
        return _support_home_win(h, a, proj)
    if family == "result" and side == "away":
        return _support_away_win(h, a, proj)
    if family == "result" and side == "draw":
        return _support_draw(h, a, proj)

    if family == "shots" and side == "under" and line is not None:
        return _support_under_shots(line, h, a, proj)
    if family == "shots" and side == "over" and line is not None:
        return _support_over_shots(line, h, a, proj)

    if family == "cards" and side == "over" and line is not None:
        return _support_over_cards(line, h, a, proj)
    if family == "cards" and side == "under" and line is not None:
        return _support_under_cards(line, h, a, proj)

    if family == "corners" and side == "over" and line is not None:
        return _support_over_corners(line, h, a, proj)
    if family == "corners" and side == "under" and line is not None:
        return _support_under_corners(line, h, a, proj)

    # Double Chance — combinación ponderada por fuerza relativa de los equipos.
    # El max() anterior inflaba artificialmente el soporte ignorando la componente débil.
    if family == "double_chance":
        h_w, d_w, a_w = _dc_component_weights(h, a)
        stat_h, proj_h = _support_home_win(h, a, proj)
        stat_d, proj_d = _support_draw(h, a, proj)
        stat_a, proj_a = _support_away_win(h, a, proj)

        if "1x" in s:
            # Normalizar pesos al espacio 1X (local + empate)
            norm = h_w + d_w
            w_h, w_d = h_w / norm, d_w / norm
            return (
                _clip_0_100(w_h * stat_h + w_d * stat_d),
                _clip_0_100(w_h * proj_h + w_d * proj_d),
            )
        if "x2" in s:
            # Normalizar al espacio X2 (visitante + empate)
            norm = a_w + d_w
            w_a, w_d2 = a_w / norm, d_w / norm
            return (
                _clip_0_100(w_a * stat_a + w_d2 * stat_d),
                _clip_0_100(w_a * proj_a + w_d2 * proj_d),
            )
        if "12" in s:
            # Normalizar al espacio 12 (local + visitante, excluye empate)
            norm = h_w + a_w
            w_h2, w_a2 = h_w / norm, a_w / norm
            return (
                _clip_0_100(w_h2 * stat_h + w_a2 * stat_a),
                _clip_0_100(w_h2 * proj_h + w_a2 * proj_a),
            )

    # DNB (Draw No Bet / Sin Empate)
    if family == "dnb":
        if "local" in s or "home" in s or "1" in s:
            stat_h, proj_h = _support_home_win(h, a, proj)
            return _clip_0_100(stat_h * 1.05), _clip_0_100(proj_h * 1.05)
        if "visitante" in s or "away" in s or "2" in s:
            stat_a, proj_a = _support_away_win(h, a, proj)
            return _clip_0_100(stat_a * 1.05), _clip_0_100(proj_a * 1.05)

    return 55.0, 55.0


def _canonical_pick_signature(selection: str) -> tuple[str, str, float | None]:
    family = _market_family(selection)
    side = _market_side(selection)
    line = _extract_line_number(selection)
    if line is not None:
        line = round(line, 2)
    return family, side, line


def _are_contradictory(selection_a: str, selection_b: str) -> bool:
    fa, sa, la = _canonical_pick_signature(selection_a)
    fb, sb, lb = _canonical_pick_signature(selection_b)

    if fa != fb:
        return False

    if fa in {"goals", "corners", "cards", "shots", "fouls"}:
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
    # Tu lógica frontend, pero un poco más fina para evitar que todo termine en 1.30
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
    edge = _safe_num(v.edge)
    odds = _safe_num(v.odds, 0.0)
    prob = _safe_num(v.model_prob)
    sel = (v.selection or "").lower()

    # Filtro 1: edge mínimo y cuota válida
    if edge < 2.0 or odds <= 1.01:
        return -1

    score = 0

    # Filtro 2: rango dorado de cuotas
    score += _profitability_band_score(odds)

    # Filtro 3: evitar picks demasiado "coinflip" salvo que el edge sea decente
    if 45.0 <= prob <= 55.0:
        if edge < 5.0:
            return -1
        score += 10

    # Filtro 4: secundarios vs principales
    is_secondary = _is_secondary_market(sel)

    if is_secondary:
        if edge < 6.0:
            score -= 40
        else:
            score += int(edge * 1.5)
    else:
        if edge > 20.0:
            score -= 50
        else:
            score += int(edge * 2)

    return score


def _rate_pick_quality(v: ValueIndicator, h, a, proj: list[ProjectedLine]) -> tuple[int, float, float, int]:
    selection = v.selection or ""
    odds = _safe_num(v.odds, None)
    prob = _safe_num(v.model_prob)
    edge = _safe_num(v.edge)
    implied = _safe_num(v.implied_prob, None)
    if implied is None:
        implied = _implied_prob_from_odds(odds)

    stat_support, proj_support = _explicit_market_support(selection, h, a, proj)
    strategic_score = _frontend_style_strategic_score(v)

    # ── FILTROS DUROS DE SEGURIDAD (FASE 1) ──
    if odds is None or odds <= 1.01:
        return -1, stat_support, proj_support, strategic_score

    # Umbral de probabilidad más conservador (de 54 a 56 para calidad base)
    if prob < 56:
        return -1, stat_support, proj_support, strategic_score

    # Umbral de edge (de 1.2 a 1.8)
    if edge < 1.8:
        return -1, stat_support, proj_support, strategic_score

    # Respaldo estadístico
    family = _market_family(selection)
    min_stat = 53 if family in {"cards", "corners", "shots"} else 52 # Restaurado a 53
    if stat_support < min_stat:
        return -1, stat_support, proj_support, strategic_score

    # Respaldo de proyección
    if proj_support < 48: # Restaurado a 48
        return -1, stat_support, proj_support, strategic_score

    # ── SCORE BASE DE SEGURIDAD (FASE 2) ──
    score = 0
    score += _probability_band_score(prob)
    score += int((stat_support - 50) * 0.85) # Restaurado
    score += int((proj_support - 50) * 0.65) # Restaurado
    score += _market_risk_weight(selection)
    score += _odds_risk_penalty(odds)

    # ── SCORE DE RENTABILIDAD ESTRATÉGICA ──
    score += strategic_score

    # Bonus por valor real sobre implícita
    if implied is not None:
        delta = prob - implied
        if delta >= 12:   score += 10
        elif delta >= 8:  score += 7
        elif delta >= 5:  score += 4
        elif delta >= 3:  score += 2

    # Penalizaciones por inconsistencia (Cuota alta vs Probabilidad baja)
    if family in {"result", "btts", "handicap"} and odds >= 2.25 and prob < 64:
        score -= 8 # Restaurado

    if family in {"goals", "cards", "corners", "shots"} and odds >= 2.60 and prob < 60:
        score -= 8 # Restaurado

    # Castigo por falta de muestra segmentada en mercados secundarios (Suavizado)
    if family in {"cards", "corners", "shots"}:
        conf = get_market_confidence_tier(selection)
        if conf != "segmented":
            score -= 3 # Restaurado a 3

    # Castigo definitivo si el strategic_score salió negativo
    if strategic_score < 0:
        return -1, stat_support, proj_support, strategic_score

    return score, stat_support, proj_support, strategic_score


async def generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    league_stats: LeagueStats,
    competition: str = "Desconocida",
    user_context: str = "",
) -> str:
    MAX_MARKETS_FOR_LLM = 4
    MAX_PROJ_FOR_LLM = 4

    scored_picks = []
    for v in vp:
        # Solo consideramos picks que pasaron el filtro de publicabilidad del backend
        if not v.is_publishable:
            continue
            
        score = v.quality_score if v.quality_score is not None else -1
        strat_score = v.strategic_score if v.strategic_score is not None else -1
        scored_picks.append((v, score, v.stat_support or 0.0, v.proj_support or 0.0, strat_score))

    # Ordenamos por confianza de datos (prioridad solicitada por el usuario), luego probabilidad, y luego criterios técnicos originales
    scored_picks.sort(
        key=lambda x: (
            _safe_num(x[0].data_quality_score),
            _safe_num(x[0].model_prob),
            x[1], # quality_score (solidez_backend)
            x[4], # strategic_score
            _safe_num(x[0].edge),
        ),
        reverse=True,
    )

    filtered_ranked = []
    for v, score, stat_support, proj_support, strategic_score in scored_picks:
        if not v.is_publishable:
            continue
        if any(_are_contradictory(v.selection, prev.selection) for prev, _, _, _, _ in filtered_ranked):
            continue
        if any(_is_too_similar(v.selection, prev.selection) for prev, _, _, _, _ in filtered_ranked):
            continue
        filtered_ranked.append((v, score, stat_support, proj_support, strategic_score))
        if len(filtered_ranked) >= 3: # Máximo 3 picks profesionales por análisis
            break

    vp_text = (
        "\n".join(
            [
                (
                    f"- {v.selection}: "
                    f"cuota={v.odds if v.odds is not None else 'N/A'} | "
                    f"modelo={_safe_num(v.model_prob):.1f}% | "
                    f"implícita={(_safe_num(v.implied_prob, None) if v.implied_prob is not None else _implied_prob_from_odds(v.odds)) or 'N/A'} | "
                    f"edge={_safe_num(v.edge):.1f}% | "
                    f"rating={v.rating} | "
                    f"solidez_backend={score} | "
                    f"score_rentabilidad={strategic_score} | "
                    f"respaldo_stats={stat_support:.1f}/100 | "
                    f"respaldo_proyeccion={proj_support:.1f}/100"
                )
                for v, score, stat_support, proj_support, strategic_score in filtered_ranked
            ]
        )
        if filtered_ranked
        else "- No hay mercados suficientemente sólidos. Debes decir claramente que no recomiendas apostar en este partido."
    )

    proj_text = (
        "\n".join(
            [
                f"- {p.label}: {p.value:.2f}" + (f" | prob={p.prob:.1f}%" if p.prob is not None else "")
                for p in proj[:MAX_PROJ_FOR_LLM]
            ]
        )
        if proj
        else "- No hay líneas proyectadas disponibles."
    )

    # ── Bloque de contexto adicional mejorado ──────────────────────────────────
    additional_context_block = ""
    if user_context:
        additional_context_block = f"""
CONTEXTO ADICIONAL DEL USUARIO:
{user_context}

INSTRUCCIONES OBLIGATORIAS SOBRE EL CONTEXTO:
- Este contexto DEBE modificar directamente tu análisis táctico y tus recomendaciones.
- No lo trates como información decorativa: úsalo para ajustar qué mercados tienen sentido dado el escenario real.
- Ejemplos de cómo aplicarlo:
    * Si es una eliminatoria (ida/vuelta) y un equipo tiene ventaja en el global, considera que el favorito puede bajar el ritmo o especular, y el otro necesita atacar sí o sí → esto afecta corners, goles, BTTS y resultado.
    * Si hay equipos que necesitan ganar por obligación (descenso, clasificación), espera más presión, más tarjetas, más corners.
    * Si el partido es intrascendente para ambos (ya clasificados, ya descendidos), penaliza picks que dependen de intensidad alta.
    * Si hay información sobre bajas confirmadas, alineaciones, clima o contexto emocional del equipo, intégrala al análisis.
- Nunca contradigas el contexto dado. Si el contexto invalida un pick del modelo, dilo explícitamente y descártalo.
""".strip()

    prompt = f"""
Eres un analista táctico y de apuestas de élite. Tu trabajo es explicar el partido con claridad, criterio estadístico y lenguaje natural, sin exagerar ni repetir números innecesariamente.

REGLAS:
- Usa SOLO la información entregada.
- No inventes lesiones, rachas recientes, contexto histórico ni alineaciones.
- No digas que un mercado tiene valor si no aparece en "MERCADOS FINALISTAS".
- Si no hay suficiente seguridad, dilo explícitamente y no fuerces picks.
- Sé concreto: máximo 420 palabras.
- Prioriza interpretación sobre repetir cifras.
- Los mercados listados en "MERCADOS DE VALOR" ya fueron prefiltrados y ordenados aproximadamente por solidez. Usa ese orden como pista secundaria, pero decide con criterio propio según estadísticas y proyecciones.

OBJETIVO PRINCIPAL:
No debes elegir picks solo porque tengan más edge.
Debes seleccionar los picks que tengan MAYOR PROBABILIDAD REAL DE CUMPLIRSE dentro de los mercados de valor disponibles.

JERARQUÍA OBLIGATORIA PARA ESCOGER PICKS:
1. Primero, prioriza la probabilidad real de acierto del mercado.
2. Después, verifica que esté claramente respaldado por las estadísticas de ambos equipos.
3. Luego, confirma que la proyección del partido y de las líneas vaya en la misma dirección.
4. Solo después de eso, usa la diferencia entre probabilidad del modelo y probabilidad implícita de la casa para validar el value.
5. El edge por sí solo NO convierte un pick en uno de los mejores.

CRITERIOS ESTRICTOS:
- Favorece mercados con probabilidad del modelo alta y sostenida por el perfil estadístico del partido.
- Penaliza mercados con cuota alta y probabilidad absoluta baja, aunque tengan edge positivo.
- Penaliza mercados atractivos en precio, pero débiles en respaldo estadístico.
- Penaliza mercados que dependan de demasiada varianza o de un guion poco sólido.
- Entre dos picks parecidos, elige el más probable de cumplirse, no el que más paga.
- No elijas picks contradictorios entre sí.
- Si un pick tiene edge alto pero parece menos probable de salir que otro mercado más sólido, NO lo selecciones.
- Tu meta no es encontrar los picks con más value bruto, sino los 2 picks más fuertes y confiables que además tengan value.
- Prefiere 1 pick muy sólido antes que 2 picks mediocres.
- Si ningún pick supera un estándar alto de seguridad, no recomiendes apostar.

PARTIDO:
Competencia: {competition}
Local: {h.name}
Visitante: {a.name}
Árbitro: {league_stats.referee_avg_yellow} amarillas/j | {league_stats.referee_avg_red} rojas/j

SEÑALES CLAVE LOCAL:
- Partidos jugados: {h.matches_played}
- Victorias: {h.wins} | Empates: {h.draws} | Derrotas: {h.losses}
- Goles p/j: {h.goals_per_game} de local | Goles concedidos p/j: {h.goals_conceded_per_game} de local
- xG p/j: {h.xg_per_game} de local | xGA p/j: {h.xga_per_game} de local
- Grandes chances creadas p/j: {h.big_chances_per_game}
- Tiros totales p/j: {h.shots_per_game} | Tiros a puerta p/j: {h.shots_on_target_per_game}
- Posesión: {h.possession_pct}%
- Corners p/j: {h.corners_per_game} de local | Corners concedidos p/j: {h.corners_conceded_per_game} de local
- Disciplina: {h.yellow_cards_per_game} Amarillas p/j | {h.fouls_per_game} Faltas p/j | {h.red_cards_total}/{h.matches_played} Rojas p/j
- Defensa: {h.clean_sheets_home} Vallas invictas de local | {h.saves_per_game} Paradas p/j
- Errores que llevan a gol p/j: {h.errors_leading_to_goal}/{h.matches_played} | Penales concedidos p/j: {h.penalties_conceded}/{h.matches_played}

SEÑALES CLAVE VISITANTE:
- Partidos jugados: {a.matches_played}
- Victorias: {a.wins} | Empates: {a.draws} | Derrotas: {a.losses}
- Goles p/j: {a.goals_per_game} de visitante | Goles concedidos p/j: {a.goals_conceded_per_game} de visitante
- xG p/j: {a.xg_per_game} de visitante | xGA p/j: {a.xga_per_game} de visitante
- Grandes chances creadas p/j: {a.big_chances_per_game}
- Tiros totales p/j: {a.shots_per_game} | Tiros a puerta p/j: {a.shots_on_target_per_game}
- Posesión: {a.possession_pct}%
- Corners p/j: {a.corners_per_game} de visitante | Corners concedidos p/j: {a.corners_conceded_per_game} de visitante
- Disciplina: {a.yellow_cards_per_game} Amarillas p/j | {a.fouls_per_game} Faltas p/j | {a.red_cards_total}/{h.matches_played} Rojas p/j
- Defensa: {a.clean_sheets_away} Vallas invictas de visitante | {a.saves_per_game} Paradas p/j
- Errores que llevan a gol p/j: {a.errors_leading_to_goal}/{h.matches_played}  | Penales concedidos p/j: {a.penalties_conceded}/{h.matches_played} 

LÍNEAS PROYECTADAS:
{proj_text}

MERCADOS FINALISTAS:
{vp_text}

{additional_context_block}

## PROTOCOLO DE ANÁLISIS (ejecuta en este orden mental)

Paso 1 - Filtro de contexto: Aplica el contexto situacional para ajustar expectativas base de goles, intensidad y riesgo.
Paso 2 - Filtro estadístico: Cruza xG, tiros a puerta, corners y disciplina para validar si las líneas proyectadas son coherentes.
Paso 3 - Filtro de probabilidad: De los mercados finalistas, identifica cuáles tienen probabilidad de modelo >60% y soporte estadístico directo.
Paso 4 - Filtro de valor: Entre los supervivientes, verifica que la cuota implícita no sobreprecie el riesgo.
Paso 5 - Filtro de correlación: Si hay 2 picks, confirma que no son mutuamente excluyentes ni del mismo mercado escalonado.

## FORMATO DE RESPUESTA OBLIGATORIO

**Diagnóstico táctico:** Explica el choque de estilos usando posesión, xG y generación de juego. Si hay contexto situacional, debe ser el eje conductor.

**Evaluación de mercados:** Solo menciona goles, BTTS, corners o tarjetas si las proyecciones y estadísticas lo justifican con números concretos. Si el contexto altera la lógica (ej: ventaja en eliminatoria reduce intensidad), declara el ajuste explícito.

**Pronósticos recomendados (máximo 2):**
Para cada pick usa exactamente esta estructura:
- **Pick:** [texto exacto del mercado]
- **Probabilidad:** Modelo [X]% | Implícita casa [Y]%
- **Justificación estadística:** [2 frases con datos concretos]
- **Respaldo proyección:** [cómo la línea proyectada respalda el pick]
- **Validación contextual:** [cómo el contexto refuerza o invalida el pick]
- **Value:** [por qué la cuota no refleja completamente la probabilidad real]

**Regla de cantidad:** Prefiere 1 pick sólido sobre 2 picks dudosos. Si ninguno supera el umbral de confianza, escribe exactamente: "No recomiendo apostar en este partido."

**Combinada sugerida (solo si hay exactamente 2 picks recomendados):**
- Picks combinados: [lista]
- Cuota combinada estimada: [producto de ambas cuotas]
- Probabilidad combinada estimada: [producto de ambas probabilidades del modelo]%
- Justificación de independencia: [1-2 frases explicando por qué no están correlacionados negativamente]
- Si están correlacionados negativamente, omite este bloque y explica brevemente por qué no se sugiere.
""".strip()

    return await _call_openrouter(prompt)



# ───────────────────────────────────────────────────────────────
# compare_football
# ───────────────────────────────────────────────────────────────
async def compare_football(req: FootballCompareRequest) -> CompareResponse:
    h, a = req.home, req.away

    h_matches = max(h.matches_played, 1)
    a_matches = max(a.matches_played, 1)

    comparisons = [
        # Ataque
        _stat_comparison("Goles por juego",           "goals_per_game",               h.goals_per_game,               a.goals_per_game),
        _stat_comparison("% Conversión Gol",          "goal_conversion_pct",          h.goal_conversion_pct,          a.goal_conversion_pct),
        _stat_comparison("Grandes chances",           "big_chances_per_game",         h.big_chances_per_game,         a.big_chances_per_game),
        _stat_comparison("G. Chances Falladas",       "big_chances_missed_per_game",  h.big_chances_missed_per_game,  a.big_chances_missed_per_game, False),
        _stat_comparison("Tiros al arco",             "shots_on_target_per_game",     h.shots_on_target_per_game,     a.shots_on_target_per_game),
        # Posesión
        _stat_comparison("Posesión %",                "possession_pct",               h.possession_pct,               a.possession_pct),
        _stat_comparison("Pases acertados",           "passes_completed",             h.passes_completed,             a.passes_completed),
        _stat_comparison("Precisión pases %",         "pass_accuracy",                h.pass_accuracy,                a.pass_accuracy),
        _stat_comparison("Pases campo rival %",       "pass_accuracy_opp_half",       h.pass_accuracy_opp_half,       a.pass_accuracy_opp_half),
        _stat_comparison("Centros completos",         "crosses_per_game",             h.crosses_per_game,             a.crosses_per_game),
        _stat_comparison("Precisión de centros %",   "cross_accuracy",               h.cross_accuracy,               a.cross_accuracy),
        _stat_comparison("Corners por juego",         "corners_per_game",             h.corners_per_game,             a.corners_per_game),
        # Defensa
        _stat_comparison("Goles concedidos",          "goals_conceded_per_game",      h.goals_conceded_per_game,      a.goals_conceded_per_game, False),
        _stat_comparison("% Vallas Invictas",         "clean_sheets_pct",             (h.clean_sheets / h_matches) * 100, (a.clean_sheets / a_matches) * 100),
        _stat_comparison("Errores a Gol/juego",       "errors_leading_to_goal_pg",    h.errors_leading_to_goal / h_matches, a.errors_leading_to_goal / a_matches, False),
        _stat_comparison("Recuperaciones/j",          "balls_recovered_per_game",     h.balls_recovered_per_game,     a.balls_recovered_per_game),
    ]

    h_lam = _compute_team_goals_lambda(h, a, req.league_stats, is_home=True)
    a_lam = _compute_team_goals_lambda(a, h, req.league_stats, is_home=False)
    lam_corners = _compute_corners_lambda(h, a, req.league_stats)
    lam_cards   = _compute_cards_lambda(h, a, req.league_stats)
    lam_shots   = _compute_shots_lambda(h, a, req.league_stats)
    lam_shots_target = _compute_shots_target_lambda(h, a, req.league_stats)

    # ── Métricas por equipo ──────────────────────────────────────
    h_goals_lam   = _compute_team_goals_lambda(h, a, req.league_stats, is_home=True)
    a_goals_lam   = _compute_team_goals_lambda(a, h, req.league_stats, is_home=False)
    h_corners_lam = _compute_team_corners_lambda(h, a, req.league_stats, is_home=True)
    a_corners_lam = _compute_team_corners_lambda(a, h, req.league_stats, is_home=False)
    h_cards_lam   = _compute_team_cards_lambda(h, a, req.league_stats, is_home=True)
    a_cards_lam   = _compute_team_cards_lambda(a, h, req.league_stats, is_home=False)
    h_shots_lam   = _compute_team_shots_lambda(h, a, req.league_stats, is_home=True)
    a_shots_lam   = _compute_team_shots_lambda(a, h, req.league_stats, is_home=False)
    h_shots_target_lam = _compute_team_shots_target_lambda(h, a, req.league_stats, is_home=True)
    a_shots_target_lam = _compute_team_shots_target_lambda(a, h, req.league_stats, is_home=False)

    # Solo necesitamos 1x2 y BTTS (Mercados base sin líneas dinámicas)
    matrix, _ = _dc_score_matrix(h_lam, a_lam)
    markets = _sum_score_matrix_1x2_and_markets(matrix)

    # Probabilidades crudas de la matriz DC (sin blend de liga todavía)
    h_prob_raw = markets["home_win_pct"] / 100.0
    d_prob_raw = markets["draw_pct"]     / 100.0
    a_prob_raw = markets["away_win_pct"] / 100.0
    p_btts_yes = markets["btts_yes_pct"] / 100.0
    p_btts_no  = markets["btts_no_pct"]  / 100.0

    # ── FIX 1: Blend diferenciado por mercado ────────────────────────────────
    # 1X2: blend fuerte (70/30) para anclar al prior de liga y evitar sobre-confianza.
    # DC:  blend leve  (90/10) — el DC ya es un mercado compuesto cuya señal proviene
    #       directamente de la matriz. Aplicar el mismo 30% de prior genera una doble
    #       regresión a la media que subestima la probabilidad del favorito.
    _BLEND_W    = 0.70  # 70% modelo, 30% prior → mercados 1X2
    _DC_BLEND_W = 0.90  # 90% modelo, 10% prior → mercados DC (señal más directa)

    _prior_sum = req.league_stats.home_win_pct + req.league_stats.draw_pct + req.league_stats.away_win_pct

    # Inicializar priors con las probabilidades crudas como fallback
    _ph, _pd, _pa = h_prob_raw, d_prob_raw, a_prob_raw
    h_prob = h_prob_raw
    d_prob = d_prob_raw
    a_prob = a_prob_raw

    if _prior_sum > 0:
        _ph = req.league_stats.home_win_pct / _prior_sum
        _pd = req.league_stats.draw_pct     / _prior_sum
        _pa = req.league_stats.away_win_pct / _prior_sum
        # Blend fuerte para mercados de resultado
        h_prob = h_prob_raw * _BLEND_W + _ph * (1.0 - _BLEND_W)
        d_prob = d_prob_raw * _BLEND_W + _pd * (1.0 - _BLEND_W)
        a_prob = a_prob_raw * _BLEND_W + _pa * (1.0 - _BLEND_W)

    # ── FIX 2: Helper local que remueve el overround antes de calcular edge ─
    # Las cuotas de la casa incluyen margen (~3–8%), lo que infla las implied
    # probability y hace que el modelo "parezca" subestimar. Normalizamos primero.
    def _overround(*odds_list: float | None) -> float:
        """Calcula el overround total de un mercado (e.g. 103.5 para un 3.5% de margen)."""
        raw = [1.0 / o for o in odds_list if o and o > 1.0]
        return sum(raw) * 100.0 if raw else 100.0

    def _vi(sel: str, odds: float | None, modelp: float, overround: float = 100.0, push_p: float = 0.0) -> ValueIndicator:
        return _value_indicator(sel, odds, modelp, h=h, a=a, overround=overround, push_p=push_p)

    _or_1x2  = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    # ── Doble Oportunidad — blend leve desde matriz raw ──────────────────────
    # Se calcula ANTES del blend fuerte del 1X2, usando directamente las probabilidades
    # de la matriz Dixon-Coles. Esto evita que h_prob/d_prob/a_prob (ya blended al 30%)
    # introduzcan una segunda regresión a la media en el DC.
    p_dc_1x = ((h_prob_raw + d_prob_raw) * _DC_BLEND_W + (_ph + _pd) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_x2 = ((d_prob_raw + a_prob_raw) * _DC_BLEND_W + (_pd + _pa) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_12 = ((h_prob_raw + a_prob_raw) * _DC_BLEND_W + (_ph + _pa) * (1.0 - _DC_BLEND_W)) * 100

    # ── Overround específico del mercado DC ──────────────────────────────────
    # Las casas publican cuotas DC con su propio margen, diferente al del 1X2.
    # Usar _or_1x2 para DC inflaba la implied_no_vig y subestimaba el edge real.
    _or_dc_raw = _overround(req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12)
    _or_dc = _or_dc_raw if _or_dc_raw > 100.5 else _or_1x2  # fallback si no hay cuotas DC

    # ── Overround específico del mercado DNB ─────────────────────────────────
    _or_dnb_raw = _overround(req.odds.dnb_home, req.odds.dnb_away)
    _or_dnb = _or_dnb_raw if _or_dnb_raw > 100.5 else _or_1x2

    # En DNB, el empate se reembolsa (push_prob = d_prob_raw * 100).
    # La probabilidad de acierto del pick se normaliza excluyendo el empate.
    p_dnb_home = (h_prob_raw / max(h_prob_raw + a_prob_raw, 0.1)) * 100
    p_dnb_away = (a_prob_raw / max(h_prob_raw + a_prob_raw, 0.1)) * 100
    push_dnb = d_prob_raw * 100

    # market: (sel, odds, model_prob, overround, push_prob)
    market_configs: list[tuple[str, float | None, float, float, float]] = [
        ("Local",     req.odds.home,     h_prob     * 100, _or_1x2, 0.0),
        ("Empate",    req.odds.draw,     d_prob     * 100, _or_1x2, 0.0),
        ("Visitante", req.odds.away,     a_prob     * 100, _or_1x2, 0.0),
        ("BTTS Sí",   req.odds.btts_yes, p_btts_yes * 100, _or_btts, 0.0),
        ("BTTS No",   req.odds.btts_no,  p_btts_no  * 100, _or_btts, 0.0),

        ("Doble Oportunidad 1X", req.odds.dc_1x, p_dc_1x, _or_dc, 0.0),
        ("Doble Oportunidad X2", req.odds.dc_x2, p_dc_x2, _or_dc, 0.0),
        ("Doble Oportunidad 12", req.odds.dc_12, p_dc_12, _or_dc, 0.0),

        (f"DNB Local ({h.name})", req.odds.dnb_home, p_dnb_home, _or_dnb, push_dnb),
        (f"DNB Visitante ({a.name})", req.odds.dnb_away, p_dnb_away, _or_dnb, push_dnb),
    ]

    projected_lines: list[ProjectedLine] = []
    projected_total_goals = h_lam + a_lam

    projected_lines.append(ProjectedLine(
        label="Goles Totales (λ)", value=round(projected_total_goals, 2),
        type="goals", prob=None
    ))
    projected_lines.append(ProjectedLine(
        label="Doble Oportunidad 1X", value=round(p_dc_1x, 1),
        type="double_chance", prob=round(p_dc_1x, 1)
    ))
    projected_lines.append(ProjectedLine(
        label="Doble Oportunidad X2", value=round(p_dc_x2, 1),
        type="double_chance", prob=round(p_dc_x2, 1)
    ))
    projected_lines.append(ProjectedLine(
        label="Doble Oportunidad 12", value=round(p_dc_12, 1),
        type="double_chance", prob=round(p_dc_12, 1)
    ))
    projected_lines.append(ProjectedLine(
        label="BTTS Sí", value=round(p_btts_yes * 100, 1),
        type="btts",  prob=round(p_btts_yes * 100, 1)
    ))

    # ── Over/Under GOLES ─────────────────────
    for line in req.odds.goals_lines:
        p_over, p_push, p_under = _poisson_over_under(projected_total_goals, line)
        key       = str(line)
        overOdds  = req.odds.goals_over_odds.get(key)
        underOdds = req.odds.goals_under_odds.get(key)
        _or_goals = _overround(overOdds, underOdds)

        market_configs.append((f"Over {line} Goles",  overOdds,  p_over,  _or_goals, p_push))
        market_configs.append((f"Under {line} Goles", underOdds, p_under, _or_goals, p_push))

        projected_lines.append(ProjectedLine(
            label=f"Over {line} Goles",  value=round(p_over, 1),
            type="goals", prob=round(p_over, 1)
        ))

    # ── Over/Under CORNERS ───────────────────
    projected_lines.append(ProjectedLine(
        label="Corners Totales (λ)", value=round(lam_corners, 1),
        type="corners", prob=None
    ))
    for line in req.odds.corners_lines:
        p_over, p_push, p_under = _poisson_over_under(lam_corners, line)
        key        = str(line)
        over_odds  = req.odds.corners_over_odds.get(key)
        under_odds = req.odds.corners_under_odds.get(key)
        _or_corn   = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Corners",  over_odds,  p_over,  _or_corn, p_push))
        market_configs.append((f"Under {line} Corners", under_odds, p_under, _or_corn, p_push))

    # ── Over/Under TARJETAS ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tarjetas Totales (λ)", value=round(lam_cards, 1),
        type="cards", prob=None
    ))
    for line in req.odds.cards_lines:
        p_over, p_push, p_under = _poisson_over_under(lam_cards, line)
        key        = str(line)
        over_odds  = req.odds.cards_over_odds.get(key)
        under_odds = req.odds.cards_under_odds.get(key)
        _or_cards  = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Tarjetas",  over_odds,  p_over,  _or_cards, p_push))
        market_configs.append((f"Under {line} Tarjetas", under_odds, p_under, _or_cards, p_push))

    # ── Over/Under TIROS TOTALES ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros Totales (λ)", value=round(lam_shots, 1),
        type="shots", prob=None
    ))
    for line in req.odds.shots_lines:
        p_over, p_push, p_under = _poisson_over_under(lam_shots, line)
        key        = str(line)
        over_odds  = req.odds.shots_over_odds.get(key)
        under_odds = req.odds.shots_under_odds.get(key)
        _or_shots  = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Tiros",  over_odds,  p_over,  _or_shots, p_push))
        market_configs.append((f"Under {line} Tiros", under_odds, p_under, _or_shots, p_push))

    # ── Over/Under TIROS A PUERTA ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros a Puerta (λ)", value=round(lam_shots_target, 1),
        type="shots_target", prob=None
    ))
    for line in req.odds.shots_target_lines:
        p_over, p_push, p_under = _poisson_over_under(lam_shots_target, line)
        key        = str(line)
        over_odds  = req.odds.shots_target_over_odds.get(key)
        under_odds = req.odds.shots_target_under_odds.get(key)
        _or_shots_t  = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Tiros a Pta",  over_odds,  p_over,  _or_shots_t, p_push))
        market_configs.append((f"Under {line} Tiros a Pta", under_odds, p_under, _or_shots_t, p_push))

    # ── Handicap Asiático ──────────────────────────────────────
    proj_hcap = h_lam - a_lam
    projected_lines.append(ProjectedLine(
        label="Handicap (Local)", value=round(proj_hcap, 2),
        type="handicap", prob=None
    ))

    # Usamos las líneas de handicap solicitadas o un set estándar profesional
    hcap_lines_to_calc = req.odds.handicap_lines if req.odds.handicap_lines else [-1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    
    for hc_line in hcap_lines_to_calc:
        probs = _compute_asian_handicap_probs(h_lam, a_lam, hc_line)
        # Probabilidad de 'CUBRIR' el handicap (Ganar la apuesta completa o media)
        p_home_covers = probs["win"] + probs["half_win"]
        p_away_covers = probs["loss"] + probs["half_loss"]
        
        projected_lines.append(ProjectedLine(
            label=f"AH {hc_line:+.2f} {h.name}",
            value=hc_line,
            type="handicap_prob",
            prob=round(p_home_covers, 1),
            push_prob=round(probs["push"], 1)
        ))

        # Añadir a configs de mercado si hay cuotas
        h_odds = req.odds.handicap_home_odds.get(str(hc_line))
        a_odds = req.odds.handicap_away_odds.get(str(hc_line))
        _or_hc = _overround(h_odds, a_odds)

        if h_odds:
            market_configs.append((f"AH {hc_line:+.2f} {h.name}", h_odds, p_home_covers, _or_hc, probs["push"]))
        if a_odds:
            market_configs.append((f"AH {(-hc_line):+.2f} {a.name}", a_odds, p_away_covers, _or_hc, probs["push"]))

    # ── Values: Cálculo masivo con nuevas métricas ─────────────
    values = [_vi(sel, odds, mp, ornd, pushp) for sel, odds, mp, ornd, pushp in market_configs]

    # ── Sincronización de Calidad y Publicabilidad ─────────────
    for v in values:
        q_score, s_support, p_support, strat_score = _rate_pick_quality(v, h, a, projected_lines)
        v.quality_score   = q_score
        v.strategic_score = strat_score
        v.stat_support    = round(s_support, 1)
        v.proj_support    = round(p_support, 1)
        
        # El backend ahora decide si un pick es publicable basándose en 
        # consistencia matemática + confianza de datos + scoring estratégico
        v.is_publishable = is_publishable_pick(v)
        
        # Sincronizamos is_value con la publicabilidad para el frontend básico
        v.is_value = v.is_publishable

    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp    = [v for v in values if v.is_value]

    # ── Faltas y Offsides Lambdas ─────────────────────────────
    lam_fouls = _compute_fouls_lambda(h, a, req.league_stats)
    h_fouls_lam = _compute_team_fouls_lambda(h, a, req.league_stats, is_home=True)
    a_fouls_lam = _compute_team_fouls_lambda(a, h, req.league_stats, is_home=False)

    lam_offsides = _compute_offsides_lambda(h, a, req.league_stats)
    h_offsides_lam = _compute_team_offsides_lambda(h, a, req.league_stats, is_home=True)
    a_offsides_lam = _compute_team_offsides_lambda(a, h, req.league_stats, is_home=False)

    # ── Most Probable Score ──
    max_p = -1.0
    best_h, best_a = 0, 0
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            if matrix[i][j] > max_p:
                max_p = matrix[i][j]
                best_h, best_a = i, j
    most_probable_score = f"{best_h} - {best_a}"

    # ── Proyecciones por Equipo ───────────────────────────────
    projected_lines.append(ProjectedLine(label=f"Goles {h.name}", value=h_goals_lam, type="goals_team"))
    projected_lines.append(ProjectedLine(label=f"Goles {a.name}", value=a_goals_lam, type="goals_team"))
    projected_lines.append(ProjectedLine(label=f"Corners {h.name}", value=h_corners_lam, type="corners_team"))
    projected_lines.append(ProjectedLine(label=f"Corners {a.name}", value=a_corners_lam, type="corners_team"))
    projected_lines.append(ProjectedLine(label=f"Tarjetas {h.name}", value=h_cards_lam, type="cards_team"))
    projected_lines.append(ProjectedLine(label=f"Tarjetas {a.name}", value=a_cards_lam, type="cards_team"))
    projected_lines.append(ProjectedLine(label=f"Tiros {h.name}", value=h_shots_lam, type="shots_team"))
    projected_lines.append(ProjectedLine(label=f"Tiros {a.name}", value=a_shots_lam, type="shots_team"))
    projected_lines.append(ProjectedLine(label=f"Tiros a Pta {h.name}", value=h_shots_target_lam, type="shots_target_team"))
    projected_lines.append(ProjectedLine(label=f"Tiros a Pta {a.name}", value=a_shots_target_lam, type="shots_target_team"))

    # Faltas y Offsides Totales y por Equipo en Projected Lines
    projected_lines.append(ProjectedLine(label="Faltas Totales (λ)", value=round(lam_fouls, 1), type="fouls", prob=None))
    projected_lines.append(ProjectedLine(label=f"Faltas {h.name}", value=h_fouls_lam, type="fouls_team"))
    projected_lines.append(ProjectedLine(label=f"Faltas {a.name}", value=a_fouls_lam, type="fouls_team"))
    projected_lines.append(ProjectedLine(label="Offsides Totales (λ)", value=round(lam_offsides, 1), type="offsides", prob=None))
    projected_lines.append(ProjectedLine(label=f"Offsides {h.name}", value=h_offsides_lam, type="offsides_team"))
    projected_lines.append(ProjectedLine(label=f"Offsides {a.name}", value=a_offsides_lam, type="offsides_team"))

    summary = (
        f"Sherlock Analytics | λ Goles: {h.name} {h_lam:.2f} - {a.name} {a_lam:.2f}\n"
        f"Proyección Total: {projected_total_goals:.2f} Goles | {lam_corners:.1f} Corners | {lam_cards:.1f} Tarjetas | {lam_shots:.1f} Tiros | {lam_shots_target:.1f} a Pta\n"
        f"Goles por equipo: {h.name} {h_goals_lam:.2f} | {a.name} {a_goals_lam:.2f}\n"
        f"Corners por equipo: {h.name} {h_corners_lam:.1f} | {a.name} {a_corners_lam:.1f}\n"
        f"Tarjetas por equipo: {h.name} {h_cards_lam:.1f} | {a.name} {a_cards_lam:.1f}\n"
        f"Handicap Estimado: {h.name} {proj_hcap:+.2f}\n"
        + (f"✅ Value detectado en: {', '.join(v.selection for v in vp)}"
           if vp else "⚖️ Sin value claro en las cuotas actuales.")
    )

    llm = None
    if req.generate_llm_analysis:
        llm = await generate_football_analysis(h, a, vp, projected_lines, req.league_stats, competition=req.competition)

    return CompareResponse(
        sport="football",
        home_name=h.name,
        away_name=a.name,
        h_lam=h_goals_lam,
        a_lam=a_goals_lam,
        h_corners_lam=h_corners_lam,
        a_corners_lam=a_corners_lam,
        h_cards_lam=h_cards_lam,
        a_cards_lam=a_cards_lam,
        h_fouls_lam=h_fouls_lam,
        a_fouls_lam=a_fouls_lam,
        h_offsides_lam=h_offsides_lam,
        a_offsides_lam=a_offsides_lam,
        most_probable_score=most_probable_score,
        comparisons=comparisons,
        values=values,
        projected_lines=projected_lines,
        summary=summary,
        llm_analysis=llm,
    )    