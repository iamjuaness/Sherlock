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


class AnalysisHistoryOut(BaseModel):
    id: str
    sport: str
    date: datetime
    match_title: str
    payload: Any

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v

    class Config:
        from_attributes = True
