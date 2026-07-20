from datetime import datetime
import json
from typing import Any

from pydantic import BaseModel, field_validator


class SportOut(BaseModel):
    value: str
    label: str


class CompetitionOut(BaseModel):
    id: str
    sport: str
    name: str
    country: str | None = None
    season: str | None = None

    class Config:
        from_attributes = True


class TeamOut(BaseModel):
    id: str
    sport: str
    name: str
    short_name: str | None = None
    country: str | None = None
    logo_url: str | None = None

    class Config:
        from_attributes = True


class BettingLineOut(BaseModel):
    id: str
    market_type: str
    selection: str
    line: float | None = None
    odds: float
    bookmaker: str | None = None
    timestamp: datetime | None = None

    class Config:
        from_attributes = True


class MatchOut(BaseModel):
    id: str
    sport: str
    date: datetime
    home_team: TeamOut | None = None
    away_team: TeamOut | None = None
    home_score: int | None = None
    away_score: int | None = None
    status: str | None = None
    venue: str | None = None
    round: str | None = None
    surface: str | None = None
    competition: CompetitionOut | None = None
    betting_lines: list[BettingLineOut] = []

    class Config:
        from_attributes = True


class SyncResult(BaseModel):
    source: str
    competitions_synced: int = 0
    matches_synced: int = 0
    message: str = ""


class AnalysisSave(BaseModel):
    id: str | None = None
    sport: str
    match_title: str
    payload: Any
    match_date: datetime | None = None
    picks_calculados: Any | None = None
    user_context: str | None = None
    llm_response: str | None = None
    llm_timestamp: datetime | None = None
    compare_response_snapshot: Any | None = None
    needs_reanalysis: bool | None = False
    count_in_profitability: bool | None = True
    has_real_stats: bool | None = True


class AnalysisResultsUpdate(BaseModel):
    final_score_home: int | None = None
    final_score_away: int | None = None
    final_corners_home: int | None = None
    final_corners_away: int | None = None
    final_yellow_cards_home: int | None = None
    final_yellow_cards_away: int | None = None
    final_red_cards_home: int | None = None
    final_red_cards_away: int | None = None
    final_shots_home: int | None = None
    final_shots_away: int | None = None
    final_shots_on_target_home: int | None = None
    final_shots_on_target_away: int | None = None
    final_fouls_home: int | None = None
    final_fouls_away: int | None = None
    final_offsides_home: int | None = None
    final_offsides_away: int | None = None

    expected_goals_home: float | None = None
    expected_goals_away: float | None = None
    ball_possession_home: float | None = None
    ball_possession_away: float | None = None
    aerial_duels_percentage_home: float | None = None
    aerial_duels_percentage_away: float | None = None
    ground_duels_percentage_home: float | None = None
    ground_duels_percentage_away: float | None = None
    dribbles_percentage_home: float | None = None
    dribbles_percentage_away: float | None = None
    duel_won_percent_home: float | None = None
    duel_won_percent_away: float | None = None
    won_tackle_percent_home: float | None = None
    won_tackle_percent_away: float | None = None
    goals_prevented_home: float | None = None
    goals_prevented_away: float | None = None

    accurate_cross_home: int | None = None
    accurate_cross_away: int | None = None
    accurate_long_balls_home: int | None = None
    accurate_long_balls_away: int | None = None
    accurate_passes_home: int | None = None
    accurate_passes_away: int | None = None
    accurate_through_ball_home: int | None = None
    accurate_through_ball_away: int | None = None
    ball_recovery_home: int | None = None
    ball_recovery_away: int | None = None
    big_chance_created_home: int | None = None
    big_chance_created_away: int | None = None
    big_chance_missed_home: int | None = None
    big_chance_missed_away: int | None = None
    big_chance_scored_home: int | None = None
    big_chance_scored_away: int | None = None
    blocked_scoring_attempt_home: int | None = None
    blocked_scoring_attempt_away: int | None = None
    corner_kicks_home: int | None = None
    corner_kicks_away: int | None = None
    dispossessed_home: int | None = None
    dispossessed_away: int | None = None
    dive_saves_home: int | None = None
    dive_saves_away: int | None = None
    final_third_entries_home: int | None = None
    final_third_entries_away: int | None = None
    final_third_phase_statistic_home: int | None = None
    final_third_phase_statistic_away: int | None = None
    fouled_final_third_home: int | None = None
    fouled_final_third_away: int | None = None
    fouls_home: int | None = None
    fouls_away: int | None = None
    free_kicks_home: int | None = None
    free_kicks_away: int | None = None
    goal_kicks_home: int | None = None
    goal_kicks_away: int | None = None
    goalkeeper_saves_home: int | None = None
    goalkeeper_saves_away: int | None = None
    high_claims_home: int | None = None
    high_claims_away: int | None = None
    hit_woodwork_home: int | None = None
    hit_woodwork_away: int | None = None
    interception_won_home: int | None = None
    interception_won_away: int | None = None
    offsides_home: int | None = None
    offsides_away: int | None = None
    passes_home: int | None = None
    passes_away: int | None = None
    punches_home: int | None = None
    punches_away: int | None = None
    shots_off_goal_home: int | None = None
    shots_off_goal_away: int | None = None
    shots_on_goal_home: int | None = None
    shots_on_goal_away: int | None = None
    throw_ins_home: int | None = None
    throw_ins_away: int | None = None
    total_clearance_home: int | None = None
    total_clearance_away: int | None = None
    total_shots_inside_box_home: int | None = None
    total_shots_inside_box_away: int | None = None
    total_shots_on_goal_home: int | None = None
    total_shots_on_goal_away: int | None = None
    total_shots_outside_box_home: int | None = None
    total_shots_outside_box_away: int | None = None
    total_tackle_home: int | None = None
    total_tackle_away: int | None = None
    touches_in_opp_box_home: int | None = None
    touches_in_opp_box_away: int | None = None
    yellow_cards_home: int | None = None
    yellow_cards_away: int | None = None


class AnalysisHistoryOut(BaseModel):
    id: str
    sport: str
    date: datetime
    match_date: datetime | None = None
    match_title: str
    payload: Any
    picks_calculados: Any | None = None
    user_context: str | None = None
    llm_response: str | None = None
    llm_timestamp: datetime | None = None
    compare_response_snapshot: Any | None = None
    needs_reanalysis: bool | None = False
    final_score_home: int | None = None
    final_score_away: int | None = None
    final_corners_home: int | None = None
    final_corners_away: int | None = None
    final_yellow_cards_home: int | None = None
    final_yellow_cards_away: int | None = None
    final_red_cards_home: int | None = None
    final_red_cards_away: int | None = None
    final_shots_home: int | None = None
    final_shots_away: int | None = None
    final_shots_on_target_home: int | None = None
    final_shots_on_target_away: int | None = None
    final_fouls_home: int | None = None
    final_fouls_away: int | None = None
    final_offsides_home: int | None = None
    final_offsides_away: int | None = None
    accuracy_percentage: float | None = None
    count_in_profitability: bool = True
    has_picks: bool = False
    picks_hits_summary: str | None = None # e.g. "2/3"
    has_real_stats: bool = True

    expected_goals_home: float | None = None
    expected_goals_away: float | None = None
    ball_possession_home: float | None = None
    ball_possession_away: float | None = None
    aerial_duels_percentage_home: float | None = None
    aerial_duels_percentage_away: float | None = None
    ground_duels_percentage_home: float | None = None
    ground_duels_percentage_away: float | None = None
    dribbles_percentage_home: float | None = None
    dribbles_percentage_away: float | None = None
    duel_won_percent_home: float | None = None
    duel_won_percent_away: float | None = None
    won_tackle_percent_home: float | None = None
    won_tackle_percent_away: float | None = None
    goals_prevented_home: float | None = None
    goals_prevented_away: float | None = None

    accurate_cross_home: int | None = None
    accurate_cross_away: int | None = None
    accurate_long_balls_home: int | None = None
    accurate_long_balls_away: int | None = None
    accurate_passes_home: int | None = None
    accurate_passes_away: int | None = None
    accurate_through_ball_home: int | None = None
    accurate_through_ball_away: int | None = None
    ball_recovery_home: int | None = None
    ball_recovery_away: int | None = None
    big_chance_created_home: int | None = None
    big_chance_created_away: int | None = None
    big_chance_missed_home: int | None = None
    big_chance_missed_away: int | None = None
    big_chance_scored_home: int | None = None
    big_chance_scored_away: int | None = None
    blocked_scoring_attempt_home: int | None = None
    blocked_scoring_attempt_away: int | None = None
    corner_kicks_home: int | None = None
    corner_kicks_away: int | None = None
    dispossessed_home: int | None = None
    dispossessed_away: int | None = None
    dive_saves_home: int | None = None
    dive_saves_away: int | None = None
    final_third_entries_home: int | None = None
    final_third_entries_away: int | None = None
    final_third_phase_statistic_home: int | None = None
    final_third_phase_statistic_away: int | None = None
    fouled_final_third_home: int | None = None
    fouled_final_third_away: int | None = None
    fouls_home: int | None = None
    fouls_away: int | None = None
    free_kicks_home: int | None = None
    free_kicks_away: int | None = None
    goal_kicks_home: int | None = None
    goal_kicks_away: int | None = None
    goalkeeper_saves_home: int | None = None
    goalkeeper_saves_away: int | None = None
    high_claims_home: int | None = None
    high_claims_away: int | None = None
    hit_woodwork_home: int | None = None
    hit_woodwork_away: int | None = None
    interception_won_home: int | None = None
    interception_won_away: int | None = None
    offsides_home: int | None = None
    offsides_away: int | None = None
    passes_home: int | None = None
    passes_away: int | None = None
    punches_home: int | None = None
    punches_away: int | None = None
    shots_off_goal_home: int | None = None
    shots_off_goal_away: int | None = None
    shots_on_goal_home: int | None = None
    shots_on_goal_away: int | None = None
    throw_ins_home: int | None = None
    throw_ins_away: int | None = None
    total_clearance_home: int | None = None
    total_clearance_away: int | None = None
    total_shots_inside_box_home: int | None = None
    total_shots_inside_box_away: int | None = None
    total_shots_on_goal_home: int | None = None
    total_shots_on_goal_away: int | None = None
    total_shots_outside_box_home: int | None = None
    total_shots_outside_box_away: int | None = None
    total_tackle_home: int | None = None
    total_tackle_away: int | None = None
    touches_in_opp_box_home: int | None = None
    touches_in_opp_box_away: int | None = None
    yellow_cards_home: int | None = None
    yellow_cards_away: int | None = None

    @field_validator("payload", "picks_calculados", "compare_response_snapshot", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v

    class Config:
        from_attributes = True
class StatItem(BaseModel):
    name: str
    picks: int
    hits: int
    accuracy: float
    profit: float = 0.0

class BucketStat(BaseModel):
    bucket: str
    count: int
    avg_odds: float
    accuracy: float

class CategoryStatsOut(BaseModel):
    total_picks: int = 0
    total_hits: int = 0
    total_pending: int = 0
    accuracy: float = 0.0
    avg_odds: float = 0.0
    avg_winning_odds: float = 0.0
    total_profit: float = 0.0
    roi: float = 0.0
    best_markets: list[StatItem] = []
    worst_markets: list[StatItem] = []
    best_leagues: list[StatItem] = []
    best_teams: list[StatItem] = []
    odds_buckets: list[BucketStat] = []
    edge_buckets: list[BucketStat] = []
    confidence_buckets: list[BucketStat] = []
    daily_profit_series: list[dict[str, Any]] = []

class GlobalStatsOut(BaseModel):
    total_matches: int
    total_matches_with_results: int
    total_picks: int
    total_hits: int
    total_pending: int = 0
    global_accuracy: float
    sport_stats: dict[str, Any]
    total_exact_scores_predicted: int = 0
    total_exact_scores_hits: int = 0
    avg_odds: float = 0.0
    avg_winning_odds: float = 0.0
    total_profit: float = 0.0
    roi: float = 0.0
    daily_profit_series: list[dict[str, Any]] = []
    best_markets: list[StatItem] = []
    worst_markets: list[StatItem] = []
    best_leagues: list[StatItem] = []
    best_teams: list[StatItem] = []
    odds_buckets: list[BucketStat] = []
    edge_buckets: list[BucketStat] = []
    confidence_buckets: list[BucketStat] = []
    category_stats: dict[str, CategoryStatsOut] = {}

class PickStat(BaseModel):
    match_id: str
    match_title: str
    sport: str
    date: datetime
    selection: str
    market: str
    line: float | None
    odds: float
    success: bool | str | None = None
    is_value: bool
    is_high_confidence: bool = False
    is_underdog: bool = False
    count_in_profitability: bool = True
    
    # Nuevas métricas quant
    calibrated_prob: float | None = None
    edge_ev: float | None = None
    display_score: float | None = None
    fair_odds: float | None = None
    kelly_fraction: float | None = None
    stat_support: float | None = None
    proj_support: float | None = None

