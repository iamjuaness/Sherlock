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
    String,
    UniqueConstraint,
    Integer,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship

from src.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Sport(str, enum.Enum):
    FOOTBALL = "football"

class MarketType(str, enum.Enum):
    MONEYLINE = "moneyline"
    OVER_UNDER = "over_under"
    HANDICAP = "handicap"


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
    """Team (football) or player-as-team."""

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
    corners_conceded = Column(Integer, nullable=True)
    offsides = Column(Integer, nullable=True)

    # Football-specific (detailed)
    yellow_cards = Column(Integer, nullable=True)
    red_cards = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    big_chances = Column(Integer, nullable=True)
    xg = Column(Float, default=0)  # Goles esperados
    xga = Column(Float, nullable=True)
    passes = Column(Integer, nullable=True)
    passes_accurate = Column(Integer, nullable=True)

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
    match_date = Column(DateTime, nullable=True, index=True)
    match_title = Column(String(200), nullable=False)  # e.g. "Real Madrid vs Barcelona"
    payload = Column(Text, nullable=False)  # JSON blob of the form data

    # Persistence & LLM
    picks_calculados = Column(Text, nullable=True)  # JSON blob
    user_context = Column(Text, nullable=True)
    llm_response = Column(Text, nullable=True)
    llm_timestamp = Column(DateTime, nullable=True)
    compare_response_snapshot = Column(Text, nullable=True)
    needs_reanalysis = Column(Boolean, default=False)

    # Final Results
    final_score_home = Column(Integer, nullable=True)
    final_score_away = Column(Integer, nullable=True)
    final_corners_home = Column(Integer, nullable=True)
    final_corners_away = Column(Integer, nullable=True)
    final_yellow_cards_home = Column(Integer, nullable=True)
    final_yellow_cards_away = Column(Integer, nullable=True)
    final_red_cards_home = Column(Integer, nullable=True)
    final_red_cards_away = Column(Integer, nullable=True)
    final_shots_home = Column(Integer, nullable=True)
    final_shots_away = Column(Integer, nullable=True)
    final_shots_on_target_home = Column(Integer, nullable=True)
    final_shots_on_target_away = Column(Integer, nullable=True)
    final_fouls_home = Column(Integer, nullable=True)
    final_fouls_away = Column(Integer, nullable=True)
    final_offsides_home = Column(Integer, nullable=True)
    final_offsides_away = Column(Integer, nullable=True)
    accuracy_percentage = Column(Float, nullable=True)
    count_in_profitability = Column(Boolean, default=True, nullable=False, server_default="1")
    has_real_stats = Column(Boolean, default=True, nullable=False, server_default="1")

    def __repr__(self) -> str:
        return f"<AnalysisHistory {self.match_title} ({self.date})>"