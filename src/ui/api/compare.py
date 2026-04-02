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
    matches_played: int = Field(1,  description="Partidos jugados")
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
    clean_sheets:             float = Field(..., description="Vallas invictas")
    saves_per_game:           float = Field(0,   description="Saves por juego")
    balls_recovered_per_game: float = Field(..., description="Recuperaciones por juego")

    # Duelos
    duels_won_per_game:        float = Field(0, description="Duelos ganados por juego")
    ground_duels_won_per_game: float = Field(0, description="Duelos en piso ganados por juego")

    # Set pieces
    penalties_conceded: float = Field(0, description="Penales concedidos")

    # Disciplina
    fouls_per_game:        float = Field(..., description="Faltas por juego")
    yellow_cards_per_game: float = Field(..., description="Amarillas por juego")
    red_cards_total:       float = Field(0.0, description="Rojas totales")

    # Extra Tactical
    errors_leading_to_goal: float = Field(0, description="Errores que llevan a gol")
    offside_per_game:       float = Field(0, description="Fuera de juego por juego")


class LeagueStats(BaseModel):
    avg_goals_per_game:        float = Field(2.5,  description="Promedio total goles liga")
    avg_corners_per_game:      float = Field(9.5,  description="Promedio corners liga")
    avg_cards_per_game:        float = Field(4.5,  description="Promedio tarjetas liga")
    home_win_pct:              float = Field(45.0, description="% Victoria local liga")
    draw_pct:                 float = Field(25.0, description="% Empate liga")
    away_win_pct:              float = Field(30.0, description="% Victoria visitante liga")
    avg_yellow_cards_per_game: float = Field(4.0,  description="Promedio amarillas liga")
    avg_red_cards_per_game:    float = Field(0.2,  description="Promedio rojas liga")


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


def _value_indicator(sel: str, odds: float | None, modelp: float) -> ValueIndicator:
    if odds is None:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1))
    
    implied = _implied_probability(odds)
    edge    = modelp - implied
    is_value = edge > 2.0
    
    if   edge > 5.0:  rating = "🔥 STRONG VALUE"
    elif edge > 2.0:  rating = "✅ VALUE"
    elif edge > -1.0: rating = "⚖️ NEUTRAL"
    else:             rating = "❌ NO VALUE"
    
    return ValueIndicator(
        selection=sel,
        odds=odds,
        implied_prob=round(implied, 1),
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
    xg_mult   = max(0.55, min(1.65, xg_mult))  # Rango ampliado ±45%
    lam_adjusted = lam_base * xg_mult

    # ── 4. Shrinkage bayesiana ADAPTATIVA por tamaño de muestra ───
    # Fórmula: shrink_w = prior_n / (prior_n + matches_played)
    # prior_n = "partidos ficticios" que representa la media de liga
    # n=6  → shrink_w ≈ 0.25  (más incertidumbre, más regresión)
    # n=12 → shrink_w ≈ 0.14  (más datos, menos regresión)
    # n=30 → shrink_w ≈ 0.06  (mucha muestra, casi sin regresión)
    prior_n  = 2
    n        = max(attacker.matches_played, 1)
    shrink_w = prior_n / (prior_n + n)
    lam_final = lam_adjusted * (1.0 - shrink_w) + avg_team * shrink_w

    # ── 5. Home / Away ────────────────────────────────────────────
    lam_final *= 1.10 if is_home else 0.93

    return max(lam_final, 0.10)

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
    """
    total = h_lam + a_lam

    if total <= 1.80:
        return -0.13
    elif total <= 2.40:
        return -0.11
    elif total <= 3.00:
        return -0.08
    else:
        return -0.05


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
    
    h_exp_corners = h.corners_per_game * h_poss_share * 1.5
    a_exp_corners = a.corners_per_game * a_poss_share * 1.5
    
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
    lam_cards = base_match_cards * ((h_foul_agg + a_foul_agg) / 2.0)
    
    # Fallback al promedio de liga
    if lam_cards < 1.0: lam_cards = league.avg_cards_per_game
    return lam_cards


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


async def _call_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "Para ver el análisis con IA, configura OPENROUTER_API_KEY en tu .env"

    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    model  = os.environ.get("OPENROUTER_MODEL")
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
        )
        return r.choices[0].message.content or "⚠️ El modelo no generó contenido."
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return f"Error al generar análisis IA: {e}"


async def generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    competition: str = "Desconocida",
    user_context: str = "",
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

    prompt = f"""
Eres un analista táctico y de apuestas de élite. Tu trabajo es explicar el partido con claridad, criterio estadístico y lenguaje natural, sin exagerar ni repetir números innecesariamente.

REGLAS:
- Usa SOLO la información entregada.
- No inventes lesiones, rachas recientes, contexto histórico ni alineaciones.
- No digas que un mercado tiene valor si no aparece en "MERCADOS DE VALOR".
- Si no hay value claro, dilo explícitamente.
- Sé concreto: máximo 360 palabras.
- Prioriza interpretación sobre repetir cifras.

PARTIDO:
Competencia: {competition}
Local: {h.name}
Visitante: {a.name}

SEÑALES CLAVE LOCAL:
- Partidos jugados: {h.matches_played}
- Victorias: {h.wins}
- Empates: {h.draws}
- Derrotas: {h.losses}
- Goles p/j: {h.goals_per_game}
- Goles concedidos p/j: {h.goals_conceded_per_game}
- Tiros totales p/j: {h.shots_per_game}
- Tiros a puerta p/j: {h.shots_on_target_per_game}
- Grandes chances p/j: {h.big_chances_per_game}
- Grandes chances falladas p/j: {h.big_chances_missed_per_game}
- Posesión: {h.possession_pct}%
- Pases totales p/j: {(h.passes_completed*100)/max(h.pass_accuracy, 1.0):.1f}
- Pases totales completados p/j: {h.passes_completed}
- Precisión pases: {h.pass_accuracy}%
- Pases totales campo rival p/j: {(h.passes_opp_half*100)/max(h.pass_accuracy_opp_half, 1.0):.1f}
- Pases totales campo rival completados p/j: {h.passes_opp_half}
- Precisión en campo rival: {h.pass_accuracy_opp_half}%
- Centros intentados p/j: {(h.crosses_per_game*100)/max(h.cross_accuracy, 1.0):.1f}
- Centros completados p/j: {h.crosses_per_game} con un accuracy de {h.cross_accuracy}%
- Corners p/j: {h.corners_per_game}
- Amarillas p/j: {h.yellow_cards_per_game}
- Vallas invictas: {h.clean_sheets}/{h.matches_played}
- Paradas del portero p/j: {h.saves_per_game}
- Recuperaciones de balón p/j: {h.balls_recovered_per_game}
- Penales cometidos (Totales): {h.penalties_conceded}
- Errores que terminan en gol: {h.errors_leading_to_goal}
- Duelos ganados p/j: {h.duels_won_per_game}
- Duelos ganados en piso p/j: {h.ground_duels_won_per_game}
- Duelos ganados aéreos p/j: {h.duels_won_per_game - h.ground_duels_won_per_game}
- Rojas totales: {h.red_cards_total}

SEÑALES CLAVE VISITANTE:
- Partidos jugados: {a.matches_played}
- Victorias: {a.wins}
- Empates: {a.draws}
- Derrotas: {a.losses}
- Goles p/j: {a.goals_per_game}
- Goles concedidos p/j: {a.goals_conceded_per_game}
- Tiros totales p/j: {a.shots_per_game}
- Tiros a puerta p/j: {a.shots_on_target_per_game}
- Grandes chances p/j: {a.big_chances_per_game}
- Grandes chances falladas p/j: {a.big_chances_missed_per_game}
- Posesión: {a.possession_pct}%
- Pases totales p/j: {(a.passes_completed*100)/max(a.pass_accuracy, 1.0):.1f}
- Pases totales completados p/j: {a.passes_completed}
- Precisión pases: {a.pass_accuracy}%
- Pases totales campo rival p/j: {(a.passes_opp_half*100)/max(a.pass_accuracy_opp_half, 1.0):.1f}
- Pases totales campo rival completados p/j: {a.passes_opp_half}
- Precisión en campo rival: {a.pass_accuracy_opp_half}%
- Centros intentados p/j: {(a.crosses_per_game*100)/max(a.cross_accuracy, 1.0):.1f}
- Centros completados p/j: {a.crosses_per_game} con un accuracy de {a.cross_accuracy}%
- Corners p/j: {a.corners_per_game}
- Amarillas p/j: {a.yellow_cards_per_game}
- Vallas invictas: {a.clean_sheets}/{a.matches_played}
- Paradas del portero p/j: {a.saves_per_game}
- Recuperaciones de balón p/j: {a.balls_recovered_per_game}
- Penales cometidos (Totales): {a.penalties_conceded}
- Errores que terminan en gol: {a.errors_leading_to_goal}
- Duelos ganados p/j: {a.duels_won_per_game}
- Duelos ganados en piso p/j: {a.ground_duels_won_per_game}
- Duelos ganados aéreos p/j: {a.duels_won_per_game - a.ground_duels_won_per_game}
- Rojas totales: {a.red_cards_total}

LÍNEAS PROYECTADAS:
{proj_text}

MERCADOS DE VALOR:
{vp_text}
{f'''
CONTEXTO ADICIONAL DEL USUARIO:
{user_context}
''' if user_context else ''}
FORMATO DE RESPUESTA:
1. Un primer párrafo explicando el choque táctico: quién debería controlar, quién genera más peligro y dónde puede estar la ventaja.
2. Un segundo párrafo evaluando goles, BTTS, corners y tarjetas solo si las proyecciones lo justifican.
3. Un bloque final llamado "Pronósticos recomendados" con exactamente 3 picks:
   - pick
   - justificación breve basada en datos + proyección + value
Si no hay 3 mercados de valor claros, da solo los que sí existan y acláralo.
"""
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
                f"- {v.selection}: cuota={v.odds if v.odds is not None else 'N/A'} | modelo={v.modelprob:.1f}% | edge={v.edge:.1f}% | rating={v.rating}"
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

    # Asegurarnos de que matches_played no sea cero para evitar divisiones por cero
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
        
        # NORMALIZACIÓN DE TOTALES A PROMEDIOS O PORCENTAJES
        _stat_comparison("% Vallas Invictas",         "clean_sheets_pct",             (h.clean_sheets / h_matches) * 100, (a.clean_sheets / a_matches) * 100),
        _stat_comparison("Errores a Gol/juego",       "errors_leading_to_goal_pg",    h.errors_leading_to_goal / h_matches, a.errors_leading_to_goal / a_matches, False),
        _stat_comparison("Recuperaciones/j",          "balls_recovered_per_game",     h.balls_recovered_per_game,     a.balls_recovered_per_game),
    ]

    h_lam = _compute_lambda_v2(h, a, req.league_stats, is_home=True)
    a_lam = _compute_lambda_v2(a, h, req.league_stats, is_home=False)
    lam_corners = _compute_corners_lambda(h, a, req.league_stats)
    lam_cards   = _compute_cards_lambda(h, a, req.league_stats)

    # Solo necesitamos 1x2 y BTTS (Mercados base sin líneas dinámicas)
    matrix, _ = _dc_score_matrix(h_lam, a_lam)
    markets = _sum_score_matrix_1x2_and_markets(matrix)
    
    h_prob = markets["home_win_pct"] / 100.0
    d_prob = markets["draw_pct"] / 100.0
    a_prob = markets["away_win_pct"] / 100.0
    p_btts_yes = markets["btts_yes_pct"] / 100.0
    p_btts_no = markets["btts_no_pct"] / 100.0

    # ── Mercados base ──────────────────────────────────────────
    market: list[tuple[str, float | None, float]] = [
        ("Local",    req.odds.home, h_prob * 100),
        ("Empate",   req.odds.draw, d_prob * 100),
        ("Visitante", req.odds.away, a_prob * 100),
        ("BTTS Sí",  req.odds.btts_yes, p_btts_yes * 100),
        ("BTTS No",  req.odds.btts_no,  p_btts_no * 100),
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
        key = str(line)
        overOdds = req.odds.goals_over_odds.get(key)
        underOdds = req.odds.goals_under_odds.get(key)      

        market.append((f"Over {line} Goles",  overOdds,  p_over))
        market.append((f"Under {line} Goles", underOdds, p_under))

        # Opcional: Agregar todas al projected_lines o dejar solo el Total.
        # Aquí agregamos todas para que se vean en UI.
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
        key = str(line)
        over_odds  = req.odds.corners_over_odds.get(key)
        under_odds = req.odds.corners_under_odds.get(key)

        market.append((f"Over {line} Corners",  over_odds,  p_over))
        market.append((f"Under {line} Corners", under_odds, p_under))

    # ── Over/Under TARJETAS: múltiples líneas ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tarjetas Totales (λ)", value=round(lam_cards, 1),
        type="cards", prob=None
    ))
    for line in req.odds.cards_lines:
        p_over, p_under = _poisson_over_under(lam_cards, line)
        key = str(line)
        over_odds  = req.odds.cards_over_odds.get(key)
        under_odds = req.odds.cards_under_odds.get(key)

        market.append((f"Over {line} Tarjetas",  over_odds,  p_over))
        market.append((f"Under {line} Tarjetas", under_odds, p_under))

    # ── Handicap ───────────────────────────────────────────────
    proj_hcap = h_lam - a_lam
    projected_lines.append(ProjectedLine(
        label="Handicap (Local)", value=round(proj_hcap, 2),
        type="handicap", prob=None
    ))

    # Calculamos todos los values (Edge y Rating) de una sola vez
    values = [_value_indicator(sel, odds, mp) for sel, odds, mp in market]


    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp    = [v for v in values if v.is_value]

    summary = (
        f"Sherlock Analytics | λ Goles: {h.name} {h_lam:.2f} - {a.name} {a_lam:.2f}\n"
        f"Proyección Total: {projected_total_goals:.2f} Goles | {lam_corners:.1f} Corners | {lam_cards:.1f} Tarjetas\n"
        f"Handicap Estimado: {h.name} {proj_hcap:+.2f}\n"
        + (f"✅ Value detectado en: {', '.join(v.selection for v in vp)}"
           if vp else "⚖️ Sin value claro en las cuotas actuales.")
    )

    llm = None

    return CompareResponse(
        sport="football",
        home_name=h.name,
        away_name=a.name,
        h_lam=h_lam,
        a_lam=a_lam,
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

    