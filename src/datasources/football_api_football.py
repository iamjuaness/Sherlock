"""API-Football (api-sports.io) adapter for football data.

Docs: https://www.api-football.com/documentation-v3
Free plan: 100 requests/day, 10 req/min.
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
    Sport,
    StatLinePlayer,
    StatLineTeam,
    Team,
)
from src.datasources.base import DataSourceAdapter

logger = logging.getLogger(__name__)

SOURCE_NAME = "api_football"


class FootballApiFootballAdapter(DataSourceAdapter):
    """Adapter for API-Football v3."""

    def __init__(self) -> None:
        self._base_url = settings.api_football_base_url
        self._headers = {
            "x-apisports-key": settings.api_football_key,
        }

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
        """Fetch football leagues.

        kwargs:
            country (str): filter by country name.
            season (int): filter by season year (e.g. 2024).
        """
        params: dict[str, Any] = {}
        if "country" in kwargs:
            params["country"] = kwargs["country"]
        if "season" in kwargs:
            params["season"] = kwargs["season"]

        async with self._client() as client:
            resp = await client.get("/leagues", params=params)
            resp.raise_for_status()
            data = resp.json()

        competitions: list[Competition] = []
        for item in data.get("response", []):
            league = item.get("league", {})
            country_info = item.get("country", {})
            seasons = item.get("seasons", [])
            season_str = str(seasons[-1]["year"]) if seasons else None

            comp = Competition(
                sport=Sport.FOOTBALL,
                name=league.get("name", ""),
                country=country_info.get("name"),
                season=season_str,
                external_id=str(league.get("id", "")),
                source=SOURCE_NAME,
            )
            competitions.append(comp)

        logger.info("API-Football: fetched %d competitions", len(competitions))
        return competitions

    # ------------------------------------------------------------------
    # Matches
    # ------------------------------------------------------------------

    async def fetch_matches(
        self,
        competition_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **kwargs: Any,
    ) -> list[Match]:
        """Fetch fixtures from API-Football.

        kwargs:
            season (int): season year.
            league (int): API-Football league ID.
        """
        params: dict[str, Any] = {}
        if competition_id:
            params["league"] = competition_id
        if "season" in kwargs:
            params["season"] = kwargs["season"]
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to

        async with self._client() as client:
            resp = await client.get("/fixtures", params=params)
            resp.raise_for_status()
            data = resp.json()

        matches: list[Match] = []
        for item in data.get("response", []):
            fixture = item.get("fixture", {})
            teams_data = item.get("teams", {})
            goals = item.get("goals", {})
            league = item.get("league", {})

            match_date = datetime.fromisoformat(
                fixture.get("date", "").replace("Z", "+00:00")
            )

            home_team = Team(
                sport=Sport.FOOTBALL,
                name=teams_data.get("home", {}).get("name", ""),
                logo_url=teams_data.get("home", {}).get("logo"),
                external_id=str(teams_data.get("home", {}).get("id", "")),
                source=SOURCE_NAME,
            )
            away_team = Team(
                sport=Sport.FOOTBALL,
                name=teams_data.get("away", {}).get("name", ""),
                logo_url=teams_data.get("away", {}).get("logo"),
                external_id=str(teams_data.get("away", {}).get("id", "")),
                source=SOURCE_NAME,
            )

            match = Match(
                sport=Sport.FOOTBALL,
                date=match_date,
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                status=fixture.get("status", {}).get("short", "NS"),
                venue=fixture.get("venue", {}).get("name"),
                round=league.get("round"),
                external_id=str(fixture.get("id", "")),
                source=SOURCE_NAME,
            )
            # Attach team objects for later persistence (caller resolves IDs)
            match._home_team_obj = home_team  # type: ignore[attr-defined]
            match._away_team_obj = away_team  # type: ignore[attr-defined]
            match._competition_name = league.get("name")  # type: ignore[attr-defined]
            matches.append(match)

        logger.info("API-Football: fetched %d matches", len(matches))
        return matches

    # ------------------------------------------------------------------
    # Team stats
    # ------------------------------------------------------------------

    async def fetch_team_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLineTeam]:
        """Fetch team statistics for a fixture.

        kwargs:
            fixture (int): API-Football fixture ID.
        """
        fixture_id = match_id or kwargs.get("fixture")
        if not fixture_id:
            return []

        async with self._client() as client:
            resp = await client.get("/fixtures/statistics", params={"fixture": fixture_id})
            resp.raise_for_status()
            data = resp.json()

        stat_lines: list[StatLineTeam] = []
        for team_stats in data.get("response", []):
            team_info = team_stats.get("team", {})
            stats_raw = {s["type"]: s["value"] for s in team_stats.get("statistics", [])}

            stat = StatLineTeam(
                team_id=None,  # resolved by caller
                shots=_safe_int(stats_raw.get("Total Shots")),
                shots_on_target=_safe_int(stats_raw.get("Shots on Goal")),
                possession=_safe_float(stats_raw.get("Ball Possession")),
                fouls=_safe_int(stats_raw.get("Fouls")),
                corners=_safe_int(stats_raw.get("Corner Kicks")),
                offsides=_safe_int(stats_raw.get("Offsides")),
            )
            stat._team_external_id = str(team_info.get("id", ""))  # type: ignore[attr-defined]
            stat_lines.append(stat)

        logger.info("API-Football: fetched %d team stat lines for fixture %s", len(stat_lines), fixture_id)
        return stat_lines

    # ------------------------------------------------------------------
    # Player stats (not available on free plan, stub)
    # ------------------------------------------------------------------

    async def fetch_player_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLinePlayer]:
        """Player stats require a premium plan on API-Football.

        Returns an empty list on the free plan.
        """
        logger.info("API-Football: player stats require premium plan – skipping")
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace("%", ""))
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace("%", ""))
    except (ValueError, TypeError):
        return None
