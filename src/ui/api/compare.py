from __future__ import annotations

from enum import Enum
from typing import Optional
import os, math
import re
import logging
from pathlib import Path
import numpy as np
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Optional, Any, Dict, List, Iterable
from src.core.pick_rules_engine import (
    evaluate_pick_rules,
    resolve_match_picks_correlation as engine_resolve_match_picks_correlation,
    load_pick_rules_data,
    StatSource,
)
from datetime import datetime
from src.domain.settlement import ReturnDistribution, Side
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

load_dotenv()

logger = logging.getLogger("sherlock.compare")


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
    goals_per_game:          float = Field(0.0, description="Goles por juego")
    goals_conceded_per_game: float = Field(0.0, description="Goles concedidos por juego")
    goal_conversion_pct:     float = Field(0.0, description="Conversión de gol %")

    # Goles Detallados (NUEVO)
    goals_inside_box:        float = Field(0.0, description="Goles dentro del área por juego")
    goals_outside_box:       float = Field(0.0, description="Goles fuera del área por juego")
    headed_goals:            float = Field(0.0, description="Goles de cabeza por juego")
    free_kick_goals:         float = Field(0.0, description="Goles de tiro libre por juego")
    fast_break_goals:        float = Field(0.0, description="Goles en contraataque por juego")
    penalty_goals:           float = Field(0.0, description="Goles de penalti por juego")
    own_goals:               float = Field(0.0, description="Autogoles por juego")

    # Ataque
    big_chances_per_game:         float = Field(0.0, description="Grandes chances por juego")
    big_chances_missed_per_game:  float = Field(0.0, description="Grandes chances falladas por juego")
    big_chances_created:          float = Field(0.0, description="Grandes chances creadas por juego")
    shots_per_game:               float = Field(0.0, description="Tiros totales por juego")
    shots_on_target_per_game:     float = Field(0.0, description="Tiros al arco por juego")

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
    possession_pct:         float = Field(50.0, description="Posesión %")
    passes_completed:       float = Field(0,   description="Pases acertados")
    pass_accuracy:          float = Field(0,   description="Precisión pases %")
    passes_opp_half:        float = Field(0,   description="Pases acertados campo rival")
    pass_accuracy_opp_half: float = Field(0,   description="Precisión pases campo rival %")
    crosses_per_game:       float = Field(0,   description="Centros completos por juego")
    cross_accuracy:         float = Field(0,   description="Precisión de centros %")
    corners_per_game:       float = Field(4.5, description="Corners por juego")

    # Posesión Avanzada (NUEVO)
    possession_lost:        float = Field(0.0, description="Pérdidas de posesión por juego")

    # Defensa
    clean_sheets_home:        int   = Field(0,   description="Vallas invictas como local")
    clean_sheets_away:        int   = Field(0,   description="Vallas invictas como visitante")
    clean_sheets:             float = Field(0.0, description="Vallas invictas totales")
    saves_per_game:           float = Field(0,   description="Saves por juego")
    balls_recovered_per_game: float = Field(0.0, description="Recuperaciones por juego")

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
    fouls_per_game:        float = Field(0.0, description="Faltas por juego")
    yellow_cards_per_game: float = Field(0.0, description="Amarillas promedio por juego")

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

    # ── NUEVO: cuotas crudas por casa, para line shopping automático ──
    # Shape: { "betano": {...normalizado...}, "betplay": {...} }
    # Si viene poblado, compare_teams_football() en main.py calcula la
    # mejor cuota por mercado/línea ANTES de correr el motor de picks.
    sources: Optional[Dict[str, dict]] = Field(default=None)


class FootballCompareRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    id: Optional[str] = None          
    analysis_id: Optional[str] = None 
    date: Optional[str] = None        

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
    league_reliability_score:   Optional[float] = None
    league_reliability_penalty: Optional[float] = None

    # Clasificación de Mercado
    market_confidence_tier: Optional[str]   = None
    market_variance_tier:   Optional[str]   = None

    # Flags de Decisión
    is_publishable:        bool = False
    is_underdog:           bool = False
    success:               Optional[bool | str] = None
    display_score:         Optional[float] = None
    push_prob:             Optional[float] = None

    # Staking
    kelly_fraction:        Optional[float] = None
    sample_size_weight:    Optional[float] = None
    is_blacklisted:        bool = False
    stake_units:           Optional[float] = None

    # ── NUEVO: line shopping — casa que ofrece la mejor cuota para este pick ──
    bookmaker: Optional[str] = None

    # ── Frecuencia real / Hit Rate empírico (% de partidos donde se dio el pick) ──
    home_hit_rate: Optional[float] = None
    away_hit_rate: Optional[float] = None
    empirical_hit_rate: Optional[float] = None
    h2h_hit_rate: Optional[float] = None
    h2h_raw_hit_rate: Optional[float] = None
    hit_rate_samples: Optional[int] = None
    h2h_samples: Optional[int] = None
    h2h_matches: Optional[List[Dict[str, Any]]] = None

    # ── Reglas de pick: True si fue bloqueado por una regla estadística o de correlación ──
    is_rule_blocked: bool = False
    correlation_blocked: bool = False
    rule_blocked_reason: Optional[str] = None
    correlation_penalty_applied: bool = False
    correlation_penalty_reason: Optional[str] = None

    # ── Elegibilidad: registro INMUTABLE de bloqueos ──────────────────────
    # `eligibility_hard_blocks` solo crece. Cualquier recálculo posterior de
    # `is_publishable` arrastra estos motivos, así que un pick bloqueado no
    # puede volver a publicarse. Antes el bloqueo se perdía al recalcular.
    eligibility_hard_blocks: List[str] = Field(default_factory=list)
    eligibility_soft_failures: List[str] = Field(default_factory=list)
    eligibility_reasons: List[str] = Field(default_factory=list)
    eligibility_policy_version: Optional[str] = None


class StatComparison(BaseModel):
    label:      str
    key:        str
    home_value: float
    away_value: float
    advantage:  str   # "home" | "away" | "even"

class ProjectedLine(BaseModel):
    label: str
    value: float
    type: str  # 'goals', 'corners', 'cards','btts'
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
    mps_confidence: Optional[float] = None  # Probabilidad acumulada del marcador y vecinos (±1 gol)
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


def _neg_bin_pmf(mu: float, r: float, k: int) -> float:
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1) + 
                   r * math.log(p) + k * math.log(1.0 - p))
        return math.exp(log_pmf)
    except (ValueError, OverflowError):
        return 0.0


def _estimate_league_variance(competition_name: str, metric: str, mean_val: float, db: Any = None) -> float:
    fano_factors = {
        "goals": 1.15,
        "corners": 1.40,
        "cards": 1.80,
        "shots": 2.50,
        "shots_target": 2.00,
        "fouls": 1.50,
        "offsides": 1.30,
    }
    fallback_fano = fano_factors.get(metric, 1.20)
    
    if db is not None:
        try:
            from src.core.domain import Competition, Match, StatLineTeam
            comp = db.query(Competition).filter(Competition.name == competition_name).first()
            if comp:
                stats = db.query(StatLineTeam).join(Match).filter(Match.competition_id == comp.id).all()
                if len(stats) >= 10:
                    vals = []
                    if metric == "goals":
                        matches = db.query(Match).filter(Match.competition_id == comp.id, Match.status == "finished").all()
                        for m in matches:
                            if m.home_score is not None: vals.append(m.home_score)
                            if m.away_score is not None: vals.append(m.away_score)
                    elif metric == "corners":
                        vals = [s.corners for s in stats if s.corners is not None]
                    elif metric == "cards":
                        vals = [(s.yellow_cards or 0) + (s.red_cards or 0) * 2.0 for s in stats if s.yellow_cards is not None or s.red_cards is not None]
                    elif metric == "shots":
                        vals = [s.shots for s in stats if s.shots is not None]
                    elif metric == "shots_target":
                        vals = [s.shots_on_target for s in stats if s.shots_on_target is not None]
                    elif metric == "fouls":
                        vals = [s.fouls for s in stats if s.fouls is not None]
                    elif metric == "offsides":
                        vals = [s.offsides for s in stats if s.offsides is not None]
                        
                    if len(vals) >= 10:
                        avg = sum(vals) / len(vals)
                        var = sum((x - avg) ** 2 for x in vals) / (len(vals) - 1)
                        if var > 0.05:
                            return var
        except Exception as e:
            pass
            
    return mean_val * fallback_fano


def _nbinom_pmf(k: int, mu: float, r: float) -> float:
    if mu <= 0 or r <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1) + 
                   r * math.log(p) + k * math.log(1.0 - p))
        return math.exp(log_pmf)
    except (ValueError, OverflowError):
        return 0.0

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


def get_dispersion_r(mu: float, variance: float) -> float:
    if variance <= mu * 1.01:
        return 100.0
    r = (mu ** 2) / (variance - mu)
    return max(0.1, min(r, 100.0))



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


def reset_calibrator_cache() -> None:
    """Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)."""
    _calibrator_cache["mtime"] = None
    _calibrator_cache["obj"] = None


def apply_calibration(raw_prob: float, odds: float, market_family: str,
                       league: "LeagueStats | None" = None,
                       league_name: str | None = None) -> float:
    """
    Calibra la probabilidad del modelo determinista contra el histórico real.

    Sustituye al GLM/IsotonicRegression retirados. En su lugar usa una
    Beta-Binomial jerárquica (global -> familia de mercado -> liga × familia)
    suavizada con isotónica PAVA:

      p̂ = (aciertos + κ·prior_del_padre) / (n + κ)

    Con muestra pequeña p̂ ≈ prior, así que un segmento con 5 picks apenas se
    mueve de su padre y no puede introducir ruido. Sin artefacto entrenado
    devuelve `raw_prob` intacta.

    `raw_prob` está en escala 0-100 y el retorno mantiene esa escala.
    """
    if raw_prob is None:
        return raw_prob

    lg_name = league_name
    if lg_name is None and league is not None:
        lg_name = getattr(league, "name", None) or getattr(league, "league_name", None)

    try:
        return get_calibrator().apply(raw_prob, market_family, lg_name)
    except Exception as exc:
        logger.warning("Fallo al calibrar (%s). Se usa la probabilidad cruda.", exc)
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
    if not h or not a or h.matches_played <= 0 or a.matches_played <= 0:
        return 0.0

    tier = get_market_confidence_tier(selection)
    if tier == "segmented":   base = 92.0
    elif tier == "hybrid":    base = 70.0
    else:                     base = 62.0  # subido de 45 → 62 para shots/cards/fouls

    min_m = min(h.matches_played, a.matches_played)
    if min_m < 8:
        sample_penalty = (10 - min_m) * 3.5  # reducido de 6 → 3.5
    elif min_m < 15:
        sample_penalty = (15 - min_m) * 1.5  # reducido de 2 → 1.5
    else:
        sample_penalty = 0

    family = _market_family(selection)
    if family in {"cards", "corners", "shots"}:
        if h.xg_per_game < 0.4 or a.xg_per_game < 0.4:
            base -= 6  # reducido de 8 → 6

    # Penalización si no hay datos avanzados (rating = 0 indica data pobre)
    if h.avg_rating < 0.1 or a.avg_rating < 0.1:
        base -= 4  # reducido de 5 → 4

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


def score_pick_quality(v: ValueIndicator) -> int:
    if not v.edge_ev: return 0

    ev_score = min(v.edge_ev * 200, 60)

    prob_score = (v.calibrated_prob or v.model_prob) / 5.0

    dq_score = (v.data_quality_score or 50) / 5.0

    total = int(ev_score + prob_score + dq_score)
    return min(max(total, 0), 100)


def is_value_pick(v: Any) -> bool:
    is_blk = v.get("is_blacklisted", False) if isinstance(v, dict) else getattr(v, "is_blacklisted", False)
    is_blk_rule = v.get("is_rule_blocked", False) if isinstance(v, dict) else getattr(v, "is_rule_blocked", False)
    if is_blk or is_blk_rule:
        return False
    # Filtro Crítico H2H: Solo se bloquea si hay partidos H2H evaluados (h2h_samples > 0) Y el hit rate fue 0.0%.
    # Los picks sin enfrentamientos H2H previos (h2h_samples == 0) NO se bloquean.
    h2h_samp = (v.get("h2h_samples", 0) or 0) if isinstance(v, dict) else (getattr(v, "h2h_samples", 0) or 0)
    h2h_hr = v.get("h2h_hit_rate") if isinstance(v, dict) else getattr(v, "h2h_hit_rate", None)
    if h2h_hr is None:
        h2h_hr = v.get("h2h_raw_hit_rate") if isinstance(v, dict) else getattr(v, "h2h_raw_hit_rate", None)
    if h2h_samp > 0 and h2h_hr is not None and h2h_hr == 0.0:
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

    # Umbral EV 0.020 para estabilidad entre recálculos
    return ev_val >= 0.020 and stake_val >= 1.0


def is_underdog_pick(v: Any) -> bool:
    if isinstance(v, dict):
        odds = v.get("odds")
        edge = v.get("edge", 0)
        dq = v.get("data_quality_score")
        stake = v.get("stake_units")
        h2h_hr = v.get("h2h_hit_rate")
        if h2h_hr is None:
            h2h_hr = v.get("h2h_raw_hit_rate")
        h2h_samp = v.get("h2h_samples", 0) or 0
    else:
        odds = getattr(v, "odds", None)
        edge = getattr(v, "edge", 0)
        dq = getattr(v, "data_quality_score", None)
        stake = getattr(v, "stake_units", None)
        h2h_hr = getattr(v, "h2h_hit_rate", None)
        if h2h_hr is None:
            h2h_hr = getattr(v, "h2h_raw_hit_rate", None)
        h2h_samp = getattr(v, "h2h_samples", 0) or 0

    # Filtro Crítico H2H: Solo se bloquea si hay partidos H2H evaluados (h2h_samples > 0) Y el hit rate fue 0.0%.
    if h2h_samp > 0 and h2h_hr is not None and h2h_hr == 0.0:
        return False

    if odds is None or odds <= 2.50 or odds > 4.50:
        return False

    if (edge or 0) < 5:
        return False

    if dq is not None and dq < 50:
        return False

    if stake is not None and stake < 1.0:
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
    Stake puro basado en Kelly fraccional con caps de seguridad.
    Devuelve unidades de 0.5 a 3.0. 0.0 = no jugable.
    """
    if edge_ev < 0.025 or kelly_fraction <= 0:
        return 0.0

    # Kelly fraccional directo: 0.25 Kelly -> 1u por cada 4% del bankroll
    raw_stake = kelly_fraction * 100.0

    # Cap según calidad de la liga
    hard_max = 3.0
    if (lrs or 0.5) < 0.50:
        hard_max = 2.0
    # NOTA (planning.txt punto 4): Se elimina la penalización artificial a underdogs (odds >= 3.0)
    # para permitir que los picks underdog de alto edge reciban su sizing óptimo según Kelly.
    if market_family in {"corners", "cards", "shots", "shots_target", "fouls"}:
        hard_max = min(hard_max, 2.5)

    # Redondeo inteligente: múltiplos de 0.5
    stake = round(max(0.5, min(hard_max, raw_stake)) * 2) / 2

    return stake if stake >= 1.0 else 0.0

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


def _value_indicator(sel, odds, modelp, h=None, a=None, overround=100.0, push_p=0.0, league: "LeagueStats | None" = None, league_name: str | None = None, odds_obj: Any = None):
    if odds is None or odds <= 1.0:
        return ValueIndicator(selection=sel, model_prob=round(modelp, 1), push_prob=round(push_p, 1))

    family = _market_family(sel)
    calibrated_p = apply_calibration(
        modelp, odds, family, league=league, league_name=league_name
    )

    # Recorte heurístico de respaldo: SOLO cuando no hay curva entrenada.
    # Antes se aplicaba siempre (`calibrated_p *= 0.82` con edge >= 20), un
    # factor codificado a mano sin respaldo empírico. Con artefacto entrenado
    # la curva jerárquica ya corrige la sobreconfianza con evidencia real, y
    # aplicar ambos castigaría dos veces el mismo sesgo.
    if not calibration_is_active():
        raw_implied_pre = (1.0 / odds) * 100.0
        if calibrated_p - raw_implied_pre >= 20.0:
            calibrated_p *= 0.82

    raw_implied = (1.0 / odds) * 100.0
    margin_factor = (overround / 100.0) if overround > 100 else 1.05
    implied_no_vig = raw_implied / margin_factor

    # ── EV por distribución de retornos (motor único de settlement) ──────
    # El cálculo anterior era  ev = (p·odds - 1) · (1 - p_push), que trata el
    # push como pérdida y luego lo escala. El push devuelve la apuesta: su
    # retorno es 0. EV correcto:  E[R] = P(win)·(odds-1) - P(loss).
    ret_dist = ReturnDistribution.simple(
        odds=odds, p_win=calibrated_p, p_push=push_p or 0.0
    )
    ev = ret_dist.expected_value

    # Edge en probabilidad, condicionado a que la apuesta resuelva.
    # Sin push esto es idéntico a (calibrated_p - raw_implied).
    edge_prob = (ret_dist.p_win_effective * 100.0) - raw_implied

    # ── League Reliability Score ──────────────────────────────────────────
    # El LRS mide la confiabilidad histórica de la liga.
    # PRINCIPIO CLAVE (planning.txt): el modelo estadístico es inmutable.
    # Su única misión es dar la probabilidad del evento. El LRS NO debe
    # contaminar la calibrated_prob; solo ajusta el kelly_multiplier (staking).
    if league is not None:
        lrs = league.league_reliability_score if league.league_reliability_score > 0.0 else _compute_league_reliability_score(league)
    else:
        lrs = 0.7  # sin datos de liga = confianza moderada

    # Calcular EV con la probabilidad PURA (sin distorsión de LRS)
    # El EV es informativo: (prob * odds) - 1. No se ajusta por LRS.
    lrs_penalty = 0.0  # guardado para display, pero no afecta la prob
    p = calibrated_p / 100.0


    # ─────────────────────────────────────────────────────────────

    conf_tier = get_market_confidence_tier(sel)
    var_tier = get_market_variance_tier(sel)
    dq_score = get_data_quality_score(sel, h, a) if h and a else None

    if   ev > 0.15:  rating = "🔥 STRONG VALUE"
    elif ev > 0.07:  rating = "✅ VALUE"
    elif ev > 0.02:  rating = "⚖️ MARGINAL"
    else:            rating = "❌ NO VALUE"

    # ── Stake Manager: ajuste por LRS ──────────────────────────────────────
    # El LRS afecta SOLO al kelly_multiplier, nunca a la probabilidad.
    # Liga baja confianza (LRS < 0.5) → pasar de 1/4 Kelly a 1/8 Kelly.
    # Liga muy baja confianza (LRS < 0.35) → 1/16 Kelly.
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
        kelly_multiplier = 0.25          # 1/4 Kelly (confianza normal)
    elif lrs >= 0.50:
        kelly_multiplier = 0.125         # 1/8 Kelly (liga baja confianza)
    elif lrs >= 0.35:
        kelly_multiplier = 0.0625        # 1/16 Kelly (liga muy baja confianza)
    else:
        kelly_multiplier = 0.03125       # 1/32 Kelly (liga sin datos reales)
    kelly_multiplier *= market_lrs_factor

    # Aplicar límite adicional si la liga tiene rendimiento histórico pobre
    if league is not None and getattr(league, "historical_picks", 0) >= 5:
        hist_profit = getattr(league, "historical_profit", 0.0)
        hist_accuracy = getattr(league, "accuracy", 100.0)
        if hist_profit < 0.0 or hist_accuracy < 40.0:
            kelly_multiplier = min(kelly_multiplier, 0.03125)

    kelly_fraction = _calculate_kelly_fraction(
        calibrated_prob=calibrated_p,   # probabilidad PURA, sin distorsión LRS
        odds=odds,
        kelly_multiplier=kelly_multiplier,
        distribution=ret_dist,          # push = retorno 0, no pérdida
    )

    family = _market_family(sel)
    stake = _calculate_stake_units(
        edge_ev=ev,
        odds=odds or 1.0,
        kelly_fraction=kelly_fraction,
        market_family=family,
        lrs=lrs,
    )


    v = ValueIndicator(
        selection=sel,
        odds=odds,
        model_prob=round(modelp, 1),
        calibrated_prob=round(calibrated_p, 1),
        implied_prob=round(raw_implied, 1),
        implied_prob_no_vig=round(implied_no_vig, 1),
        fair_odds=round(ret_dist.fair_odds, 2) if ret_dist.fair_odds else None,
        edge=round(edge_prob, 1),
        edge_ev=round(ev, 3),
        push_prob=round(push_p, 1),
        is_value=ev >= 0.020 and stake >= 1.0 and odds <= 3.50,
        rating=rating,
        data_quality_score=dq_score,
        market_confidence_tier=conf_tier,
        market_variance_tier=var_tier,
        kelly_fraction=round(kelly_fraction, 4),
        stake_units=stake,
        sample_size_weight=min(1.0, (h.matches_played + a.matches_played) / 30.0) if h and a else 0.5,
        league_reliability_score=round(lrs, 3),
        league_reliability_penalty=lrs_penalty,
    )

    # ── Blacklist de liga: bloqueo duro ──────────────────────────────────
    if league_name and is_market_blacklisted_for_league(league_name, sel):
        block_pick(v, BlockReason.BLACKLISTED)
        v.strategic_score = -1
    else:
        v.quality_score = score_pick_quality(v)
        # `evaluate_pick_eligibility` fija is_publishable y, si hay bloqueo
        # duro, fuerza quality_score = -1. Debe ir DESPUÉS de calcular la
        # calidad para que el centinela no se sobrescriba.
        evaluate_pick_eligibility(v)
        v.is_value = is_value_pick(v) and v.is_publishable
        v.display_score = _calculate_display_score(v)
        v.is_underdog = is_underdog_pick(v)

    # ── Reglas estadísticas: bloqueo duro ────────────────────────────────
    if not v.is_blacklisted and h is not None and a is not None:
        if is_pick_blocked_by_rules(sel, h, a, odds_obj):
            block_pick(v, BlockReason.RULE_BLOCKED)

    return v



# ───────────────────────────────────────────────────────────────
# Poisson engine (Football)
# ───────────────────────────────────────────────────────────────

def estimate_empirical_bayes_prior_n(
    league_variance: float,
    league_mean: float,
    baseline_prior_n: float = 5.0,
    min_prior_n: float = 2.0,
    max_prior_n: float = 12.0,
) -> float:
    """
    league_variance: varianza observada de la métrica (goles/tarjetas/corners)
                      entre partidos de esta liga.
    league_mean:     media de la misma métrica.

    Ligas con dispersión relativa (varianza/media, índice de Fano) alta
    respecto a lo esperado bajo Poisson (Fano=1) son más "caóticas" ->
    prior_n sube (confiamos menos en pocos partidos del equipo).
    Ligas con Fano < 1 (más estables que Poisson puro) -> prior_n baja.
    """
    if league_mean <= 0:
        return baseline_prior_n
    fano = league_variance / league_mean
    prior_n = baseline_prior_n * fano
    return round(max(min_prior_n, min(max_prior_n, prior_n)), 2)

def _compute_team_goals_lambda(
    attacker: FootballTeamStats,
    defender: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
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

    # Dynamic prior_n estimation using Empirical Bayes
    goals_mean = league.avg_goals_per_game
    goals_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "goals", goals_mean, db=db)
    beta_prior = estimate_empirical_bayes_prior_n(goals_var, goals_mean, baseline_prior_n=5.0)

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

    # ── 5. Ajuste por forma reciente (ventanas 5 / 10 / 15) ──
    # Si el attacker tiene stats de forma reciente, las usamos para ajustar
    # el factor de ataque; de lo contrario caemos a 1.0 (sin ajuste extra).
    form_factor_att = 1.0
    form_factor_def = 1.0

    att_recent = getattr(attacker, "recent_form", None)
    if att_recent and isinstance(att_recent, dict):
        w5  = att_recent.get("last_5",  {}).get("goals_scored", avg_team_goals)
        w10 = att_recent.get("last_10", {}).get("goals_scored", avg_team_goals)
        w15 = att_recent.get("last_15", {}).get("goals_scored", avg_team_goals)
        form_avg_att = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor_att = form_avg_att / max(avg_team_goals, 0.10)
        form_factor_att = max(0.70, min(1.30, form_factor_att))

    def_recent = getattr(defender, "recent_form", None)
    if def_recent and isinstance(def_recent, dict):
        w5  = def_recent.get("last_5",  {}).get("goals_conceded", avg_team_goals)
        w10 = def_recent.get("last_10", {}).get("goals_conceded", avg_team_goals)
        w15 = def_recent.get("last_15", {}).get("goals_conceded", avg_team_goals)
        form_avg_def = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor_def = form_avg_def / max(avg_team_goals, 0.10)
        form_factor_def = max(0.70, min(1.30, form_factor_def))

    lam_adjusted = lam_base * form_factor_att * form_factor_def

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
    db: Any = None,
) -> tuple[float, float]:
    """Retorna (mu, r) de la distribución Binomial Negativa para corners del equipo.

    La sobredispersión es intrínseca a corners (Var > Media), por lo que se usa
    Binomial Negativa en lugar de Poisson. El parámetro r = mu / (fano - 1).
    """
    avg_team_corners = league.avg_corners_per_game / 2.0

    # ── 1. Fuerza de generación de corners: normalizada contra media de liga ──
    att_str = team.corners_per_game / max(avg_team_corners, 0.5)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Capacidad del rival de conceder corners: normalizada contra media ──
    opp_conceded = opponent.corners_conceded_per_game / max(avg_team_corners, 0.5)
    opp_conceded = max(0.40, min(2.0, opp_conceded))

    # ── 3. Lambda base: ataque x debilidad rival, anclado a media de liga ──
    lam = att_str * opp_conceded * avg_team_corners

    # ── 4. Ajuste por forma reciente de corners (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5  = team_recent.get("last_5",  {}).get("corners", avg_team_corners)
        w10 = team_recent.get("last_10", {}).get("corners", avg_team_corners)
        w15 = team_recent.get("last_15", {}).get("corners", avg_team_corners)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_corners, 0.5)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    corners_mean = league.avg_corners_per_game
    corners_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "corners", corners_mean, db=db)
    prior_n = estimate_empirical_bayes_prior_n(corners_var, corners_mean, baseline_prior_n=5.0)

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_corners * shrink_w
    mu = max(lam, 0.5)

    # ── Parámetro de dispersión r (Binomial Negativa) por equipo ──
    team_var = corners_var / 4.0
    r = get_dispersion_r(mu, max(team_var, corners_mean / 2.0 + 0.01))

    return mu, r





def _compute_team_cards_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
) -> float:
    if general:
        actual_matches = max(team.matches_played, 1)
        opp_matches = max(opponent.matches_played, 1)
    else:
        actual_matches = max(team.matches_home if is_home else team.matches_away, 1)
        opp_matches = max(opponent.matches_away if is_home else opponent.matches_home, 1)

    # Determinar promedio de liga (tarjetas equivalentes ponderadas)
    if league.avg_yellow_cards_per_game > 0 and league.avg_red_cards_per_game > 0:
        league_cards_avg = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0)
    else:
        league_cards_avg = league.avg_cards_per_game
    avg_team_cards = league_cards_avg / 2.0

    # Dynamic prior_n estimation using Empirical Bayes
    cards_mean = league_cards_avg
    cards_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "cards", cards_mean, db=db)
    prior_n = estimate_empirical_bayes_prior_n(cards_var, cards_mean, baseline_prior_n=10.0)

    # 1. Fuerza de disciplina del equipo normalizada contra la media de liga
    red_card_weight = 2.0
    team_reds_per_game = (team.red_cards_total / actual_matches) * red_card_weight
    own_cards_avg = team.yellow_cards_per_game + team_reds_per_game

    # Shrinkage bayesiana al promedio de liga (primer paso)
    shrink_w_pre = prior_n / (prior_n + actual_matches)
    own_cards_avg = own_cards_avg * (1.0 - shrink_w_pre) + avg_team_cards * shrink_w_pre

    # 2. Ratio de disciplina del equipo vs media de liga (continuo, sin escalones)
    team_card_ratio = own_cards_avg / max(avg_team_cards, 0.5)
    team_card_ratio = max(0.50, min(1.50, team_card_ratio))

    # 3. Ratio de tarjetas provocadas del rival (cuánto genera el rival)
    rival_draw_cards_avg = (opponent.yellow_cards_against + (opponent.red_cards_against * 2.0)) / opp_matches
    rival_ratio = rival_draw_cards_avg / max(avg_team_cards, 0.5)
    rival_ratio = max(0.50, min(1.50, rival_ratio))

    lam = own_cards_avg * rival_ratio

    # 4. Ajuste por forma reciente de tarjetas (ventanas 5 / 10 / 15)
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5  = team_recent.get("last_5",  {}).get("yellow_cards", avg_team_cards)
        w10 = team_recent.get("last_10", {}).get("yellow_cards", avg_team_cards)
        w15 = team_recent.get("last_15", {}).get("yellow_cards", avg_team_cards)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_cards, 0.5)
        form_factor = max(0.70, min(1.30, form_factor))

    lam = lam * form_factor

    # 5. Integración del Árbitro (dato real — conservar)
    if league.referee_avg_yellow > 0:
        ref_baseline = league.referee_avg_yellow + (league.referee_avg_red * 2.0)
        ref_dev_ratio = ref_baseline / max(league_cards_avg, 1.0)
        ref_modifier = 1.0 + (ref_dev_ratio - 1.0) * 0.50
        ref_modifier = max(0.70, min(1.30, ref_modifier))
        lam *= ref_modifier

    # 6. Shrinkage final al promedio de liga
    shrink_w = prior_n / (prior_n + actual_matches)
    lam = lam * (1.0 - shrink_w) + avg_team_cards * shrink_w

    mu = max(lam, 0.4)
    team_var = cards_var / 4.0
    r = get_dispersion_r(mu, max(team_var, cards_mean / 2.0 + 0.01))
    return mu, r




def _compute_team_shots_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
) -> tuple[float, float]:
    """Retorna (mu, r) de la distribución Binomial Negativa para tiros del equipo.

    La sobredispersión es intrínseca a los tiros (Var >> Media, Fano ~2.5), por lo
    que se usa Binomial Negativa en lugar de Poisson para modelar las colas correctamente.
    """
    avg_team_shots = league.avg_shots_per_game / 2.0

    # ── 1. Fuerza de tiros del equipo normalizada contra media de liga ──
    att_str = team.shots_per_game / max(avg_team_shots, 1.0)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Debilidad defensiva del rival: tiros concedidos vs media de liga ──
    opp_shots_conceded = opponent.shots_against_per_game
    def_weakness = opp_shots_conceded / max(avg_team_shots, 1.0)
    def_weakness = max(0.40, min(2.0, def_weakness))

    # ── 3. Lambda base ──
    lam = att_str * def_weakness * avg_team_shots

    # ── 4. Ajuste por forma reciente de tiros (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5  = team_recent.get("last_5",  {}).get("shots", avg_team_shots)
        w10 = team_recent.get("last_10", {}).get("shots", avg_team_shots)
        w15 = team_recent.get("last_15", {}).get("shots", avg_team_shots)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_shots, 1.0)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    shots_mean = league.avg_shots_per_game
    shots_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "shots", shots_mean, db=db)
    prior_n = estimate_empirical_bayes_prior_n(shots_var, shots_mean, baseline_prior_n=5.0)

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_shots * shrink_w
    mu = max(lam, 1.0)

    team_var = shots_var / 4.0
    r = get_dispersion_r(mu, max(team_var, shots_mean / 2.0 + 0.01))

    return mu, r


def _compute_team_shots_target_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
) -> tuple[float, float]:
    avg_team_sot = league.avg_shots_target_per_game / 2.0

    # ── 1. Fuerza de tiros a puerta normalizada ──
    att_str = team.shots_on_target_per_game / max(avg_team_sot, 0.5)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Debilidad defensiva del rival en tiros a puerta ──
    def_weakness = opponent.shots_on_target_against_per_game / max(avg_team_sot, 0.5)
    def_weakness = max(0.40, min(2.0, def_weakness))

    # ── 3. Lambda base ──
    lam = att_str * def_weakness * avg_team_sot

    # ── 4. Ajuste por forma reciente (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5  = team_recent.get("last_5",  {}).get("shots_target") or team_recent.get("last_5",  {}).get("shots_on_target", avg_team_sot)
        w10 = team_recent.get("last_10", {}).get("shots_target") or team_recent.get("last_10", {}).get("shots_on_target", avg_team_sot)
        w15 = team_recent.get("last_15", {}).get("shots_target") or team_recent.get("last_15", {}).get("shots_on_target", avg_team_sot)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_sot, 0.5)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    sot_mean = league.avg_shots_target_per_game
    sot_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "shots_target", sot_mean, db=db)
    prior_n = estimate_empirical_bayes_prior_n(sot_var, sot_mean, baseline_prior_n=5.0)

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_sot * shrink_w
    mu = max(lam, 0.5)
    team_var = sot_var / 4.0
    r = get_dispersion_r(mu, max(team_var, sot_mean / 2.0 + 0.01))
    return mu, r



def split_asian_line(line: float) -> list[float]:
    """Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)."""
    if abs(line * 4 % 2) != 0:
        return [line - 0.25, line + 0.25]
    return [line]


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
    """Heurística original — se mantiene como fallback."""
    total = h_lam + a_lam
    base = -0.13
    if total < 2.0:
        return max(-0.18, base - 0.03)
    if total > 3.0:
        return min(-0.08, base + 0.03)
    return base


def _dc_log_likelihood(rho: float, matches: list[tuple[int, int, float, float]]) -> float:
    """
    matches: lista de (goles_local, goles_visitante, lambda_local, lambda_visitante)
    de partidos históricos ya jugados de una liga.
    """
    ll = 0.0
    for hg, ag, lam, mu in matches:
        p = _poisson_pmf(lam, hg) * _poisson_pmf(mu, ag) * _dc_tau(hg, ag, lam, mu, rho)
        p = max(p, 1e-10)
        ll += math.log(p)
    return ll


def fit_dixon_coles_rho(
    matches: list[tuple[int, int, float, float]],
    min_matches: int = 100,
    rho_bounds: tuple[float, float] = (-0.30, 0.05),
    grid_steps: int = 71,
) -> float:
    """
    Ajusta rho por máxima verosimilitud (búsqueda en grilla, robusta y sin
    dependencias externas de optimización) sobre partidos históricos reales.

    Si no hay suficientes partidos (< min_matches), usa el promedio de
    lambdas del set para caer de vuelta en la heurística original — así
    nunca se comporta peor que antes.
    """
    if len(matches) < min_matches:
        if matches:
            avg_lam = sum(m[2] for m in matches) / len(matches)
            avg_mu = sum(m[3] for m in matches) / len(matches)
            return _default_dc_rho(avg_lam, avg_mu)
        return -0.13

    lo, hi = rho_bounds
    best_rho, best_ll = lo, float("-inf")
    for i in range(grid_steps):
        rho = lo + (hi - lo) * i / (grid_steps - 1)
        ll = _dc_log_likelihood(rho, matches)
        if ll > best_ll:
            best_ll, best_rho = ll, rho

    return round(best_rho, 4)


def _dc_score_matrix(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> tuple[list[list[float]], float]:
    rho_used = _default_dc_rho(h_lam, a_lam) if rho is None else rho

    min_lam = min(h_lam, a_lam)
    if min_lam > 0:
        rho_used = max(rho_used, -1.0 / min_lam)
    else:
        rho_used = 0.0

    home_probs = [_poisson_pmf(h_lam, i) for i in range(max_goals + 1)]
    away_probs = [_poisson_pmf(a_lam, j) for j in range(max_goals + 1)]

    matrix: list[list[float]] = []
    for i in range(max_goals + 1):
        row = []
        for j in range(max_goals + 1):
            p = home_probs[i] * away_probs[j]
            p *= _dc_tau(i, j, h_lam, a_lam, rho_used)
            row.append(p)
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


def _combine_nb_params(mu1: float, r1: float, mu2: float, r2: float) -> tuple[float, float]:
    """Combina dos distribuciones Binomial Negativa independientes.

    Para X1 ~ NB(mu1, r1) y X2 ~ NB(mu2, r2) independientes:
      mu_total  = mu1 + mu2
      Var_total = Var1 + Var2  donde Var_i = mu_i + mu_i²/r_i
      r_total   = mu_total² / (Var_total - mu_total)

    Si la varianza combinada no excede la media (i.e. Var ≤ mu), se usa r → ∞
    (equivalente Poisson) como fallback.
    """
    var1 = mu1 + mu1 ** 2 / r1 if r1 > 0 else mu1
    var2 = mu2 + mu2 ** 2 / r2 if r2 > 0 else mu2
    mu_total = mu1 + mu2
    var_total = var1 + var2
    if var_total <= mu_total or mu_total <= 0:
        return mu_total, 50.0  # r grande ≈ Poisson como fallback seguro
    r_total = mu_total ** 2 / (var_total - mu_total)
    return mu_total, max(r_total, 0.5)


def _compute_corners_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    """Retorna (h_mu, h_r, a_mu, a_r) para corners de cada equipo (Binomial Negativa)."""
    h_mu, h_r = _compute_team_corners_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_corners_lambda(a, h, league, is_home=False, general=general, db=db)

    # Fallback si la suma total es demasiado baja
    if (h_mu + a_mu) < 2.0:
        avg = league.avg_corners_per_game / 2.0
        corners_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "corners", avg)
        fallback_r = get_dispersion_r(avg, max(corners_var, avg + 0.01))
        h_mu = avg
        h_r = fallback_r
        a_mu = avg
        a_r = fallback_r

    return h_mu, h_r, a_mu, a_r


def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    h_r = max(4.0, h_r)
    a_r = max(4.0, a_r)

    if (h_mu + a_mu) < 1.0:
        factor = league.avg_cards_per_game / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r


def _compute_shots_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_lambda(a, h, league, is_home=False, general=general, db=db)
    
    min_total = league.avg_shots_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r


def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general, db=db)
    
    min_total = league.avg_shots_target_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r



# ── Faltas y Offsides MEJORADOS ─────────────────────────────

def _compute_team_fouls_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
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

    # Dynamic prior_n from Negative Binomial dispersion: r = mu² / (var - mu)
    fouls_mean = avg_team_fouls
    fouls_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "fouls", fouls_mean, db=db)
    if fouls_var > fouls_mean:
        prior_n = max(1.0, min(8.0, fouls_mean ** 2 / (fouls_var - fouls_mean)))
    else:
        prior_n = 2.0

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_fouls * shrink_w
    return max(lam, 1.0)


def _compute_fouls_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> float:
    h_f_exp = _compute_team_fouls_lambda(h, a, league, is_home=True, general=general, db=db)
    a_f_exp = _compute_team_fouls_lambda(a, h, league, is_home=False, general=general, db=db)
    lam_fouls = h_f_exp + a_f_exp
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    return max(lam_fouls, avg_league_fouls * 0.5)


def _compute_team_offsides_lambda(
    team: FootballTeamStats,
    opponent: FootballTeamStats,
    league: LeagueStats,
    is_home: bool,
    general: bool = False,
    db: Any = None,
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

    # Dynamic prior_n from Negative Binomial dispersion: r = mu² / (var - mu)
    offsides_mean = avg_team_offsides
    offsides_var = _estimate_league_variance(getattr(league, "name", "Desconocida"), "offsides", offsides_mean, db=db)
    if offsides_var > offsides_mean:
        prior_n = max(1.0, min(8.0, offsides_mean ** 2 / (offsides_var - offsides_mean)))
    else:
        prior_n = 2.0

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_offsides * shrink_w
    return max(lam, 0.1)


def _compute_offsides_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> float:
    h_o_exp = _compute_team_offsides_lambda(h, a, league, is_home=True, general=general, db=db)
    a_o_exp = _compute_team_offsides_lambda(a, h, league, is_home=False, general=general, db=db)
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


def _neg_binomial_over_under(mu: float, line: float, r: float, max_k: int = 60) -> tuple[float, float, float]:
    def _get_single_line_probs(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        for k in range(max_k + 1):
            p = _neg_bin_pmf(mu, r, k)
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
    # shots_target DEBE ir antes que shots (tiro/shot es subconjunto)
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
        (r'\b(1x|home_draw)\b', "home_draw"),
        (r'\b(x2|draw_away)\b', "draw_away"),
        (r'\b(12|home_away)\b', "home_away"),
    ]
    
    for pattern, side in patterns:
        if re.search(pattern, s):
            return side
    
    return "none"


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
    max_picks_per_match: Optional[int] = None,
    max_total_stake: Optional[float] = None,
    correlation_rules: Optional[dict] = None
) -> list[ValueIndicator]:
    """
    Filtra picks correlacionados en un mismo evento garantizando
    la máxima expectativa matemática sin sobreexposición de varianza.
    Utiliza el motor de reglas centralizado pick_rules_engine.
    """
    if correlation_rules is None:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json")
        _, correlation_rules = load_pick_rules_data(rules_path)

    return engine_resolve_match_picks_correlation(
        candidates,
        correlation_rules=correlation_rules,
        max_picks_per_match=max_picks_per_match,
        max_total_stake=max_total_stake
    )

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
            content = f.read().strip()
            if not content:
                return False
            penalties = json.loads(content)

        if not isinstance(penalties, list):
            return False

        family = _market_family(selection)
        side = _market_side(selection)

        for rule in penalties:
            rule_league = (rule.get("league") or "").strip()
            # Coincidencia exacta de liga case-insensitive o coincidencia normalizada
            if rule_league and (rule_league.lower() == (league_name or "").strip().lower() or _normalize_text(rule_league) == _normalize_text(league_name)):
                rule_family = rule.get("market_family", "").strip().lower().replace(" ", "_")
                rule_side = rule.get("market_side", "").strip().lower().replace(" ", "_")

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
    """stat_support = 0.60 * P_modelo_Poisson(over line) + 0.40 * HitRate_empírico."""
    # Probabilidad del modelo (Poisson/DC) desde ProjectedLines
    pval, pprob, _ = _projected_value_by_keywords(proj, ["goles"])
    if pval is None:
        pval, pprob, _ = _projected_value_by_keywords(proj, ["goals"])

    # P_modelo desde la proyección o estimación por stats si no hay proyección
    if pprob is not None:
        model_prob = float(pprob)  # ya viene en 0-100
    elif pval is not None:
        model_prob = _clip_0_100(55.0 + (pval - line) * 20)
    else:
        # Fallback: estimación rápida desde stats del equipo
        h_exp = (_safe_num(h.goals_per_game) + _safe_num(h.xg_per_game)) / 2.0
        a_exp = (_safe_num(a.goals_per_game) + _safe_num(a.xg_per_game)) / 2.0
        total_exp = h_exp + a_exp
        model_over, _, _ = _poisson_over_under(total_exp, line)
        model_prob = model_over

    # Hit rate empírico del ValueIndicator
    empirical = None
    if vi is not None:
        empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)
        if empirical is None:
            h_hr = _safe_num(getattr(vi, "home_hit_rate", None), None)
            a_hr = _safe_num(getattr(vi, "away_hit_rate", None), None)
            if h_hr is not None and a_hr is not None:
                empirical = (h_hr + a_hr) / 2.0

    if empirical is not None:
        stat = _clip_0_100(0.60 * model_prob + 0.40 * empirical)
    else:
        stat = _clip_0_100(model_prob)

    proj_score = model_prob if pprob is not None else _clip_0_100(55.0 + (pval - line) * 20 if pval else model_prob)
    return stat, _clip_0_100(proj_score)


def _support_under_goals(line: float, h, a, proj: list, vi=None) -> tuple[float, float]:
    stat_over, proj_over = _support_over_goals(line, h, a, proj, vi)
    return _clip_0_100(100 - stat_over), _clip_0_100(100 - proj_over)




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
    return _clip_0_100(110 - stat_yes), _clip_0_100(110 - proj_yes)


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
    return _clip_0_100(110 - stat_u), _clip_0_100(110 - proj_u)


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

    if family == "double_chance":
        h_w, d_w, a_w = _dc_component_weights(h, a)
        stat_h, proj_h = _support_home_win(h, a, proj, vi)
        stat_d, proj_d = _support_draw(h, a, proj, vi)
        stat_a, proj_a = _support_away_win(h, a, proj, vi)

        base_stat = 55.0
        base_proj = 55.0

        if "1x" in s:
            norm = h_w + d_w
            w_h, w_d = h_w / norm, d_w / norm
            base_stat = _clip_0_100(w_h * stat_h + w_d * stat_d)
            base_proj = _clip_0_100(w_h * proj_h + w_d * proj_d)
        elif "x2" in s:
            norm = a_w + d_w
            w_a, w_d2 = a_w / norm, d_w / norm
            base_stat = _clip_0_100(w_a * stat_a + w_d2 * stat_d)
            base_proj = _clip_0_100(w_a * proj_a + w_d2 * proj_d)
        elif "12" in s:
            norm = h_w + a_w
            w_h2, w_a2 = h_w / norm, a_w / norm
            base_stat = _clip_0_100(w_h2 * stat_h + w_a2 * stat_a)
            base_proj = _clip_0_100(w_h2 * proj_h + w_a2 * proj_a)

        empirical = None
        if vi is not None:
            if "1x" in s:
                empirical = _safe_num(getattr(vi, "home_hit_rate", None), None) or _safe_num(getattr(vi, "empirical_hit_rate", None), None)
            elif "x2" in s:
                empirical = _safe_num(getattr(vi, "away_hit_rate", None), None) or _safe_num(getattr(vi, "empirical_hit_rate", None), None)
            else:
                empirical = _safe_num(getattr(vi, "empirical_hit_rate", None), None)

        if empirical is not None:
            base_stat = _clip_0_100(0.60 * base_stat + 0.40 * empirical)

        return base_stat, base_proj

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
        # Reducir el score proporcionalmente a la falta de confiabilidad
        if reliability < 0.5:
            score = int(score * (0.5 + reliability))  # máx penalización del 50%

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
async def compare_football(
    req: FootballCompareRequest,
    db: Any = None,
    exclude_match_id: Optional[Any] = None,
    current_match_date: Optional[Any] = None,
) -> CompareResponse:
    """
    NOTA DE FIX:
    Se agregaron los parámetros explícitos `exclude_match_id` y `current_match_date`.
    Tienen PRIORIDAD sobre cualquier valor que venga dentro de `req` (req.id,
    req.analysis_id, req.match_id, req.exclude_match_id, req.match_date, req.date).
    Esto es necesario porque en el flujo de RE-ANÁLISIS (main.py) el `req` se
    reconstruye desde el `payload` histórico guardado, el cual casi nunca trae
    poblado el `id` real de la fila en `analysis_history` ni una fecha confiable.
    Si el llamador pasa estos dos parámetros explícitamente (ej. exclude_match_id=history.id,
    current_match_date=history.match_date), se garantiza que el propio partido
    quede excluido del hit rate y del H2H, evitando el data leakage.
    """
    # Enriquecer league_stats con estadísticas históricas de la BD
    try:
        from src.core.database import SessionLocal
        from src.core.domain import AnalysisHistory
        from src.ui.api.main import _check_pick_success, _calculate_pick_profit, _is_pick_hit
        import json

        db_created = False
        if db is not None:
            db_session = db
        else:
            db_session = SessionLocal()
            db_created = True

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

    h_lam = _compute_team_goals_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_lam = _compute_team_goals_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)
    h_lam_corners, h_r_corners, a_lam_corners, a_r_corners = _compute_corners_lambda(h, a, req.league_stats, general=use_general, db=db)
    lam_corners = h_lam_corners + a_lam_corners
    h_lam_cards, h_r_cards, a_lam_cards, a_r_cards = _compute_cards_lambda(h, a, req.league_stats, general=use_general, db=db)
    lam_cards = h_lam_cards + a_lam_cards
    h_lam_shots, h_r_shots, a_lam_shots, a_r_shots = _compute_shots_lambda(h, a, req.league_stats, general=use_general, db=db)
    lam_shots = h_lam_shots + a_lam_shots
    h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)
    lam_shots_target = h_lam_shots_target + a_lam_shots_target

    h_goals_lam   = h_lam
    a_goals_lam   = a_lam
    h_corners_lam, _h_corners_r = _compute_team_corners_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_corners_lam, _a_corners_r = _compute_team_corners_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)
    h_cards_lam, _h_cards_r   = _compute_team_cards_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_cards_lam, _a_cards_r   = _compute_team_cards_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)
    h_shots_lam, _h_shots_r = _compute_team_shots_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_shots_lam, _a_shots_r = _compute_team_shots_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)
    h_shots_target_lam, _h_shots_target_r = _compute_team_shots_target_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_shots_target_lam, _a_shots_target_r = _compute_team_shots_target_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)

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
        return _value_indicator(sel, odds, modelp, h=h, a=a, overround=overround, push_p=push_p, league=req.league_stats, league_name=req.competition, odds_obj=req.odds)

    _or_1x2  = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    p_dc_1x = ((h_prob_raw + d_prob_raw) * _DC_BLEND_W + (_ph + _pd) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_x2 = ((d_prob_raw + a_prob_raw) * _DC_BLEND_W + (_pd + _pa) * (1.0 - _DC_BLEND_W)) * 100
    p_dc_12 = ((h_prob_raw + a_prob_raw) * _DC_BLEND_W + (_ph + _pa) * (1.0 - _DC_BLEND_W)) * 100

    _or_dc_raw = _overround(req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12)
    _or_dc = _or_dc_raw if _or_dc_raw > 100.5 else _or_1x2

    market_configs: list[tuple[str, float | None, float, float, float]] = [
        ("Local",     req.odds.home,     h_prob     * 100, _or_1x2, 0.0),
        ("Empate",    req.odds.draw,     d_prob     * 100, _or_1x2, 0.0),
        ("Visitante", req.odds.away,     a_prob     * 100, _or_1x2, 0.0),
        ("BTTS Sí",   req.odds.btts_yes, p_btts_yes * 100, _or_btts, 0.0),
        ("BTTS No",   req.odds.btts_no,  p_btts_no  * 100, _or_btts, 0.0),

        ("Doble Oportunidad 1X", req.odds.dc_1x, p_dc_1x, _or_dc, 0.0),
        ("Doble Oportunidad X2", req.odds.dc_x2, p_dc_x2, _or_dc, 0.0),
        ("Doble Oportunidad 12", req.odds.dc_12, p_dc_12, _or_dc, 0.0),
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

    # ── Over/Under CORNERS (Binomial Negativa con r combinado por equipo) ───────────────────
    projected_lines.append(ProjectedLine(
        label="Corners Totales (λ)", value=round(lam_corners, 1),
        type="corners", prob=None
    ))
    for line in req.odds.corners_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_corners, h_r_corners, a_lam_corners, a_r_corners)
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
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_cards, h_r_cards, a_lam_cards, a_r_cards)
        key        = str(line)
        over_odds  = req.odds.cards_over_odds.get(key)
        under_odds = req.odds.cards_under_odds.get(key)
        _or_cards  = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Tarjetas",  over_odds,  p_over,  _or_cards, p_push))
        market_configs.append((f"Under {line} Tarjetas", under_odds, p_under, _or_cards, p_push))

    # ── Over/Under TIROS TOTALES (Binomial Negativa con r combinado por equipo) ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros Totales (λ)", value=round(lam_shots, 1),
        type="shots", prob=None
    ))
    for line in req.odds.shots_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_shots, h_r_shots, a_lam_shots, a_r_shots)
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
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target)
        key        = str(line)
        over_odds  = req.odds.shots_target_over_odds.get(key)
        under_odds = req.odds.shots_target_under_odds.get(key)
        _or_shots_t  = _overround(over_odds, under_odds)

        market_configs.append((f"Over {line} Tiros a Pta",  over_odds,  p_over,  _or_shots_t, p_push))
        market_configs.append((f"Under {line} Tiros a Pta", under_odds, p_under, _or_shots_t, p_push))

    # ── Values: Cálculo masivo ─────────────
    values = [_vi(sel, odds, mp, ornd, pushp) for sel, odds, mp, ornd, pushp in market_configs]

    # ── Deduplicación de picks correlacionados ──────────────────
    # Se elimina redundancia dentro del mismo mercado (p.ej. Over 1.5 + Over 2.5 Goles)
    # conservando únicamente la línea con mejor EV por dirección (over/under) y familia.
    values = _deduplicate_correlated_picks(values)

    # ── Sincronización de Calidad, Hit Rate Empírico y Publicabilidad ─────────────
    # Obtener historial de partidos de la liga para calcular Hit Rates reales (Filtro temporal estricto sin data leakage)
    # ── 1. Extraer ID del partido actual ──
    # FIX: se prioriza el parámetro explícito exclude_match_id (pasado por el llamador,
    # ej. history.id en el batch de re-análisis) sobre lo que venga dentro de req,
    # porque req suele reconstruirse desde un payload histórico que NO trae el id real.
    exclude_analysis_id = None
    if exclude_match_id is not None:
        exclude_analysis_id = exclude_match_id
    elif hasattr(req, "id") and req.id:
        exclude_analysis_id = req.id
    elif hasattr(req, "analysis_id") and req.analysis_id:
        exclude_analysis_id = req.analysis_id
    elif hasattr(req, "match_id") and req.match_id:
        exclude_analysis_id = req.match_id
    elif hasattr(req, "exclude_match_id") and req.exclude_match_id:
        exclude_analysis_id = req.exclude_match_id
    elif isinstance(req, dict):
        exclude_analysis_id = req.get("id") or req.get("analysis_id") or req.get("match_id") or req.get("exclude_match_id")

    # ── 2. Extraer Fecha/Hora del partido actual ──
    # FIX: mismo criterio de prioridad que arriba para current_match_date.
    raw_date = None
    if current_match_date is not None:
        raw_date = current_match_date
    elif hasattr(req, "match_date") and req.match_date:
        raw_date = req.match_date
    elif hasattr(req, "date") and req.date:
        raw_date = req.date
    elif isinstance(req, dict):
        raw_date = req.get("match_date") or req.get("date")

    current_match_time = None
    if raw_date:
        try:
            if isinstance(raw_date, datetime):
                current_match_time = raw_date
            else:
                date_str = str(raw_date).strip().replace("Z", "+00:00")
                if "T" in date_str or " " in date_str:
                    current_match_time = datetime.fromisoformat(date_str)
                elif len(date_str) >= 10:
                    current_match_time = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception as e:
            print(f"[DEBUG COMPARE] Error parseando raw_date: {e}")

    curr_date_only = current_match_time.date() if current_match_time else None
    historical_records = []
    if db is not None:
        try:
            from sqlalchemy import text
            comp_name = req.competition or ""
            q_hist = text("""
                SELECT id, match_title, match_date, payload,
                       final_score_home, final_score_away,
                       final_corners_home, final_corners_away,
                       final_yellow_cards_home, final_yellow_cards_away,
                       final_shots_home, final_shots_away,
                       final_shots_on_target_home, final_shots_on_target_away,
                       final_fouls_home, final_fouls_away
                FROM analysis_history
                WHERE final_score_home IS NOT NULL AND final_score_away IS NOT NULL
                ORDER BY match_date DESC
            """)
            rows = db.execute(q_hist).mappings().all()
            target_l = comp_name.strip().lower()
            for r in rows:
                r_dict = dict(r)
                m_id = r_dict.get("id")

                # 1) Exclusión por ID (el propio partido que se está recalculando)
                if exclude_analysis_id and m_id and str(m_id).strip() == str(exclude_analysis_id).strip():
                    continue

                # 2) Parseo de la fecha de ESTA fila ANTES de usarla.
                # FIX: antes este cálculo ocurría después del chequeo "current_match_time and m_dt",
                # lo que hacía que m_dt fuera el de la fila ANTERIOR (o estuviera indefinido en la
                # primera iteración), permitiendo que el propio partido u otros posteriores se
                # filtraran incorrectamente. Ahora se calcula primero y se usa de inmediato.
                m_date = r_dict.get("match_date")
                m_dt = None
                if m_date:
                    try:
                        if isinstance(m_date, datetime):
                            m_dt = m_date
                        else:
                            m_s = str(m_date).replace("Z", "+00:00")
                            if "T" in m_s or " " in m_s:
                                m_dt = datetime.fromisoformat(m_s)
                            elif len(m_s) >= 10:
                                m_dt = datetime.strptime(m_s[:10], "%Y-%m-%d")
                    except Exception:
                        m_dt = None

                # 3) Exclusión por fecha/hora exacta (data leakage a nivel de instante)
                if current_match_time and m_dt and m_dt >= current_match_time:
                    continue

                # 4) Filtrado temporal estricto por día si se conoce la fecha del partido actual
                if curr_date_only and m_dt and m_dt.date() >= curr_date_only:
                    continue

                # Incluir registros de la base de datos histórica para evaluación de hit rates
                historical_records.append(r_dict)
        except Exception:
            pass

    from src.core.math_engine import LeagueMathEngine

    # ── Check 6 (planning.txt): Omitir partidos si un equipo solo tiene Rating y Posesión ──
    def _team_has_only_rating_and_possession(team: Any) -> bool:
        if team is None:
            return False
        goals = (getattr(team, "goals_per_game", 0.0) or getattr(team, "goals_scored", 0.0) or 0.0)
        xg = getattr(team, "xg_per_game", 0.0) or 0.0
        shots = (getattr(team, "shots_per_game", 0.0) or getattr(team, "shots", 0.0) or 0.0)
        corners = (getattr(team, "corners_per_game", 0.0) or getattr(team, "corners", 0.0) or 0.0)
        cards = (getattr(team, "yellow_cards_per_game", 0.0) or getattr(team, "yellow_cards", 0.0) or 0.0)
        possession = getattr(team, "possession_pct", 0.0) or 0.0
        rating = getattr(team, "team_rating", 0.0) or getattr(team, "rating", 0.0) or 0.0
        no_core_stats = (goals == 0.0 and xg == 0.0 and shots == 0.0 and corners == 0.0 and cards == 0.0)
        has_basic_info = (possession > 0.0 or rating > 0.0)
        return no_core_stats and has_basic_info

    match_incomplete_stats = _team_has_only_rating_and_possession(h) or _team_has_only_rating_and_possession(a)

    for v in values:
        if match_incomplete_stats:
            block_pick(
                v,
                BlockReason.RULE_BLOCKED,
                detail="Partido omitido por datos insuficientes: al menos un equipo solo tiene Rating de equipo y Posesión"
            )
            continue

        # ── Hit Rate empírico (% de acierto real en partidos históricos para TODOS los mercados) ──
        if historical_records:
            fam = _market_family(v.selection)
            side = _market_side(v.selection)
            line = _extract_line_number(v.selection)
            is_ov = (side == "over")

            # Mapeo según familia de mercado
            if fam in {"goals", "corners", "cards", "shots", "shots_target", "fouls"} and line is not None:
                hr_h = LeagueMathEngine.compute_pick_hit_rate(historical_records, h.name, fam, line=line, is_over=is_ov, role_filter="home", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_a = LeagueMathEngine.compute_pick_hit_rate(historical_records, a.name, fam, line=line, is_over=is_ov, role_filter="away", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(historical_records, h.name, a.name, fam, line=line, is_over=is_ov, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)

                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                # Ponderación de Hit Rate H2H por tamaño de muestra (planning.txt punto 3):
                # Si H2H tiene menos de 3 partidos se excluye (ruido), si tiene 3-4 se exige muestra mínima
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam in {"btts", "btts_yes", "btts_no"}:
                btts_fam = "btts_no" if "no" in side or "no" in v.selection.lower() else "btts_yes"
                hr_h = LeagueMathEngine.compute_pick_hit_rate(historical_records, h.name, btts_fam, role_filter="home", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_a = LeagueMathEngine.compute_pick_hit_rate(historical_records, a.name, btts_fam, role_filter="away", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(historical_records, h.name, a.name, btts_fam, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)

                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam in {"result", "moneyline", "1x2"}:
                t_side = "home" if side == "home" or "local" in v.selection.lower() else ("away" if side == "away" or "visitante" in v.selection.lower() else "draw")
                hr_h = LeagueMathEngine.compute_pick_hit_rate(historical_records, h.name, "1x2", role_filter="home", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_a = LeagueMathEngine.compute_pick_hit_rate(historical_records, a.name, "1x2", role_filter="away", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(historical_records, h.name, a.name, "1x2", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)

                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Si es gana local, el hit rate principal es el del local; si gana visitante, el del visitante
                if t_side == "home":
                    v.empirical_hit_rate = v.home_hit_rate
                    v.hit_rate_samples = hr_h.get("sample_size", 0)
                elif t_side == "away":
                    v.empirical_hit_rate = v.away_hit_rate
                    v.hit_rate_samples = hr_a.get("sample_size", 0)
                else:
                    tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                    v.hit_rate_samples = tot_samples
                    if tot_samples > 0:
                        tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                        v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam == "double_chance":
                t_side = "1x" if "1x" in v.selection.lower() or side == "home_draw" else ("x2" if "x2" in v.selection.lower() or side == "draw_away" else "12")
                hr_h = LeagueMathEngine.compute_pick_hit_rate(historical_records, h.name, "double_chance", role_filter="home", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_a = LeagueMathEngine.compute_pick_hit_rate(historical_records, a.name, "double_chance", role_filter="away", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(historical_records, h.name, a.name, "double_chance", target_side=t_side, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time)

                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Para 1X el porcentaje clave es el del local (ganó o empató)
                if t_side == "1x":
                    v.empirical_hit_rate = v.home_hit_rate
                    v.hit_rate_samples = hr_h.get("sample_size", 0)
                elif t_side == "x2":
                    v.empirical_hit_rate = v.away_hit_rate
                    v.hit_rate_samples = hr_a.get("sample_size", 0)
                else:
                    tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                    v.hit_rate_samples = tot_samples
                    if tot_samples > 0:
                        tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                        v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

        # Regla de veto post-calibración por brecha (planning.txt punto 1):
        # En mercados Over/Under de conteo (Tiros, Corners, Tiros a Puerta), si abs(model_prob - empirical_hit_rate) > 15%,
        # veto estructural del pick por brecha irreconciliable entre el modelo y la evidencia empírica.
        fam_v = _market_family(v.selection)
        if fam_v in {"shots", "corners", "shots_target"} and v.empirical_hit_rate is not None and v.model_prob is not None:
            if abs(v.model_prob - v.empirical_hit_rate) > 15.0:
                block_pick(
                    v,
                    BlockReason.RULE_BLOCKED,
                    detail=f"Veto por brecha Prob Modelo ({v.model_prob}%) vs Hit Rate Total ({v.empirical_hit_rate}%) > 15 pts"
                )

        q_score, s_support, p_support, strat_score = _rate_pick_quality(v, h, a, projected_lines)
        v.quality_score   = q_score
        v.strategic_score = strat_score
        v.stat_support    = round(s_support, 1)
        v.proj_support    = round(p_support, 1)
        evaluate_pick_eligibility(v)
        v.is_value        = is_value_pick(v) and v.is_publishable
        # Los underdogs tienen cuotas > 2.50 que superan el max_odds del sistema
        # de eligibilidad (pensado para value picks), por lo que is_publishable
        # siempre les devuelve False (ODDS_TOO_HIGH). Se verifica únicamente que
        # no haya bloqueos duros activos.
        _not_hard_blocked = (
            not v.is_blacklisted
            and not v.is_rule_blocked
            and not getattr(v, "correlation_blocked", False)
        )
        v.is_underdog     = is_underdog_pick(v) and _not_hard_blocked

    # ── Descorrelación de picks del mismo partido (reglas estructurales) ──
    values = resolve_match_picks_correlation(values)

    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp    = [v for v in values if v.is_value and v.is_publishable]

    # ── Faltas y Offsides Lambdas ─────────────────────────────
    lam_fouls = _compute_fouls_lambda(h, a, req.league_stats, general=use_general, db=db)
    h_fouls_lam = _compute_team_fouls_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_fouls_lam = _compute_team_fouls_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)

    lam_offsides = _compute_offsides_lambda(h, a, req.league_stats, general=use_general, db=db)
    h_offsides_lam = _compute_team_offsides_lambda(h, a, req.league_stats, is_home=True,  general=use_general, db=db)
    a_offsides_lam = _compute_team_offsides_lambda(a, h, req.league_stats, is_home=False, general=use_general, db=db)

    # ── Most Probable Score (mejorado) ──
    # Se elige el marcador con mayor probabilidad puntual de la distribución Dixon-Coles.
    # Adicionalmente se calcula un "score de confianza" ponderando el entorno de la moda.
    max_p = -1.0
    best_h, best_a = 0, 0
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            if matrix[i][j] > max_p:
                max_p = matrix[i][j]
                best_h, best_a = i, j

    # Probabilidad acumulada del marcador y sus vecinos directos (±1 gol) como medida de estabilidad
    _mps_neighborhood = 0.0
    for di in range(-1, 2):
        for dj in range(-1, 2):
            _ni, _nj = best_h + di, best_a + dj
            if 0 <= _ni < len(matrix) and 0 <= _nj < len(matrix[_ni]):
                _mps_neighborhood += matrix[_ni][_nj]
    _mps_confidence = round(_mps_neighborhood * 100.0, 1)

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
        mps_confidence=_mps_confidence,
        comparisons=comparisons,
        values=values,
        projected_lines=projected_lines,
        summary=summary,
        llm_analysis=llm,
    )

if __name__ == "__main__":
    casos = [
        ("Cuota baja, prob alta",  82.1, 1.55),
        ("Cuota media",            50.0, 2.46),
        ("Cuota alta, prob baja",  28.7, 5.40),
        ("Sin valor (prob = implícita)", 40.7, 2.46),
    ]
    for nombre, prob, odds in casos:
        kf = _calculate_kelly_fraction(prob, odds)
        implied = 1 / odds * 100
        ev = (prob / 100 * odds) - 1
        print(f"{nombre:35s} | prob={prob:5.1f}% odds={odds:4.2f} "
              f"implied={implied:5.1f}% EV={ev:+.3f} -> Kelly 1/4={kf*100:5.2f}%")