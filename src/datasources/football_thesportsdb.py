"""TheSportsDB adapter for football data (fallback).

Docs: https://www.thesportsdb.com/api.php
Free API with demo key '3'.
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

SOURCE_NAME = "thesportsdb"


class FootballTheSportsDBAdapter(DataSourceAdapter):
    """Adapter for TheSportsDB – football leagues and events."""

    def __init__(self) -> None:
        self._base_url = settings.thesportsdb_base_url

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def fetch_competitions(self, **kwargs: Any) -> list[Competition]:
        """Fetch football leagues from TheSportsDB."""
        async with self._client() as client:
            resp = await client.get("/searchallleagues.php", params={"s": "Soccer"})
            resp.raise_for_status()
            data = resp.json()

        competitions: list[Competition] = []
        for item in data.get("countrys", []) or []:
            comp = Competition(
                sport=Sport.FOOTBALL,
                name=item.get("strLeague", ""),
                country=item.get("strCountry"),
                external_id=str(item.get("idLeague", "")),
                source=SOURCE_NAME,
            )
            competitions.append(comp)

        logger.info("TheSportsDB (football): fetched %d competitions", len(competitions))
        return competitions

    async def fetch_matches(
        self,
        competition_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **kwargs: Any,
    ) -> list[Match]:
        """Fetch events for a league season.

        kwargs:
            season (str): e.g. '2024-2025'.
        """
        if not competition_id:
            return []

        season = kwargs.get("season", "2024-2025")
        async with self._client() as client:
            resp = await client.get(
                "/eventsseason.php",
                params={"id": competition_id, "s": season},
            )
            resp.raise_for_status()
            data = resp.json()

        matches: list[Match] = []
        for item in data.get("events", []) or []:
            date_str = item.get("dateEvent", "")
            time_str = item.get("strTime", "00:00:00")
            try:
                match_date = datetime.fromisoformat(f"{date_str}T{time_str}")
            except ValueError:
                match_date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()

            home_team = Team(
                sport=Sport.FOOTBALL,
                name=item.get("strHomeTeam", ""),
                external_id=str(item.get("idHomeTeam", "")),
                source=SOURCE_NAME,
            )
            away_team = Team(
                sport=Sport.FOOTBALL,
                name=item.get("strAwayTeam", ""),
                external_id=str(item.get("idAwayTeam", "")),
                source=SOURCE_NAME,
            )

            match = Match(
                sport=Sport.FOOTBALL,
                date=match_date,
                home_score=_safe_int(item.get("intHomeScore")),
                away_score=_safe_int(item.get("intAwayScore")),
                status="FT" if item.get("intHomeScore") is not None else "NS",
                venue=item.get("strVenue"),
                round=item.get("intRound"),
                external_id=str(item.get("idEvent", "")),
                source=SOURCE_NAME,
            )
            match._home_team_obj = home_team  # type: ignore[attr-defined]
            match._away_team_obj = away_team  # type: ignore[attr-defined]
            matches.append(match)

        logger.info("TheSportsDB (football): fetched %d matches", len(matches))
        return matches

    async def fetch_team_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLineTeam]:
        """TheSportsDB doesn't provide detailed team match stats."""
        logger.info("TheSportsDB: no detailed team stats available")
        return []

    async def fetch_player_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLinePlayer]:
        """TheSportsDB doesn't provide detailed player match stats."""
        logger.info("TheSportsDB: no detailed player stats available")
        return []


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
