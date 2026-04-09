from __future__ import annotations
from enum import Enum
from typing import Optional
import os, math
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
def _value_indicator(sel, odds, modelp, market_overround=None):
    if odds is None:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1))
    raw_implied = (1.0 / odds) * 100.0
    # Quitar el margen antes de calcular edge
    fair_implied = raw_implied / ((market_overround or 100.0) / 100.0)
    edge = modelp - fair_implied
    is_value = edge > 2.0
    
    if   edge > 5.0:  rating = "🔥 STRONG VALUE"
    elif edge > 2.0:  rating = "✅ VALUE"
    elif edge > -1.0: rating = "⚖️ NEUTRAL"
    else:             rating = "❌ NO VALUE"
    
    return ValueIndicator(
        selection=sel,
        odds=odds,
        implied_prob=round(fair_implied, 1),
        model_prob=round(modelp, 1),
        edge=round(edge, 1),
        is_value=is_value,
        rating=rating,
    )


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
    if is_home:
        # El atacante es local, el defensor es visita
        att_n = max(attacker.matches_home, 1)
        prior_att_xg = attacker.xg_per_game
        actual_att_g = attacker.goals_per_game

        def_n = max(defender.matches_away, 1)
        prior_def_xga = defender.xga_per_game
        actual_def_g = defender.goals_conceded_per_game
    else:
        # El atacante es visita, el defensor es local
        att_n = max(attacker.matches_away, 1)
        prior_att_xg = attacker.xg_per_game
        actual_att_g = attacker.goals_per_game

        def_n = max(defender.matches_home, 1)
        prior_def_xga = defender.xga_per_game
        actual_def_g = defender.goals_conceded_per_game

    # beta_prior representa cuántos "partidos de peso" le damos a la estadística subyacente (xG / xGA)
    beta_prior = 4.0 

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

    # ── 5. Señales Tácticas Adicionales (Opcional) ──
    bc_signal = attacker.big_chances_per_game / max(attacker.big_chances_missed_per_game + 0.5, 0.5)
    tactical_mult = 1.0 + (min(bc_signal, 2.5) - 1.0) * 0.12
    lam_adjusted = lam_base * tactical_mult

    # ── 6. Shrinkage Global a la Liga ──
    # Actúa como seguro de "Regresión a la Media" cuando la muestra segmentada (Local/Visita) es muy pequeña
    total_n = min(att_n, def_n)
    prior_league_n = max(0.5, 3.0 - (total_n / 10.0))
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
    Considera:
    - Generación propia (Corners y Centros)
    - Propensión del rival a conceder (Corners concedidos)
    - Ventaja de local
    """
    avg_team_corners = league.avg_corners_per_game / 2.0

    # 70% corners históricos, 30% basado en centros efectivos
    # (Los equipos que centran mucho suelen forzar más despejes a corner)
    gen_str = (team.corners_per_game * 0.7) + (team.crosses_per_game * 0.3)
    
    # Capacidad del rival de conceder corners (normalizado al promedio liga)
    opp_def_weakness = opponent.corners_conceded_per_game / max(avg_team_corners, 1.0)

    # Lambda base cruzada
    lam = gen_str * opp_def_weakness

    # Shrinkage
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
    # En vez de multiplicar ciegamente, medimos cuánto se desvía del promedio (12.5)
    foul_deviation = (team.fouls_per_game - 12.5) / 12.5
    # Solo permitimos que las faltas modifiquen el promedio un máximo de ±15%
    foul_modifier = 1.0 + (foul_deviation * 0.15)

    # 3. Ajuste por inducción del rival (Duelos/Posesión)
    # Medimos la desviación en lugar del valor absoluto
    poss_deviation = (opponent.possession_pct - 50.0) / 50.0
    duel_deviation = (opponent.ground_duels_won_per_game - 10.0) / 10.0
    
    # Solo permitimos que el rival modifique las tarjetas un máximo de ±15%
    rival_modifier = 1.0 + (poss_deviation * 0.05) + (duel_deviation * 0.10)
    
    # Limitamos los modificadores a un techo lógico (max 25% de alteración total)
    total_modifier = max(0.75, min(1.25, foul_modifier * rival_modifier))

    # 4. Cálculo del lambda del equipo
    lam = own_cards_avg * total_modifier

    # 5. Shrinkage (Regresión a la media)
    avg_team_cards = league.avg_cards_per_game / 2.0
    prior_n = 5.0 # Mayor peso al promedio de la liga para estabilizar
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


def _compute_handicap_probabilities(
    h_lam: float,
    a_lam: float,
    handicap_line: float,
) -> tuple[float, float]:
    """
    Calcula probabilidades de cubrir handicap.
    Retorna (p_home_covers, p_away_covers)

    handicap_line: línea de handicap para el local
    - Si handicap_line = -1.5, local necesita ganar por 2+ para cubrir
    - Si handicap_line = +0.5, local puede ganar o empatar
    """
    matrix, _ = _dc_score_matrix(h_lam, a_lam)
    max_goals = len(matrix) - 1

    p_home_covers = 0.0
    p_away_covers = 0.0

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = matrix[i][j]
            margin = i - j

            # Si línea es -1.5, home necesita margin > -1.5 (es decir, margin >= -1)
            # Pero en apuestas: cubrir significa ganar por más de la línea
            # handicap_line negativo = favorito local
            if handicap_line < 0:
                # Local es favorito, necesita ganar por más del valor absoluto
                if margin > abs(handicap_line):
                    p_home_covers += p
                elif margin < handicap_line:
                    p_away_covers += p
            else:
                # Visitante es favorito (línea positiva para local)
                if margin > handicap_line:
                    p_home_covers += p
                elif margin < -handicap_line:
                    p_away_covers += p

    return p_home_covers * 100.0, p_away_covers * 100.0


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

    # Rho menos conservador para favorecer victorias claras
    if total <= 1.80:
        return -0.08
    elif total <= 2.40:
        return -0.06
    elif total <= 3.00:
        return -0.04
    else:
        return -0.02


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
    # Corners generados / corners concedidos cruzados (Simplificado a medias)
    # Asumimos que los corners concedidos son proporcionales a la defensa
    avg_team_corners = league.avg_corners_per_game / 2.0
    
    h_att_c = h.corners_per_game / max(avg_team_corners, 1.0)
    a_att_c = a.corners_per_game / max(avg_team_corners, 1.0)
    
    # Lambda = (Fuerza generacion Local * Defensa Visita) + (Fuerza generacion Visita * Defensa Local)
    # Como no tenemos "corners concedidos", usamos posesión como proxy táctico
    h_poss_share = h.possession_pct / max((h.possession_pct + a.possession_pct), 1.0)
    a_poss_share = a.possession_pct / max((h.possession_pct + a.possession_pct), 1.0)
    
    h_exp_corners = h.corners_per_game * h_poss_share * 2.0
    a_exp_corners = a.corners_per_game * a_poss_share * 2.0
    
    lam_corners = (h_exp_corners + a_exp_corners)
    
    # Fallback de seguridad al promedio de la liga si la data está mal
    if lam_corners < 2.0: lam_corners = league.avg_corners_per_game
    return lam_corners


def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats) -> float:
    # Normalizar tarjetas sumando rojas (ponderadas más alto)
    h_cards = h.yellow_cards_per_game + (h.red_cards_total / max(h.matches_played, 1)) * 2.0
    a_cards = a.yellow_cards_per_game + (a.red_cards_total / max(a.matches_played, 1)) * 2.0
    
    # Faltas cometidas vs promedio estimado (12 faltas por equipo = 24 totales)
    h_foul_agg = h.fouls_per_game / 12.0
    a_foul_agg = a.fouls_per_game / 12.0
    
    # Promedio base del partido
    base_match_cards = h_cards + a_cards
    
    # Ajuste por agresividad
    h_foul_factor = h.fouls_per_game / 12.0
    a_foul_factor = a.fouls_per_game / 12.0
    foul_adj = (h_foul_factor + a_foul_factor) / 2.0
    # Cuando fouls=12 → foul_adj=1.0 → sin cambio; cuando fouls=6 → reduce 15%
    lam_cards = base_match_cards * (0.7 + 0.3 * foul_adj * 2.0)
    lam_cards = max(lam_cards, league.avg_cards_per_game * 0.6)
    
    # Fallback al promedio de liga
    if lam_cards < 1.0: lam_cards = league.avg_cards_per_game
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


def _poisson_over_under(lam: float, line: float, max_k: int = 30) -> tuple[float, float]:
    """
    Devuelve (p_over, p_under) en porcentaje.
    Matemáticamente seguro para líneas enteras (e.g. 9.0) y medias (9.5).
    """
    p_under = 0.0
    p_over  = 0.0
    
    floor_line = math.floor(line)
    ceil_line = math.ceil(line)
    
    for k in range(max_k + 1):
        p = _poisson_pmf(lam, k)
        if k < line:
            p_under += p
        elif k > line:
            p_over += p
        # Si k == line exacto (ej. línea 9.0 y salen 9), en apuestas es PUSH (Void).
        # Ese % se excluye del over y del under, por lo que al normalizar se reparte.
            
    total = p_under + p_over
    if total == 0: return 50.0, 50.0 # Fallback
    
    return (p_over / total) * 100.0, (p_under / total) * 100.0


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
                max_tokens=3000,
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


def _rate_pick_quality(v: ValueIndicator) -> int:
    """
    Replica la lógica de filtrado del frontend para asegurar que el LLM 
    solo reciba picks verdaderamente viables y rentables.
    """
    edge = v.edge
    odds = v.odds if v.odds is not None else 0.0
    prob = v.model_prob
    sel = (v.selection or "").lower()

    # Filtro 1: Descartar edge negativo, muy bajo o cuotas inválidas
    if edge < 2.0 or odds <= 1.01:
        return -1

    score = 0

    # Filtro 2: Rango Dorado de Cuotas (1.50 - 2.50)
    if 1.50 <= odds <= 2.50:
        score += 50
    elif 2.50 < odds <= 3.50:
        score += 20
    else:
        score -= 30

    # Filtro 3: Filtro de Ruido (Eventos cercanos al 50/50)
    if 45.0 <= prob <= 55.0:
        if edge < 5.0:
            return -1
        else:
            score += 10

    # Filtro 4: Identificación de Mercados Secundarios y Anomalías
    is_secondary = "corner" in sel or "tarjeta" in sel

    if is_secondary:
        if edge < 6.0:
            return -1
        else:
            score += int(edge * 1.5)
    else:
        if edge > 20.0:
            score -= 50
        else:
            score += int(edge * 2)

    return score

async def generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    competition: str = "Desconocida",
    user_context: str = "",
) -> str:
   
    # ── NUEVO: Filtramos y ordenamos los picks antes de dárselos al LLM ──
    # Creamos tuplas de (pick, score)
    scored_picks = [(v, _rate_pick_quality(v)) for v in vp]
    # Filtramos los que tienen score negativo (descartados)
    valid_picks = [(v, score) for v, score in scored_picks if score >= 0]
    # Ordenamos de mejor a peor pick
    valid_picks.sort(key=lambda x: x[1], reverse=True)
    # Extraemos solo los objetos ValueIndicator de los mejores 6 picks
    top_filtered_vp = [p[0] for p in valid_picks[:6]]


    # Armamos el texto solo con los picks filtrados
    vp_text = (
        "\n".join(
            [
                f"- {v.selection}: cuota={v.odds if v.odds is not None else 'N/A'} | modelo={v.model_prob:.1f}% | edge={v.edge:.1f}% | rating={v.rating}"
                for v in top_filtered_vp
            ]
        )
        if top_filtered_vp
        else "- No hay mercados de valor claros. Aclara que no recomiendas apostar en este partido."
    )


    proj_text = (
        "\n".join(
            [
                f"- {p.label}: {p.value:.2f}" + (f" | prob={p.prob:.1f}%" if p.prob is not None else "")
                for p in proj[:10]
            ]
        )
        if proj
        else "- No hay líneas proyectadas disponibles."
    )

    additional_context = f"\nCONTEXTO ADICIONAL DEL USUARIO:\n{user_context}\n" if user_context else ""

    prompt = f"""
Eres un analista táctico y de apuestas de élite. Tu trabajo es explicar el partido con claridad, criterio estadístico y lenguaje natural, sin exagerar ni repetir números innecesariamente.

REGLAS:
- Usa SOLO la información entregada.
- No inventes lesiones, rachas recientes, contexto histórico ni alineaciones.
- No digas que un mercado tiene valor si no aparece en "MERCADOS DE VALOR".
- Si no hay value claro, dilo explícitamente y no fuerces ningún pick.
- Sé concreto: máximo 360 palabras.
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

PARTIDO:
Competencia: {competition}
Local: {h.name}
Visitante: {a.name}

SEÑALES CLAVE LOCAL:
- Partidos jugados: {h.matches_played}
- Victorias: {h.wins} | Empates: {h.draws} | Derrotas: {h.losses}
- Goles p/j: {h.goals_per_game} | Goles concedidos p/j: {h.goals_conceded_per_game}
- xG (Goles Esperados) p/j: {h.xg_per_game} | xGA (Goles Esperados en Contra) p/j: {h.xga_per_game}
- Grandes chances creadas p/j: {h.big_chances_per_game}
- Tiros totales p/j: {h.shots_per_game} | Tiros a puerta p/j: {h.shots_on_target_per_game}
- Posesión: {h.possession_pct}%
- Pases Totales (Intentados) p/j: {h.passes_total_per_game} | Completados: {h.passes_completed} ({h.pass_accuracy}%)
- Pases en Campo Rival (Intentados) p/j: {h.passes_opp_half_total_per_game} | Completados: {h.passes_opp_half} ({h.pass_accuracy_opp_half}%)
- Centros (Intentados) p/j: {h.crosses_total_per_game} | Completados: {h.crosses_per_game} ({h.cross_accuracy}%)
- Corners p/j: {h.corners_per_game} | Corners concedidos p/j: {h.corners_conceded_per_game}
- Disciplina: {h.yellow_cards_per_game} Amarillas p/j | {h.fouls_per_game} Faltas p/j | {h.red_cards_total} Rojas
- Defensa: {h.clean_sheets}/{h.matches_played} Vallas invictas | {h.saves_per_game} Paradas p/j | {h.balls_recovered_per_game} Recuperaciones p/j
- Errores que llevan a gol: {h.errors_leading_to_goal} | Penales concedidos: {h.penalties_conceded}

SEÑALES CLAVE VISITANTE:
- Partidos jugados: {a.matches_played}
- Victorias: {a.wins} | Empates: {a.draws} | Derrotas: {a.losses}
- Goles p/j: {a.goals_per_game} | Goles concedidos p/j: {a.goals_conceded_per_game}
- xG (Goles Esperados) p/j: {a.xg_per_game} | xGA (Goles Esperados en Contra) p/j: {a.xga_per_game}
- Grandes chances creadas p/j: {a.big_chances_per_game}
- Tiros totales p/j: {a.shots_per_game} | Tiros a puerta p/j: {a.shots_on_target_per_game}
- Posesión: {a.possession_pct}%
- Pases Totales (Intentados) p/j: {a.passes_total_per_game} | Completados: {a.passes_completed} ({a.pass_accuracy}%)
- Pases en Campo Rival (Intentados) p/j: {a.passes_opp_half_total_per_game} | Completados: {a.passes_opp_half} ({a.pass_accuracy_opp_half}%)
- Centros (Intentados) p/j: {a.crosses_total_per_game} | Completados: {a.crosses_per_game} ({a.cross_accuracy}%)
- Corners p/j: {a.corners_per_game} | Corners concedidos p/j: {a.corners_conceded_per_game}
- Disciplina: {a.yellow_cards_per_game} Amarillas p/j | {a.fouls_per_game} Faltas p/j | {a.red_cards_total} Rojas
- Defensa: {a.clean_sheets}/{a.matches_played} Vallas invictas | {a.saves_per_game} Paradas p/j | {a.balls_recovered_per_game} Recuperaciones p/j
- Errores que llevan a gol: {a.errors_leading_to_goal} | Penales concedidos: {a.penalties_conceded}

LÍNEAS PROYECTADAS:
{proj_text}

MERCADOS DE VALOR:
{vp_text}
{additional_context}

FORMATO DE RESPUESTA:
1. Un primer párrafo explicando el choque táctico: quién debería controlar, quién genera más peligro y dónde puede estar la ventaja.
2. Un segundo párrafo evaluando goles, BTTS, corners y tarjetas solo si las proyecciones y estadísticas lo justifican.
3. Un bloque final llamado "Pronósticos recomendados".
4. Incluye HASTA 2 picks, nunca más.
5. Esos picks deben ser los 2 mercados más sólidos, más probables y mejor sustentados del partido entre los mercados disponibles.
6. No elijas picks solo por tener edge alto.
7. Para cada pick escribe exactamente:
   - pick
   - probabilidad de modelo e implícita de casa
   - justificación breve basada en estadísticas
   - respaldo de la proyección
   - por qué además tiene valor
8. Si solo existe 1 pick realmente sólido, da solo 1.
9. Si no hay picks suficientemente sólidos, di claramente que no recomiendas apostar en este partido.
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
    prompt = f"""Eres un comentarista y analista de élite del circuito ATP/WTA. Habla con emoción y lenguaje técnico de tenis.

SUPERFICIE: {surface}

DATOS DEL ENFRENTAMIENTO:
JUGADOR 1 ({p1.name}): WinPct={(max(p1.matches_won, 0)/max(p1.total_matches, 1))*100:.1f}% | WinPct Surface={(max(p1.matches_on_surface_won, 0)/max(p1.total_matches_on_surface, 1))*100:.1f}% | 1erServ={p1.first_serve_pct}% | BreakPointsSaved={p1.break_points_saved}/{max(p1.break_points_saved_total, 1)} | H2H Won={p1.head_to_head_won}/{max(p1.total_head_to_head, 1)}
JUGADOR 2 ({p2.name}): WinPct={(max(p2.matches_won, 0)/max(p2.total_matches, 1))*100:.1f}% | WinPct Surface={(max(p2.matches_on_surface_won, 0)/max(p2.total_matches_on_surface, 1))*100:.1f}% | 1erServ={p2.first_serve_pct}% | BreakPointsSaved={p2.break_points_saved}/{max(p2.break_points_saved_total, 1)} | H2H Won={p2.head_to_head_won}/{max(p2.total_head_to_head, 1)}
MERCADOS DE VALOR DETECTADOS: {vp_names}
{user_context_section}
INSTRUCCIONES:
1. Redacta un análisis narrativo (2-3 párrafos cortos) resaltando la solidez al servicio de cada uno, rendimientos bajo presión (break points, tiebreaks) y estado de forma general en esta superficie.
2. Al final, incluye 2 PRONÓSTICOS O TIPS recomendados basados en la estadística y en los mercados de valor detectados.
Usa emojis como 🎾🔥 para ilustrar."""
    return await _call_openrouter(prompt)


async def _safe_generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    competition: str,
    user_context: str = ""
) -> str:
    try:
        return await generate_football_analysis(h, a, vp, proj, competition, user_context)
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

    h_lam = _compute_lambda_v2(h, a, req.league_stats, is_home=True)
    a_lam = _compute_lambda_v2(a, h, req.league_stats, is_home=False)
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

    # ── FIX 1: Blend con prior histórico de la liga (18% de peso) ──────────
    # Ancla las probabilidades a la distribución real de la competición,
    # especialmente útil con pocas jornadas disputadas.
    _BLEND_W = 0.82  # 82% modelo, 18% prior de liga
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

    def _vi(sel: str, odds: float | None, modelp: float, overround: float = 100.0) -> ValueIndicator:
        """
        Calcula ValueIndicator usando la implied probability REAL.
        El Edge es la ventaja real sobre lo que paga la casa, asumiendo su margen.
        """
        if odds is None:
            return ValueIndicator(selection=sel, model_prob=round(modelp, 1))

        # 1. La probabilidad que necesitas para empatar (Break-even)
        raw_implied  = (1.0 / odds) * 100.0
        
        # 2. La probabilidad "justa" sin el margen de la casa (Opcional, solo para análisis)
        fair_implied = raw_implied / (overround / 100.0) 

        # 3. EL CAMBIO CRÍTICO: Calculamos el Edge contra la cuota real
        edge = modelp - raw_implied
        is_value = edge > 0.0  # Solo hay valor si superamos el margen de la casa

        # Reajustamos los rangos porque un Edge real del 5% es altísimo
        if   edge > 8.0:  rating = "🔥 STRONG VALUE"
        elif edge > 3.0:  rating = "✅ VALUE"
        elif edge > 0.0:  rating = "⚖️ MARGINAL VALUE"
        else:             rating = "❌ NO VALUE"

        return ValueIndicator(
            selection=sel,
            odds=odds,
            # Es mejor mandar la raw_implied al frontend para que el usuario 
            # vea exactamente qué porcentaje necesita superar para ser rentable
            implied_prob=round(raw_implied, 1), 
            model_prob=round(modelp, 1),
            edge=round(edge, 1),
            is_value=is_value,
            rating=rating,
        )

    # ── FIX 3: market incluye overround por grupo de mercado ────────────────
    # Cada grupo (1X2, BTTS, Goals O/U, Corners O/U, Cards O/U) tiene su propio
    # overround calculado sólo con las cuotas disponibles de ese grupo.
    _or_1x2  = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    # market: (sel, odds, model_prob, overround_del_mercado)
    market: list[tuple[str, float | None, float, float]] = [
        ("Local",     req.odds.home,     h_prob     * 100, _or_1x2),
        ("Empate",    req.odds.draw,     d_prob     * 100, _or_1x2),
        ("Visitante", req.odds.away,     a_prob     * 100, _or_1x2),
        ("BTTS Sí",   req.odds.btts_yes, p_btts_yes * 100, _or_btts),
        ("BTTS No",   req.odds.btts_no,  p_btts_no  * 100, _or_btts),
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

    # ── Over/Under GOLES: múltiples líneas ─────────────────────
    for line in req.odds.goals_lines:
        p_over, p_under = _poisson_over_under(projected_total_goals, line)
        key       = str(line)
        overOdds  = req.odds.goals_over_odds.get(key)
        underOdds = req.odds.goals_under_odds.get(key)
        _or_goals = _overround(overOdds, underOdds)

        market.append((f"Over {line} Goles",  overOdds,  p_over,  _or_goals))
        market.append((f"Under {line} Goles", underOdds, p_under, _or_goals))

        projected_lines.append(ProjectedLine(
            label=f"Over {line} Goles",  value=round(p_over, 1),
            type="goals", prob=round(p_over, 1)
        ))

    # ── Over/Under CORNERS: múltiples líneas ───────────────────
    projected_lines.append(ProjectedLine(
        label="Corners Totales (λ)", value=round(lam_corners, 1),
        type="corners", prob=None
    ))
    for line in req.odds.corners_lines:
        p_over, p_under = _poisson_over_under(lam_corners, line)
        key        = str(line)
        over_odds  = req.odds.corners_over_odds.get(key)
        under_odds = req.odds.corners_under_odds.get(key)
        _or_corn   = _overround(over_odds, under_odds)

        market.append((f"Over {line} Corners",  over_odds,  p_over,  _or_corn))
        market.append((f"Under {line} Corners", under_odds, p_under, _or_corn))

    # ── Over/Under TARJETAS: múltiples líneas ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tarjetas Totales (λ)", value=round(lam_cards, 1),
        type="cards", prob=None
    ))
    for line in req.odds.cards_lines:
        p_over, p_under = _poisson_over_under(lam_cards, line)
        key        = str(line)
        over_odds  = req.odds.cards_over_odds.get(key)
        under_odds = req.odds.cards_under_odds.get(key)
        _or_cards  = _overround(over_odds, under_odds)

        market.append((f"Over {line} Tarjetas",  over_odds,  p_over,  _or_cards))
        market.append((f"Under {line} Tarjetas", under_odds, p_under, _or_cards))

    # ── Over/Under TIROS TOTALES: múltiples líneas ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros Totales (λ)", value=round(lam_shots, 1),
        type="shots", prob=None
    ))
    for line in req.odds.shots_lines:
        p_over, p_under = _poisson_over_under(lam_shots, line)
        key        = str(line)
        over_odds  = req.odds.shots_over_odds.get(key)
        under_odds = req.odds.shots_under_odds.get(key)
        _or_shots  = _overround(over_odds, under_odds)

        market.append((f"Over {line} Tiros",  over_odds,  p_over,  _or_shots))
        market.append((f"Under {line} Tiros", under_odds, p_under, _or_shots))

    # ── Over/Under TIROS A PUERTA: múltiples líneas ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros a Puerta (λ)", value=round(lam_shots_target, 1),
        type="shots_target", prob=None
    ))
    for line in req.odds.shots_target_lines:
        p_over, p_under = _poisson_over_under(lam_shots_target, line)
        key        = str(line)
        over_odds  = req.odds.shots_target_over_odds.get(key)
        under_odds = req.odds.shots_target_under_odds.get(key)
        _or_shots_t  = _overround(over_odds, under_odds)

        market.append((f"Over {line} Tiros a Pta",  over_odds,  p_over,  _or_shots_t))
        market.append((f"Under {line} Tiros a Pta", under_odds, p_under, _or_shots_t))

    # ── Handicap ───────────────────────────────────────────────
    proj_hcap = h_lam - a_lam
    projected_lines.append(ProjectedLine(
        label="Handicap (Local)", value=round(proj_hcap, 2),
        type="handicap", prob=None
    ))



    # ── Probabilidades de Handicap ─────────────────────────────
    for hc_line in [-1.5, -1.0, -0.5, 0.5, 1.0, 1.5]:
        p_home_cov, p_away_cov = _compute_handicap_probabilities(h_lam, a_lam, hc_line)
        projected_lines.append(ProjectedLine(
            label=f"Handicap {hc_line:+.1f} Local",
            value=hc_line,
            type="handicap_prob",
            prob=round(p_home_cov, 1)
        ))

    # ── Values: usando _vi con overround por mercado ────────────
    values = [_vi(sel, odds, mp, ornd) for sel, odds, mp, ornd in market]

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
        # Performance
        _stat_comparison("Partidos Ganados",   "matches_won",       float(p1.matches_won),       float(p2.matches_won)),
        _stat_comparison("Torneos Ganados",    "tournaments_won",   float(p1.tournaments_won),   float(p2.tournaments_won)),
        # Service
        _stat_comparison("% 1er Servicio",     "first_serve_pct",   p1.first_serve_pct,          p2.first_serve_pct),
        _stat_comparison("% Puntos 1er Serv",  "first_serve_points_won_pct",  p1.first_serve_points_won_pct,  p2.first_serve_points_won_pct),
        _stat_comparison("% 2do Servicio",     "second_serve_pct",  p1.second_serve_pct,         p2.second_serve_pct),
        _stat_comparison("% Puntos 2do Serv",  "second_serve_points_won_pct", p1.second_serve_points_won_pct, p2.second_serve_points_won_pct),
        _stat_comparison("Aces/Partido",       "aces_per_match",    p1.aces_per_match,           p2.aces_per_match),
        _stat_comparison("Dobles faltas/Part", "double_faults_per_match", p1.double_faults_per_match, p2.double_faults_per_match, False),
        # Pressure
        _stat_comparison("BP Salvados",        "break_points_saved",     float(p1.break_points_saved),     float(p2.break_points_saved)),
        _stat_comparison("BP Convertidos",     "break_points_converted", float(p1.break_points_converted), float(p2.break_points_converted)),
        _stat_comparison("Tiebreaks Ganados",  "tiebreaks_won",          float(p1.tiebreaks_won),          float(p2.tiebreaks_won)),
        _stat_comparison("Win % Superficie",   "surface_win_pct",        (p1.matches_on_surface_won / max(p1.total_matches_on_surface, 1)) * 100, (p2.matches_on_surface_won / max(p2.total_matches_on_surface, 1)) * 100),
        _stat_comparison("H2H Ganados",        "h2h_won",               float(p1.head_to_head_won),       float(p2.head_to_head_won)),
    ]

    p1_serve_power = (
        p1.first_serve_pct * p1.first_serve_points_won_pct
        + (100 - p1.first_serve_pct) * p1.second_serve_points_won_pct
    )
    p2_serve_power = (
        p2.first_serve_pct * p2.first_serve_points_won_pct
        + (100 - p2.first_serve_pct) * p2.second_serve_points_won_pct
    )

    p1_clutch = (
        p1.break_points_converted / max(p1.break_points_converted_total, 1)
        + p1.break_points_saved / max(p1.break_points_saved_total, 1)
    )
    p2_clutch = (
        p2.break_points_converted / max(p2.break_points_converted_total, 1)
        + p2.break_points_saved / max(p2.break_points_saved_total, 1)
    )

    p1_rating = p1_serve_power + (p1_clutch * 100)
    p2_rating = p2_serve_power + (p2_clutch * 100)

    total_r = p1_rating + p2_rating or 1.0
    p1_prob = (p1_rating / total_r) * 100
    p2_prob = (p2_rating / total_r) * 100

    values = [
        _value_indicator("Jugador 1", req.odds.player1, p1_prob),
        _value_indicator("Jugador 2", req.odds.player2, p2_prob),
    ]

    p1a = sum(1 for c in comparisons if c.advantage == "home")
    p2a = sum(1 for c in comparisons if c.advantage == "away")
    vp  = [v for v in values if v.is_value]

    summary = (
        f"{p1.name} domina en {p1a}/{len(comparisons)} métricas · {p2.name} en {p2a}/{len(comparisons)}.\n"
        f"Rating: {p1.name} {p1_rating:.1f} vs {p2.name} {p2_rating:.1f} | Probs → P1: {p1_prob:.1f}% | P2: {p2_prob:.1f}%\n"
        + (f"✅ Value: {', '.join(v.selection for v in vp)}."
           if vp else "⚖️ Sin value claro.")
    )

    llm = None

    return CompareResponse(
        sport="tennis",
        home_name=p1.name,
        away_name=p2.name,
        comparisons=comparisons,
        values=values,
        summary=summary,
        llm_analysis=llm,
    )

    