from __future__ import annotations

from enum import Enum
from typing import Optional
import json
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
from datetime import datetime, timezone
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
# ── Nueva Arquitectura: Stake Engine, Trazabilidad, Taxonomía de Mercado ──
from src.domain.stake_engine import (
    RiskPolicy,
    StakeFactors,
    EdgeResult,
    compute_edge,
    compute_stake_final,
    compute_risk_decision,
)
from src.domain.traceability import PickTrace
from src.domain.market_taxonomy import (
    parse_market,
    market_group_key,
    line_bucket_for,
    normalize_market_side,
    normalize_market_family,
)
# ── Portfolio: control de sobreexposición simultánea por jornada ──
from src.domain.portfolio import apply_portfolio_exposure_cap
from src.core.math.dixon_coles import (
    tau as dc_tau,
    build_dixon_coles_matrix,
    solve_dixon_coles_mle,
)
from src.core.math.bayesian import (
    fit_gamma_prior_from_league,
    update_gamma_poisson,
)
from src.core.math.calibration import (
    normalize_categorical_market,
    PlattCalibrator,
    IsotonicCalibrator,
)
from src.core.math.kelly import (
    calculate_fractional_kelly,
)

load_dotenv()

logger = logging.getLogger("sherlock.compare")

MIN_STAKE = 1
MAX_STAKE = 3

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
    matches_home:   int = Field(0,  description="Partidos jugados como local")
    matches_away:   int = Field(0,  description="Partidos jugados como visitante")
    matches_played: int = Field(0,  description="Partidos totales")
    wins:           int = Field(0,  description="Ganados")
    draws:          int = Field(0,  description="Empates")
    losses:         int = Field(0,  description="Perdidos")
    has_stats:      bool = Field(True, description="Indica si el equipo tiene datos reales cargados")

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
    possession_pct:         Optional[float] = Field(None, description="Posesión % (None si ausente)")
    passes_completed:       float = Field(0,   description="Pases acertados")
    pass_accuracy:          float = Field(0,   description="Precisión pases %")
    passes_opp_half:        float = Field(0,   description="Pases acertados campo rival")
    pass_accuracy_opp_half: float = Field(0,   description="Precisión pases campo rival %")
    crosses_per_game:       float = Field(0,   description="Centros completos por juego")
    cross_accuracy:         float = Field(0,   description="Precisión de centros %")
    corners_per_game:       float = Field(0.0, description="Corners por juego")

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
    corners_conceded_per_game:    float = Field(0.0, description="Corners concedidos por juego")
    xg_per_game:                  Optional[float] = Field(None, description="Expected Goals por juego")
    xga_per_game:                 Optional[float] = Field(None, description="Expected Goals Against por juego")
    xg_is_imputed:                bool = Field(False, description="True si xG no es oficial y fue estimado o imputado")
    # Pases / Centros (Totales vs Acertados)
    passes_total_per_game:          float = Field(0.0, description="Pases totales intentados por juego")
    passes_opp_half_total_per_game: float = Field(0.0, description="Pases totales intentados en campo rival")
    crosses_total_per_game:         float = Field(0.0,  description="Centros totales intentados por juego")

    # Portero Avanzado (NUEVO)
    save_pct:                       float = Field(0.0, description="Paradas %")
    goal_kicks:                     float = Field(0.0, description="Saque de meta por juego")

    # Físicas (NUEVO)
    kilometers_covered:             float = Field(0.0, description="Kilómetros recorridos por juego")
    number_of_sprints:              float = Field(0.0, description="Sprints por juego")

    # Rating (NUEVO)
    avg_rating:                     Optional[float] = Field(None, description="Rating promedio del equipo")

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
    match_date: Optional[str] = Field(default=None, description="Fecha del partido (YYYY-MM-DD). A partir del 2026-01-01 las stats son generales (sin segmentación por localía).")
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

    # 10. Correcciones menores de xg / xga si están ausentes (Issue #4)
    if t.xg_per_game is None or t.xg_per_game <= 0.0:
        t.xg_per_game = max(t.goals_per_game, 0.1)
        t.xg_is_imputed = True
    if t.xga_per_game is None or t.xga_per_game <= 0.0:
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

    # ── Snapshot e inmutabilidad temporal ──
    pick_id:               Optional[str] = None
    predicted_at_utc:      Optional[str] = None
    model_prob_raw:        Optional[float] = None
    calibration_version:   Optional[str] = None

    # ── NUEVO: line shopping — casa que ofrece la mejor cuotas para este pick ──
    bookmaker: Optional[str] = None

    # ── Frecuencia real / Hit Rate empírico (% de partidos donde se dio el pick) ──
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    home_hit_rate: Optional[float] = None
    away_hit_rate: Optional[float] = None
    home_bayesian_ewma_hit_rate: Optional[float] = None
    away_bayesian_ewma_hit_rate: Optional[float] = None
    home_trend_label: Optional[str] = None
    away_trend_label: Optional[str] = None
    home_trend_delta_pp: Optional[float] = None
    away_trend_delta_pp: Optional[float] = None
    home_hits: Optional[int] = None
    home_matches_count: Optional[int] = None
    away_hits: Optional[int] = None
    away_matches_count: Optional[int] = None
    empirical_hit_rate: Optional[float] = None
    h2h_hit_rate: Optional[float] = None
    h2h_raw_hit_rate: Optional[float] = None
    hit_rate_samples: Optional[int] = None
    h2h_samples: Optional[int] = None
    h2h_hits: Optional[int] = None
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

    # ── Nueva Arquitectura: Trazabilidad Completa (Fase 13) ───────────────
    # Taxonomía canónica de mercado
    market_family:  Optional[str]  = None  # goals | btts | result | corners | cards | shots | ...
    market_side:    Optional[str]  = None  # over | under | yes | no | home | away | draw | ...
    line_bucket:    Optional[str]  = None  # low_0_5_1_5 | core_2_5 | high_3_5 | no_line | ...
    segment_key:    Optional[str]  = None  # league:X|family:Y|side:Z|bucket:W

    # Probabilidades desglosadas por etapa del pipeline
    final_prob:              Optional[float] = None  # blend calibrado + mercado (la más informada)
    p_market_no_vig:         Optional[float] = None  # prob implícita de mercado sin vig (0-100)

    # Edge desglosado (raw → calibrado → final)
    edge_raw:        Optional[float] = None   # edge con prob. Poisson cruda
    edge_calibrated: Optional[float] = None   # edge con prob. calibrada (curva jerárquica)
    edge_final:      Optional[float] = None   # edge con prob. final (blend mercado)

    # Gobernanza de segmento
    segment_status:       Optional[str]   = None   # active | watch | reduced | blocked | experimental
    drift_score:          Optional[float] = None   # score de drift del segmento (0-1)
    governance_multiplier: Optional[float] = None  # factor aplicado al stake por gobernanza [0-1]
    min_edge_add:         Optional[float] = None   # incremento mínimo de edge requerido por gobernanza (en pp)

    # Componentes de fiabilidad
    reliability_components: Dict[str, float] = Field(default_factory=dict)


class StatComparison(BaseModel):
    label:      str
    key:        str
    home_value: Optional[float] = None
    away_value: Optional[float] = None
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

from datetime import timezone

def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza un datetime a naive-UTC para permitir comparaciones seguras
    entre fechas que pueden venir con o sin zona horaria."""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


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

    # ── Issue #25: Estimar varianza real desde AnalysisHistory en lugar de tablas legacy ──
    if db is not None and competition_name and competition_name not in ("Desconocida", "General", ""):
        try:
            from src.core.domain import AnalysisHistory
            rows = (
                db.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.competition == competition_name,
                    AnalysisHistory.final_score_home.isnot(None),
                    AnalysisHistory.final_score_away.isnot(None),
                )
                .order_by(AnalysisHistory.date.desc())
                .limit(100)
                .all()
            )

            if len(rows) >= 8:
                vals: list[float] = []
                for r in rows:
                    if metric == "goals":
                        if r.final_score_home is not None: vals.append(float(r.final_score_home))
                        if r.final_score_away is not None: vals.append(float(r.final_score_away))
                    elif metric == "corners":
                        if r.final_corners_home is not None: vals.append(float(r.final_corners_home))
                        if r.final_corners_away is not None: vals.append(float(r.final_corners_away))
                    elif metric == "cards":
                        if r.final_yellow_cards_home is not None or r.final_red_cards_home is not None:
                            vals.append(float((r.final_yellow_cards_home or 0) + (r.final_red_cards_home or 0) * 2.0))
                        if r.final_yellow_cards_away is not None or r.final_red_cards_away is not None:
                            vals.append(float((r.final_yellow_cards_away or 0) + (r.final_red_cards_away or 0) * 2.0))
                    elif metric == "shots":
                        if r.final_shots_home is not None: vals.append(float(r.final_shots_home))
                        if r.final_shots_away is not None: vals.append(float(r.final_shots_away))
                    elif metric == "shots_target":
                        if r.final_shots_on_target_home is not None: vals.append(float(r.final_shots_on_target_home))
                        if r.final_shots_on_target_away is not None: vals.append(float(r.final_shots_on_target_away))
                    elif metric == "fouls":
                        if r.final_fouls_home is not None: vals.append(float(r.final_fouls_home))
                        if r.final_fouls_away is not None: vals.append(float(r.final_fouls_away))
                    elif metric == "offsides":
                        if r.final_offsides_home is not None: vals.append(float(r.final_offsides_home))
                        if r.final_offsides_away is not None: vals.append(float(r.final_offsides_away))

                if len(vals) >= 8:
                    avg = sum(vals) / len(vals)
                    var = sum((x - avg) ** 2 for x in vals) / (len(vals) - 1)
                    if var > 0.05:
                        return var
        except Exception:
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
    Calcula un score de confiabilidad de la liga en rango [0.15, 1.0].

    Combina dos fuentes ponderadas por el tamaño de muestra de partidos:
    A) Coherencia estadística interna (rangos razonables de goles, corners, tarjetas)
    B) Rendimiento histórico real (acierto + beneficio)

    IMPORTANTE: Si la liga no tiene partidos registrados (historical_matches <= 0)
    o tiene una muestra ínfima, NO puede obtener un score alto únicamente por
    tener valores por defecto "coherentes". Se aplica un shrinkage estricto por muestra.
    """
    # ── Muestra de partidos y penalización por falta de datos ──
    matches = int(getattr(league, "historical_matches", 0) or 0)
    picks = int(getattr(league, "historical_picks", 0) or 0)

    # Factor de confianza por muestra de partidos [0.20, 1.0]
    # Una liga es "buena" si tiene 600+ partidos y 60+ picks.
    # Con 0 partidos:   0.20 (penalización máxima, liga no probada)
    # Con 150 partidos: ~0.40
    # Con 300 partidos: ~0.60
    # Con 600+ partidos: 1.0 (muestra suficiente para plena confianza)
    _MATCH_REF = 600.0  # partidos necesarios para saturar a 1.0
    if matches <= 0 and picks <= 0:
        match_confidence = 0.20
    else:
        effective_n = max(matches, int(picks * 10.0))  # picks × 10 ≈ partidos equivalentes
        match_confidence = min(1.0, 0.20 + (effective_n / _MATCH_REF) * 0.80)

    # ── A. Coherencia estadística ─────────────────────────────────
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

    stat_score = max(0.20, min(1.0, stat_score))

    # ── B. Rendimiento histórico real ────────────────────────────
    if picks <= 0:
        # Sin historial de picks: el score depende de la coherencia estadística
        # escalada estrictamente por la muestra de partidos evaluados.
        final_score = stat_score * match_confidence
        # Si tiene gran muestra de partidos (ej. 600+ o 1000+), asegura confianza de liga establecida
        if matches >= 1000:
            final_score = max(final_score, 0.70)
        elif matches >= 600:
            final_score = max(final_score, 0.60)
        return round(max(0.15, min(1.0, final_score)), 3)

    N_MIN = 60.0  # número de picks para 50% de peso histórico (liga "buena" = 60+ picks)
    hist_weight = picks / (picks + N_MIN)   # ∈ [0, 1)
    stat_weight = 1.0 - hist_weight

    # Componente de acierto:
    # ACC_REF = 0.42 (realista: la mayoría de picks de valor ronda el 42-55%)
    accuracy_rate = league.historical_hits / picks
    ACC_REF  = 0.42          # mínimo aceptable
    ACC_IDEAL = 0.58         # nivel sobresaliente para value betting
    acc_score = (accuracy_rate - ACC_REF) / max(ACC_IDEAL - ACC_REF, 0.01)
    acc_score = max(0.0, min(1.0, acc_score))  # [0, 1]

    # Componente de beneficio: normalizado a picks (ROI por pick).
    roi_per_pick = league.historical_profit / picks
    PROFIT_LOW  = -0.20
    PROFIT_HIGH =  0.25
    profit_score = (roi_per_pick - PROFIT_LOW) / max(PROFIT_HIGH - PROFIT_LOW, 0.01)
    profit_score = max(0.0, min(1.0, profit_score))

    # Score histórico combinado (50% acierto, 50% beneficio)
    hist_score = acc_score * 0.50 + profit_score * 0.50
    hist_score = max(0.0, min(1.0, hist_score))

    # ── Combinar A + B con shrinkage hacia prior estadístico ──────────────
    # match_confidence actúa como peso del historial vs el prior estadístico.
    # Con muestra baja → más peso al stat_score; con muestra alta → más peso al hist.
    # Fórmula: blended = stat * (1 - conf_hist) + hist * conf_hist
    #   donde conf_hist satura a 1.0 con 600+ partidos.
    conf_hist = match_confidence  # ya es [0.20, 1.0]
    blended = stat_score * (1.0 - conf_hist * hist_weight) + hist_score * (conf_hist * hist_weight)
    # Piso mínimo: la coherencia estadística siempre aporta algo
    blended = max(stat_score * 0.30, blended)
    final_score = min(1.0, max(0.15, blended))

    # ── Respaldo de muestra alta (evitar LRS injustamente bajo con 1000+ partidos y 60+ picks) ──
    if matches >= 1000 and picks >= 60:
        if accuracy_rate >= 0.42:
            final_score = max(final_score, 0.75 + min(0.25, (accuracy_rate - 0.42) * 1.5))
        else:
            final_score = max(final_score, 0.55)
    elif matches >= 600 and accuracy_rate >= 0.42:
        if picks >= 60:
            final_score = max(final_score, 0.68 + min(0.30, (accuracy_rate - 0.42) * 1.5))
        else:
            final_score = max(final_score, 0.58)
    elif matches >= 200 and accuracy_rate >= 0.42:
        # Liga con muestra media y acierto decente: piso razonable
        final_score = max(final_score, 0.45)
    elif matches >= 100 and picks >= 20 and accuracy_rate >= 0.40:
        # Liga emergente con algo de historial positivo
        final_score = max(final_score, 0.38)

    return round(max(0.15, min(1.0, final_score)), 3)


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
    Calcula el score de Confianza de Datos (0 a 100).

    Evalúa 3 pilares indispensables:
    1. Cobertura de Muestra (40 pts): Partidos jugados por ambos equipos.
       - Muestra n < 3: castigo severo (no hay significancia).
       - Muestra n >= 15: máxima puntuación.
    2. Integridad de Métricas Clave y Avanzadas (35 pts):
       - Presencia de xG/xGA real (no valores dummy).
       - Tiros a puerta, faltas, córners y posesión reales.
       - Ratings de rendimiento de jugadores/equipos.
    3. Estabilidad del Tipo de Mercado (25 pts):
       - Mercados de baja varianza (1X2, goles, btts): base 25 pts.
       - Córners (varianza media): base 18 pts.
       - Mercados volátiles (tarjetas, tiros, faltas): base 12 pts.
    """
    if not h or not a:
        return 0.0

    min_m = min(h.matches_played, a.matches_played)
    if min_m <= 0:
        return 0.0

    # ── 1. Cobertura de Muestra (hasta 40 puntos) ─────────────────
    if min_m >= 15:
        sample_pts = 40.0
    elif min_m >= 10:
        sample_pts = 30.0 + (min_m - 10) * 2.0  # 30 a 40
    elif min_m >= 5:
        sample_pts = 18.0 + (min_m - 5) * 2.4   # 18 a 30
    elif min_m >= 3:
        sample_pts = 10.0 + (min_m - 3) * 4.0   # 10 a 18
    else:
        sample_pts = min_m * 3.0                 # 0 a 9 (muestra crítica)

    # ── 2. Integridad y Riqueza de Métricas (hasta 35 puntos) ──────
    # Chequear disponibilidad de métricas estadísticas fundamentales
    metrics_pts = 0.0

    # Presencia de xG/xGA diferenciado y real (Issue #4: xg imputado no puntúa como real)
    has_xg_h = not getattr(h, "xg_is_imputed", False) and h.xg_per_game is not None and h.xg_per_game > 0.1
    has_xg_a = not getattr(a, "xg_is_imputed", False) and a.xg_per_game is not None and a.xg_per_game > 0.1
    if has_xg_h and has_xg_a:
        metrics_pts += 12.0
    elif has_xg_h or has_xg_a:
        metrics_pts += 6.0

    # Tiros y tiros a puerta registrados
    has_shots = (h.shots_per_game > 0 and a.shots_per_game > 0)
    has_sot = (h.shots_on_target_per_game > 0 and a.shots_on_target_per_game > 0)
    if has_shots and has_sot:
        metrics_pts += 8.0
    elif has_shots:
        metrics_pts += 4.0

    # Córners y faltas registradas
    if h.corners_per_game > 0 and a.corners_per_game > 0:
        metrics_pts += 5.0
    if h.fouls_per_game > 0 and a.fouls_per_game > 0:
        metrics_pts += 5.0

    # Presencia de rating o métricas avanzadas de pase
    if (h.avg_rating or 0.0) > 0.1 and (a.avg_rating or 0.0) > 0.1:
        metrics_pts += 5.0
    elif h.pass_accuracy > 10.0 and a.pass_accuracy > 10.0:
        metrics_pts += 3.0

    # ── 3. Estabilidad del Tipo de Mercado (hasta 25 puntos) ───────
    tier = get_market_confidence_tier(selection)
    if tier == "segmented":
        market_tier_pts = 25.0
    elif tier == "hybrid":
        market_tier_pts = 18.0
    else:
        market_tier_pts = 12.0

    family = _market_family(selection)
    # Si el mercado depende de métricas de conteo (tiros, tarjetas) y faltan esas métricas, penalizar
    if family in {"shots", "shots_target"} and not (has_shots and has_sot):
        metrics_pts = max(0.0, metrics_pts - 10.0)
    if family == "cards" and (h.yellow_cards_per_game <= 0 or a.yellow_cards_per_game <= 0):
        metrics_pts = max(0.0, metrics_pts - 8.0)

    total_dq = sample_pts + metrics_pts + market_tier_pts
    return round(max(5.0, min(100.0, total_dq)), 1)

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
    Stake cuantitativo basado en Fractional Kelly (1/8 Kelly con cap del 3% del bankroll).
    Retorna unidades escaladas (0.0 = no jugable, hasta 3.0u).
    """
    if edge_ev < 0.025 or kelly_fraction <= 0 or odds <= 1.0:
        return 0.0

    prob_est = (edge_ev + 1.0) / odds
    stake_frac, edge_pct = calculate_fractional_kelly(
        calibrated_prob=prob_est,
        odds=odds,
        fraction_divisor=8.0,
        max_stake_cap=0.03,
    )

    if stake_frac <= 0.0:
        return 0.0

    raw_units = stake_frac * 100.0

    _lrs = lrs or 0.50
    if _lrs >= 0.65:
        hard_max = 3.0
    elif _lrs >= 0.50:
        hard_max = 2.5
    elif _lrs >= 0.35:
        hard_max = 2.0
    else:
        hard_max = 1.5

    if market_family in {"corners", "cards", "shots", "shots_target", "fouls"}:
        hard_max = min(hard_max, 2.5)

    clamped = max(0.0, min(hard_max, raw_units))
    if clamped <= 0:
        return 0.0
    stake = round(clamped * 4) / 4
    return max(0.25, stake)

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

    # Recorte heurístico de respaldo: SOLO cuando no hay curva entrenada.
    if not calibration_is_active():
        raw_implied_pre = (1.0 / odds) * 100.0
        if calibrated_p - raw_implied_pre >= 20.0:
            calibrated_p *= 0.82

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

    # Blend con probabilidad de mercado (no-vig): 80% calibrado + 20% mercado
    _p_market_01 = (implied_no_vig / 100.0) if implied_no_vig > 0.0 else _p_calibrated_01
    _p_final_01 = 0.80 * _p_calibrated_01 + 0.20 * _p_market_01

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

    # ── 5. League Reliability Score ──────────────────────────────────────
    if league is not None:
        # Siempre recalcular con la fórmula actualizada; el valor de BD puede estar obsoleto
        lrs = _compute_league_reliability_score(league)
    else:
        lrs = 0.7
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
    fano = goals_var / max(goals_mean, 0.1)

    # ── Issue #20: Ponderación de goles y xG por varianza observada ──
    # En muestras pequeñas el xG predice mejor que los goles reales (menor varianza);
    # conforme aumentan los partidos, los goles reales ganan peso según la varianza.
    w_xg = 1.0 / (1.0 + (att_n / max(5.0 * fano, 1.0)))
    if prior_att_xg is not None and prior_att_xg > 0:
        att_rate = (1.0 - w_xg) * actual_att_g + w_xg * prior_att_xg
    else:
        att_rate = actual_att_g

    w_xga = 1.0 / (1.0 + (def_n / max(5.0 * fano, 1.0)))
    if prior_def_xga is not None and prior_def_xga > 0:
        def_rate = (1.0 - w_xga) * actual_def_g + w_xga * prior_def_xga
    else:
        def_rate = actual_def_g

    # ── Issue #20: Un solo shrinkage Bayesiano hacia la media de liga ──
    # Empirical Bayes Gamma-Poisson shrinkage for attack and defense rates
    alpha_prior, beta_prior = fit_gamma_prior_from_league([avg_team_goals, goals_mean, max(goals_var, 0.1)])
    post_att_rate = update_gamma_poisson(alpha_prior, beta_prior, att_rate * att_n, att_n)
    post_def_rate = update_gamma_poisson(alpha_prior, beta_prior, def_rate * def_n, def_n)

    att_str = post_att_rate / max(avg_team_goals, 0.1)
    def_weakness = post_def_rate / max(avg_team_goals, 0.1)

    # ── Issue #18: Factor de localía derivado de la liga incorporado directamente al lambda ──
    home_factor = league.home_advantage_factor if is_home else league.away_disadvantage_factor

    # ── Lambda Base ──
    lam_base = att_str * def_weakness * avg_team_goals * home_factor

    # ── 5. Ajuste por forma reciente (ventanas 5 / 10 / 15) — Issue #21 ──
    form_factor_att = 1.0
    form_factor_def = 1.0

    att_recent = getattr(attacker, "recent_form", None) or getattr(attacker, "recent_form_stats", None)
    if att_recent and isinstance(att_recent, dict):
        w5  = att_recent.get("last_5",  {}).get("goals_scored", avg_team_goals)
        w10 = att_recent.get("last_10", {}).get("goals_scored", avg_team_goals)
        w15 = att_recent.get("last_15", {}).get("goals_scored", avg_team_goals)
        form_avg_att = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor_att = form_avg_att / max(avg_team_goals, 0.10)
        form_factor_att = max(0.70, min(1.30, form_factor_att))

    def_recent = getattr(defender, "recent_form", None) or getattr(defender, "recent_form_stats", None)
    if def_recent and isinstance(def_recent, dict):
        w5  = def_recent.get("last_5",  {}).get("goals_conceded", avg_team_goals)
        w10 = def_recent.get("last_10", {}).get("goals_conceded", avg_team_goals)
        w15 = def_recent.get("last_15", {}).get("goals_conceded", avg_team_goals)
        form_avg_def = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor_def = form_avg_def / max(avg_team_goals, 0.10)
        form_factor_def = max(0.70, min(1.30, form_factor_def))

    lam_final = lam_base * form_factor_att * form_factor_def
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
    n = max(m_count, 1)
    alpha_prior_c, beta_prior_c = fit_gamma_prior_from_league([avg_team_corners, corners_mean, max(corners_var, 0.1)])
    lam = update_gamma_poisson(alpha_prior_c, beta_prior_c, lam * n, n)

    # ── Issue #28: Factor de localía por métrica de corners ──
    # local genera más corners que visitante (~+10-15% de promedio de liga)
    home_corner_factor = league.home_advantage_factor if is_home else league.away_disadvantage_factor
    lam = lam * home_corner_factor
    mu = max(lam, 0.5)

    # ── Issue #23: Varianza por equipo = Fano × mu (no var/4) ──
    fano_corners = corners_var / max(corners_mean, 0.1)
    team_var = fano_corners * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))

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
    alpha_prior_cd, beta_prior_cd = fit_gamma_prior_from_league([avg_team_cards, cards_mean, max(cards_var, 0.1)])
    lam = update_gamma_poisson(alpha_prior_cd, beta_prior_cd, lam * actual_matches, actual_matches)

    # ── Issue #28: Factor de localía para tarjetas (visitante recibe más amarillas) ──
    # El equipo visitante suele cometer más faltas y recibir más tarjetas (~+8%)
    card_home_factor = 0.95 if is_home else 1.05
    lam = lam * card_home_factor

    mu = max(lam, 0.4)
    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_cards = cards_var / max(cards_mean, 0.1)
    team_var = fano_cards * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))
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

    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_shots = shots_var / max(shots_mean, 0.1)
    team_var = fano_shots * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))

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
    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_sot = sot_var / max(sot_mean, 0.1)
    team_var = fano_sot * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))
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

    mat_np = build_dixon_coles_matrix(h_lam, a_lam, rho_used, max_goals=max_goals)
    matrix = mat_np.tolist()
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
    opp_possession = opponent.possession_pct if (opponent.possession_pct is not None and opponent.possession_pct > 0) else 50.0
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

    team_possession = team.possession_pct if (team.possession_pct is not None and team.possession_pct > 0) else 50.0
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



def _matrix_over_under(matrix: list[list[float]], line: float) -> tuple[float, float, float]:
    """
    Issue #19: Deriva Over, Push y Under de goles directamente de la matriz Dixon-Coles
    en lugar de un Poisson independiente no correlacionado.
    Soporta líneas estándar y líneas asiáticas divididas (ej. 2.25 -> 2.0 y 2.5).
    """
    def _single_line(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        max_i = len(matrix)
        for i in range(max_i):
            max_j = len(matrix[i])
            for j in range(max_j):
                tot = i + j
                p = matrix[i][j]
                if tot < l:
                    p_u += p
                elif tot > l:
                    p_o += p
                else:
                    p_p += p
        return p_o, p_p, p_u

    lines = split_asian_line(line)
    results = [_single_line(l) for l in lines]
    avg_over = sum(r[0] for r in results) / len(results)
    avg_push = sum(r[1] for r in results) / len(results)
    avg_under = sum(r[2] for r in results) / len(results)

    return avg_over * 100.0, avg_push * 100.0, avg_under * 100.0


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
    precomputed_historical_records: Optional[list] = None,
    precomputed_team_index: Optional[dict] = None,
    precomputed_league_stats: Optional[dict] = None,
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
    # Enriquecer league_stats con estadísticas históricas de la BD o precomputadas
    db_created = False
    db_session = None
    try:
        from src.core.database import SessionLocal
        from src.core.domain import AnalysisHistory, Sport
        from src.ui.api.main import _check_pick_success, _calculate_pick_profit, _is_pick_hit
        import json as _json

        comp_key = (req.competition or "").strip().lower()
        if precomputed_league_stats and comp_key in precomputed_league_stats and req.league_stats.historical_picks <= 0:
            ls_data = precomputed_league_stats[comp_key]
            req = req.model_copy(update={
                "league_stats": req.league_stats.model_copy(update={
                    "historical_matches": ls_data.get("historical_matches", 0),
                    "historical_picks":   ls_data.get("historical_picks", 0),
                    "historical_hits":    ls_data.get("historical_hits", 0),
                    "historical_profit":  round(ls_data.get("historical_profit", 0.0), 4),
                })
            })
        elif req.league_stats.historical_picks <= 0 and req.competition and req.competition not in ("", "Desconocida", "General"):
            db_session = db if db is not None else SessionLocal()
            db_created = (db is None)
            league_rows = (
                db_session.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.competition == req.competition,
                    AnalysisHistory.sport == Sport.FOOTBALL,
                    AnalysisHistory.picks_calculados.isnot(None),
                )
                .all()
            )

            total_matches  = len(league_rows)
            total_picks    = 0
            total_hits     = 0
            total_profit   = 0.0

            for row in league_rows:
                # Resultado del partido (necesario para calcular hits)
                res_dict = {
                    "final_score_home":  row.final_score_home,
                    "final_score_away":  row.final_score_away,
                    "final_corners_home": row.final_corners_home,
                    "final_corners_away": row.final_corners_away,
                    "final_yellow_cards_home": row.final_yellow_cards_home,
                    "final_yellow_cards_away": row.final_yellow_cards_away,
                    "final_red_cards_home": row.final_red_cards_home,
                    "final_red_cards_away": row.final_red_cards_away,
                    "final_shots_home": row.final_shots_home,
                    "final_shots_away": row.final_shots_away,
                    "final_shots_on_target_home": row.final_shots_on_target_home,
                    "final_shots_on_target_away": row.final_shots_on_target_away,
                }
                # Solo contar picks si el partido tiene resultado real
                has_result = (
                    res_dict["final_score_home"] is not None
                    and res_dict["final_score_away"] is not None
                )

                try:
                    picks_raw = _json.loads(row.picks_calculados) if row.picks_calculados else []
                except Exception:
                    picks_raw = []

                for pick in picks_raw:
                    if not isinstance(pick, dict):
                        continue
                    stake = float(pick.get("stake", pick.get("stake_units", 0)) or 0)
                    if stake <= 0:
                        continue  # solo contar picks publicados
                    total_picks += 1
                    if has_result:
                        outcome = _check_pick_success(pick, res_dict)
                        if _is_pick_hit(outcome):
                            total_hits += 1
                        odds_val = float(pick.get("odds", 1.0) or 1.0)
                        total_profit += _calculate_pick_profit(outcome, odds_val)

            if total_matches > 0 or total_picks > 0:
                req = req.model_copy(update={
                    "league_stats": req.league_stats.model_copy(update={
                        "historical_matches": total_matches,
                        "historical_picks":   total_picks,
                        "historical_hits":    total_hits,
                        "historical_profit":  round(total_profit, 4),
                    })
                })
                logger.debug(
                    "League %s enriched: matches=%d picks=%d hits=%d profit=%.2f",
                    req.competition, total_matches, total_picks, total_hits, total_profit,
                )

        # ── Issue #63: Calcular avg_corners_per_game desde la BD si Sofascore no lo envía ──
        # Si el valor es el default (9.5), intentar calcularlo desde los resultados históricos.
        _DEFAULT_CORNERS_PER_GAME = 9.5
        if abs(req.league_stats.avg_corners_per_game - _DEFAULT_CORNERS_PER_GAME) < 0.01 and req.competition and req.competition not in ("", "Desconocida", "General"):
            try:
                if db_session is None:
                    db_session = db if db is not None else SessionLocal()
                    db_created = db is None

                from src.ui.api.main import _compute_league_season_corners
                season_val = getattr(req, "season", None) or getattr(req.league_stats, "season", None)
                computed_avg = _compute_league_season_corners(req.competition, season_val, db_session=db_session)
                if computed_avg is not None and 5.0 <= computed_avg <= 16.0:
                    req = req.model_copy(update={
                        "league_stats": req.league_stats.model_copy(update={
                            "avg_corners_per_game": round(computed_avg, 2),
                        })
                    })
                    logger.info(
                        "League %s avg_corners_per_game calculado desde BD: %.2f",
                        req.competition, computed_avg,
                    )
            except Exception as ex_corners:
                logger.warning("Error calculando avg_corners desde BD para %s: %s", req.competition, ex_corners)

    except Exception as ex:
        logger.warning("Error enriching league stats from DB: %s", ex)
    finally:
        if db_created and db_session is not None:
            try:
                db_session.close()
            except Exception:
                pass

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

    use_general = _use_general_stats(req)  # True para partidos >= 2026-01-01

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

    # ── Issue #22: Ajustar rho desde verosimilitud conjunta sobre historial de la liga ──
    # Si hay DB disponible, extraemos partidos históricos de AnalysisHistory y ajustamos rho
    # por máxima verosimilitud (búsqueda en grilla). Si no hay datos suficientes, cae en
    # la heurística original (_default_dc_rho), que es peor pero nunca explota.
    fitted_rho: float | None = None
    if db is not None and req.competition and req.competition not in ("", "Desconocida", "General"):
        try:
            from src.core.domain import AnalysisHistory
            hist_rows = (
                db.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.competition == req.competition,
                    AnalysisHistory.final_score_home.isnot(None),
                    AnalysisHistory.final_score_away.isnot(None),
                )
                .order_by(AnalysisHistory.date.desc())
                .limit(200)
                .all()
            )
            # Build match tuples (home_goals, away_goals, h_lambda, a_lambda)
            # We use the league average lambdas as approximation since we don't store
            # the original lambdas — the key signal is the score distribution shape.
            avg_lambda = req.league_stats.avg_goals_per_game / 2.0
            match_tuples: list[tuple[int, int, float, float]] = []
            for row in hist_rows:
                hg = row.final_score_home
                ag = row.final_score_away
                if hg is None or ag is None:
                    continue
                try:
                    match_tuples.append((int(hg), int(ag), h_lam, a_lam))
                except (ValueError, TypeError):
                    continue
            if len(match_tuples) >= 100:
                fitted_rho = fit_dixon_coles_rho(match_tuples)
                logger.debug(
                    "Liga %s: rho ajustado por MV = %.4f (n=%d partidos).",
                    req.competition, fitted_rho, len(match_tuples),
                )
        except Exception as _rho_err:
            logger.debug("Error ajustando rho para %s: %s", req.competition, _rho_err)
            fitted_rho = None

    matrix, _ = _dc_score_matrix(h_lam, a_lam, rho=fitted_rho)
    markets = _sum_score_matrix_1x2_and_markets(matrix)

    # Exact categorical market normalization
    norm_1x2 = normalize_categorical_market({
        "home": markets["home_win_pct"] / 100.0,
        "draw": markets["draw_pct"] / 100.0,
        "away": markets["away_win_pct"] / 100.0,
    })
    h_prob_raw = norm_1x2["home"]
    d_prob_raw = norm_1x2["draw"]
    a_prob_raw = norm_1x2["away"]

    norm_btts = normalize_categorical_market({
        "yes": markets["btts_yes_pct"] / 100.0,
        "no": markets["btts_no_pct"] / 100.0,
    })
    p_btts_yes = norm_btts["yes"]
    p_btts_no = norm_btts["no"]

    h_prob = h_prob_raw
    d_prob = d_prob_raw
    a_prob = a_prob_raw

    def _overround(*odds_list: float | None) -> float:
        raw = [1.0 / o for o in odds_list if o and o > 1.0]
        return sum(raw) * 100.0 if raw else 100.0

    m_date_eval = current_match_date or getattr(req, "match_date", None) or getattr(req, "date", None)

    def _vi(sel: str, odds: float | None, modelp: float, overround: float = 100.0, push_p: float = 0.0, market_novig_pct: float | None = None) -> ValueIndicator:
        return _value_indicator(
            sel, odds, modelp, h=h, a=a, overround=overround, push_p=push_p,
            league=req.league_stats, league_name=req.competition, odds_obj=req.odds,
            match_date=m_date_eval, market_novig_pct=market_novig_pct,
        )

    _or_1x2  = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    # ── Issue #19: Derivar Doble Oportunidad exactamente de la matriz Dixon-Coles ──
    p_dc_1x = (h_prob_raw + d_prob_raw) * 100.0
    p_dc_x2 = (d_prob_raw + a_prob_raw) * 100.0
    p_dc_12 = (h_prob_raw + a_prob_raw) * 100.0

    _or_dc_raw = _overround(req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12)
    _or_dc = _or_dc_raw if _or_dc_raw > 100.5 else _or_1x2

    # Issue #44: No-vig de Doble Oportunidad por método de potencia
    from src.models.market_probability import remove_vig_power
    _dc_odds_list = [req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12]
    _dc_novig_probs = remove_vig_power(_dc_odds_list) if all(o and o > 1.0 for o in _dc_odds_list) else []
    _dc_novig_1x = (_dc_novig_probs[0] * 100.0) if len(_dc_novig_probs) == 3 else None
    _dc_novig_x2 = (_dc_novig_probs[1] * 100.0) if len(_dc_novig_probs) == 3 else None
    _dc_novig_12 = (_dc_novig_probs[2] * 100.0) if len(_dc_novig_probs) == 3 else None

    market_configs: list[tuple[str, float | None, float, float, float, float | None]] = [
        ("Local",     req.odds.home,     h_prob     * 100, _or_1x2, 0.0, None),
        ("Empate",    req.odds.draw,     d_prob     * 100, _or_1x2, 0.0, None),
        ("Visitante", req.odds.away,     a_prob     * 100, _or_1x2, 0.0, None),
        ("BTTS Sí",   req.odds.btts_yes, p_btts_yes * 100, _or_btts, 0.0, None),
        ("BTTS No",   req.odds.btts_no,  p_btts_no  * 100, _or_btts, 0.0, None),

        ("Doble Oportunidad 1X", req.odds.dc_1x, p_dc_1x, _or_dc, 0.0, _dc_novig_1x),
        ("Doble Oportunidad X2", req.odds.dc_x2, p_dc_x2, _or_dc, 0.0, _dc_novig_x2),
        ("Doble Oportunidad 12", req.odds.dc_12, p_dc_12, _or_dc, 0.0, _dc_novig_12),
    ]
    # Issue #34: Track Over/Under complementary pairs for post-calibration renormalization.
    # Each entry is (over_index, under_index, push_prob_pct) in market_configs.
    _ou_pairs: list[tuple[int, int, float]] = []

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

    # ── Over/Under GOLES: Issue #19 derivado directamente de la matriz Dixon-Coles ─────
    for line in req.odds.goals_lines:
        p_over, p_push, p_under = _matrix_over_under(matrix, line)
        key       = str(line)
        overOdds  = req.odds.goals_over_odds.get(key)
        underOdds = req.odds.goals_under_odds.get(key)
        _or_goals = _overround(overOdds, underOdds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
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

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
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

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
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

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
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

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Tiros a Pta",  over_odds,  p_over,  _or_shots_t, p_push))
        market_configs.append((f"Under {line} Tiros a Pta", under_odds, p_under, _or_shots_t, p_push))

    # ── Values: Cálculo masivo ─────────────
    values = [
        _vi(cfg[0], cfg[1], cfg[2], cfg[3], cfg[4], cfg[5] if len(cfg) > 5 else None)
        for cfg in market_configs
    ]

    # ── Issue #34: Renormalizar pares Over/Under tras calibración independiente ──
    # La calibración jerárquica se aplica por separado a Over y Under, lo que puede
    # romper la condición P(over) + P(push) + P(under) = 100%. Renormalizamos el par
    # calibrado conservando la ratio over/under del modelo crudo cuando hay push,
    # o derivando un lado del otro (under = 100 - push - over) cuando no hay push.
    for _oi, _ui, _push_pct in _ou_pairs:
        if _oi >= len(values) or _ui >= len(values):
            continue
        vo, vu = values[_oi], values[_ui]
        cal_o = vo.calibrated_prob
        cal_u = vu.calibrated_prob
        if cal_o is None or cal_u is None:
            continue
        available = max(0.0, 100.0 - _push_pct)  # probability budget excluding push
        raw_sum = cal_o + cal_u
        if raw_sum > 0.01 and abs(raw_sum - available) > 0.5:  # only fix if out of balance
            scale = available / raw_sum
            new_cal_o = round(max(0.0, min(available, cal_o * scale)), 1)
            new_cal_u = round(max(0.0, min(available, available - new_cal_o)), 1)
            vo.calibrated_prob = new_cal_o
            vu.calibrated_prob = new_cal_u
            # Also normalize model_prob to be consistent
            mp_o = vo.model_prob or 0.0
            mp_u = vu.model_prob or 0.0
            mp_sum = mp_o + mp_u
            if mp_sum > 0.01 and abs(mp_sum - available) > 0.5:
                mp_scale = available / mp_sum
                vo.model_prob = round(max(0.0, min(available, mp_o * mp_scale)), 1)
                vu.model_prob = round(max(0.0, min(available, available - vo.model_prob)), 1)

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

    # ── Extraer Competición / Liga actual ──
    target_competition = None
    if hasattr(req, "competition") and req.competition:
        target_competition = str(req.competition).strip().lower()
    elif hasattr(req, "league") and req.league:
        target_competition = str(req.league).strip().lower()
    elif isinstance(req, dict):
        target_competition = (req.get("competition") or req.get("league") or "").strip().lower()

    current_match_time = _to_naive_utc(current_match_time)
    curr_date_only = current_match_time.date() if current_match_time else None
    historical_records = []
    if precomputed_historical_records is not None:
        source_rows = precomputed_historical_records
    elif db is not None:
        try:
            from sqlalchemy import text
            q_hist = text("""
                SELECT id, match_title, match_date, competition,
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
            source_rows = [dict(r) for r in db.execute(q_hist).mappings().all()]
        except Exception:
            source_rows = []
    else:
        source_rows = []

    if source_rows:
        for r_dict in source_rows:
            m_id = r_dict.get("id")

            if exclude_analysis_id and m_id and str(m_id).strip() == str(exclude_analysis_id).strip():
                continue

            # Filtro por competición/liga para evitar contaminar con estadísticas de otras ligas/homónimos
            if target_competition:
                r_comp = (r_dict.get("competition") or "").strip().lower()
                if r_comp and r_comp != target_competition and target_competition not in r_comp and r_comp not in target_competition:
                    continue

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

            m_dt = _to_naive_utc(m_dt)

            if current_match_time and m_dt and m_dt >= current_match_time:
                continue

            if curr_date_only and m_dt and m_dt.date() >= curr_date_only:
                continue

            historical_records.append(r_dict)

    from src.core.math_engine import LeagueMathEngine, get_league_profile
    from src.domain.temporal import TemporalCutoff
    _shared_cutoff = TemporalCutoff.create(current_match_time)

    target_profile = get_league_profile(target_competition)
    prof_half_life = float(target_profile.get("team_half_life_matches", 10.0))
    prof_prior_strength = float(target_profile.get("league_prior_strength", 12.0))

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

    # ── Filtro de relevancia: solo records que involucren a H o A en la misma liga ──
    _h_lower = h.name.strip().lower()
    _a_lower = a.name.strip().lower()

    def _record_involves_team(rec: dict) -> bool:
        title = rec.get("match_title", "") or ""
        ht = (rec.get("home_team") or (title.split(" vs ")[0] if " vs " in title else "")).strip().lower()
        at = (rec.get("away_team") or (title.split(" vs ")[1] if " vs " in title else "")).strip().lower()
        return (
            _h_lower == ht or _h_lower == at or _h_lower in ht or _h_lower in at
            or _a_lower == ht or _a_lower == at or _a_lower in ht or _a_lower in at
        )

    if precomputed_team_index is not None:
        def _lookup_team(team_lower: str) -> list:
            if target_competition:
                exact_comp = precomputed_team_index.get(f"{target_competition}::{team_lower}")
                if exact_comp is not None:
                    return exact_comp
            exact = precomputed_team_index.get(team_lower)
            if exact is not None:
                if target_competition:
                    return [
                        r for r in exact
                        if not r.get("competition") or target_competition in str(r.get("competition")).lower() or str(r.get("competition")).lower() in target_competition
                    ]
                return exact
            # Fallback: solo si el nombre no está en el índice
            return [r for r in historical_records if team_lower in r.get("match_title", "").lower()]

        _seen_ids = set()
        relevant_records = []
        for r in _lookup_team(_h_lower) + _lookup_team(_a_lower):
            rid = r.get("id")
            if rid in _seen_ids:
                continue
            _seen_ids.add(rid)
            relevant_records.append(r)
    else:
        relevant_records = [r for r in historical_records if _record_involves_team(r)]

    # ── Filtro por Temporada Actual para Hit Rates de Equipos ──
    target_year = current_match_time.year if current_match_time else datetime.now().year
    if isinstance(req, dict) and req.get("season_year"):
        try:
            target_year = int(req.get("season_year"))
        except Exception:
            pass

    def _is_current_season_record(rec: dict) -> bool:
        s_year = rec.get("season_year") or rec.get("season")
        if s_year is not None:
            if str(target_year) in str(s_year):
                return True
        m_date = rec.get("match_date")
        if m_date:
            try:
                if isinstance(m_date, datetime):
                    return m_date.year == target_year
                m_s = str(m_date)
                return str(target_year) in m_s[:4]
            except Exception:
                pass
        return False

    season_records = [r for r in relevant_records if _is_current_season_record(r)]
    team_hr_records = season_records if season_records else relevant_records

    for v in values:
        v.home_team = h.name
        v.away_team = a.name
        if match_incomplete_stats:
            block_pick(
                v,
                BlockReason.RULE_BLOCKED,
                detail="Partido omitido por datos insuficientes: al menos un equipo solo tiene Rating de equipo y Posesión"
            )
            continue

        # ── Hit Rate empírico (% de acierto real en partidos históricos de LA TEMPORADA ACTUAL para TODOS los mercados) ──
        if relevant_records:
            fam = _market_family(v.selection)
            side = _market_side(v.selection)
            line = _extract_line_number(v.selection)
            is_ov = (side == "over")

            # Mapeo según familia de mercado
            if fam in {"goals", "corners", "cards", "shots", "shots_target", "fouls"} and line is not None:
                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records, fam, line=line, is_over=is_ov,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(team_hr_records, h.name, fam, line=line, is_over=is_ov, role_filter="home", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength)
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(team_hr_records, a.name, fam, line=line, is_over=is_ov, role_filter="away", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(relevant_records, h.name, a.name, fam, line=line, is_over=is_ov, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff)

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
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
                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records, btts_fam,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(team_hr_records, h.name, btts_fam, role_filter="home", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength)
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(team_hr_records, a.name, btts_fam, role_filter="away", exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength)
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(relevant_records, h.name, a.name, btts_fam, exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff)

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam in {"result", "moneyline", "1x2"}:
                sel_lower = v.selection.lower()
                if "home" in side or "local" in sel_lower:
                    tside = "home"
                elif "away" in side or "visitante" in sel_lower:
                    tside = "away"
                else:
                    tside = "draw"

                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records, "1x2", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records, h.name, "1x2", role_filter="home", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records, a.name, "1x2", role_filter="away", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records, h.name, a.name, "1x2", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Combinación equilibrada de la muestra de ambos equipos
                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)
                else:
                    v.empirical_hit_rate = None

            elif fam in {"double_chance", "doublechance"}:
                sel_lower = v.selection.lower()
                if "1x" in sel_lower or side in {"home_draw", "homedraw"}:
                    tside = "1x"
                elif "x2" in sel_lower or side in {"draw_away", "drawaway"}:
                    tside = "x2"
                else:
                    tside = "12"

                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records, "double_chance", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records, h.name, "double_chance", role_filter="home", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records, a.name, "double_chance", role_filter="away", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff, prior_rate=league_prior, half_life=prof_half_life, prior_strength=prof_prior_strength
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records, h.name, a.name, "double_chance", target_side=tside,
                    exclude_match_id=exclude_analysis_id, current_match_date=current_match_time, cutoff=_shared_cutoff
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Combinación equilibrada de la muestra de ambos equipos
                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)
                else:
                    v.empirical_hit_rate = None

        # #50: Veto por hit rate solo con muestra real y suficiente (emp_n >= 15).
        # Evitar falsos positivos por muestras cortas de 5-10 partidos con alta varianza.
        fam_v = _market_family(v.selection)
        emp_n = getattr(v, "hit_rate_samples", 0) or 0
        if v.empirical_hit_rate is not None and v.model_prob is not None and emp_n >= 15:
            gap = abs(v.model_prob - v.empirical_hit_rate)
            if fam_v in {"shots", "corners", "shots_target"} and gap > 20.0:
                block_pick(
                    v,
                    BlockReason.RULE_BLOCKED,
                    detail=f"Veto por brecha Prob Modelo ({v.model_prob}%) vs Hit Rate Total ({v.empirical_hit_rate}% en {emp_n} partidos) > 20 pts"
                )
            elif gap > 30.0 or (v.empirical_hit_rate < 15.0 and v.model_prob >= 50.0):
                block_pick(
                    v,
                    BlockReason.RULE_BLOCKED,
                    detail=f"Veto por inconsistencia empírica: Prob Modelo ({v.model_prob}%) vs Hit Rate Real ({v.empirical_hit_rate}% en {emp_n} partidos)"
                )

        q_score, s_support, p_support, strat_score = _rate_pick_quality(v, h, a, projected_lines)
        # quality_score siempre se almacena como métrica analítica.
        # Ya no es gate de publicación; el pick se muestra si tiene valor
        # (EV/edge/stake) y no está bloqueado por blacklist o correlación.
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

    # ── Control de sobreexposición simultánea (Simultaneous Kelly Scaling) ──
    # Aplica el portfolio cap definido en RiskPolicy sobre todos los picks
    # publicables del análisis. Si la suma de kelly_fractions supera max_total_exposure,
    # todos se escalan proporcionalmente; picks que quedan bajo MIN_STAKE se
    # bloquean de forma irreversible con trazabilidad en eligibility_hard_blocks.
    _policy = RiskPolicy.from_json()
    values = apply_portfolio_exposure_cap(
        value_indicators=values,
        max_total_exposure=_policy.max_total_exposure,
        min_stake_threshold=float(MIN_STAKE),  # unidades absolutas (no fracción bankroll)
    )

    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp = [
        v for v in values
        if v.is_value and v.is_publishable and not getattr(v, "is_rule_blocked", False) and not getattr(v, "correlation_blocked", False)
    ]

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