"""Modelos Pydantic de la API de comparación de fútbol (DTOs)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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
    matches_home: int = Field(0, description="Partidos jugados como local")
    matches_away: int = Field(0, description="Partidos jugados como visitante")
    matches_played: int = Field(0, description="Partidos totales")
    wins: int = Field(0, description="Ganados")
    draws: int = Field(0, description="Empates")
    losses: int = Field(0, description="Perdidos")
    has_stats: bool = Field(True, description="Indica si el equipo tiene datos reales cargados")

    # Goles
    goals_per_game: float = Field(0.0, description="Goles por juego")
    goals_conceded_per_game: float = Field(0.0, description="Goles concedidos por juego")
    goal_conversion_pct: float = Field(0.0, description="Conversión de gol %")

    # Goles Detallados (NUEVO)
    goals_inside_box: float = Field(0.0, description="Goles dentro del área por juego")
    goals_outside_box: float = Field(0.0, description="Goles fuera del área por juego")
    headed_goals: float = Field(0.0, description="Goles de cabeza por juego")
    free_kick_goals: float = Field(0.0, description="Goles de tiro libre por juego")
    fast_break_goals: float = Field(0.0, description="Goles en contraataque por juego")
    penalty_goals: float = Field(0.0, description="Goles de penalti por juego")
    own_goals: float = Field(0.0, description="Autogoles por juego")

    # Ataque
    big_chances_per_game: float = Field(0.0, description="Grandes chances por juego")
    big_chances_missed_per_game: float = Field(
        0.0, description="Grandes chances falladas por juego"
    )
    big_chances_created: float = Field(0.0, description="Grandes chances creadas por juego")
    shots_per_game: float = Field(0.0, description="Tiros totales por juego")
    shots_on_target_per_game: float = Field(0.0, description="Tiros al arco por juego")

    # Tiros Detallados (NUEVO)
    shots_blocked: float = Field(0.0, description="Tiros bloqueados por juego")
    shots_inside_box: float = Field(0.0, description="Tiros dentro del área por juego")
    shots_outside_box: float = Field(0.0, description="Tiros fuera del área por juego")
    hit_woodwork: float = Field(0.0, description="Tiros al palo por juego")
    fast_break_shots: float = Field(0.0, description="Tiros en contraataque por juego")
    free_kick_shots: float = Field(0.0, description="Tiros libres por juego")
    penalties_taken: float = Field(0.0, description="Penales ejecutados por juego")

    # Acciones Ofensivas (NUEVO)
    dribble_success_pct: float = Field(0.0, description="% dribbles exitosos")
    fast_breaks: float = Field(0.0, description="Contraataques por juego")
    throw_ins: float = Field(0.0, description="Saques de banda por juego")

    # Posesión / Pases
    possession_pct: Optional[float] = Field(None, description="Posesión % (None si ausente)")
    passes_completed: float = Field(0, description="Pases acertados")
    pass_accuracy: float = Field(0, description="Precisión pases %")
    passes_opp_half: float = Field(0, description="Pases acertados campo rival")
    pass_accuracy_opp_half: float = Field(0, description="Precisión pases campo rival %")
    crosses_per_game: float = Field(0, description="Centros completos por juego")
    cross_accuracy: float = Field(0, description="Precisión de centros %")
    corners_per_game: float = Field(0.0, description="Corners por juego")

    # Posesión Avanzada (NUEVO)
    possession_lost: float = Field(0.0, description="Pérdidas de posesión por juego")

    # Defensa
    clean_sheets_home: int = Field(0, description="Vallas invictas como local")
    clean_sheets_away: int = Field(0, description="Vallas invictas como visitante")
    clean_sheets: float = Field(0.0, description="Vallas invictas totales")
    saves_per_game: float = Field(0, description="Saves por juego")
    balls_recovered_per_game: float = Field(0.0, description="Recuperaciones por juego")

    # Defensa Avanzada (NUEVO)
    clearances_off_line: float = Field(0.0, description="Despejes en línea por juego")
    last_man_tackles: float = Field(0.0, description="Entradas último hombre por juego")

    # Duelos
    duels_won_per_game: float = Field(0, description="Duelos ganados por juego")
    ground_duels_won_per_game: float = Field(0, description="Duelos en piso ganados por juego")

    # Duelos Avanzados (NUEVO)
    duels_total_per_game: float = Field(0.0, description="Duelos totales por juego")
    aerial_duels_won_per_game: float = Field(0.0, description="Duelos aéreos ganados por juego")
    aerial_duels_won_pct: float = Field(0.0, description="% duelos aéreos ganados")

    # Set pieces
    penalties_conceded: float = Field(0, description="Penales concedidos")

    # Set pieces Avanzado (NUEVO)
    penalty_goals_conceded: float = Field(
        0.0, description="Penales convertidos en contra por juego"
    )

    # Disciplina
    fouls_per_game: float = Field(0.0, description="Faltas por juego")
    yellow_cards_per_game: float = Field(0.0, description="Amarillas promedio por juego")

    red_cards_total: float = Field(0.0, description="Rojas totales")
    errors_leading_to_goal: float = Field(0, description="Errores que llevan a gol")
    offside_per_game: float = Field(0, description="Fuera de juego por juego")

    # Disciplina Avanzada (NUEVO)
    errors_leading_to_shot: float = Field(0.0, description="Errores que llevan a tiro por juego")

    # Extra Advanced
    corners_conceded_per_game: float = Field(0.0, description="Corners concedidos por juego")
    xg_per_game: Optional[float] = Field(None, description="Expected Goals por juego")
    xga_per_game: Optional[float] = Field(None, description="Expected Goals Against por juego")
    xg_is_imputed: bool = Field(
        False, description="True si xG no es oficial y fue estimado o imputado"
    )
    # Pases / Centros (Totales vs Acertados)
    passes_total_per_game: float = Field(0.0, description="Pases totales intentados por juego")
    passes_opp_half_total_per_game: float = Field(
        0.0, description="Pases totales intentados en campo rival"
    )
    crosses_total_per_game: float = Field(0.0, description="Centros totales intentados por juego")

    # Portero Avanzado (NUEVO)
    save_pct: float = Field(0.0, description="Paradas %")
    goal_kicks: float = Field(0.0, description="Saque de meta por juego")

    # Físicas (NUEVO)
    kilometers_covered: float = Field(0.0, description="Kilómetros recorridos por juego")
    number_of_sprints: float = Field(0.0, description="Sprints por juego")

    # Rating (NUEVO)
    avg_rating: Optional[float] = Field(None, description="Rating promedio del equipo")

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
    big_chances_created_per_game: float = Field(
        0.0, description="Grandes chances creadas por juego"
    )
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
    passes_opp_half_per_game: float = Field(
        0.0, description="Pases completados campo rival por juego"
    )
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
    shots_on_target_against_per_game: float = Field(
        0.0, description="Tiros concedidos al arco por juego"
    )
    shots_off_target_against: float = Field(0.0, description="Tiros concedidos desviados totales")
    shots_off_target_against_per_game: float = Field(
        0.0, description="Tiros concedidos desviados por juego"
    )
    shots_blocked_against: float = Field(0.0, description="Tiros concedidos bloqueados totales")
    shots_blocked_against_per_game: float = Field(
        0.0, description="Tiros concedidos bloqueados por juego"
    )
    blocked_scoring_attempt_against: float = Field(
        0.0, description="Intentos de tiro bloqueados al oponente"
    )
    blocked_scoring_attempt_against_per_game: float = Field(
        0.0, description="Intentos de tiro bloqueados al oponente por juego"
    )
    shots_inside_box_against: float = Field(
        0.0, description="Tiros concedidos dentro del área totales"
    )
    shots_inside_box_against_per_game: float = Field(
        0.0, description="Tiros concedidos dentro del área por juego"
    )
    shots_outside_box_against: float = Field(
        0.0, description="Tiros concedidos fuera del área totales"
    )
    shots_outside_box_against_per_game: float = Field(
        0.0, description="Tiros concedidos fuera del área por juego"
    )
    big_chances_against: float = Field(0.0, description="Grandes chances concedidas totales")
    big_chances_against_per_game: float = Field(
        0.0, description="Grandes chances concedidas por juego"
    )
    big_chances_created_against: float = Field(
        0.0, description="Grandes chances creadas por el oponente totales"
    )
    big_chances_created_against_per_game: float = Field(
        0.0, description="Grandes chances creadas por el oponente por juego"
    )
    big_chances_missed_against: float = Field(
        0.0, description="Grandes chances falladas por el oponente totales"
    )
    big_chances_missed_against_per_game: float = Field(
        0.0, description="Grandes chances falladas por el oponente por juego"
    )
    hit_woodwork_against: float = Field(0.0, description="Tiros al palo del oponente totales")
    hit_woodwork_against_per_game: float = Field(
        0.0, description="Tiros al palo del oponente por juego"
    )
    total_passes_against: float = Field(0.0, description="Pases del oponente totales")
    accurate_passes_against: float = Field(
        0.0, description="Pases completados del oponente totales"
    )
    total_own_half_passes_against: float = Field(
        0.0, description="Pases propia mitad oponente totales"
    )
    accurate_own_half_passes_against: float = Field(
        0.0, description="Pases completados propia mitad oponente totales"
    )
    total_opp_half_passes_against: float = Field(
        0.0, description="Pases mitad rival oponente totales"
    )
    accurate_opp_half_passes_against: float = Field(
        0.0, description="Pases completados mitad rival oponente totales"
    )
    total_final_third_passes_against: float = Field(0.0, description="Pases 3/4 oponente totales")
    accurate_final_third_passes_against: float = Field(
        0.0, description="Pases completados 3/4 oponente totales"
    )
    crosses_total_against: float = Field(0.0, description="Centros del oponente totales")
    crosses_successful_against: float = Field(
        0.0, description="Centros completados del oponente totales"
    )
    long_balls_total_against: float = Field(0.0, description="Long balls del oponente totales")
    long_balls_successful_against: float = Field(
        0.0, description="Long balls completadas del oponente totales"
    )
    dribble_attempts_against: float = Field(
        0.0, description="Dribbles intentados del oponente totales"
    )
    dribble_attempts_won_against: float = Field(
        0.0, description="Dribbles ganados del oponente totales"
    )
    tackles_against: float = Field(0.0, description="Entradas del oponente totales")
    interceptions_against: float = Field(0.0, description="Intercepciones del oponente totales")
    clearances_against: float = Field(0.0, description="Despejes del oponente totales")
    key_passes_against: float = Field(0.0, description="Pases clave del oponente totales")
    corners_against: float = Field(0.0, description="Corners del oponente totales")
    offsides_against: float = Field(0.0, description="Offsides del oponente totales")
    yellow_cards_against: float = Field(0.0, description="Tarjetas amarillas del oponente totales")
    red_cards_against: float = Field(0.0, description="Tarjetas rojas del oponente totales")


class LeagueStats(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field("", description="Nombre de la liga")
    avg_goals_per_game: float = Field(2.5, description="Promedio total goles liga")
    avg_corners_per_game: float = Field(9.5, description="Promedio corners liga")
    avg_cards_per_game: float = Field(4.5, description="Promedio tarjetas liga")
    home_win_pct: float = Field(45.0, description="% Victoria local liga")
    draw_pct: float = Field(25.0, description="% Empate liga")
    away_win_pct: float = Field(30.0, description="% Victoria visitante liga")
    avg_yellow_cards_per_game: float = Field(4.0, description="Promedio amarillas liga")
    avg_red_cards_per_game: float = Field(0.2, description="Promedio rojas liga")
    avg_shots_per_game: float = Field(26.0, description="Promedio tiros totales liga")
    avg_shots_target_per_game: float = Field(8.5, description="Promedio tiros a puerta liga")
    home_advantage_factor: float = Field(1.20, description="Multiplicador goles local (1.15–1.30)")
    away_disadvantage_factor: float = Field(0.85, description="Factor penalización visitante")

    # Referee stats
    referee_avg_yellow: float = Field(0.0, description="Promedio amarillas del árbitro")
    referee_avg_red: float = Field(0.0, description="Promedio rojas del árbitro")

    # League Reliability Score (0.0 – 1.0)
    # 1.0 = liga de máxima confianza (top5 europeas, datos completos y estables)
    # 0.0 = liga de muy baja confianza (poca data, alta varianza, comportamiento impredecible)
    # Si se deja en 0.0 (por defecto) el sistema lo autocalibrará con _compute_league_reliability_score().
    league_reliability_score: float = Field(
        0.0, description="Confiabilidad histórica de la liga (0–1). 0 = autocalibrarse."
    )

    # Historical performance data (optional – used to compute LRS from real pick history)
    historical_matches: int = Field(
        0, description="Partidos analizados históricamente en esta liga"
    )
    historical_picks: int = Field(0, description="Picks resueltos históricamente en esta liga")
    historical_hits: int = Field(0, description="Picks acertados históricamente en esta liga")
    historical_profit: float = Field(
        0.0, description="Beneficio histórico acumulado en esta liga (unidades)"
    )
    accuracy: float = Field(0.0, description="Precisión de picks histórica de la liga")
    roi: float = Field(0.0, description="ROI histórico de la liga")
    # Per-market win rates (family → hits/total dict serialized as JSON string; parsed internally)
    market_hit_rates: Dict[str, float] = Field(
        default_factory=dict, description="Tasa de acierto por mercado {family: rate}"
    )


class FootballOdds(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    home: float | None = Field(None, gt=1.0)
    draw: float | None = Field(None, gt=1.0)
    away: float | None = Field(None, gt=1.0)
    btts_yes: float | None = Field(None, gt=1.0)
    btts_no: float | None = Field(None, gt=1.0)

    # DC
    dc_1x: float | None = Field(None, gt=1.0)
    dc_x2: float | None = Field(None, gt=1.0)
    dc_12: float | None = Field(None, gt=1.0)

    goals_lines: list[float] = [1.5, 2.5, 3.5, 4.5]
    goals_over_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    goals_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    corners_lines: list[float] = [7.5, 8.5, 9.5, 10.5]
    corners_over_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    corners_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    cards_lines: list[float] = [2.5, 3.5, 4.5, 5.5]
    cards_over_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    cards_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    shots_lines: list[float] = [21.5, 22.5, 23.5, 24.5]
    shots_over_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
    shots_under_odds: Dict[str, Optional[float]] = Field(default_factory=dict)

    shots_target_lines: list[float] = [7.5, 8.5, 9.5, 10.5]
    shots_target_over_odds: Dict[str, Optional[float]] = Field(default_factory=dict)
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
    user_context: str = Field(
        default="", description="Contexto adicional proporcionado por el usuario sobre los equipos"
    )
    match_date: Optional[str] = Field(
        default=None,
        description="Fecha del partido (YYYY-MM-DD). A partir del 2026-01-01 las stats son generales (sin segmentación por localía).",
    )
    use_general_stats: bool = Field(
        default=False,
        description="Si es True, se usan stats generales. Si es False, se usan stats segmentadas por localía.",
    )


# ───────────────────────────────────────────────────────────────
# Response models
# ───────────────────────────────────────────────────────────────
class ValueIndicator(BaseModel):
    selection: str
    odds: float | None = None

    # Probabilidades
    model_prob: float  # Raw Poisson/Bayesian prob
    calibrated_prob: Optional[float] = None
    implied_prob: Optional[float] = None  # 1/odds (raw)
    implied_prob_no_vig: Optional[float] = None  # Fair market prob

    # Métricas de Valor
    edge: float = 0.0  # Diferencia de prob (legacy/display)
    edge_ev: float = 0.0  # Expected Value real: (cal_prob * odds) - 1
    fair_odds: Optional[float] = None

    # Status y Calidad
    is_value: bool = False
    rating: str = "N/A"
    quality_score: Optional[int] = None
    strategic_score: Optional[int] = None
    stat_support: Optional[float] = None
    proj_support: Optional[float] = None
    data_quality_score: Optional[float] = None

    # League Reliability
    league_reliability_score: Optional[float] = None
    league_reliability_penalty: Optional[float] = None

    # Clasificación de Mercado
    market_confidence_tier: Optional[str] = None
    market_variance_tier: Optional[str] = None

    # Flags de Decisión
    is_publishable: bool = False
    is_underdog: bool = False
    success: Optional[bool | str] = None
    display_score: Optional[float] = None
    push_prob: Optional[float] = None

    # Staking
    kelly_fraction: Optional[float] = None
    sample_size_weight: Optional[float] = None
    is_blacklisted: bool = False
    stake_units: Optional[float] = None

    # ── Snapshot e inmutabilidad temporal ──
    pick_id: Optional[str] = None
    predicted_at_utc: Optional[str] = None
    model_prob_raw: Optional[float] = None
    calibration_version: Optional[str] = None

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
    market_family: Optional[str] = None  # goals | btts | result | corners | cards | shots | ...
    market_side: Optional[str] = None  # over | under | yes | no | home | away | draw | ...
    line_bucket: Optional[str] = None  # low_0_5_1_5 | core_2_5 | high_3_5 | no_line | ...
    segment_key: Optional[str] = None  # league:X|family:Y|side:Z|bucket:W

    # Probabilidades desglosadas por etapa del pipeline
    final_prob: Optional[float] = None  # blend calibrado + mercado (la más informada)
    p_market_no_vig: Optional[float] = None  # prob implícita de mercado sin vig (0-100)

    # Edge desglosado (raw → calibrado → final)
    edge_raw: Optional[float] = None  # edge con prob. Poisson cruda
    edge_calibrated: Optional[float] = None  # edge con prob. calibrada (curva jerárquica)
    edge_final: Optional[float] = None  # edge con prob. final (blend mercado)

    # Gobernanza de segmento
    segment_status: Optional[str] = None  # active | watch | reduced | blocked | experimental
    drift_score: Optional[float] = None  # score de drift del segmento (0-1)
    governance_multiplier: Optional[float] = None  # factor aplicado al stake por gobernanza [0-1]
    min_edge_add: Optional[float] = (
        None  # incremento mínimo de edge requerido por gobernanza (en pp)
    )

    # Componentes de fiabilidad
    reliability_components: Dict[str, float] = Field(default_factory=dict)


class StatComparison(BaseModel):
    label: str
    key: str
    home_value: Optional[float] = None
    away_value: Optional[float] = None
    advantage: str  # "home" | "away" | "even"


class ProjectedLine(BaseModel):
    label: str
    value: float
    type: str  # 'goals', 'corners', 'cards','btts'
    prob: Optional[float] = None  # Probabilidad (0-100)


class CompareResponse(BaseModel):
    sport: str
    home_name: str
    away_name: str
    h_lam: Optional[float] = None
    a_lam: Optional[float] = None
    h_corners_lam: Optional[float] = None
    a_corners_lam: Optional[float] = None
    h_cards_lam: Optional[float] = None
    a_cards_lam: Optional[float] = None
    h_fouls_lam: Optional[float] = None
    a_fouls_lam: Optional[float] = None
    h_offsides_lam: Optional[float] = None
    a_offsides_lam: Optional[float] = None
    most_probable_score: Optional[str] = None
    mps_confidence: Optional[float] = None  # Probabilidad acumulada del marcador y vecinos (±1 gol)
    comparisons: list[StatComparison]
    values: list[ValueIndicator]
    projected_lines: list[ProjectedLine] = []
    summary: str
    llm_analysis: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Shared helpers
# ───────────────────────────────────────────────────────────────
