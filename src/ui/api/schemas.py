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
    accuracy_percentage: float | None = None
    has_picks: bool = False
    picks_hits_summary: str | None = None # e.g. "2/3"

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
class GlobalStatsOut(BaseModel):
    total_matches: int
    total_matches_with_results: int
    total_picks: int
    total_hits: int
    global_accuracy: float
    sport_stats: dict[str, Any]

class PickStat(BaseModel):
    match_id: str
    match_title: str
    sport: str
    date: datetime
    selection: str
    market: str
    line: float | None
    odds: float
    success: bool | None
    is_value: bool
