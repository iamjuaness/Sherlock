"""Domain model – common entities for all sports.

All datasource adapters map their API responses to these entities.
No API-specific formats should leak beyond the datasources layer.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Sport(str, enum.Enum):
    FOOTBALL = "football"
    NBA = "nba"
    BASKETBALL = "basketball"
    TENNIS = "tennis"


class MarketType(str, enum.Enum):
    MONEYLINE = "moneyline"
    OVER_UNDER = "over_under"
    HANDICAP = "handicap"


class Surface(str, enum.Enum):
    """Tennis court surface."""

    HARD = "hard"
    CLAY = "clay"
    GRASS = "grass"
    INDOOR = "indoor"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------


class Competition(Base):
    """League, tournament or cup."""

    __tablename__ = "competitions"

    id = Column(String(36), primary_key=True, default=_new_id)
    sport = Column(Enum(Sport), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    country = Column(String(100), nullable=True)
    season = Column(String(20), nullable=True)
    external_id = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)

    matches = relationship("Match", back_populates="competition")

    __table_args__ = (
        UniqueConstraint("sport", "name", "season", name="uq_competition_sport_name_season"),
    )

    def __repr__(self) -> str:
        return f"<Competition {self.name} ({self.sport.value}, {self.season})>"


class Team(Base):
    """Team (football/basketball) or player-as-team for tennis."""

    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=_new_id)
    sport = Column(Enum(Sport), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    logo_url = Column(Text, nullable=True)
    external_id = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("sport", "name", name="uq_team_sport_name"),
    )

    def __repr__(self) -> str:
        return f"<Team {self.name} ({self.sport.value})>"


class Player(Base):
    """Individual player."""

    __tablename__ = "players"

    id = Column(String(36), primary_key=True, default=_new_id)
    sport = Column(Enum(Sport), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    nationality = Column(String(100), nullable=True)
    position = Column(String(50), nullable=True)
    external_id = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)

    team = relationship("Team")

    def __repr__(self) -> str:
        return f"<Player {self.name} ({self.sport.value})>"


class Match(Base):
    """A single fixture / game between two teams or players."""

    __tablename__ = "matches"

    id = Column(String(36), primary_key=True, default=_new_id)
    sport = Column(Enum(Sport), nullable=False, index=True)
    competition_id = Column(String(36), ForeignKey("competitions.id"), nullable=True)
    date = Column(DateTime, nullable=False, index=True)

    home_team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    status = Column(String(30), nullable=True, default="scheduled")
    venue = Column(String(200), nullable=True)
    round = Column(String(50), nullable=True)

    # Tennis-specific
    surface = Column(Enum(Surface), nullable=True)

    external_id = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)

    competition = relationship("Competition", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    betting_lines = relationship("BettingLine", back_populates="match")
    stat_lines_team = relationship("StatLineTeam", back_populates="match")
    stat_lines_player = relationship("StatLinePlayer", back_populates="match")

    __table_args__ = (
        UniqueConstraint("sport", "external_id", "source", name="uq_match_ext"),
    )

    def __repr__(self) -> str:
        return f"<Match {self.date} {self.sport.value}>"


class BettingLine(Base):
    """A single betting market line for a match."""

    __tablename__ = "betting_lines"

    id = Column(String(36), primary_key=True, default=_new_id)
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=False, index=True)

    market_type = Column(Enum(MarketType), nullable=False)
    selection = Column(String(50), nullable=False)  # e.g. "home", "away", "over", "under"
    line = Column(Float, nullable=True)  # e.g. 2.5 for over/under, -1.5 for handicap
    odds = Column(Float, nullable=False)
    bookmaker = Column(String(100), nullable=True)
    timestamp = Column(DateTime, nullable=True, default=datetime.utcnow)

    match = relationship("Match", back_populates="betting_lines")

    def __repr__(self) -> str:
        return f"<BettingLine {self.market_type.value} {self.selection} @ {self.odds}>"


class StatLineTeam(Base):
    """Aggregated team stats for a single match."""

    __tablename__ = "stat_lines_team"

    id = Column(String(36), primary_key=True, default=_new_id)
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=False, index=True)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)

    # Common stats (nullable – not all sports have all stats)
    shots = Column(Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    possession = Column(Float, nullable=True)
    fouls = Column(Integer, nullable=True)
    corners = Column(Integer, nullable=True)
    offsides = Column(Integer, nullable=True)

    # Basketball-specific
    rebounds = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    turnovers = Column(Integer, nullable=True)
    field_goal_pct = Column(Float, nullable=True)
    three_point_pct = Column(Float, nullable=True)
    free_throw_pct = Column(Float, nullable=True)

    match = relationship("Match", back_populates="stat_lines_team")
    team = relationship("Team")

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", name="uq_stat_team_match"),
    )

    def __repr__(self) -> str:
        return f"<StatLineTeam match={self.match_id} team={self.team_id}>"


class StatLinePlayer(Base):
    """Individual player stats for a single match."""

    __tablename__ = "stat_lines_player"

    id = Column(String(36), primary_key=True, default=_new_id)
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=False, index=True)
    player_id = Column(String(36), ForeignKey("players.id"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)

    minutes_played = Column(Integer, nullable=True)
    points = Column(Integer, nullable=True)
    goals = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    rebounds = Column(Integer, nullable=True)
    steals = Column(Integer, nullable=True)
    blocks = Column(Integer, nullable=True)
    turnovers = Column(Integer, nullable=True)
    field_goal_pct = Column(Float, nullable=True)

    # Tennis-specific
    aces = Column(Integer, nullable=True)
    double_faults = Column(Integer, nullable=True)
    first_serve_pct = Column(Float, nullable=True)
    break_points_won = Column(Integer, nullable=True)

    match = relationship("Match", back_populates="stat_lines_player")
    player = relationship("Player")
    team = relationship("Team")

    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_stat_player_match"),
    )

    def __repr__(self) -> str:
        return f"<StatLinePlayer match={self.match_id} player={self.player_id}>"


class AnalysisHistory(Base):
    """History of manual analyses performed in the comparator."""

    __tablename__ = "analysis_history"

    id = Column(String(36), primary_key=True, default=_new_id)
    sport = Column(Enum(Sport), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    match_title = Column(String(200), nullable=False)  # e.g. "Real Madrid vs Barcelona"
    payload = Column(Text, nullable=False)  # JSON blob of the form data

    def __repr__(self) -> str:
        return f"<AnalysisHistory {self.match_title} ({self.date})>"
