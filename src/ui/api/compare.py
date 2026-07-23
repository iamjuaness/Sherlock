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
# Football — modelo limpio (AMPLIADO CON STATS AVANZADAS)
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

    # Goles Detallados (NUEVO)
    goals_inside_box:        float = Field(0.0, description="Goles dentro del área por juego")
    goals_outside_box:       float = Field(0.0, description="Goles fuera del área por juego")
    headed_goals:            float = Field(0.0, description="Goles de cabeza por juego")
    free_kick_goals:         float = Field(0.0, description="Goles de tiro libre por juego")
    fast_break_goals:        float = Field(0.0, description="Goles en contraataque por juego")
    penalty_goals:           float = Field(0.0, description="Goles de penalti por juego")
    own_goals:               float = Field(0.0, description="Autogoles por juego")

    # Ataque
    big_chances_per_game:         float = Field(..., description="Grandes chances por juego")
    big_chances_missed_per_game:  float = Field(..., description="Grandes chances falladas por juego")
    big_chances_created:          float = Field(0.0, description="Grandes chances creadas por juego")
    shots_per_game:               float = Field(..., description="Tiros totales por juego")
    shots_on_target_per_game:     float = Field(..., description="Tiros al arco por juego")

    # Tiros Detallados (NUEVO)
    shots_blocked:                float = Field(0.0, description="Tiros bloqueados por juego")
    shots_inside_box:             float = Field(0.0, description="Tiros dentro del área por juego")
    shots_outside_box:            float = Field(0.0, description="Tiros fuera del área por juego")
    hit_woodwork:                 float = Field(0.0, description="Tiros al palo por juego")
    fast_break_shots:             float = Field(0.0, description="Tiros en contraataque por juego")
    free_kick_shots:              float = Field(0.0, description="Tiros libres por juego")
    penalties_taken:              float = Field(0.0, description="Penales ejecutados por juego")

    # Acciones Ofensivas (NUEVO)
    dribble_success_pct:          float = Field(0.0, description="% dribbles exitosos")
    fast_breaks:                  float = Field(0.0, description="Contraataques por juego")
    throw_ins:                    float = Field(0.0, description="Saques de banda por juego")

    # Posesión / Pases
    possession_pct:         float = Field(..., description="Posesión %")
    passes_completed:       float = Field(0,   description="Pases acertados")
    pass_accuracy:          float = Field(0,   description="Precisión pases %")
    passes_opp_half:        float = Field(0,   description="Pases acertados campo rival")
    pass_accuracy_opp_half: float = Field(0,   description="Precisión pases campo rival %")
    crosses_per_game:       float = Field(0,   description="Centros completos por juego")
    cross_accuracy:         float = Field(0,   description="Precisión de centros %")
    corners_per_game:       float = Field(..., description="Corners por juego")

    # Posesión Avanzada (NUEVO)
    possession_lost:        float = Field(0.0, description="Pérdidas de posesión por juego")

    # Defensa
    clean_sheets_home:        int   = Field(0,   description="Vallas invictas como local")
    clean_sheets_away:        int   = Field(0,   description="Vallas invictas como visitante")
    clean_sheets:             float = Field(..., description="Vallas invictas totales")
    saves_per_game:           float = Field(0,   description="Saves por juego")
    balls_recovered_per_game: float = Field(..., description="Recuperaciones por juego")

    # Defensa Avanzada (NUEVO)
    clearances_off_line:      float = Field(0.0, description="Despejes en línea por juego")
    last_man_tackles:         float = Field(0.0, description="Entradas último hombre por juego")

    # Duelos
    duels_won_per_game:        float = Field(0, description="Duelos ganados por juego")
    ground_duels_won_per_game: float = Field(0, description="Duelos en piso ganados por juego")

    # Duelos Avanzados (NUEVO)
    duels_total_per_game:      float = Field(0.0, description="Duelos totales por juego")
    aerial_duels_won_per_game: float = Field(0.0, description="Duelos aéreos ganados por juego")
    aerial_duels_won_pct:      float = Field(0.0, description="% duelos aéreos ganados")

    # Set pieces
    penalties_conceded: float = Field(0, description="Penales concedidos")

    # Set pieces Avanzado (NUEVO)
    penalty_goals_conceded: float = Field(0.0, description="Penales convertidos en contra por juego")

    # Disciplina
    fouls_per_game:        float = Field(..., description="Faltas por juego")
    yellow_cards_per_game: float = Field(..., description="Amarillas promedio por juego")
    red_cards_total:       float = Field(0.0, description="Rojas totales")
    errors_leading_to_goal: float = Field(0, description="Errores que llevan a gol")
    offside_per_game:       float = Field(0, description="Fuera de juego por juego")

    # Disciplina Avanzada (NUEVO)
    errors_leading_to_shot: float = Field(0.0, description="Errores que llevan a tiro por juego")

    # Extra Advanced
    corners_conceded_per_game:    float = Field(5.0, description="Corners concedidos por juego")
    xg_per_game:                  float = Field(1.5, description="Expected Goals por juego")
    xga_per_game:                 float = Field(1.5, description="Expected Goals Against por juego")
    # Pases / Centros (Totales vs Acertados)
    passes_total_per_game:          float = Field(500.0, description="Pases totales intentados por juego")
    passes_opp_half_total_per_game: float = Field(200.0, description="Pases totales intentados en campo rival")
    crosses_total_per_game:         float = Field(20.0,  description="Centros totales intentados por juego")

    # Portero Avanzado (NUEVO)
    save_pct:                       float = Field(0.0, description="Paradas %")
    goal_kicks:                     float = Field(0.0, description="Saque de meta por juego")

    # Físicas (NUEVO)
    kilometers_covered:             float = Field(0.0, description="Kilómetros recorridos por juego")
    number_of_sprints:              float = Field(0.0, description="Sprints por juego")

    # Rating (NUEVO)
    avg_rating:                     float = Field(0.0, description="Rating promedio del equipo")

    # Nuevas variables (Fase de ampliación de stats)
    goals_scored: float = Field(0.0, description="Goles anotados totales")
    goals_conceded: float = Field(0.0, description="Goles concedidos totales")
    assists: float = Field(0.0, description="Asistencias totales")
    left_foot_goals: float = Field(0.0, description="Goles pie izquierdo")
    right_foot_goals: float = Field(0.0, description="Goles pie derecho")
    shots: float = Field(0.0, description="Tiros totales")
    shots_on_target: float = Field(0.0, description="Tiros al arco totales")
    shots_off_target: float = Field(0.0, description="Tiros desviados totales")
    big_chances: float = Field(0.0, description="Grandes chances totales")
    big_chances_missed: float = Field(0.0, description="Grandes chances falladas totales")
    shots_off_target_per_game: float = Field(0.0, description="Tiros desviados por juego")
    shots_blocked_per_game: float = Field(0.0, description="Tiros bloqueados por juego")
    shots_inside_box_per_game: float = Field(0.0, description="Tiros dentro del área por juego")
    shots_outside_box_per_game: float = Field(0.0, description="Tiros fuera del área por juego")
    big_chances_created_per_game: float = Field(0.0, description="Grandes chances creadas por juego")
    hit_woodwork_per_game: float = Field(0.0, description="Tiros al palo por juego")
    fast_break_shots_per_game: float = Field(0.0, description="Tiros en contraataque por juego")
    free_kick_shots_per_game: float = Field(0.0, description="Tiros de tiro libre por juego")
    total_passes: float = Field(0.0, description="Pases totales")
    accurate_passes: float = Field(0.0, description="Pases completados totales")
    total_own_half_passes: float = Field(0.0, description="Pases propia mitad")
    accurate_own_half_passes: float = Field(0.0, description="Pases completados propia mitad")
    pass_accuracy_own_half: float = Field(0.0, description="Precisión pases propia mitad %")
    total_opp_half_passes: float = Field(0.0, description="Pases mitad rival")
    accurate_opp_half_passes: float = Field(0.0, description="Pases completados mitad rival")
    total_long_balls: float = Field(0.0, description="Long balls totales")
    accurate_long_balls: float = Field(0.0, description="Long balls completadas totales")
    long_ball_accuracy: float = Field(0.0, description="Precisión long balls %")
    total_crosses: float = Field(0.0, description="Centros totales")
    accurate_crosses: float = Field(0.0, description="Centros completados totales")
    passes_completed_per_game: float = Field(0.0, description="Pases completados por juego")
    passes_opp_half_per_game: float = Field(0.0, description="Pases completados campo rival por juego")
    long_balls_total_per_game: float = Field(0.0, description="Long balls totales por juego")
    long_balls_per_game: float = Field(0.0, description="Long balls completadas por juego")
    successful_dribbles: float = Field(0.0, description="Dribbles exitosos totales")
    dribble_attempts: float = Field(0.0, description="Dribbles intentados totales")
    corners: float = Field(0.0, description="Corners totales")
    fast_breaks_per_game: float = Field(0.0, description="Contraataques por juego")
    throw_ins_per_game: float = Field(0.0, description="Saques de banda por juego")
    ball_recovery: float = Field(0.0, description="Recuperaciones totales")
    ball_recovery_per_game: float = Field(0.0, description="Recuperaciones por juego")
    free_kicks: float = Field(0.0, description="Tiros libres totales")
    free_kicks_per_game: float = Field(0.0, description="Tiros libres por juego")
    possession_lost_per_game: float = Field(0.0, description="Pérdidas de posesión por juego")
    saves: float = Field(0.0, description="Saves totales")
    goal_kicks_per_game: float = Field(0.0, description="Saques de meta por juego")
    tackles: float = Field(0.0, description="Entradas totales")
    tackles_per_game: float = Field(0.0, description="Entradas por juego")
    interceptions: float = Field(0.0, description="Intercepciones totales")
    interceptions_per_game: float = Field(0.0, description="Intercepciones por juego")
    clearances: float = Field(0.0, description="Despejes totales")
    clearances_per_game: float = Field(0.0, description="Despejes por juego")
    clearances_off_line_per_game: float = Field(0.0, description="Despejes en línea por juego")
    last_man_tackles_per_game: float = Field(0.0, description="Entradas último hombre por juego")
    total_duels: float = Field(0.0, description="Duelos totales")
    duels_won: float = Field(0.0, description="Duelos ganados totales")
    duels_won_pct: float = Field(0.0, description="% Duelos ganados")
    total_ground_duels: float = Field(0.0, description="Duelos suelo totales")
    ground_duels_won: float = Field(0.0, description="Duelos suelo ganados totales")
    ground_duels_won_pct: float = Field(0.0, description="% Duelos suelo ganados")
    total_aerial_duels: float = Field(0.0, description="Duelos aéreos totales")
    aerial_duels_won: float = Field(0.0, description="Duelos aéreos ganados totales")
    fouls: float = Field(0.0, description="Faltas totales")
    offsides: float = Field(0.0, description="Fuera de juego total")
    yellow_cards: float = Field(0.0, description="Tarjetas amarillas totales")
    yellow_red_cards: float = Field(0.0, description="Doble tarjeta amarilla total")
    red_cards: float = Field(0.0, description="Tarjetas rojas directas totales")
    errors_leading_to_goal_per_game: float = Field(0.0, description="Errores gol por juego")
    errors_leading_to_shot_per_game: float = Field(0.0, description="Errores tiro por juego")
    kilometers_covered_per_game: float = Field(0.0, description="Kilómetros recorridos por juego")
    sprints_per_game: float = Field(0.0, description="Sprints por juego")

    # Estadísticas Contra (Oponente)
    shots_against: float = Field(0.0, description="Tiros concedidos totales")
    shots_against_per_game: float = Field(0.0, description="Tiros concedidos por juego")
    shots_on_target_against: float = Field(0.0, description="Tiros concedidos al arco totales")
    shots_on_target_against_per_game: float = Field(0.0, description="Tiros concedidos al arco por juego")
    shots_off_target_against: float = Field(0.0, description="Tiros concedidos desviados totales")
    shots_off_target_against_per_game: float = Field(0.0, description="Tiros concedidos desviados por juego")
    shots_blocked_against: float = Field(0.0, description="Tiros concedidos bloqueados totales")
    shots_blocked_against_per_game: float = Field(0.0, description="Tiros concedidos bloqueados por juego")
    blocked_scoring_attempt_against: float = Field(0.0, description="Intentos de tiro bloqueados al oponente")
    blocked_scoring_attempt_against_per_game: float = Field(0.0, description="Intentos de tiro bloqueados al oponente por juego")
    shots_inside_box_against: float = Field(0.0, description="Tiros concedidos dentro del área totales")
    shots_inside_box_against_per_game: float = Field(0.0, description="Tiros concedidos dentro del área por juego")
    shots_outside_box_against: float = Field(0.0, description="Tiros concedidos fuera del área totales")
    shots_outside_box_against_per_game: float = Field(0.0, description="Tiros concedidos fuera del área por juego")
    big_chances_against: float = Field(0.0, description="Grandes chances concedidas totales")
    big_chances_against_per_game: float = Field(0.0, description="Grandes chances concedidas por juego")
    big_chances_created_against: float = Field(0.0, description="Grandes chances creadas por el oponente totales")
    big_chances_created_against_per_game: float = Field(0.0, description="Grandes chances creadas por el oponente por juego")
    big_chances_missed_against: float = Field(0.0, description="Grandes chances falladas por el oponente totales")
    big_chances_missed_against_per_game: float = Field(0.0, description="Grandes chances falladas por el oponente por juego")
    hit_woodwork_against: float = Field(0.0, description="Tiros al palo del oponente totales")
    hit_woodwork_against_per_game: float = Field(0.0, description="Tiros al palo del oponente por juego")
    total_passes_against: float = Field(0.0, description="Pases del oponente totales")
    accurate_passes_against: float = Field(0.0, description="Pases completados del oponente totales")
    total_own_half_passes_against: float = Field(0.0, description="Pases propia mitad oponente totales")
    accurate_own_half_passes_against: float = Field(0.0, description="Pases completados propia mitad oponente totales")
    total_opp_half_passes_against: float = Field(0.0, description="Pases mitad rival oponente totales")
    accurate_opp_half_passes_against: float = Field(0.0, description="Pases completados mitad rival oponente totales")
    total_final_third_passes_against: float = Field(0.0, description="Pases 3/4 oponente totales")
    accurate_final_third_passes_against: float = Field(0.0, description="Pases completados 3/4 oponente totales")
    crosses_total_against: float = Field(0.0, description="Centros del oponente totales")
    crosses_successful_against: float = Field(0.0, description="Centros completados del oponente totales")
    long_balls_total_against: float = Field(0.0, description="Long balls del oponente totales")
    long_balls_successful_against: float = Field(0.0, description="Long balls completadas del oponente totales")
    dribble_attempts_against: float = Field(0.0, description="Dribbles intentados del oponente totales")
    dribble_attempts_won_against: float = Field(0.0, description="Dribbles ganados del oponente totales")
    tackles_against: float = Field(0.0, description="Entradas del oponente totales")
    interceptions_against: float = Field(0.0, description="Intercepciones del oponente totales")
    clearances_against: float = Field(0.0, description="Despejes del oponente totales")
    key_passes_against: float = Field(0.0, description="Pases clave del oponente totales")
    corners_against: float = Field(0.0, description="Corners del oponente totales")
    offsides_against: float = Field(0.0, description="Offsides del oponente totales")
    yellow_cards_against: float = Field(0.0, description="Tarjetas amarillas del oponente totales")
    red_cards_against: float = Field(0.0, description="Tarjetas rojas del oponente totales")


class LeagueStats(BaseModel):
    name:                      str   = Field("",  description="Nombre de la liga")
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

    # League Reliability Score (0.0 – 1.0)
    # 1.0 = liga de máxima confianza (top5 europeas, datos completos y estables)
    # 0.0 = liga de muy baja confianza (poca data, alta varianza, comportamiento impredecible)
    # Si se deja en 0.0 (por defecto) el sistema lo autocalibrará con _compute_league_reliability_score().
    league_reliability_score:  float = Field(0.0,  description="Confiabilidad histórica de la liga (0–1). 0 = autocalibrarse.")

    # Historical performance data (optional – used to compute LRS from real pick history)
    historical_matches:  int   = Field(0,   description="Partidos analizados históricamente en esta liga")
    historical_picks:    int   = Field(0,   description="Picks resueltos históricamente en esta liga")
    historical_hits:     int   = Field(0,   description="Picks acertados históricamente en esta liga")
    historical_profit:   float = Field(0.0, description="Beneficio histórico acumulado en esta liga (unidades)")
    accuracy:            float = Field(0.0, description="Precisión de picks histórica de la liga")
    roi:                 float = Field(0.0, description="ROI histórico de la liga")
    # Per-market win rates (family → hits/total dict serialized as JSON string; parsed internally)
    market_hit_rates: Dict[str, float] = Field(default_factory=dict, description="Tasa de acierto por mercado {family: rate}")


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
    match_date: Optional[str] = Field(default=None, description="Fecha del partido (YYYY-MM-DD). A partir del 2026-07-01 las stats son generales (sin segmentación por localía).")
    use_general_stats: bool = Field(default=False, description="Si es True, se usan stats generales. Si es False, se usan stats segmentadas por localía.")


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

    # 10. Correcciones menores de xg / xga si están ausentes
    if t.xg_per_game <= 0.0:
        t.xg_per_game = max(t.goals_per_game, 0.1)
    if t.xga_per_game <= 0.0:
        t.xga_per_game = max(t.goals_conceded_per_game, 0.1)

    return t


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

    # League Reliability
    league_reliability_score:   Optional[float] = None  # 0–1, penaliza ligas con peor rendimiento
    league_reliability_penalty: Optional[float] = None  # EV ajustado por confiabilidad de liga

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
    is_blacklisted:        bool = False


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
    Calcula un score de confiabilidad de la liga en rango [0.25, 1.0].

    Combina dos fuentes:
    A) Coherencia estadística interna (rangos razonables de goles, corners, tarjetas)
    B) Rendimiento histórico real (acierto + beneficio), con peso Bayesiano proporcional
       al número de partidos/picks analizados. Con pocos datos (<10 picks), el peso
       histórico se reduce drásticamente para evitar que 1 partido = 100% confianza.

    Un score bajo (<0.6) penaliza el EV efectivo de los picks.
    """
    # ── A. Coherencia estadística (igual que antes) ──────────────
    stat_score = 1.0

    pct_sum = league.home_win_pct + league.draw_pct + league.away_win_pct
    if pct_sum > 0:
        deviation = abs(pct_sum - 100.0) / 100.0
        stat_score -= min(0.20, deviation * 2.0)

    g = league.avg_goals_per_game
    if g < 1.5 or g > 4.5:
        stat_score -= 0.10
    elif g < 2.0 or g > 3.8:
        stat_score -= 0.05

    c = league.avg_corners_per_game
    if c < 6.0 or c > 14.0:
        stat_score -= 0.08
    elif c < 7.5 or c > 12.0:
        stat_score -= 0.03

    ha = league.home_advantage_factor
    if ha < 1.05 or ha > 1.50:
        stat_score -= 0.07

    if league.avg_yellow_cards_per_game > 0 and league.avg_red_cards_per_game > 0:
        ratio = league.avg_red_cards_per_game / max(league.avg_yellow_cards_per_game, 0.1)
        if ratio > 0.15:
            stat_score -= 0.05

    stat_score = max(0.25, min(1.0, stat_score))

    # ── B. Rendimiento histórico real ────────────────────────────
    # Solo se activa si hay suficientes picks resueltos.
    # Peso Bayesiano: el histórico va ganando influencia conforme crece el nº de picks.
    # Con N_MIN picks se tiene 50% de influencia histórica; con el doble, ~75%, etc.
    hist_picks = league.historical_picks  # picks resueltos (no pendientes)
    if hist_picks <= 0:
        # Sin historial: solo usamos la coherencia estadística
        return round(stat_score, 3)

    N_MIN = 20.0  # número de picks para 50% de peso histórico
    hist_weight = hist_picks / (hist_picks + N_MIN)   # ∈ [0, 1)
    stat_weight = 1.0 - hist_weight

    # Componente de acierto: acierto esperado en apuestas value ≈ 55%.
    # Normalizar alrededor de 0.55 → score 1.0 si acierto ≥ 0.60, 0.5 si = 0.45, etc.
    accuracy_rate = league.historical_hits / hist_picks
    ACC_REF = 0.50          # mínimo aceptable
    ACC_IDEAL = 0.62        # nivel excelente
    acc_score = (accuracy_rate - ACC_REF) / max(ACC_IDEAL - ACC_REF, 0.01)
    acc_score = max(0.0, min(1.0, acc_score))  # [0, 1]

    # Componente de beneficio: normalizado a picks (ROI por pick).
    # +0.15u/pick = excelente (score 1.0); -0.15u/pick = malo (score 0.0).
    roi_per_pick = league.historical_profit / hist_picks
    PROFIT_LOW  = -0.15
    PROFIT_HIGH =  0.20
    profit_score = (roi_per_pick - PROFIT_LOW) / max(PROFIT_HIGH - PROFIT_LOW, 0.01)
    profit_score = max(0.0, min(1.0, profit_score))

    # Muestra suficiente: bonus si hay ≥ 30 partidos analizados
    sample_bonus = 0.0
    if league.historical_matches >= 30:
        sample_bonus = 0.05
    elif league.historical_matches >= 15:
        sample_bonus = 0.02

    # Score histórico combinado (50% acierto, 50% beneficio)
    hist_score = acc_score * 0.50 + profit_score * 0.50 + sample_bonus
    hist_score = max(0.0, min(1.0, hist_score))

    # ── Combinar A + B ────────────────────────────────────────────
    final_score = stat_score * stat_weight + hist_score * hist_weight
    return round(max(0.25, min(1.0, final_score)), 3)


def apply_calibration(raw_prob: float, odds: float, market_family: str) -> float:
    p = raw_prob / 100.0

    b = 0.85 
    if market_family in {"corners", "cards", "shots"}:
        b = 0.75
    elif market_family == "double_chance":
        if p >= 0.80:
            b = 0.78
        elif p >= 0.70:
            b = 0.74
        else:
            b = 0.70
    elif market_family == "dnb":
        b = 0.82

    calibrated = (p**b) / (p**b + (1-p)**b)

    if market_family == "double_chance":
        if p >= 0.80:
            shrinkage = 0.07
        elif p >= 0.70:
            shrinkage = 0.09
        else:
            shrinkage = 0.12
        calibrated = (1.0 - shrinkage) * calibrated + shrinkage * 0.50
    elif market_family == "dnb":
        calibrated = 0.95 * calibrated + 0.05 * 0.50

    if odds > 3.0:
        calibrated *= 0.90
    elif odds > 2.0:
        calibrated *= 0.94

    return calibrated * 100.0

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
    elif tier == "hybrid":    base = 70.0
    else:                     base = 45.0

    min_m = min(h.matches_played, a.matches_played)
    if min_m < 8:
        sample_penalty = (10 - min_m) * 6.0
    elif min_m < 15:
        sample_penalty = (15 - min_m) * 2.0
    else:
        sample_penalty = 0

    family = _market_family(selection)
    if family in {"cards", "corners", "shots"}:
        if h.xg_per_game < 0.4 or a.xg_per_game < 0.4:
            base -= 8

    # NUEVO: Penalización si no hay datos avanzados (rating = 0 indica data pobre)
    if h.avg_rating < 0.1 or a.avg_rating < 0.1:
        base -= 5

    return max(5.0, base - sample_penalty)

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

def is_publishable_pick(v: ValueIndicator) -> bool:
    if v.is_blacklisted:
        return False
    family = _market_family(v.selection)

    if v.odds is None or v.odds < 1.4 or v.odds > 2.50:
        return False

    prob = v.calibrated_prob if v.calibrated_prob is not None else v.model_prob
    is_binary = family in {"result", "btts", "goals"}

    if is_binary and prob < 60.0:
        return False
    if not is_binary and prob < 35.0:
        return False

    if v.edge_ev < 0.025 or v.edge_ev > 0.20:
        return False

    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False

    return True



def score_pick_quality(v: ValueIndicator) -> int:
    if not v.edge_ev: return 0

    ev_score = min(v.edge_ev * 200, 60)

    prob_score = (v.calibrated_prob or v.model_prob) / 5.0

    dq_score = (v.data_quality_score or 50) / 5.0

    total = int(ev_score + prob_score + dq_score)
    return min(max(total, 0), 100)

def is_high_confidence_pick(v: ValueIndicator) -> bool:
    family = _market_family(v.selection)

    if v.model_prob < 75.0:
        return False

    if v.edge_ev >= 0.02:
        return False

    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False

    return True


def is_underdog_pick(v: ValueIndicator) -> bool:
    family = _market_family(v.selection)

    if v.odds is None or v.odds <= 2.5 or v.odds > 5.80:
        return False

    if v.edge_ev < 0.05:
        return False

    if v.data_quality_score is not None and v.data_quality_score < 50:
        return False

    return True



def _value_indicator(sel, odds, modelp, h=None, a=None, overround=100.0, push_p=0.0, league: "LeagueStats | None" = None, league_name: str | None = None):
    if odds is None or odds <= 1.0:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1), push_prob=round(push_p, 1))

    family = _market_family(sel)
    calibrated_p = apply_calibration(modelp, odds, family)

    raw_implied = (1.0 / odds) * 100.0
    margin_factor = (overround / 100.0) if overround > 100 else 1.05
    implied_no_vig = raw_implied / margin_factor

    edge_prob = calibrated_p - raw_implied
    ev = (calibrated_p / 100.0 * odds) - 1.0

    if push_p > 0:
        p_resolve = 1.0 - (push_p / 100.0)
        ev = ev * p_resolve
        edge_prob = edge_prob * p_resolve

    # ── League Reliability Score ──────────────────────────────────
    # Calcula o reutiliza el LRS y aplica una penalización al EV efectivo.
    # Ligas con baja confiabilidad (score < 0.6) comprimen el EV hacia cero.
    if league is not None:
        lrs = league.league_reliability_score if league.league_reliability_score > 0.0 else _compute_league_reliability_score(league)
    else:
        lrs = 0.2  # sin datos de liga = sin penalización

    # ── Penalización por mercado específico (market-level LRS) ────
    # Si la liga tiene historial de acierto por tipo de mercado, aplicar ajuste
    # adicional para los mercados que peor se comportan en esa liga.
    market_lrs_factor = 1.0
    if league is not None and league.market_hit_rates:
        market_rate = league.market_hit_rates.get(family)
        if market_rate is not None and league.historical_picks >= 5:
            # Tasa de acierto de referencia por familia de mercado
            # (Tasas razonables de referencia cuando el modelo funciona bien)
            MARKET_REF = {
                "corners": 0.52, "cards": 0.52, "shots": 0.52, "fouls": 0.52,
                "goals": 0.55,   "btts": 0.54,  "result": 0.55,
                "handicap": 0.54, "double_chance": 0.57, "dnb": 0.56, "generic": 0.53,
            }
            ref_rate = MARKET_REF.get(family, 0.53)
            # Penalizar mercados que rinden peor que la referencia en esta liga
            # Peso Bayesiano: solo aplica con suficientes picks en esa familia
            market_dev = market_rate - ref_rate   # negativo → peor que ref
            market_lrs_factor = 1.0 + max(-0.35, min(0.15, market_dev * 1.5))

    # Penalización: ev_adj = ev * lrs  (lrs=1 → sin cambio; lrs=0.5 → EV a la mitad)
    # La penalización es más agresiva para mercados secundarios (corners, cards, shots)
    if family in {"corners", "cards", "shots", "fouls"}:
        lrs_factor = lrs ** 1.5  # penalización extra en mercados de alta varianza
    else:
        lrs_factor = lrs
    lrs_factor *= market_lrs_factor
    ev_adj = ev * lrs_factor
    lrs_penalty = round(ev - ev_adj, 4)  # cuánto se descontó
    ev = ev_adj
    p = calibrated_p / 100.0
    kelly_full = (p * odds - 1.0) / (odds - 1.0) if ev > 0 else 0


    # ─────────────────────────────────────────────────────────────

    conf_tier = get_market_confidence_tier(sel)
    var_tier = get_market_variance_tier(sel)
    dq_score = get_data_quality_score(sel, h, a) if h and a else None

    if   ev > 0.15:  rating = "🔥 STRONG VALUE"
    elif ev > 0.07:  rating = "✅ VALUE"
    elif ev > 0.02:  rating = "⚖️ MARGINAL"
    else:            rating = "❌ NO VALUE"

    # Aplicar fracción conservadora según confianza
    kelly_fraction = {
        "🔥 STRONG VALUE": 0.25,   # 1/4 Kelly
        "✅ VALUE": 0.125,         # 1/8 Kelly  
        "⚖️ MARGINAL": 0.0625,     # 1/16 Kelly
        "❌ NO VALUE": 0.0,
    }[rating]

    # Aplicar límite de Kelly/Stake si la liga tiene rendimiento pobre (beneficio negativo o acierto < 40%)
    if league is not None and getattr(league, "historical_picks", 0) >= 5:
        hist_profit = getattr(league, "historical_profit", 0.0)
        hist_accuracy = getattr(league, "accuracy", 100.0)
        if hist_profit < 0.0 or hist_accuracy < 40.0:
            kelly_fraction = min(kelly_fraction, 0.01) # Limita stake a máximo 1u (1% Kelly -> Stake 1)

    kelly = kelly_full * kelly_fraction

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
        is_value=ev > 0.03,
        rating=rating,
        data_quality_score=dq_score,
        market_confidence_tier=conf_tier,
        market_variance_tier=var_tier,
        kelly_fraction=round(kelly, 4),
        sample_size_weight=min(1.0, (h.matches_played + a.matches_played) / 30.0) if h and a else 0.5,
        league_reliability_score=round(lrs, 3),
        league_reliability_penalty=lrs_penalty,
    )

    # Check league blacklist
    if league_name and is_market_blacklisted_for_league(league_name, sel):
        v.is_blacklisted = True
        v.is_publishable = False
        v.is_value = False
        v.quality_score = -1
        v.strategic_score = -1
    else:
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
    general: bool = False,
) -> float:
    avg_team_goals = league.avg_goals_per_game / 2.0

    prior_att_xg = attacker.xg_per_game
    actual_att_g = attacker.goals_per_game
    prior_def_xga = defender.xga_per_game
    actual_def_g = defender.goals_conceded_per_game

    # ── Determinar nº de partidos (att_n, def_n) — necesario para conversiones por juego
    if general:
        att_n = max(attacker.matches_played, 1)
        def_n = max(defender.matches_played, 1)
    else:
        if is_home:
            att_n = max(attacker.matches_home, 1)
            def_n = max(defender.matches_away, 1)
        else:
            att_n = max(attacker.matches_away, 1)
            def_n = max(defender.matches_home, 1)

    # ── 1b. Corrección de xga por "suerte defensiva" (Big Chances Concedidas vs Falladas) ──
    bc_conceded = defender.big_chances_against_per_game
    bc_missed = defender.big_chances_missed_against_per_game
    if bc_conceded > 0.1:
        bc_scored_against = max(0.0, bc_conceded - bc_missed)
        bc_conv_against = bc_scored_against / bc_conceded
        # Tasa de conversión promedio típica de big chances es ~0.45.
        # Si la tasa es > 0.45, es mala suerte defensiva (goles inflados). Si es < 0.45, es buena suerte.
        luck_adjustment = (bc_conv_against - 0.45) * 0.15
        luck_adjustment = max(-0.10, min(0.10, luck_adjustment))
        # Ajustamos el prior xGa (si hubo mala suerte, restamos para corregir a la media)
        prior_def_xga = prior_def_xga * (1.0 - luck_adjustment)

    # ── 1c. Corrección xga por tiros al palo del rival (hit_woodwork_against)
    # Muchos tiros al palo = mala suerte defensiva real → la defensa es más frágil de lo que muestran los goles
    hw_against = defender.hit_woodwork_against  # totales en el período
    if hw_against > 0:
        hw_per_game = hw_against / def_n
        # Referencia: ~0.5 tiros/palo por juego es normal. Más = defensa con mala suerte real.
        hw_boost = min((hw_per_game - 0.5) * 0.08, 0.10)  # hasta +10% xga
        if hw_boost > 0:
            prior_def_xga = prior_def_xga * (1.0 + hw_boost)

    # ── 1d. Factor de pases clave del rival contra esta defensa (key_passes_against)
    # Muchos pases clave concedidos → defensa que permite creación de juego → más goles esperados
    kp_against = defender.key_passes_against  # totales en el período
    kp_factor = 1.0
    if kp_against > 0:
        kp_per_game = kp_against / def_n
        # Referencia: ~4-5 pases clave concedidos/juego es promedio
        kp_dev = (kp_per_game - 4.5) / 4.5
        kp_factor = 1.0 + max(-0.08, min(0.10, kp_dev * 0.18))

    beta_prior = 5.0 

    # ── 2. Fuerza de Ataque Bayesiana ──
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

    # ── 5. Señales Tácticas Adicionales (MEJORADAS) ──
    # 5a. Eficiencia de chances (penaliza ineficiencia)
    bc_signal = attacker.big_chances_per_game / max(attacker.big_chances_missed_per_game + 0.5, 0.5)
    tactical_mult = 1.0 + (min(bc_signal, 2.0) - 1.0) * 0.08

    # 5b. Perfil de goles: equipos que marcan de fuera son más impredecibles y peligrosos
    outside_ratio = attacker.goals_outside_box / max(attacker.goals_per_game, 0.1)
    if outside_ratio > 0.25:
        tactical_mult *= 1.04  # +4% si >25% de goles son de fuera

    # 5c. Goles en contraataque = mayor peligro en transiciones
    fb_ratio = attacker.fast_break_goals / max(attacker.goals_per_game, 0.1)
    if fb_ratio > 0.15:
        tactical_mult *= 1.05  # +5% si >15% son en contraataque

    # 5d. Penaliza posesión perdida excesiva (menos oportunidades de gol)
    poss_lost_factor = 1.0
    if attacker.possession_lost > 120:
        poss_lost_factor = 0.94
    elif attacker.possession_lost > 90:
        poss_lost_factor = 0.97

    # 5e. Fragilidad defensiva rival: errores que llevan a gol/tiro aumentan expectativa
    rival_errors = defender.errors_leading_to_goal_per_game + (defender.errors_leading_to_shot_per_game * 0.3)
    error_boost = 1.0 + min(rival_errors / 5.0, 0.08)  # hasta +8%

    # 5f. Calidad del equipo (rating) como factor de ajuste
    rating_factor = 1.0
    if attacker.avg_rating > 0:
        # Rating típico 6.5-7.5. Normalizar alrededor de 7.0
        rating_factor = 1.0 + (attacker.avg_rating - 7.0) * 0.03  # ±3% por punto de rating
        rating_factor = max(0.90, min(1.10, rating_factor))

    # 5g. Eficiencia del portero rival (save_pct) reduce goles esperados
    keeper_factor = 1.0
    if defender.save_pct > 0:
        # save_pct típico ~70%. >75% es bueno, <65% es malo
        keeper_factor = 1.0 - (defender.save_pct - 0.70) * 0.20
        keeper_factor = max(0.85, min(1.15, keeper_factor))

    # 5h. Presión defensiva del rival (interceptions + tackles)
    def_pressure = defender.interceptions_per_game + defender.tackles_per_game
    pressure_factor = 1.0 - (def_pressure - 28.0) * 0.01  # ±1% por cada tackle/intercepción de diferencia
    pressure_factor = max(0.88, min(1.12, pressure_factor))

    # 5i. Perfil colectivo del atacante (assists): más asistencias = juego más predecible y fluido
    # Un equipo con muchas asistencias genera situaciones más construidas → +% conversión esperado
    att_assists = attacker.assists  # totales en el período
    assists_factor = 1.0
    if att_assists > 0 and att_n > 0:
        assists_per_game = att_assists / att_n
        assists_ref = attacker.goals_per_game * 0.75  # ~75% de goles deberían tener asistencia
        if assists_per_game > assists_ref:
            assists_factor = 1.0 + min((assists_per_game - assists_ref) / max(assists_ref, 0.5) * 0.06, 0.06)
        assists_factor = max(0.96, min(1.06, assists_factor))

    lam_adjusted = lam_base * tactical_mult * poss_lost_factor * error_boost * rating_factor * keeper_factor * pressure_factor * kp_factor * assists_factor

    # ── 6. Shrinkage Global a la Liga ──
    total_n = min(att_n, def_n)
    prior_league_n = max(1.0, 4.0 - (total_n / 8.0))
    shrink_w = prior_league_n / (prior_league_n + total_n)

    lam_final = lam_adjusted * (1.0 - shrink_w) + avg_team_goals * shrink_w

    return max(lam_final, 0.10)



def _compute_team_corners_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    avg_team_corners = league.avg_corners_per_game / 2.0

    # ── 1. Señal de centros: ratio de completud ──
    cross_total = max(team.crosses_total_per_game, 0.1)
    cross_ratio = team.crosses_per_game / cross_total
    CROSS_REF = 0.45
    cross_mult = 1.0 + 0.80 * (cross_ratio - CROSS_REF)  # reducido de 1.20 a 0.80
    cross_mult = max(0.70, min(1.30, cross_mult))  # rango más ajustado

    # ── 2. Base de generación: corners históricos ajustados por cross_mult
    gen_base = team.corners_per_game * cross_mult

    # ── 3. Capacidad del rival de conceder corners ──
    # Centrado: si rival concede avg_team_corners → ratio ~1.0; escalamos por 0.87 igual que shots
    opp_def_weakness = (opponent.corners_conceded_per_game / max(avg_team_corners, 1.0)) * 0.87
    opp_def_weakness = max(0.55, min(1.15, opp_def_weakness))

    # ── 4. Lambda base cruzada ──
    lam = gen_base * opp_def_weakness

    # ── Determinar conteo de partidos para cálculos por juego ──
    if general:
        att_n_c = max(team.matches_played, 1)
        opp_n_c = max(opponent.matches_played, 1)
    else:
        att_n_c = max(team.matches_home if is_home else team.matches_away, 1)
        opp_n_c = max(opponent.matches_away if is_home else opponent.matches_home, 1)

    # ── Factores avanzados de corners (con caps reducidos) ──
    # 4a. Duelos aéreos
    aerial_factor = 1.0
    if team.aerial_duels_won_per_game > 12:
        aerial_factor = 1.05
    elif team.aerial_duels_won_per_game > 8:
        aerial_factor = 1.02

    # 4b. Posesión
    possession_factor = 1.0 + (team.possession_pct - 50.0) * 0.0010  # +1% por cada 10%
    possession_factor = max(0.93, min(1.07, possession_factor))

    # 4c. Contraataques
    fastbreak_factor = 1.0 + min(team.fast_breaks / 20.0, 0.04)

    # 4d. Tiros bloqueados del rival
    blocked_factor = 1.0 + min(opponent.shots_blocked / 30.0, 0.03)

    # 4e. Despejes en línea del rival
    if opponent.clearances_off_line > 0.3:
        opp_def_weakness *= 0.95

    # 4f. Despejes totales del rival (clearances): proxy de presión sufrida
    # Un rival que despeja mucho → recibe mucho ataque → genera corners para este equipo
    opp_clearances = opponent.clearances  # totales en el período
    if opp_clearances > 0:
        opp_clear_per_game = opp_clearances / opp_n_c
        # Referencia: ~25 despejes/juego es promedio bajo presión
        clear_boost = 1.0 + max(0.0, min((opp_clear_per_game - 22.0) / 22.0 * 0.10, 0.10))
        lam = lam * clear_boost

    # 4g. Despejes concedidos del equipo atacante (clearances_against en la defensa del rival)
    # Si el equipo atacante tiene muchos despejes contra (el rival despeja mucho ante él)
    # → el equipo genera mucho ataque → más corners.
    team_clearances_against = team.clearances_against  # totales del rival despejando ante este equipo
    if team_clearances_against > 0:
        tca_per_game = team_clearances_against / att_n_c
        # Más despejes del rival ante este equipo → más presión ejercida → más corners
        tca_boost = 1.0 + max(0.0, min((tca_per_game - 20.0) / 20.0 * 0.08, 0.08))
        lam = lam * tca_boost

    # 4h. Pases precisos del rival: rival con muchos pases exitosos → más posesión → menos corners
    # (un rival que domina la posesión mediante pases genera menos situaciones de corner)
    opp_acc_passes = opponent.accurate_passes_against  # pases completados del rival en partidos vs este equipo
    if opp_acc_passes > 0:
        opp_acc_per_game = opp_acc_passes / opp_n_c
        # >400 pases precisos del rival/juego → domina posesión → menos corners para el atacante
        pass_penalty = 1.0 - max(0.0, min((opp_acc_per_game - 350.0) / 350.0 * 0.07, 0.07))
        lam = lam * pass_penalty

    # Cap global de boosts avanzados: máximo +12%
    raw_boost = aerial_factor * possession_factor * fastbreak_factor * blocked_factor
    capped_boost = max(0.90, min(1.12, raw_boost))
    lam = lam * capped_boost

    # ── 5. Shrinkage bayesiana fortalecida ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    prior_n = 5.0
    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_corners * shrink_w

    return max(lam, 0.5)


def _compute_team_cards_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    if general:
        actual_matches = max(team.matches_played, 1)
        opp_matches = max(opponent.matches_played, 1)
    else:
        actual_matches = max(team.matches_home if is_home else team.matches_away, 1)
        # Rival plays the opposite side
        opp_matches = max(opponent.matches_away if is_home else opponent.matches_home, 1)

    # 1. Promedio base del equipo
    red_card_weight = 2.0 
    team_reds_per_game = (team.red_cards_total / actual_matches) * red_card_weight
    own_cards_avg = team.yellow_cards_per_game + team_reds_per_game

    # 2. Ajuste por agresividad (Faltas)
    foul_deviation = (team.fouls_per_game - 12.5) / 12.5
    foul_modifier = 1.0 + (foul_deviation * 0.15)

    # 3. Ajuste por inducción del rival
    poss_deviation = (opponent.possession_pct - 50.0) / 50.0
    duel_deviation = (opponent.ground_duels_won_per_game - 10.0) / 10.0

    rival_modifier = 1.0 + (poss_deviation * 0.05) + (duel_deviation * 0.10)

    total_modifier = max(0.75, min(1.25, foul_modifier * rival_modifier))
    lam = own_cards_avg * total_modifier

    # ── NUEVO: Factores avanzados de tarjetas ──
    # 3b. Penales concedidos: indica indisciplina defensiva
    if team.penalties_conceded > 0.15:
        lam *= 1.08
    if team.penalty_goals_conceded > 0.1:
        lam *= 1.05

    # 3c. Errores que llevan a tiro: más errores = más faltas para compensar
    error_card_boost = 1.0 + min(team.errors_leading_to_shot / 3.0, 0.06)
    lam *= error_card_boost

    # 3d. Duelos totales: más contacto físico = más tarjetas
    duel_intensity = team.duels_total_per_game / 50.0  # 50 es referencia
    if duel_intensity > 1.2:
        lam *= 1.06
    elif duel_intensity > 1.0:
        lam *= 1.03

    # 3e. Contraataques del rival: más transiciones = más faltas tácticas
    if opponent.fast_breaks > 4:
        lam *= 1.05

    # 3f. Pérdidas de posesión en zonas peligrosas
    if team.possession_lost > 100:
        lam *= 1.04

    # 3g. Duelos aéreos intensos
    if team.aerial_duels_won_per_game + opponent.aerial_duels_won_per_game > 25:
        lam *= 1.03

    # 3h. Tarjetas provocadas por el estilo de juego del rival (against stats)
    # Si league.avg_yellow_cards_per_game no está seteado, se deduce de league.avg_cards_per_game.
    temp_league_cards = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0) if league.avg_yellow_cards_per_game > 0 else league.avg_cards_per_game
    avg_team_cards_ref = temp_league_cards / 2.0
    rival_draw_cards_avg = (opponent.yellow_cards_against + (opponent.red_cards_against * 2.0)) / opp_matches
    if rival_draw_cards_avg > 0:
        rival_card_modifier = 1.0 + ((rival_draw_cards_avg - avg_team_cards_ref) / max(avg_team_cards_ref, 1.0)) * 0.15
        lam *= max(0.85, min(1.25, rival_card_modifier))

    # 4. Integración del Árbitro
    if league.avg_yellow_cards_per_game > 0 and league.avg_red_cards_per_game > 0:
        league_cards_avg = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0)
    else:
        league_cards_avg = league.avg_cards_per_game

    if league.referee_avg_yellow > 0:
        ref_baseline = league.referee_avg_yellow + (league.referee_avg_red * 2.0)
        ref_dev_ratio = ref_baseline / max(league_cards_avg, 1.0)
        ref_modifier = 1.0 + (ref_dev_ratio - 1.0) * 0.50
        lam *= ref_modifier

    # 5. Shrinkage
    avg_team_cards = league_cards_avg / 2.0
    prior_n = 5.0
    shrink_w = prior_n / (prior_n + actual_matches)  # uses segmented match count when general=False

    lam = lam * (1.0 - shrink_w) + avg_team_cards * shrink_w

    return max(lam, 0.5)


def _compute_team_shots_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    avg_team_shots = league.avg_shots_per_game / 2.0

    # Base: tiros propios
    gen_str = team.shots_per_game

    # Ajuste por calidad de tiros (tiros dentro del área)
    inside_ratio = team.shots_inside_box / max(team.shots_per_game, 0.1)
    quality_mult = 1.0 + (inside_ratio - 0.55) * 0.10  # ±5%

    # Big chances created indica alta generación
    chance_boost = 1.0 + min(team.big_chances_created / 5.0, 0.06)

    # Dribbles exitosos crean espacios
    dribble_boost = 1.0 + min(team.dribble_success_pct / 200.0, 0.04)

    # Tiros al palo (regresión a la media)
    woodwork_boost = 1.0 + min(team.hit_woodwork / 3.0, 0.03)

    # Contraataques generan tiros rápidos
    fastbreak_boost = 1.0 + min(team.fast_break_shots / 5.0, 0.04)

    # Aplicar boosts con cap global: máximo +12% sobre gen_str
    raw_boost = quality_mult * chance_boost * dribble_boost * woodwork_boost * fastbreak_boost
    capped_boost = max(0.90, min(1.12, raw_boost))
    gen_str = gen_str * capped_boost

    # Factor defensivo del rival (re-centrado: 1.0 = rival promedio → factor ~0.87)
    # poss_factor: rival con 50% posesión → 1.0; defensas con más posesión reducen tiros rivales
    poss_factor = (100.0 - opponent.possession_pct) / 50.0  # sin clamp inferior agresivo
    poss_factor = max(0.50, min(1.30, poss_factor))

    xga_factor = opponent.xga_per_game / max(league.avg_goals_per_game / 2.0, 0.5)
    xga_factor = max(0.60, min(1.40, xga_factor))

    # Factor de tiros concedidos por el rival (centrado en 1.0, ponderando dentro/fuera del área)
    opp_shots_conceded = opponent.shots_inside_box_against_per_game * 1.3 + opponent.shots_outside_box_against_per_game * 0.7
    if opp_shots_conceded <= 0:
        opp_shots_conceded = opponent.shots_against_per_game

    shots_against_factor = opp_shots_conceded / max(avg_team_shots, 1.0)
    shots_against_factor = max(0.50, min(1.50, shots_against_factor))

    # Ajuste por defensas proactivas (bloquean muchos tiros) vs pasivas
    opp_blocks = max(opponent.shots_blocked_against_per_game, opponent.blocked_scoring_attempt_against_per_game)
    block_ratio = opp_blocks / max(opponent.shots_against_per_game, 1.0)
    block_mult = 1.0 - (block_ratio - 0.22) * 0.20  # ajuste de hasta ±8%
    block_mult = max(0.92, min(1.08, block_mult))

    # Factor compuesto centrado en ~0.87 para rival promedio (reduce tiros esperados)
    opp_def_factor = (0.30 * poss_factor + 0.30 * xga_factor + 0.40 * shots_against_factor) * 0.87 * block_mult
    opp_def_factor = max(0.50, min(1.15, opp_def_factor))

    lam = gen_str * opp_def_factor

    # Shrinkage bayesiana: aumentamos prior_n para anclar mejor al promedio de liga
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    prior_n = 5.0
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_shots * shrink_w
    return max(lam, 1.0)


def _compute_team_shots_target_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    avg_team_sot = league.avg_shots_target_per_game / 2.0
    gen_str = team.shots_on_target_per_game

    # Precisión de tiros basada en ubicación
    inside_ratio = team.shots_inside_box / max(team.shots_per_game, 0.1)
    accuracy_mult = 1.0 + (inside_ratio - 0.55) * 0.12

    # Big chances created = tiros de alta calidad
    chance_boost = 1.0 + min(team.big_chances_created / 5.0, 0.07)

    # Dribbles exitosos = tiros más claros
    dribble_boost = 1.0 + min(team.dribble_success_pct / 200.0, 0.04)

    # Cap global: máximo +10% sobre gen_str
    raw_boost = accuracy_mult * chance_boost * dribble_boost
    capped_boost = max(0.90, min(1.10, raw_boost))
    gen_str = gen_str * capped_boost

    # Factor defensivo del rival (mismo re-centrado que en shots)
    poss_factor = (100.0 - opponent.possession_pct) / 50.0
    poss_factor = max(0.50, min(1.30, poss_factor))

    xga_factor = opponent.xga_per_game / max(league.avg_goals_per_game / 2.0, 0.5)
    xga_factor = max(0.60, min(1.40, xga_factor))

    # Factor de tiros a puerta concedidos por el rival (centrado en 1.0)
    sot_against_factor = opponent.shots_on_target_against_per_game / max(avg_team_sot, 0.5)
    sot_against_factor = max(0.50, min(1.50, sot_against_factor))

    opp_def_factor = (0.30 * poss_factor + 0.30 * xga_factor + 0.40 * sot_against_factor) * 0.87
    opp_def_factor = max(0.50, min(1.15, opp_def_factor))

    lam = gen_str * opp_def_factor

    # Shrinkage bayesiana fortalecida
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    prior_n = 5.0
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_sot * shrink_w
    return max(lam, 0.5)


def split_asian_line(line: float) -> list[float]:
    """Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)."""
    if abs(line * 4 % 2) != 0:
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
    total = h_lam + a_lam
    base = -0.13

    if total < 2.0: return max(-0.18, base - 0.03)
    if total > 3.0: return min(-0.08, base + 0.03)
    return base


def _dc_score_matrix(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> tuple[list[list[float]], float]:
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


def _compute_corners_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_lam_c = _compute_team_corners_lambda(h, a, league, is_home=True, general=general)
    a_lam_c = _compute_team_corners_lambda(a, h, league, is_home=False, general=general)
    lam_corners = h_lam_c + a_lam_c

    if lam_corners < 2.0:
        lam_corners = league.avg_corners_per_game
    return lam_corners


def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_lam_cards = _compute_team_cards_lambda(h, a, league, is_home=True, general=general)
    a_lam_cards = _compute_team_cards_lambda(a, h, league, is_home=False, general=general)

    lam_cards = h_lam_cards + a_lam_cards

    if lam_cards < 1.0:
        lam_cards = league.avg_cards_per_game

    return lam_cards


def _compute_shots_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_s_exp = _compute_team_shots_lambda(h, a, league, is_home=True, general=general)
    a_s_exp = _compute_team_shots_lambda(a, h, league, is_home=False, general=general)
    lam_shots = h_s_exp + a_s_exp
    return max(lam_shots, league.avg_shots_per_game * 0.5)


def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_st_exp = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general)
    a_st_exp = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general)
    lam_shots_target = h_st_exp + a_st_exp
    return max(lam_shots_target, league.avg_shots_target_per_game * 0.5)


# ── Faltas y Offsides MEJORADOS ─────────────────────────────

def _compute_team_fouls_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    avg_team_fouls = avg_league_fouls / 2.0
    gen_str = team.fouls_per_game if team.fouls_per_game > 0 else avg_team_fouls

    # NUEVO: Factor de intensidad física
    physical_intensity = 1.0
    if team.kilometers_covered > 105:
        physical_intensity = 1.08
    elif team.kilometers_covered > 95:
        physical_intensity = 1.04

    if team.number_of_sprints > 300:
        physical_intensity *= 1.05

    # NUEVO: Duelos totales como proxy de contacto físico
    duel_factor = 1.0 + (team.duels_total_per_game - 45.0) * 0.003  # 45 es referencia

    # NUEVO: Posesión rival (más posesión rival = más faltas para recuperar)
    opp_possession = opponent.possession_pct if opponent.possession_pct > 0 else 50.0
    opp_factor = max(opp_possession / 50.0, 0.5)

    lam = gen_str * opp_factor * physical_intensity * duel_factor
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_fouls * shrink_w
    return max(lam, 1.0)


def _compute_fouls_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_f_exp = _compute_team_fouls_lambda(h, a, league, is_home=True, general=general)
    a_f_exp = _compute_team_fouls_lambda(a, h, league, is_home=False, general=general)
    lam_fouls = h_f_exp + a_f_exp
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    return max(lam_fouls, avg_league_fouls * 0.5)


def _compute_team_offsides_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
) -> float:
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    avg_team_offsides = avg_league_offsides / 2.0
    gen_str = team.offside_per_game if team.offside_per_game > 0 else avg_team_offsides

    team_possession = team.possession_pct if team.possession_pct > 0 else 50.0
    pos_factor = max(team_possession / 50.0, 0.5)

    # NUEVO: Contraataques aumentan offsides (línea defensiva alta del rival)
    fastbreak_factor = 1.0 + min(team.fast_breaks / 15.0, 0.10)

    # NUEVO: Dribbles exitosos = más penetración = más offsides potenciales
    dribble_factor = 1.0 + min(team.dribble_success_pct / 300.0, 0.05)

    lam = gen_str * pos_factor * fastbreak_factor * dribble_factor
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    n = max(m_count, 1)
    shrink_w = 2.0 / (2.0 + n)
    lam = lam * (1.0 - shrink_w) + avg_team_offsides * shrink_w
    return max(lam, 0.1)


def _compute_offsides_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False) -> float:
    h_o_exp = _compute_team_offsides_lambda(h, a, league, is_home=True, general=general)
    a_o_exp = _compute_team_offsides_lambda(a, h, league, is_home=False, general=general)
    lam_offsides = h_o_exp + a_o_exp
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    return max(lam_offsides, avg_league_offsides * 0.5)


def _poisson_over_under(lam: float, line: float, max_k: int = 40) -> tuple[float, float, float]:
    def _get_single_line_probs(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        for k in range(max_k + 1):
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


import re

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
        (r'\b(1x|local\s+o\s+empate)\b', "home_draw"),
        (r'\b(x2|empate\s+o\s+visitante)\b', "draw_away"),
        (r'\b(12|local\s+o\s+visitante)\b', "home_away"),
    ]
    
    for pattern, side in patterns:
        if re.search(pattern, s):
            return side
    
    return "none"


def is_market_blacklisted_for_league(league_name: str, selection: str, category: str | None = None) -> bool:
    """
    Comprueba si una combinación de competición (nombre exacto) y selección/mercado
    está en la blacklist de data/league_penalties.json.
    Si la regla especifica una categoría, solo se aplica a esa categoría.
    Si no especifica categoría, se aplica a todas.
    """
    try:
        data_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "league_penalties.json")
        if not os.path.exists(data_path):
            return False
        import json
        with open(data_path, "r", encoding="utf-8") as f:
            penalties = json.load(f)

        if not isinstance(penalties, list):
            return False

        family = _market_family(selection)
        side = _market_side(selection)

        for rule in penalties:
            rule_league = (rule.get("league") or "").strip()
            # Coincidencia exacta de liga case-insensitive o coincidencia normalizada
            if rule_league and (rule_league.lower() == (league_name or "").strip().lower() or _normalize_text(rule_league) == _normalize_text(league_name)):
                rule_family = rule.get("market_family", "").strip().lower()
                rule_side = rule.get("market_side", "").strip().lower()

                match_family = not rule_family or rule_family == family.lower()
                match_side = not rule_side or rule_side == side.lower()

                if match_family and match_side:
                    # Comprobar categoría
                    rule_cat = rule.get("category")
                    
                    def normalize_cat(c: str | None) -> str | None:
                        if not c:
                            return None
                        c_lower = c.strip().lower()
                        if c_lower in {"profesional", "publishable"}:
                            return "profesional"
                        if c_lower in {"high", "high_confidence", "alta confianza"}:
                            return "high_confidence"
                        return c_lower

                    norm_rule_cat = normalize_cat(rule_cat)
                    norm_requested_cat = normalize_cat(category)

                    match_category = True
                    if norm_rule_cat is not None:
                        match_category = (norm_rule_cat == norm_requested_cat)

                    if match_category:
                        # Si tiene un flag blacklist=true o si esta especificado en el json
                        if rule.get("blacklist", True) or rule.get("blacklist") is not False:
                            return True

        return False
    except Exception:
        return False


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


# ── Support Over/Under Goals MEJORADO ──
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

    # NUEVO: Factores avanzados
    h_fb = _safe_num(h.fast_break_goals)
    a_fb = _safe_num(a.fast_break_goals)
    h_out = _safe_num(h.goals_outside_box)
    a_out = _safe_num(a.goals_outside_box)
    h_poss_lost = _safe_num(h.possession_lost)
    a_poss_lost = _safe_num(a.possession_lost)
    h_errors = _safe_num(h.errors_leading_to_goal) + _safe_num(h.errors_leading_to_shot) * 0.3
    a_errors = _safe_num(a.errors_leading_to_goal) + _safe_num(a.errors_leading_to_shot) * 0.3

    base_total = (h_g + a_g + h_c + a_c + h_xg + a_xg + h_xga + a_xga) / 4
    attack_bonus = (h_big + a_big) * 1.8 + (h_sot + a_sot) * 0.9

    # NUEVO: Bonus por transiciones y errores
    transition_bonus = (h_fb + a_fb) * 2.5 + (h_out + a_out) * 1.5
    error_bonus = (h_errors + a_errors) * 1.2

    # NUEVO: Pérdidas de posesión altas = más transiciones = más goles
    turnover_bonus = 0
    if h_poss_lost > 100 and a_poss_lost > 100:
        turnover_bonus = 3.0

    stat = 56 + (base_total - line) * 18 + attack_bonus + transition_bonus + error_bonus + turnover_bonus
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


# ── Support BTTS MEJORADO ──
def _support_btts_yes(h, a, proj: list) -> tuple[float, float]:
    h_g = _safe_num(h.goals_per_game)
    a_g = _safe_num(a.goals_per_game)
    h_xg = _safe_num(h.xg_per_game)
    a_xg = _safe_num(a.xg_per_game)
    h_c = _safe_num(h.goals_conceded_per_game)
    a_c = _safe_num(a.goals_conceded_per_game)
    h_xga = _safe_num(h.xga_per_game)
    a_xga = _safe_num(a.xga_per_game)

    # Nota: _support_btts_yes no recibe `general` directamente, pero puede inferirlo
    # comparando si matches_home/away tienen valor útil. Se usa matches_played como fallback.
    _h_mp = max(_safe_num(h.matches_home, 1), 1)
    _a_ma = max(_safe_num(a.matches_away, 1), 1)
    _h_mp_total = max(_safe_num(h.matches_played, 1), 1)
    _a_mp_total = max(_safe_num(a.matches_played, 1), 1)
    # Si matches_home/away son 1 (valor por defecto) pero matches_played > 1, usar el total
    if _safe_num(h.matches_home, 1) <= 1 and _h_mp_total > 1:
        h_cs_rate = _safe_num(h.clean_sheets) / _h_mp_total
    else:
        h_cs_rate = _safe_num(h.clean_sheets_home) / _h_mp
    if _safe_num(a.matches_away, 1) <= 1 and _a_mp_total > 1:
        a_cs_rate = _safe_num(a.clean_sheets) / _a_mp_total
    else:
        a_cs_rate = _safe_num(a.clean_sheets_away) / _a_ma

    h_attack = (h_g + h_xg) / 2.0
    a_attack = (a_g + a_xg) / 2.0
    h_def_weakness = (a_c + a_xga) / 2.0
    a_def_weakness = (h_c + h_xga) / 2.0

    h_score = h_attack * 8.0 + h_def_weakness * 5.0 - h_cs_rate * 20.0
    a_score = a_attack * 8.0 + a_def_weakness * 5.0 - a_cs_rate * 20.0

    stat = 45.0 + (h_score + a_score) / 2.0

    # NUEVO: Ajustes BTTS avanzados
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


# ── Support Shots MEJORADO ──
def _support_under_shots(line: float, h, a, proj: list) -> tuple[float, float]:
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

    return stat, _clip_0_100(proj_score)


def _support_over_shots(line: float, h, a, proj: list) -> tuple[float, float]:
    stat_u, proj_u = _support_under_shots(line, h, a, proj)
    return _clip_0_100(110 - stat_u), _clip_0_100(110 - proj_u)


# ── Support Cards MEJORADO ──
def _support_over_cards(line: float, h, a, proj: list) -> tuple[float, float]:
    total_y = _safe_num(h.yellow_cards_per_game) + _safe_num(a.yellow_cards_per_game)
    total_f = _safe_num(h.fouls_per_game) + _safe_num(a.fouls_per_game)
    total_r = (_safe_num(h.red_cards_total) + _safe_num(a.red_cards_total)) / max(
        _safe_num(h.matches_played, 1) + _safe_num(a.matches_played, 1), 2
    )

    # NUEVO: Factores avanzados de tarjetas
    h_pen = _safe_num(h.penalties_conceded)
    a_pen = _safe_num(a.penalties_conceded)
    h_err = _safe_num(h.errors_leading_to_shot)
    a_err = _safe_num(a.errors_leading_to_shot)
    h_duels = _safe_num(h.duels_total_per_game)
    a_duels = _safe_num(a.duels_total_per_game)
    h_km = _safe_num(h.kilometers_covered)
    a_km = _safe_num(a.kilometers_covered)

    base = total_y + total_f * 0.10 + total_r * 2.0

    # Ajustes avanzados
    discipline_penalty = (h_pen + a_pen) * 3.0 + (h_err + a_err) * 0.8
    physical_factor = (h_duels + a_duels - 90) * 0.02  # 90 duelos totales = referencia
    intensity_factor = 0
    if h_km > 105 or a_km > 105:
        intensity_factor = 1.5

    base += discipline_penalty + physical_factor + intensity_factor

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


# ── Support Corners MEJORADO ──
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

    # Ajuste por efectividad en centros
    h_cross_ratio = _safe_num(h.crosses_per_game) / max(_safe_num(h.crosses_total_per_game, 20), 1)
    a_cross_ratio = _safe_num(a.crosses_per_game) / max(_safe_num(a.crosses_total_per_game, 20), 1)
    cross_signal = (h_cross_ratio + a_cross_ratio) / 2.0
    stat += (cross_signal - 0.45) * 8

    # NUEVO: Duelos aéreos
    h_aerial = _safe_num(h.aerial_duels_won_per_game)
    a_aerial = _safe_num(a.aerial_duels_won_per_game)
    stat += (h_aerial + a_aerial - 20) * 0.3  # 20 duelos aéreos = referencia

    # NUEVO: Posesión
    h_poss = _safe_num(h.possession_pct)
    a_poss = _safe_num(a.possession_pct)
    stat += ((h_poss + a_poss) / 2.0 - 50) * 0.08

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

    if family == "double_chance":
        h_w, d_w, a_w = _dc_component_weights(h, a)
        stat_h, proj_h = _support_home_win(h, a, proj)
        stat_d, proj_d = _support_draw(h, a, proj)
        stat_a, proj_a = _support_away_win(h, a, proj)

        if "1x" in s:
            norm = h_w + d_w
            w_h, w_d = h_w / norm, d_w / norm
            return (
                _clip_0_100(w_h * stat_h + w_d * stat_d),
                _clip_0_100(w_h * proj_h + w_d * proj_d),
            )
        if "x2" in s:
            norm = a_w + d_w
            w_a, w_d2 = a_w / norm, d_w / norm
            return (
                _clip_0_100(w_a * stat_a + w_d2 * stat_d),
                _clip_0_100(w_a * proj_a + w_d2 * proj_d),
            )
        if "12" in s:
            norm = h_w + a_w
            w_h2, w_a2 = h_w / norm, a_w / norm
            return (
                _clip_0_100(w_h2 * stat_h + w_a2 * stat_a),
                _clip_0_100(w_h2 * proj_h + w_a2 * proj_a),
            )

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


def _deduplicate_correlated_picks(values: list["ValueIndicator"]) -> list["ValueIndicator"]:
    """
    Elimina picks correlacionados dentro del mismo mercado.

    Para mercados donde múltiples líneas van en la misma dirección
    (p.ej. Over 1.5, Over 2.5, Over 3.5 Goles) se mantiene ÚNICAMENTE
    el pick con mayor EV (edge_ev). Esto reduce la varianza de la cartera
    y evita exposición concentrada en el mismo resultado subyacente.

    Mercados afectados por deduplicación:
      - goals over / goals under
      - corners over / corners under
      - cards over / cards under
      - shots over / shots under
      - shots_target over / shots_target under
      - handicap (por equipo, best line)

    Mercados excluidos (un pick único por naturaleza):
      - result (home/draw/away)
      - btts (yes/no)
      - double_chance (1X/X2/12)
      - dnb
    """
    DEDUP_FAMILIES = {"goals", "corners", "cards", "shots", "shots_target", "handicap"}

    # Agrupar por (family, side) → lista de ValueIndicators
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
            key=lambda v: v.edge_ev if v.edge_ev is not None else -999.0,
            reverse=True,
        )
        keep = 2 if len(sorted_group) >= 3 else 1
        best_picks.extend(sorted_group[:keep])

    return non_dedup + best_picks


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
    if v.is_blacklisted:
        return -1
    edge = _safe_num(v.edge)
    odds = _safe_num(v.odds, 0.0)
    prob = _safe_num(v.model_prob)
    sel = (v.selection or "").lower()

    if edge < 2.0 or odds <= 1.01:
        return -1

    score = 0

    score += _profitability_band_score(odds)

    if 45.0 <= prob <= 55.0:
        if edge < 5.0:
            return -1
        score += 10

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
    if v.is_blacklisted:
        return -1, 0.0, 0.0, -1
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

    if prob < 56:
        return -1, stat_support, proj_support, strategic_score

    if edge < 1.8:
        return -1, stat_support, proj_support, strategic_score

    family = _market_family(selection)
    min_stat = 53 if family in {"cards", "corners", "shots"} else 52
    if stat_support < min_stat:
        return -1, stat_support, proj_support, strategic_score

    if proj_support < 48:
        return -1, stat_support, proj_support, strategic_score

    # ── SCORE BASE DE SEGURIDAD (FASE 2) ──
    score = 0
    score += _probability_band_score(prob)
    score += int((stat_support - 50) * 0.85)
    score += int((proj_support - 50) * 0.65)
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

    # Penalizaciones por inconsistencia
    if family in {"result", "btts", "handicap"} and odds >= 2.25 and prob < 64:
        score -= 8

    if family in {"goals", "cards", "corners", "shots"} and odds >= 2.60 and prob < 60:
        score -= 8

    # Castigo por falta de muestra segmentada en mercados secundarios
    if family in {"cards", "corners", "shots"}:
        conf = get_market_confidence_tier(selection)
        if conf != "segmented":
            score -= 3

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
        if not v.is_publishable:
            continue

        score = v.quality_score if v.quality_score is not None else -1
        strat_score = v.strategic_score if v.strategic_score is not None else -1
        scored_picks.append((v, score, v.stat_support or 0.0, v.proj_support or 0.0, strat_score))

    scored_picks.sort(
        key=lambda x: (
            _safe_num(x[0].data_quality_score),
            _safe_num(x[0].model_prob),
            x[1],
            x[4],
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
        if len(filtered_ranked) >= 3:
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
- Goles dentro/fuera área: {h.goals_inside_box}/{h.goals_outside_box}
- Goles contraataque: {h.fast_break_goals} | Goles cabeza: {h.headed_goals}
- Grandes chances creadas p/j: {h.big_chances_created} | Creadas/Recibidas: {h.big_chances_per_game}/{h.big_chances_missed_per_game}
- Tiros totales p/j: {h.shots_per_game} | Tiros a puerta p/j: {h.shots_on_target_per_game}
- Tiros dentro/fuera área: {h.shots_inside_box}/{h.shots_outside_box} | Tiros al palo: {h.hit_woodwork}
- Dribbles exitosos %: {h.dribble_success_pct} | Contraataques: {h.fast_breaks}
- Posesión: {h.possession_pct}% | Pérdidas posesión: {h.possession_lost}
- Corners p/j: {h.corners_per_game} de local | Corners concedidos p/j: {h.corners_conceded_per_game} de local
- Duelos aéreos ganados: {h.aerial_duels_won_per_game} | Duelos totales: {h.duels_total_per_game}
- Disciplina: {h.yellow_cards_per_game} Amarillas p/j | {h.fouls_per_game} Faltas p/j | {h.red_cards_total}/{h.matches_played} Rojas p/j
- Penales concedidos: {h.penalties_conceded} | Errores a gol: {h.errors_leading_to_goal} | Errores a tiro: {h.errors_leading_to_shot}
- Defensa: {h.clean_sheets_home} Vallas invictas de local | {h.saves_per_game} Paradas p/j | Save%: {h.save_pct}
- Despejes línea: {h.clearances_off_line} | Entradas último hombre: {h.last_man_tackles}
- Kilómetros: {h.kilometers_covered} | Sprints: {h.number_of_sprints}
- Rating: {h.avg_rating}

SEÑALES CLAVE VISITANTE:
- Partidos jugados: {a.matches_played}
- Victorias: {a.wins} | Empates: {a.draws} | Derrotas: {a.losses}
- Goles p/j: {a.goals_per_game} de visitante | Goles concedidos p/j: {a.goals_conceded_per_game} de visitante
- xG p/j: {a.xg_per_game} de visitante | xGA p/j: {a.xga_per_game} de visitante
- Goles dentro/fuera área: {a.goals_inside_box}/{a.goals_outside_box}
- Goles contraataque: {a.fast_break_goals} | Goles cabeza: {a.headed_goals}
- Grandes chances creadas p/j: {a.big_chances_created} | Creadas/Recibidas: {a.big_chances_per_game}/{a.big_chances_missed_per_game}
- Tiros totales p/j: {a.shots_per_game} | Tiros a puerta p/j: {a.shots_on_target_per_game}
- Tiros dentro/fuera área: {a.shots_inside_box}/{a.shots_outside_box} | Tiros al palo: {a.hit_woodwork}
- Dribbles exitosos %: {a.dribble_success_pct} | Contraataques: {a.fast_breaks}
- Posesión: {a.possession_pct}% | Pérdidas posesión: {a.possession_lost}
- Corners p/j: {a.corners_per_game} de visitante | Corners concedidos p/j: {a.corners_conceded_per_game} de visitante
- Duelos aéreos ganados: {a.aerial_duels_won_per_game} | Duelos totales: {a.duels_total_per_game}
- Disciplina: {a.yellow_cards_per_game} Amarillas p/j | {a.fouls_per_game} Faltas p/j | {a.red_cards_total}/{a.matches_played} Rojas p/j
- Penales concedidos: {a.penalties_conceded} | Errores a gol: {a.errors_leading_to_goal} | Errores a tiro: {a.errors_leading_to_shot}
- Defensa: {a.clean_sheets_away} Vallas invictas de visitante | {a.saves_per_game} Paradas p/j | Save%: {a.save_pct}
- Despejes línea: {a.clearances_off_line} | Entradas último hombre: {a.last_man_tackles}
- Kilómetros: {a.kilometers_covered} | Sprints: {a.number_of_sprints}
- Rating: {a.avg_rating}

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
                "429", "500", "502", "503", "504", "524", "529",
                "rate limit", "timeout", "temporarily unavailable",
                "internal server error", "bad gateway", "service unavailable",
            ]

            if not any(marker.lower() in msg.lower() for marker in retryable_markers):
                return f"Error al generar análisis IA: {e}"

        if attempt < len(retry_delays):
            await asyncio.sleep(delay)

    return last_error or "⚠️ No se pudo generar el análisis con IA tras varios intentos."

# ───────────────────────────────────────────────────────────────
# compare_football
# ───────────────────────────────────────────────────────────────
async def compare_football(req: FootballCompareRequest) -> CompareResponse:
    # Enriquecer league_stats con estadísticas históricas de la BD
    try:
        from src.core.database import SessionLocal
        from src.core.domain import AnalysisHistory
        from src.ui.api.main import _check_pick_success, _calculate_pick_profit, _is_pick_hit
        import json
        
        comp_name = req.competition or "Desconocida"
        req.league_stats.name = comp_name
        
        with SessionLocal() as db_session:
            history = db_session.query(AnalysisHistory).all()
            
            comp_matches = []
            for h_record in history:
                if h_record.payload:
                    try:
                        p_data = json.loads(h_record.payload) if isinstance(h_record.payload, str) else h_record.payload
                        record_comp = p_data.get("competition") or "Desconocida"
                        if record_comp.strip().lower() == comp_name.strip().lower():
                            comp_matches.append(h_record)
                    except:
                        pass
            
            total_matches = len(comp_matches)
            total_picks = 0
            total_hits = 0
            total_profit = 0.0
            market_stats = {}
            
            for h_record in comp_matches:
                if h_record.picks_calculados:
                    try:
                        picks = json.loads(h_record.picks_calculados) if isinstance(h_record.picks_calculados, str) else h_record.picks_calculados
                        if isinstance(picks, list):
                            res_dict = {
                                "final_score_home": h_record.final_score_home,
                                "final_score_away": h_record.final_score_away,
                                "final_corners_home": h_record.final_corners_home,
                                "final_corners_away": h_record.final_corners_away,
                                "final_yellow_cards_home": h_record.final_yellow_cards_home,
                                "final_yellow_cards_away": h_record.final_yellow_cards_away,
                                "final_red_cards_home": h_record.final_red_cards_home,
                                "final_red_cards_away": h_record.final_red_cards_away,
                            }
                            has_result = h_record.final_score_home is not None
                            
                            for pick in picks:
                                is_pub = pick.get("is_publishable", False)
                                is_und = pick.get("is_underdog", False)
                                is_hc = pick.get("is_high_confidence", False)
                                if not is_pub and not is_und and not is_hc:
                                    if pick.get("is_value", False):
                                        is_pub = True
                                if not (is_pub or is_und or is_hc):
                                    continue
                                
                                if has_result:
                                    success = _check_pick_success(pick, res_dict)
                                    if success is not None:
                                        kelly = float(pick.get("kelly_fraction") or 0.0)
                                        stake = min(5, max(1, round(kelly * 100.0))) if kelly > 0 else 1
                                        pick_profit = _calculate_pick_profit(success, pick.get("odds", 0.0)) * stake
                                        total_profit += pick_profit
                                        if success != "void":
                                            total_picks += 1
                                            is_hit = _is_pick_hit(success)
                                            if is_hit:
                                                total_hits += 1
                                                
                                            family = _market_family(pick.get("selection", ""))
                                            if family not in market_stats:
                                                market_stats[family] = {"hits": 0, "total": 0}
                                            market_stats[family]["total"] += 1
                                            if is_hit:
                                                market_stats[family]["hits"] += 1
                    except Exception as e:
                        pass
            
            req.league_stats.historical_matches = total_matches
            req.league_stats.historical_picks = total_picks
            req.league_stats.historical_hits = total_hits
            req.league_stats.historical_profit = round(total_profit, 2)
            req.league_stats.accuracy = round((total_hits / total_picks * 100), 1) if total_picks > 0 else 0.0
            req.league_stats.roi = round((total_profit / total_picks * 100), 2) if total_picks > 0 else 0.0
            
            market_hit_rates = {}
            for family, stats in market_stats.items():
                if stats["total"] >= 3:
                    market_hit_rates[family] = round(stats["hits"] / stats["total"], 3)
            req.league_stats.market_hit_rates = market_hit_rates
    except Exception as ex:
        print(f"Error enriching league stats: {ex}")

    h = _sanitize_and_fill_team_stats(req.home)
    a = _sanitize_and_fill_team_stats(req.away)
    req = req.model_copy(update={"home": h, "away": a})

    h_matches = max(h.matches_played, 1)
    a_matches = max(a.matches_played, 1)

    # ── COMPARACIONES AMPLIADAS CON STATS AVANZADAS ──
    comparisons = [
        # Ataque Básico
        _stat_comparison("Goles por juego",           "goals_per_game",               h.goals_per_game,               a.goals_per_game),
        _stat_comparison("Goles dentro área",         "goals_inside_box",             h.goals_inside_box,             a.goals_inside_box),
        _stat_comparison("Goles fuera área",          "goals_outside_box",            h.goals_outside_box,            a.goals_outside_box),
        _stat_comparison("Goles cabeza",              "headed_goals",                 h.headed_goals,                 a.headed_goals),
        _stat_comparison("Goles contraataque",        "fast_break_goals",             h.fast_break_goals,             a.fast_break_goals),
        _stat_comparison("% Conversión Gol",          "goal_conversion_pct",          h.goal_conversion_pct,          a.goal_conversion_pct),
        _stat_comparison("Grandes chances",           "big_chances_per_game",         h.big_chances_per_game,         a.big_chances_per_game),
        _stat_comparison("G. Chances Creadas",        "big_chances_created",          h.big_chances_created,          a.big_chances_created),
        _stat_comparison("G. Chances Falladas",       "big_chances_missed_per_game",  h.big_chances_missed_per_game,  a.big_chances_missed_per_game, False),
        
        # Tiros
        _stat_comparison("Tiros al arco",             "shots_on_target_per_game",     h.shots_on_target_per_game,     a.shots_on_target_per_game),
        _stat_comparison("Tiros dentro área",         "shots_inside_box",             h.shots_inside_box,             a.shots_inside_box),
        _stat_comparison("Tiros fuera área",          "shots_outside_box",            h.shots_outside_box,            a.shots_outside_box),
        _stat_comparison("Tiros al palo",             "hit_woodwork",                 h.hit_woodwork,                 a.hit_woodwork),
        _stat_comparison("Tiros bloqueados",          "shots_blocked",                h.shots_blocked,                a.shots_blocked),
        
        # Calidad Individual
        _stat_comparison("Dribbles exitosos %",       "dribble_success_pct",          h.dribble_success_pct,          a.dribble_success_pct),
        _stat_comparison("Contraataques",             "fast_breaks",                  h.fast_breaks,                  a.fast_breaks),
        
        # Posesión
        _stat_comparison("Posesión %",                "possession_pct",               h.possession_pct,               a.possession_pct),
        _stat_comparison("Pérdidas posesión",         "possession_lost",              h.possession_lost,              a.possession_lost, False),
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
        _stat_comparison("Errores a Tiro/juego",      "errors_leading_to_shot_pg",    h.errors_leading_to_shot / h_matches, a.errors_leading_to_shot / a_matches, False),
        _stat_comparison("Recuperaciones/j",          "balls_recovered_per_game",     h.balls_recovered_per_game,     a.balls_recovered_per_game),
        _stat_comparison("Despejes línea",            "clearances_off_line",          h.clearances_off_line,          a.clearances_off_line),
        _stat_comparison("Entradas último hombre",    "last_man_tackles",             h.last_man_tackles,             a.last_man_tackles),
        _stat_comparison("Save %",                    "save_pct",                     h.save_pct * 100,               a.save_pct * 100),
        
        # Duelos
        _stat_comparison("Duelos ganados",            "duels_won_per_game",           h.duels_won_per_game,           a.duels_won_per_game),
        _stat_comparison("Duelos aéreos ganados",     "aerial_duels_won_per_game",    h.aerial_duels_won_per_game,    a.aerial_duels_won_per_game),
        _stat_comparison("Duelos en piso",            "ground_duels_won_per_game",    h.ground_duels_won_per_game,    a.ground_duels_won_per_game),
        
        # Disciplina
        _stat_comparison("Faltas/j",                  "fouls_per_game",               h.fouls_per_game,               a.fouls_per_game),
        _stat_comparison("Penales concedidos",        "penalties_conceded",           h.penalties_conceded,           a.penalties_conceded, False),
        _stat_comparison("Amarillas/j",               "yellow_cards_per_game",        h.yellow_cards_per_game,        a.yellow_cards_per_game, False),
        
        # Físicas
        _stat_comparison("Kilómetros/j",              "kilometers_covered",           h.kilometers_covered,           a.kilometers_covered),
        _stat_comparison("Sprints/j",                 "number_of_sprints",            h.number_of_sprints,            a.number_of_sprints),
        
        # Rating
        _stat_comparison("Rating equipo",             "avg_rating",                   h.avg_rating,                   a.avg_rating),
    ]

    use_general = _use_general_stats(req)  # True para partidos >= 2026-07-01

    h_lam = _compute_team_goals_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_lam = _compute_team_goals_lambda(a, h, req.league_stats, is_home=False, general=use_general)
    lam_corners      = _compute_corners_lambda(h, a, req.league_stats, general=use_general)
    lam_cards        = _compute_cards_lambda(h, a, req.league_stats, general=use_general)
    lam_shots        = _compute_shots_lambda(h, a, req.league_stats, general=use_general)
    lam_shots_target = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general)

    h_goals_lam   = h_lam
    a_goals_lam   = a_lam
    h_corners_lam = _compute_team_corners_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_corners_lam = _compute_team_corners_lambda(a, h, req.league_stats, is_home=False, general=use_general)
    h_cards_lam   = _compute_team_cards_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_cards_lam   = _compute_team_cards_lambda(a, h, req.league_stats, is_home=False, general=use_general)
    h_shots_lam   = _compute_team_shots_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_shots_lam   = _compute_team_shots_lambda(a, h, req.league_stats, is_home=False, general=use_general)
    h_shots_target_lam = _compute_team_shots_target_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_shots_target_lam = _compute_team_shots_target_lambda(a, h, req.league_stats, is_home=False, general=use_general)

    matrix, _ = _dc_score_matrix(h_lam, a_lam)
    markets = _sum_score_matrix_1x2_and_markets(matrix)

    h_prob_raw = markets["home_win_pct"] / 100.0
    d_prob_raw = markets["draw_pct"]     / 100.0
    a_prob_raw = markets["away_win_pct"] / 100.0
    p_btts_yes = markets["btts_yes_pct"] / 100.0
    p_btts_no  = markets["btts_no_pct"]  / 100.0

    _BLEND_W    = 0.70
    _DC_BLEND_W = 0.90

    _prior_sum = req.league_stats.home_win_pct + req.league_stats.draw_pct + req.league_stats.away_win_pct

    _ph, _pd, _pa = h_prob_raw, d_prob_raw, a_prob_raw
    h_prob = h_prob_raw
    d_prob = d_prob_raw
    a_prob = a_prob_raw

    if _prior_sum > 0:
        _ph = req.league_stats.home_win_pct / _prior_sum
        _pd = req.league_stats.draw_pct     / _prior_sum
        _pa = req.league_stats.away_win_pct / _prior_sum
        h_prob = h_prob_raw * _BLEND_W + _ph * (1.0 - _BLEND_W)
        d_prob = d_prob_raw * _BLEND_W + _pd * (1.0 - _BLEND_W)
        a_prob = a_prob_raw * _BLEND_W + _pa * (1.0 - _BLEND_W)

    def _overround(*odds_list: float | None) -> float:
        raw = [1.0 / o for o in odds_list if o and o > 1.0]
        return sum(raw) * 100.0 if raw else 100.0

    def _vi(sel: str, odds: float | None, modelp: float, overround: float = 100.0, push_p: float = 0.0) -> ValueIndicator:
        return _value_indicator(sel, odds, modelp, h=h, a=a, overround=overround, push_p=push_p, league=req.league_stats, league_name=req.competition)

    _or_1x2  = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    p_dc_1x = ((h_prob_raw + d_prob_raw) * _DC_BLEND_W + (_ph + _pd) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_x2 = ((d_prob_raw + a_prob_raw) * _DC_BLEND_W + (_pd + _pa) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_12 = ((h_prob_raw + a_prob_raw) * _DC_BLEND_W + (_ph + _pa) * (1.0 - _DC_BLEND_W)) * 100

    _or_dc_raw = _overround(req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12)
    _or_dc = _or_dc_raw if _or_dc_raw > 100.5 else _or_1x2

    _or_dnb_raw = _overround(req.odds.dnb_home, req.odds.dnb_away)
    _or_dnb = _or_dnb_raw if _or_dnb_raw > 100.5 else _or_1x2

    p_dnb_home = (h_prob_raw / max(h_prob_raw + a_prob_raw, 0.1)) * 100
    p_dnb_away = (a_prob_raw / max(h_prob_raw + a_prob_raw, 0.1)) * 100
    push_dnb = d_prob_raw * 100

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
        market_configs.append((f"Under {line} Tiros", underOdds, p_under, _or_shots, p_push))

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

    hcap_lines_to_calc = req.odds.handicap_lines if req.odds.handicap_lines else [-1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    
    for hc_line in hcap_lines_to_calc:
        probs = _compute_asian_handicap_probs(h_lam, a_lam, hc_line)
        p_home_covers = probs["win"] + probs["half_win"]
        p_away_covers = probs["loss"] + probs["half_loss"]
        
        projected_lines.append(ProjectedLine(
            label=f"AH {hc_line:+.2f} {h.name}",
            value=hc_line,
            type="handicap_prob",
            prob=round(p_home_covers, 1),
            push_prob=round(probs["push"], 1)
        ))

        h_odds = req.odds.handicap_home_odds.get(str(hc_line))
        a_odds = req.odds.handicap_away_odds.get(str(hc_line))
        _or_hc = _overround(h_odds, a_odds)

        if h_odds:
            market_configs.append((f"AH {hc_line:+.2f} {h.name}", h_odds, p_home_covers, _or_hc, probs["push"]))
        if a_odds:
            market_configs.append((f"AH {(-hc_line):+.2f} {a.name}", a_odds, p_away_covers, _or_hc, probs["push"]))

    # ── Values: Cálculo masivo ─────────────
    values = [_vi(sel, odds, mp, ornd, pushp) for sel, odds, mp, ornd, pushp in market_configs]

    # ── Deduplicación de picks correlacionados ──────────────────
    # Se elimina redundancia dentro del mismo mercado (p.ej. Over 1.5 + Over 2.5 Goles)
    # conservando únicamente la línea con mejor EV por dirección (over/under) y familia.
    values = _deduplicate_correlated_picks(values)

    # ── Sincronización de Calidad y Publicabilidad ─────────────
    for v in values:
        q_score, s_support, p_support, strat_score = _rate_pick_quality(v, h, a, projected_lines)
        v.quality_score   = q_score
        v.strategic_score = strat_score
        v.stat_support    = round(s_support, 1)
        v.proj_support    = round(p_support, 1)
        v.is_publishable = is_publishable_pick(v)
        v.is_value = v.is_publishable

    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp    = [v for v in values if v.is_value]

    # ── Faltas y Offsides Lambdas ─────────────────────────────
    lam_fouls = _compute_fouls_lambda(h, a, req.league_stats, general=use_general)
    h_fouls_lam = _compute_team_fouls_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_fouls_lam = _compute_team_fouls_lambda(a, h, req.league_stats, is_home=False, general=use_general)

    lam_offsides = _compute_offsides_lambda(h, a, req.league_stats, general=use_general)
    h_offsides_lam = _compute_team_offsides_lambda(h, a, req.league_stats, is_home=True,  general=use_general)
    a_offsides_lam = _compute_team_offsides_lambda(a, h, req.league_stats, is_home=False, general=use_general)

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

    projected_lines.append(ProjectedLine(label="Faltas Totales (λ)", value=round(lam_fouls, 1), type="fouls", prob=None))
    projected_lines.append(ProjectedLine(label=f"Faltas {h.name}", value=h_fouls_lam, type="fouls_team"))
    projected_lines.append(ProjectedLine(label=f"Faltas {a.name}", value=a_fouls_lam, type="fouls_team"))
    projected_lines.append(ProjectedLine(label="Offsides Totales (λ)", value=round(lam_offsides, 1), type="offsides", prob=None))
    projected_lines.append(ProjectedLine(label=f"Offsides {h.name}", value=h_offsides_lam, type="offsides_team"))
    projected_lines.append(ProjectedLine(label=f"Offsides {a.name}", value=a_offsides_lam, type="offsides_team"))

    summary = (
        f"Sherlock Analytics | λ Goles: {h.name} {h_lam:.2f} - {a.name} {a_lam:.2f}\\n"
        f"Proyección Total: {projected_total_goals:.2f} Goles | {lam_corners:.1f} Corners | {lam_cards:.1f} Tarjetas | {lam_shots:.1f} Tiros | {lam_shots_target:.1f} a Pta\\n"
        f"Goles por equipo: {h.name} {h_goals_lam:.2f} | {a.name} {a_goals_lam:.2f}\\n"
        f"Corners por equipo: {h.name} {h_corners_lam:.1f} | {a.name} {a_corners_lam:.1f}\\n"
        f"Tarjetas por equipo: {h.name} {h_cards_lam:.1f} | {a.name} {a_cards_lam:.1f}\\n"
        f"Handicap Estimado: {h.name} {proj_hcap:+.2f}\\n"
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