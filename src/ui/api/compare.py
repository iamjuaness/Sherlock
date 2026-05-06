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
    NBA      = "nba"
    TENNIS   = "tennis"


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
    competition_name: str = "Desconocida"
    generate_llm_analysis: bool = False
    user_context: str = Field(default="", description="Contexto adicional proporcionado por el usuario sobre los equipos")


# ───────────────────────────────────────────────────────────────
# NBA
# ───────────────────────────────────────────────────────────────
class NBATeamStats(BaseModel):
    name: str = Field(..., description="Nombre del equipo")

    # Generales / Marcador
    points:          float = Field(0.0, description="Puntos por partido")
    points_against:  float = Field(0.0, description="Puntos permitidos por partido (PA)")
    assists:         float = Field(0.0, description="Asistencias por partido")
    ast_to_ratio:    float = Field(0.0, description="Ratio asistencias/pérdidas")

    # Tiros de campo
    fg_made:        float = Field(0.0, description="Tiros de campo anotados por partido")
    fg_attempted:   float = Field(0.0, description="Tiros de campo intentados por partido")
    fg_pct:         float = Field(0.0, description="% tiros de campo (anotados)")

    # Triples
    three_pt_made:       float = Field(0.0, description="Triples anotados por partido")
    three_pt_attempted:  float = Field(0.0, description="Triples intentados por partido")
    three_pt_pct:        float = Field(0.0, description="% de triples (anotados)")

    # Tiros libres
    ft_made:        float = Field(0.0, description="Tiros libres anotados por partido")
    ft_attempted:   float = Field(0.0, description="Tiros libres intentados por partido")
    ft_pct:         float = Field(0.0, description="% de tiros libres (anotados)")

    # Eficiencia de tiro
    efg_pct:        float = Field(0.0, description="Porcentaje de tiro efectivo (eFG%)")
    ts_pct:         float = Field(0.0, description="Porcentaje de tiro real (TS%)")

    # Rebotes
    off_rebounds:   float = Field(0.0, description="Rebotes ofensivos por partido")
    def_rebounds:   float = Field(0.0, description="Rebotes defensivos por partido")
    total_rebounds: float = Field(0.0, description="Rebotes totales por partido")

    # Defensa
    blocks:               float = Field(0.0, description="Tapones por partido")
    steals:               float = Field(0.0, description="Robos por partido")
    three_pt_pct_allowed: float = Field(0.0, description="Porcentaje de triples permitidos")

    # Control balón / Ritmo / Ratings
    turnovers:     float = Field(0.0, description="Pérdidas por partido")
    pace:          float = Field(0.0, description="Ritmo")
    off_rating:    float = Field(0.0, description="Valoración ofensiva")
    def_rating:    float = Field(0.0, description="Valoración defensiva")
    net_rating:    float = Field(0.0, description="Valoración neta")

    # Extra desde frontend (si lo quieres usar)
    three_pt_attempts: float = Field(0.0, description="Triples intentados totales (helper)")

    # Record / Clasificación
    games_played: int   = Field(0,   description="Partidos jugados")
    wins:         int   = Field(0,   description="Partidos ganados")
    losses:       int   = Field(0,   description="Partidos perdidos")
    point_diff:   float = Field(0.0, description="Diferencia de puntos")
    win_pct:      float = Field(0.0, description="PCT (porcentaje de victorias)")
    streak:       str   = Field("",  description="Racha (STR)")


class NBAOdds(BaseModel):
    home:              float | None = Field(
        None, gt=1.0, description="Moneyline Local"
    )
    away:              float | None = Field(
        None, gt=1.0, description="Moneyline Visitante"
    )

    total_line:        float | None = Field(
        None, description="Línea de puntos totales (Over/Under)"
    )
    over_odds:         float | None = Field(
        None, gt=1.0, description="Cuota Over puntos totales"
    )
    under_odds:        float | None = Field(
        None, gt=1.0, description="Cuota Under puntos totales"
    )

    spread_line:       float | None = Field(
        None, description="Línea de Handicap para el local"
    )
    home_spread_odds:  float | None = Field(
        None, gt=1.0, description="Cuota Handicap Local"
    )
    away_spread_odds:  float | None = Field(
        None, gt=1.0, description="Cuota Handicap Visitante"
    )

    bookmaker:         str = Field("", description="Casa de apuestas")


class NBACompareRequest(BaseModel):
    home: NBATeamStats = Field(..., description="Stats del equipo local")
    away: NBATeamStats = Field(..., description="Stats del equipo visitante")
    odds: NBAOdds      = Field(..., description="Cuotas principales del partido")

    home_court_advantage: float = Field(
        3.0, description="Ventaja de cancha local (puntos)"
    )
    generate_llm_analysis: bool = Field(
        False, description="Si True, genera análisis con LLM"
    )
    user_context: str = Field(default="", description="Contexto adicional proporcionado por el usuario sobre los equipos")


# ───────────────────────────────────────────────────────────────
# Tennis
# ───────────────────────────────────────────────────────────────
class TennisPlayerStats(BaseModel):
    name:                          str
    age:                           int = Field(0, description="Edad del jugador")
    height:                        int = Field(0, description="Altura en cm")
    hand:                          str = Field("Right", description="Mano dominante (Right/Left)")
    rank:                          int = Field(0, description="Clasificación ATP")

    # Performance
    matches_won:                   int = 0
    total_matches:                 int = 0
    tournaments_won:               int = 0
    total_tournaments:             int = 0
    # Service
    first_serve_pct:               float = 0.0
    first_serve_points_won_pct:    float = 0.0
    second_serve_pct:              float = 0.0
    second_serve_points_won_pct:   float = 0.0
    aces_per_match:                float = 0.0
    double_faults_per_match:       float = 0.0
    # Pressure
    break_points_saved:            int = 0
    break_points_saved_total:      int = 0
    break_points_converted:        int = 0
    break_points_converted_total:  int = 0
    tiebreaks_won:                 int = 0
    tiebreaks_total:               int = 0
    # Surface/H2H
    matches_on_surface_won:        int = 0
    total_matches_on_surface:      int = 0
    head_to_head_won:              int = 0
    total_head_to_head:            int = 0



class TennisOdds(BaseModel):
    player1:  float | None = Field(None, gt=1.0)
    player2:  float | None = Field(None, gt=1.0)
    bookmaker: str  = Field("")


class TennisCompareRequest(BaseModel):
    player1: TennisPlayerStats
    player2: TennisPlayerStats
    odds:    TennisOdds
    surface: str = "hard"
    generate_llm_analysis: bool = False
    user_context: str = Field(default="", description="Contexto adicional proporcionado por el usuario sobre los jugadores")


# ───────────────────────────────────────────────────────────────
# Response models
# ───────────────────────────────────────────────────────────────
class ValueIndicator(BaseModel):
    selection:    str
    odds:         float | None = None
    implied_prob: float | None = None
    model_prob:   float
    edge:         float = 0.0
    is_value:     bool  = False
    rating:       str   = "N/A"
    # Campos de calidad calculados en backend
    quality_score:   Optional[int] = None
    strategic_score: Optional[int] = None
    stat_support:    Optional[float] = None
    proj_support:    Optional[float] = None

    # Nuevos campos de calidad y seguridad
    data_quality_score:     Optional[float] = None
    market_confidence_tier: Optional[str]   = None # 'segmented', 'hybrid', 'global'
    market_variance_tier:   Optional[str]   = None # 'low', 'medium', 'high'
    is_publishable:        bool = False
    push_prob:             Optional[float] = None


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
    Remueve el overround de un mercado completo y devuelve probs justas (suman 100).
    Funciona para 1X2, O/U, BTTS, etc.
    """
    raw = [(1.0 / o) for o in odds_list if o and o > 1.0]
    total = sum(raw)
    if total <= 0:
        return [0.0] * len(odds_list)
    # Normalizar a 100%
    normalized = [(r / total) * 100.0 for r in raw]
    return normalized

# Y en _value_indicator, pasar el overround del mercado:
def get_market_confidence_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals", "handicap", "dnb", "double_chance"}:
        return "segmented"
    if family == "corners":
        return "hybrid"
    return "global"

def get_market_variance_tier(selection: str) -> str:
    family = _market_family(selection)
    if family in {"result", "btts", "goals"}:
        return "low"
    if family in {"handicap", "dnb", "double_chance"}:
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

def is_publishable_pick(v: ValueIndicator) -> bool:
    """Filtro balanceado para determinar si un pick es apto para recomendación profesional."""
    # 1. Probabilidad mínima absoluta
    if v.model_prob < 54.0: return False # Restaurado a 54
    
    # 2. Edge mínimo real
    if v.edge < 2.5: return False # Restaurado a 2.5
    
    # 3. Calidad de datos mínima
    if v.data_quality_score is not None and v.data_quality_score < 45: # Restaurado a 45
        return False
        
    # 4. Reglas específicas por mercado
    family = _market_family(v.selection)
    
    # Mercados secundarios (Tarjetas, Corners, Tiros)
    if family in {"cards", "shots", "fouls", "corners"}:
        # Suavizamos los umbrales para permitir más picks en estos mercados
        if v.edge < 5.5: return False # Restaurado a 5.5
        if v.model_prob < 56.0: return False # Restaurado a 56
        # Si no hay buen respaldo estadístico, descartar
        if v.stat_support is not None and v.stat_support < 53: # Restaurado a 53
            return False
            
    # 5. Penalización por cuota alta (Riesgo de Ruina)
    if v.odds is not None:
        if v.odds > 3.5: return False # Restaurado a 3.5
        if v.odds > 2.50 and v.edge < 6.5: return False # Restaurado
        
    # 6. Score estratégico mínimo
    if v.strategic_score is not None and v.strategic_score < 40: # Restaurado a 40
        return False
        
    return True

def _value_indicator(sel, odds, modelp, h=None, a=None, overround=100.0, push_p=0.0):
    if odds is None:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1), push_prob=round(push_p, 1))
        
    raw_implied = (1.0 / odds) * 100.0
    # El edge se calcula contra la cuota bruta (lo que el usuario ve)
    edge = modelp - raw_implied
    
    # Metadatos de calidad
    conf_tier = get_market_confidence_tier(sel)
    var_tier = get_market_variance_tier(sel)
    dq_score = get_data_quality_score(sel, h, a) if h and a else None
    
    is_val = edge > 2.0
    
    if   edge > 7.0:  rating = "🔥 STRONG VALUE"
    elif edge > 3.5:  rating = "✅ VALUE"
    elif edge > 1.5:  rating = "⚖️ MARGINAL"
    else:             rating = "❌ NO VALUE"
    
    v = ValueIndicator(
        selection=sel,
        odds=odds,
        implied_prob=round(raw_implied, 1),
        model_prob=round(modelp, 1),
        push_prob=round(push_p, 1),
        edge=round(edge, 1),
        is_value=is_val,
        rating=rating,
        data_quality_score=dq_score,
        market_confidence_tier=conf_tier,
        market_variance_tier=var_tier
    )
    
    v.is_publishable = is_publishable_pick(v)
    return v


# Helpers para value de un pick individual
def compute_model_prob_over_under_from_lambda(
    lam: float,
    line: float,
    side: str,  # "over" o "under"
) -> float:
    p_over, p_under = _poisson_over_under(lam, line)
    return p_over if side.lower() == "over" else p_under


def value_for_market_pick(
    selection_name: str,
    odds: float,
    model_prob: float,
) -> ValueIndicator:
    return _value_indicator(selection_name, odds, model_prob)


# ───────────────────────────────────────────────────────────────
# Tennis Engine
# ───────────────────────────────────────────────────────────────

def _tennis_point_prob_on_serve(p: TennisPlayerStats) -> float:
    """Calcula la probabilidad de que el jugador gane un punto cuando saca."""
    s1_in = p.first_serve_pct / 100.0
    w1    = p.first_serve_points_won_pct / 100.0
    w2    = p.second_serve_points_won_pct / 100.0
    
    # Si tenemos dobles faltas por partido, estimamos la prob de DF por punto
    # Un set promedio tiene ~30 puntos de saque por jugador. Un partido 2-set ~60.
    df_prob = (p.double_faults_per_match / 65.0) 
    df_prob = max(0.01, min(0.12, df_prob)) # Cap razonable
    
    # P(Point) = P(1st In)*W1 + P(1st Out)*(P(2nd In)*W2)
    # Aquí simplificamos P(2nd In) como (1 - DF)
    return s1_in * w1 + (1 - s1_in) * (1 - df_prob) * w2

def _tennis_game_win_prob(s: float) -> float:
    """Probabilidad de ganar un juego de servicio con prob s de ganar punto."""
    if s <= 0: return 0.0
    if s >= 1: return 1.0
    # Fórmula estándar de juego de tenis (incluyendo deuce)
    p40_0   = s**4
    p40_15  = 4 * (s**4) * (1-s)
    p40_30  = 10 * (s**4) * ((1-s)**2)
    p_deuce = 20 * (s**3) * ((1-s)**3)
    p_win_deuce = (s**2) / (s**2 + (1-s)**2)
    return p40_0 + p40_15 + p40_30 + (p_deuce * p_win_deuce)

def _tennis_set_win_prob(s1: float, s2: float) -> float:
    """Probabilidad de que el jugador 1 gane el set."""
    g1 = _tennis_game_win_prob(s1)     # P(P1 gana su saque)
    g2 = _tennis_game_win_prob(1 - s2) # P(P1 quiebra el saque de P2)
    
    # Aproximación de Newton-Barnett para P(Set)
    # Basado en la ventaja relativa de juegos
    diff = g1 - (1 - g2)
    # En tenis, 0.1 de diff en prob de juego suele ser ~0.35 en prob de set
    prob = 0.5 + 3.65 * (g1 + g2 - 1.0)
    return max(0.01, min(0.99, prob))

def _tennis_match_win_prob(p1: TennisPlayerStats, p2: TennisPlayerStats, surface: str = "hard") -> float:
    """Calcula la probabilidad final de victoria de P1."""
    s1 = _tennis_point_prob_on_serve(p1)
    s2 = _tennis_point_prob_on_serve(p2)
    
    # Ajuste por superficie (Heurística)
    # En hierba el saque pesa más, en tierra menos.
    surf = (surface or "hard").lower()
    if surf == "clay":
        s1 *= 0.96; s2 *= 0.96
    elif surf == "grass":
        s1 *= 1.03; s2 *= 1.03
        
    p_set = _tennis_set_win_prob(s1, s2)
    
    # ── Ajuste por Clutch (Tiebreaks / Break Points) ──
    p1_clutch = (p1.tiebreaks_won / max(p1.tiebreaks_total, 1)) * 0.5 + (p1.break_points_saved / max(p1.break_points_saved_total, 1)) * 0.5
    p2_clutch = (p2.tiebreaks_won / max(p2.tiebreaks_total, 1)) * 0.5 + (p2.break_points_saved / max(p2.break_points_saved_total, 1)) * 0.5
    clutch_adj = (p1_clutch - p2_clutch) * 0.05
    
    p_set = max(0.01, min(0.99, p_set + clutch_adj))
    
    # ── Ajuste por Ranking / Experiencia ──
    # Si la diferencia de ranking es enorme, influye en la mentalidad
    if p1.rank > 0 and p2.rank > 0:
        rank_diff = (p2.rank - p1.rank) / 500.0 # P2 Rank 600 vs P1 Rank 100 -> +1.0
        p_set += max(-0.1, min(0.1, rank_diff * 0.02))
        
    p_set = max(0.01, min(0.99, p_set))
    
    # Asumimos al mejor de 3 (circuito normal)
    # Prob(2-0) + Prob(2-1) = p^2 + 2*p^2*(1-p)
    return (p_set**2 + 2*(p_set**2)*(1-p_set)) * 100.0



# ───────────────────────────────────────────────────────────────
# Poisson engine (Football)
# ───────────────────────────────────────────────────────────────

def _compute_lambda_v2(
    attacker: FootballTeamStats,
    defender: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
) -> float:
    avg_team = league.avg_goals_per_game / 2.0

    # ── 1. Base Dixon-Coles ───────────────────────────────────────
    att_str  = attacker.goals_per_game / max(avg_team, 0.1)
    def_str  = defender.goals_conceded_per_game / max(avg_team, 0.1)
    lam_base = att_str * def_str * avg_team

    # ── 2. xG proxy táctico ───────────────────────────────────────
    bc_converted = max(
        attacker.big_chances_per_game - attacker.big_chances_missed_per_game, 0.0
    )
    shot_xg   = attacker.shots_on_target_per_game * (attacker.goal_conversion_pct / 100.0)
    xg_signal = bc_converted * 0.45 + shot_xg * 0.55

    # ── 3. Multiplicador xG centrado en 1.0 con rango más amplio ──
    # Cuando xg_signal == avg_xg → multiplier = 1.0 (neutro)
    # alpha controla la sensibilidad a las desviaciones tácticas
    avg_xg    = max(avg_team * 0.50, 0.10)
    alpha     = 0.40  # 40% de sensibilidad a desviaciones del xG
    xg_mult   = 1.0 + alpha * (xg_signal / avg_xg - 1.0)
    # Rango ampliado para capturar equipos dominantes: 0.45 a 2.20
    xg_mult   = max(0.45, min(2.20, xg_mult))
    lam_adjusted = lam_base * xg_mult

    # ── 4. Shrinkage bayesiana ADAPTATIVA por tamaño de muestra ───
    # Fórmula: shrink_w = prior_n / (prior_n + matches_played)
    # prior_n adaptativo: menos regresión para equipos con buena data
    # prior_n = 0.5 para muestras grandes (n>=15), más para muestras pequeñas
    prior_n  = max(0.5, 2.0 - (attacker.matches_played / 10.0))
    n        = max(attacker.matches_played, 1)
    shrink_w = prior_n / (prior_n + n)
    lam_final = lam_adjusted * (1.0 - shrink_w) + avg_team * shrink_w

    # ── 5. Home / Away ────────────────────────────────────────────
    # Ventaja de local más realista: +15% local, -10% visitante
    lam_final *= league.home_advantage_factor if is_home else league.away_disadvantage_factor

    return max(lam_final, 0.10)


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
    if league.referee_avg_yellow > 0:
        # El árbitro es una señal de alta calidad pero externa a los equipos
        ref_baseline = league.referee_avg_yellow + (league.referee_avg_red * 2.0)
        league_cards_avg = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0)
        
        # Desviación del árbitro frente a la media de la liga
        ref_dev_ratio = ref_baseline / max(league_cards_avg, 1.0)
        
        # El árbitro influye un 50% en el ajuste (shrinkage hacia 1.0)
        # Esto evita que un árbitro muy 'tarjetero' dispare el lambda si los equipos son limpios
        ref_modifier = 1.0 + (ref_dev_ratio - 1.0) * 0.50
        lam *= ref_modifier

    # 5. Shrinkage (Regresión a la media)
    avg_team_cards = league.avg_cards_per_game / 2.0
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

def _poisson_1x2(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
):
    res = _dc_match_probs(h_lam, a_lam, max_goals=max_goals, rho=rho)
    return (
        res["home_win_pct"],
        res["draw_pct"],
        res["away_win_pct"],
    )


def _poisson_markets(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
):
    res = _dc_match_probs(h_lam, a_lam, max_goals=max_goals, rho=rho)
    return (
        res["over_25_pct"] / 100.0,
        res["under_25_pct"] / 100.0,
        res["btts_yes_pct"] / 100.0,
        res["btts_no_pct"] / 100.0,
    )


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


# ───────────────────────────────────────────────────────────────
# LLM analysis (Football, NBA, Tennis) + placeholders Sherlock
# ───────────────────────────────────────────────────────────────
PLACEHOLDER_FOOTBALL = (
    "Sherlock está analizando las estadísticas del partido para darte un veredicto de valor en unos segundos..."
)
PLACEHOLDER_NBA = (
    "Sherlock está procesando los ratings avanzados para darte una lectura clara del partido..."
)
PLACEHOLDER_TENNIS = (
    "Sherlock está evaluando servicio, presión y momentum para darte su veredicto..."
)


import os
import asyncio
from openai import AsyncOpenAI

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
    if any(k in s for k in ["draw no bet", "dnb"]):
        return "dnb"
    if any(k in s for k in ["double chance", "doble oportunidad", "1x", "x2", "12"]):
        return "double_chance"
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
    if family == "dnb":
        return -10
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


def _edge_score(edge: float) -> int:
    if edge < 2:
        return -8
    if edge < 4:
        return 2
    if edge < 7:
        return 6
    if edge < 10:
        return 8
    if edge < 15:
        return 9
    return 7


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
    h_clean = _safe_num(h.clean_sheets)
    a_clean = _safe_num(a.clean_sheets)
    h_mp = max(1.0, _safe_num(h.matches_played, 1))
    a_mp = max(1.0, _safe_num(a.matches_played, 1))

    clean_rate = (h_clean / h_mp) + (a_clean / a_mp)
    both_attack = min(h_g + h_xg, a_g + a_xg)
    both_allow = min(h_c + h_xga, a_c + a_xga)

    stat = 48 + both_attack * 12 + both_allow * 8 - clean_rate * 16
    stat = _clip_0_100(stat)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["btts"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["ambos", "marcan"])

    proj_score = 55.0
    if pprob is not None:
        proj_score += (pprob - 50) * 0.75

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
    reds = _safe_num(h.red_cards_total) + _safe_num(a.red_cards_total)

    base = total_y + total_f * 0.08 + reds * 0.2
    stat = _clip_0_100(58 + (base - line) * 11)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["tarjetas"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["cards"])

    proj_score = 55.0
    if pval is not None:
        proj_score += (pval - line) * 11
    if pprob is not None:
        proj_score += (pprob - 50) * 0.45

    return stat, _clip_0_100(proj_score)


def _support_under_cards(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_o, proj_o = _support_over_cards(line, h, a, proj)
    return _clip_0_100(110 - stat_o), _clip_0_100(110 - proj_o)


def _support_over_corners(line: float, h, a, proj: list) -> tuple[float, float]:
    base = (
        _safe_num(h.corners_per_game) + _safe_num(a.corners_per_game) +
        _safe_num(h.corners_conceded_per_game) + _safe_num(a.corners_conceded_per_game)
    ) / 2

    stat = _clip_0_100(57 + (base - line) * 10)

    pval, pprob, _ = _projected_value_by_keywords(proj, ["corners"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["córners"])

    proj_score = 55.0
    if pval is not None:
        proj_score += (pval - line) * 10
    if pprob is not None:
        proj_score += (pprob - 50) * 0.45

    return stat, _clip_0_100(proj_score)


def _support_under_corners(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_o, proj_o = _support_over_corners(line, h, a, proj)
    return _clip_0_100(110 - stat_o), _clip_0_100(110 - proj_o)


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


def _is_main_market(selection: str) -> bool:
    family = _market_family(selection)
    return family in {"goals", "btts", "result", "handicap", "dnb", "double_chance"}


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


async def generate_nba_analysis(
    h: NBATeamStats,
    a: NBATeamStats,
    vp: list[ValueIndicator],
    req: NBACompareRequest,
) -> str:
    vp_text = (
        "\n".join(
            [
                f"- {v.selection}: cuota={v.odds if v.odds is not None else 'N/A'} | modelo={v.model_prob:.1f}% | edge={v.edge:.1f}% | rating={v.rating}"
                for v in vp[:6]
            ]
        )
        if vp
        else "- No hay mercados de valor claros."
    )

    prompt = f"""
Eres un analista experto de NBA. Explica el partido con criterio estadístico y lenguaje claro, sin narración vacía ni exageraciones.

REGLAS:
- Usa SOLO estos datos.
- No inventes lesiones, back-to-back, quintetos ni contexto externo.
- No llames "value" a un mercado que no esté en la lista.
- Máximo 260 palabras.

PARTIDO NBA:
Local: {h.name}
Visitante: {a.name}
Ventaja de cancha local: {req.home_court_advantage}

LOCAL:
- OffRtg: {h.off_rating}
- DefRtg: {h.def_rating}
- Pace: {h.pace}
- Puntos: {h.points}
- Rebotes totales: {h.total_rebounds}
- Asistencias: {h.assists}
- Pérdidas: {h.turnovers}
- 3P%: {h.three_pt_pct}
- 3PA: {h.three_pt_attempts}
- Record: {h.wins}-{h.losses}

VISITANTE:
- OffRtg: {a.off_rating}
- DefRtg: {a.def_rating}
- Pace: {a.pace}
- Puntos: {a.points}
- Rebotes totales: {a.total_rebounds}
- Asistencias: {a.assists}
- Pérdidas: {a.turnovers}
- 3P%: {a.three_pt_pct}
- 3PA: {a.three_pt_attempts}
- Record: {a.wins}-{a.losses}

MERCADOS DE VALOR:
{vp_text}
{f'''
CONTEXTO ADICIONAL DEL USUARIO:
{req.user_context}
''' if req.user_context else ''}
FORMATO:
1. Un párrafo sobre el matchup: eficiencia ofensiva, defensa, ritmo y tiro exterior.
2. Un párrafo sobre cómo eso impacta moneyline, spread o total, solo si los datos lo sostienen.
3. Un bloque final "Pronósticos recomendados" con exactamente 2 picks y justificación breve.
Si no hay value claro, dilo en lugar de forzar picks.
"""
    return await _call_openrouter(prompt)


async def generate_tennis_analysis(p1: TennisPlayerStats, p2: TennisPlayerStats, vp: list[ValueIndicator], surface: str = "hard", user_context: str = "") -> str:
    vp_names = ", ".join([v.selection for v in vp]) if vp else "Ninguno claro"
    user_context_section = f'''

CONTEXTO ADICIONAL DEL USUARIO:
{user_context}
''' if user_context else ''
    
    # Preparamos métricas clave para el prompt
    def get_player_stats_text(p: TennisPlayerStats):
        return (
            f"Ranking: {p.rank} | Edad: {p.age} | Altura: {p.height}cm | Mano: {p.hand}\n"
            f"- Servicio: 1ero {p.first_serve_pct}% (W: {p.first_serve_points_won_pct}%) | 2do {p.second_serve_pct}% (W: {p.second_serve_points_won_pct}%)\n"
            f"- Potencia/Error: Aces {p.aces_per_match} | Dobles Faltas {p.double_faults_per_match}\n"
            f"- Presión: BP Salvados {p.break_points_saved}/{p.break_points_saved_total} ({ (p.break_points_saved/max(p.break_points_saved_total,1))*100:.1f}%) | "
            f"BP Convertidos {p.break_points_converted}/{p.break_points_converted_total} ({ (p.break_points_converted/max(p.break_points_converted_total,1))*100:.1f}%)\n"
            f"- Clutch: Tiebreaks {p.tiebreaks_won}/{p.tiebreaks_total} | Win% Sup {surface}: {(p.matches_on_surface_won/max(p.total_matches_on_surface,1))*100:.1f}%"
        )

    p1_stats = get_player_stats_text(p1)
    p2_stats = get_player_stats_text(p2)

    prompt = f"""Eres un analista experto del circuito profesional de tenis (ATP/WTA).
Analiza el enfrentamiento entre {p1.name} y {p2.name} en superficie {surface}.

DATOS TÉCNICOS:
--- {p1.name} ---
{p1_stats}

--- {p2.name} ---
{p2_stats}

VALORES DETECTADOS POR EL MODELO: {vp_names}
{user_context_section}

REGLAS DE ANÁLISIS:
1. Evalúa el "Matchup" técnico: ¿Cómo influye la altura o la mano dominante? ¿Quién tiene mejor servicio y quién es más sólido bajo presión (break points/tiebreaks)?
2. Factor Superficie: Analiza quién se adapta mejor a {surface} según sus porcentajes históricos.
3. Propón exactamente 2 pronósticos (tips) basados en los datos. No inventes lesiones ni rumores.

ESTILO: Profesional, técnico, con emojis 🎾📉. Máximo 400 palabras.
"""
    return await _call_openrouter(prompt)



async def _safe_generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    league_stats: LeagueStats,
    competition: str,
    user_context: str = ""
) -> str:
    try:
        return await generate_football_analysis(h, a, vp, proj, league_stats, competition, user_context)
    except Exception as e:
        print(f"LLM generation failed: {e}")
        return PLACEHOLDER_FOOTBALL

async def _safe_generate_nba_analysis(h: NBATeamStats, a: NBATeamStats, vp: list[ValueIndicator], req: NBACompareRequest) -> str:
    try:
        return await generate_nba_analysis(h, a, vp, req)
    except Exception:
        return PLACEHOLDER_NBA


async def _safe_generate_tennis_analysis(p1: TennisPlayerStats, p2: TennisPlayerStats, vp: list[ValueIndicator], surface: str, user_context: str = "") -> str:
    try:
        return await generate_tennis_analysis(p1, p2, vp, surface, user_context)
    except Exception:
        return PLACEHOLDER_TENNIS


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

    h_prob = markets["home_win_pct"] / 100.0
    d_prob = markets["draw_pct"]     / 100.0
    a_prob = markets["away_win_pct"] / 100.0
    p_btts_yes = markets["btts_yes_pct"] / 100.0
    p_btts_no  = markets["btts_no_pct"]  / 100.0

    # ── FIX 1: Blend con prior histórico de la liga (30% de peso) ──────────
    # Ancla las probabilidades a la distribución real de la competición para evitar
    # sobre-confianza en los números de corto plazo de los equipos.
    _BLEND_W = 0.70  # 70% modelo, 30% prior de liga
    _prior_sum = req.league_stats.home_win_pct + req.league_stats.draw_pct + req.league_stats.away_win_pct
    if _prior_sum > 0:
        _ph = req.league_stats.home_win_pct / _prior_sum
        _pd = req.league_stats.draw_pct     / _prior_sum
        _pa = req.league_stats.away_win_pct / _prior_sum
        h_prob = h_prob * _BLEND_W + _ph * (1.0 - _BLEND_W)
        d_prob = d_prob * _BLEND_W + _pd * (1.0 - _BLEND_W)
        a_prob = a_prob * _BLEND_W + _pa * (1.0 - _BLEND_W)

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

    # market: (sel, odds, model_prob, overround, push_prob)
    market_configs: list[tuple[str, float | None, float, float, float]] = [
        ("Local",     req.odds.home,     h_prob     * 100, _or_1x2, 0.0),
        ("Empate",    req.odds.draw,     d_prob     * 100, _or_1x2, 0.0),
        ("Visitante", req.odds.away,     a_prob     * 100, _or_1x2, 0.0),
        ("BTTS Sí",   req.odds.btts_yes, p_btts_yes * 100, _or_btts, 0.0),
        ("BTTS No",   req.odds.btts_no,  p_btts_no  * 100, _or_btts, 0.0),
    ]

    projected_lines: list[ProjectedLine] = []
    projected_total_goals = h_lam + a_lam

    projected_lines.append(ProjectedLine(
        label="Goles Totales (λ)", value=round(projected_total_goals, 2),
        type="goals", prob=None
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
        llm = await generate_football_analysis(h, a, vp, projected_lines, req.league_stats, competition=req.competition_name)

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
        comparisons=comparisons,
        values=values,
        projected_lines=projected_lines,
        summary=summary,
        llm_analysis=llm,
    )


# ───────────────────────────────────────────────────────────────
# compare_nba
# ───────────────────────────────────────────────────────────────
async def compare_nba(req: NBACompareRequest) -> CompareResponse:
    h, a = req.home, req.away

    # Comparaciones de stats — MISMO ORDEN QUE TU LISTA
    comparisons = [
        # Generales / resultado
        _stat_comparison("Puntos por partido",              "points",               h.points,               a.points),
        _stat_comparison("Puntos permitidos por partido",   "points_against",       h.points_against,       a.points_against, False),
        _stat_comparison("Asistencias por partido",         "assists",              h.assists,              a.assists),
        _stat_comparison("Ratio AST/Pérdidas",              "ast_to_ratio",         h.ast_to_ratio,         a.ast_to_ratio),

        # Tiros de campo
        _stat_comparison("TC anotados por partido",         "fg_made",              h.fg_made,              a.fg_made),
        _stat_comparison("TC intentados por partido",       "fg_attempted",         h.fg_attempted,         a.fg_attempted),
        _stat_comparison("% tiros de campo",                "fg_pct",               h.fg_pct,               a.fg_pct),

        # Triples
        _stat_comparison("Triples anotados por partido",    "three_pt_made",        h.three_pt_made,        a.three_pt_made),
        _stat_comparison("Triples intentados por partido",  "three_pt_attempted",   h.three_pt_attempted,   a.three_pt_attempted),
        _stat_comparison("% de triples",                    "three_pt_pct",         h.three_pt_pct,         a.three_pt_pct),

        # Tiros libres
        _stat_comparison("TL anotados por partido",         "ft_made",              h.ft_made,              a.ft_made),
        _stat_comparison("TL intentados por partido",       "ft_attempted",         h.ft_attempted,         a.ft_attempted),
        _stat_comparison("% tiros libres",                  "ft_pct",               h.ft_pct,               a.ft_pct),

        # Eficiencia tiro
        _stat_comparison("Porcentaje tiro efectivo (eFG%)", "efg_pct",              h.efg_pct,              a.efg_pct),
        _stat_comparison("Porcentaje tiro real (TS%)",      "ts_pct",               h.ts_pct,               a.ts_pct),

        # Rebotes
        _stat_comparison("Rebotes ofensivos por partido",   "off_rebounds",         h.off_rebounds,         a.off_rebounds),
        _stat_comparison("Rebotes defensivos por partido",  "def_rebounds",         h.def_rebounds,         a.def_rebounds),
        _stat_comparison("Rebotes totales por partido",     "total_rebounds",       h.total_rebounds,       a.total_rebounds),

        # Defensa
        _stat_comparison("Tapones por partido",             "blocks",               h.blocks,               a.blocks),
        _stat_comparison("Robos por partido",               "steals",               h.steals,               a.steals),
        _stat_comparison("% triples permitidos",            "three_pt_pct_allowed", h.three_pt_pct_allowed, a.three_pt_pct_allowed, False),

        # Control balón / ritmo / ratings
        _stat_comparison("Pérdidas por partido",            "turnovers",            h.turnovers,            a.turnovers, False),
        _stat_comparison("Ritmo",                           "pace",                 h.pace,                 a.pace),
        _stat_comparison("Valoración ofensiva",             "off_rating",           h.off_rating,           a.off_rating),
        _stat_comparison("Valoración defensiva",            "def_rating",           h.def_rating,           a.def_rating, False),
        _stat_comparison("Valoración neta",                 "net_rating",           h.net_rating,           a.net_rating),

        # Record / standings
        _stat_comparison("Partidos jugados",                "games_played",         float(h.games_played),  float(a.games_played)),
        _stat_comparison("Partidos ganados",                "wins",                 float(h.wins),          float(a.wins)),
        _stat_comparison("Partidos perdidos",               "losses",               float(h.losses),        float(a.losses), False),
        _stat_comparison("Diferencia de puntos",            "point_diff",           h.point_diff,           a.point_diff),
        _stat_comparison("PA (Puntos permitidos)",          "pa",                   h.points_against,       a.points_against, False),
        _stat_comparison("PCT (Win%)",                      "win_pct",              h.win_pct,              a.win_pct),
    ]

    # --- Proyecciones usando solo stats dadas + HCA ---
    proj_pace = (h.pace + a.pace) / 2.0

    # Ajuste por HCA como boost directo a puntos esperados locales
    hca_boost = req.home_court_advantage

    # Usamos ofensiva propia + defensiva rival, escalado por ritmo
    h_base = (h.off_rating + a.def_rating) / 2.0
    a_base = (a.off_rating + h.def_rating) / 2.0

    h_proj_pts = (h_base + hca_boost) * (proj_pace / 100.0)
    a_proj_pts = (a_base) * (proj_pace / 100.0)

    total_proj = h_proj_pts + a_proj_pts
    spread_proj = h_proj_pts - a_proj_pts  # >0: local favorito

    # Probabilidades ML via función logística en el spread
    k_ml = 0.17
    h_prob = 100.0 / (1.0 + math.exp(-k_ml * spread_proj))
    a_prob = 100.0 - h_prob

    # Prob O/U usando logística sobre diferencia total proyectado vs línea
    p_over = 50.0
    p_under = 50.0
    if req.odds.total_line is not None:
        k_total = 0.13
        diff_total = total_proj - req.odds.total_line
        p_over = 100.0 / (1.0 + math.exp(-k_total * diff_total))
        p_under = 100.0 - p_over

    # Prob spread local vs línea de handicap
    p_h_spread = 50.0
    p_a_spread = 50.0
    if req.odds.spread_line is not None:
        k_spread = 0.18
        # línea es para el local, ej -5.5; ajustamos con spread justo del modelo
        diff_spread = spread_proj - (-req.odds.spread_line)
        p_h_spread = 100.0 / (1.0 + math.exp(-k_spread * diff_spread))
        p_a_spread = 100.0 - p_h_spread

    # --- Mercados / Value ---
    market: list[tuple[str, float | None, float]] = [
        ("Ganador (Local)",     req.odds.home, h_prob),
        ("Ganador (Visitante)", req.odds.away, a_prob),
    ]

    if req.odds.total_line is not None:
        market.append((f"Over {req.odds.total_line}",  req.odds.over_odds,  p_over))
        market.append((f"Under {req.odds.total_line}", req.odds.under_odds, p_under))

    if req.odds.spread_line is not None:
        market.append((f"Handicap Local ({req.odds.spread_line:+.1f})",   req.odds.home_spread_odds, p_h_spread))
        market.append((f"Handicap Visitante ({-req.odds.spread_line:+.1f})", req.odds.away_spread_odds, p_a_spread))

    values = [_value_indicator(sel, odds, mp) for sel, odds, mp in market]
    for v in values:
        v.strategic_score = _frontend_style_strategic_score(v)
        v.quality_score = v.strategic_score # Para NBA usamos el mismo score estratégico como calidad base
        v.is_value = v.strategic_score >= 0

    # --- Projected Lines (derivadas solo de stats) ---
    projected_lines = [
        ProjectedLine(label="Total Puntos",      value=round(total_proj, 1), type="total",    prob=round(p_over, 1)),
        ProjectedLine(label="Spread (Local)",    value=round(-spread_proj, 1), type="handicap", prob=round(p_h_spread, 1)),
        ProjectedLine(label=f"Total {h.name}",   value=round(h_proj_pts, 1), type="team_total"),
        ProjectedLine(label=f"Total {a.name}",   value=round(a_proj_pts, 1), type="team_total"),
        ProjectedLine(label="Ritmo Esperado",    value=round(proj_pace, 1),  type="pace"),
    ]

    vp = [v for v in values if v.is_value]
    summary = (
        f"Sherlock NBA | Puntos Proyectados: {h.name} {h_proj_pts:.1f} - {a.name} {a_proj_pts:.1f}\n"
        f"Total Proyectado: {total_proj:.1f} | Ritmo: {proj_pace:.1f} posesiones\n"
        f"Handicap Estimado: {h.name} {-spread_proj:+.1f}\n"
        + (f"✅ Value detectado en: {', '.join(v.selection for v in vp)}"
           if vp else "⚖️ Sin value claro en las cuotas actuales.")
    )

    llm = None

    return CompareResponse(
        sport="nba",
        home_name=h.name,
        away_name=a.name,
        comparisons=comparisons,
        values=values,
        projected_lines=projected_lines,
        summary=summary,
        llm_analysis=llm,
    )


# ───────────────────────────────────────────────────────────────
# compare_tennis
# ───────────────────────────────────────────────────────────────
async def compare_tennis(req: TennisCompareRequest) -> CompareResponse:
    p1, p2 = req.player1, req.player2

    comparisons = [
        # Perfil
        _stat_comparison("Edad",                "age",               float(p1.age),               float(p2.age), False),
        _stat_comparison("Altura (cm)",         "height",            float(p1.height),            float(p2.height)),
        _stat_comparison("Ranking ATP",         "rank",              float(p1.rank),              float(p2.rank), False),
        # Performance
        _stat_comparison("Global: Ganados %",   "win_pct_total",      (p1.matches_won / max(p1.total_matches, 1)) * 100, (p2.matches_won / max(p2.total_matches, 1)) * 100),
        _stat_comparison("Torneos Ganados",    "tournaments_won",   float(p1.tournaments_won),   float(p2.tournaments_won)),
        # Service
        _stat_comparison("% 1er Servicio",     "first_serve_pct",   p1.first_serve_pct,          p2.first_serve_pct),
        _stat_comparison("% Pts 1er Serv",     "first_serve_points_won_pct",  p1.first_serve_points_won_pct,  p2.first_serve_points_won_pct),
        _stat_comparison("% Pts 2do Serv",     "second_serve_points_won_pct", p1.second_serve_points_won_pct, p2.second_serve_points_won_pct),
        _stat_comparison("Aces/Partido",       "aces_per_match",    p1.aces_per_match,           p2.aces_per_match),
        _stat_comparison("DF/Partido",         "double_faults_per_match", p1.double_faults_per_match, p2.double_faults_per_match, False),
        # Pressure
        _stat_comparison("% BP Salvados",       "bp_saved_pct",       (p1.break_points_saved / max(p1.break_points_saved_total, 1)) * 100, (p2.break_points_saved / max(p2.break_points_saved_total, 1)) * 100),
        _stat_comparison("% BP Convertidos",   "bp_conv_pct",        (p1.break_points_converted / max(p1.break_points_converted_total, 1)) * 100, (p2.break_points_converted / max(p2.break_points_converted_total, 1)) * 100),
        _stat_comparison("% Tiebreaks Ganados","tiebreaks_won_pct",  (p1.tiebreaks_won / max(p1.tiebreaks_total, 1)) * 100, (p2.tiebreaks_won / max(p2.tiebreaks_total, 1)) * 100),
        _stat_comparison("Win % Superficie",   "surface_win_pct",   (p1.matches_on_surface_won / max(p1.total_matches_on_surface, 1)) * 100, (p2.matches_on_surface_won / max(p2.total_matches_on_surface, 1)) * 100),
    ]

    # --- Motor de Probabilidades de Tenis (O'Malley / Barnett) ---
    p1_prob = _tennis_match_win_prob(p1, p2, surface=req.surface)
    p2_prob = 100.0 - p1_prob

    # --- Values ---
    market = [
        (p1.name, req.odds.player1, p1_prob),
        (p2.name, req.odds.player2, p2_prob),
    ]
    
    values = [_value_indicator(sel, odds, mp) for sel, odds, mp in market]
    for v in values:
        v.strategic_score = _frontend_style_strategic_score(v)
        v.quality_score = v.strategic_score
        v.is_value = v.strategic_score >= 10 

    # --- LLM Analysis ---
    llm = None
    if req.generate_llm_analysis:
        llm = await _safe_generate_tennis_analysis(p1, p2, [v for v in values if v.is_value], req.surface, req.user_context)

    # --- Resumen ---
    p1a = sum(1 for c in comparisons if c.advantage == "home")
    p2a = sum(1 for c in comparisons if c.advantage == "away")
    vp  = [v for v in values if v.is_value]
    
    summary = (
        f"Sherlock Tennis | Proyección: {p1.name} {p1_prob:.1f}% vs {p2.name} {p2_prob:.1f}%\n"
        f"{p1.name} domina {p1a} métricas, {p2.name} {p2a}.\n"
        + (f"✅ Value en: {', '.join(v.selection for v in vp)}." if vp else "⚖️ Sin value claro.")
    )

    return CompareResponse(
        sport="tennis",
        home_name=p1.name,
        away_name=p2.name,
        comparisons=comparisons,
        values=values,
        summary=summary,
        llm_analysis=llm,
    )


    