"""BallDontLie API adapter for NBA data.

Docs: https://www.balldontlie.io/
Free tier: 30 req/min.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from src.config import settings
from src.core.domain import (
    Competition,
    Match,
    Player,
    Sport,
    StatLinePlayer,
    StatLineTeam,
    Team,
)
from src.datasources.base import DataSourceAdapter

logger = logging.getLogger(__name__)

SOURCE_NAME = "balldontlie"

# NBA is a single competition – we create a virtual one.
NBA_COMPETITION_NAME = "NBA"


class NBABallDontLieAdapter(DataSourceAdapter):
    """Adapter for BallDontLie API (NBA)."""

    def __init__(self) -> None:
        self._base_url = settings.balldontlie_base_url
        self._headers: dict[str, str] = {}
        if settings.balldontlie_api_key:
            self._headers["Authorization"] = settings.balldontlie_api_key

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    async def fetch_competitions(self, **kwargs: Any) -> list[Competition]:
        """NBA is a single competition."""
        season = kwargs.get("season", "2024")
        return [
            Competition(
                sport=Sport.BASKETBALL,
                name=NBA_COMPETITION_NAME,
                country="USA",
                season=str(season),
                external_id="nba",
                source=SOURCE_NAME,
            )
        ]

    # ------------------------------------------------------------------
    # Matches (games)
    # ------------------------------------------------------------------

    async def fetch_matches(
        self,
        competition_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **kwargs: Any,
    ) -> list[Match]:
        """Fetch NBA games.

        kwargs:
            season (int): NBA season year.
            per_page (int): results per page (max 100).
        """
        params: dict[str, Any] = {"per_page": kwargs.get("per_page", 100)}
        if "season" in kwargs:
            params["seasons[]"] = kwargs["season"]
        if date_from:
            params["start_date"] = date_from
        if date_to:
            params["end_date"] = date_to

        async with self._client() as client:
            resp = await client.get("/games", params=params)
            resp.raise_for_status()
            data = resp.json()

        matches: list[Match] = []
        for item in data.get("data", []):
            game_date_str = item.get("date", "")
            try:
                game_date = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
            except ValueError:
                game_date = datetime.utcnow()

            home_data = item.get("home_team", {})
            away_data = item.get("visitor_team", {})

            home_team = Team(
                sport=Sport.BASKETBALL,
                name=home_data.get("full_name", ""),
                short_name=home_data.get("abbreviation"),
                country="USA",
                external_id=str(home_data.get("id", "")),
                source=SOURCE_NAME,
            )
            away_team = Team(
                sport=Sport.BASKETBALL,
                name=away_data.get("full_name", ""),
                short_name=away_data.get("abbreviation"),
                country="USA",
                external_id=str(away_data.get("id", "")),
                source=SOURCE_NAME,
            )

            match = Match(
                sport=Sport.BASKETBALL,
                date=game_date,
                home_score=item.get("home_team_score"),
                away_score=item.get("visitor_team_score"),
                status="FT" if item.get("status") == "Final" else item.get("status", "NS"),
                external_id=str(item.get("id", "")),
                source=SOURCE_NAME,
            )
            match._home_team_obj = home_team  # type: ignore[attr-defined]
            match._away_team_obj = away_team  # type: ignore[attr-defined]
            match._competition_name = NBA_COMPETITION_NAME  # type: ignore[attr-defined]
            matches.append(match)

        logger.info("BallDontLie: fetched %d NBA games", len(matches))
        return matches

    # ------------------------------------------------------------------
    # Team stats (derived from game scores – no team stats endpoint)
    # ------------------------------------------------------------------

    async def fetch_team_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLineTeam]:
        """BallDontLie doesn't provide team-level stats per game directly."""
        logger.info("BallDontLie: team stats derived from player stats – not implemented yet")
        return []

    # ------------------------------------------------------------------
    # Player stats
    # ------------------------------------------------------------------

    async def fetch_player_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLinePlayer]:
        """Fetch player stats from BallDontLie.

        kwargs:
            game_id (int): BallDontLie game ID.
            season (int): season year.
            per_page (int): results per page.
        """
        params: dict[str, Any] = {"per_page": kwargs.get("per_page", 100)}
        if match_id:
            params["game_ids[]"] = match_id
        if "season" in kwargs:
            params["seasons[]"] = kwargs["season"]

        async with self._client() as client:
            resp = await client.get("/stats", params=params)
            resp.raise_for_status()
            data = resp.json()

        stat_lines: list[StatLinePlayer] = []
        for item in data.get("data", []):
            player_data = item.get("player", {})
            team_data = item.get("team", {})

            player = Player(
                sport=Sport.BASKETBALL,
                name=f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip(),
                position=player_data.get("position"),
                external_id=str(player_data.get("id", "")),
                source=SOURCE_NAME,
            )

            stat = StatLinePlayer(
                minutes_played=_parse_minutes(item.get("min")),
                points=item.get("pts"),
                rebounds=item.get("reb"),
                assists=item.get("ast"),
                steals=item.get("stl"),
                blocks=item.get("blk"),
                turnovers=item.get("turnover"),
                field_goal_pct=item.get("fg_pct"),
            )
            stat._player_obj = player  # type: ignore[attr-defined]
            stat._team_external_id = str(team_data.get("id", ""))  # type: ignore[attr-defined]
            stat_lines.append(stat)

        logger.info("BallDontLie: fetched %d player stat lines", len(stat_lines))
        return stat_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_minutes(value: Any) -> int | None:
    """Parse minutes string (e.g. '36:12') to integer minutes."""
    if value is None:
        return None
    try:
        if isinstance(value, str) and ":" in value:
            return int(value.split(":")[0])
        return int(value)
    except (ValueError, TypeError):
        return None
