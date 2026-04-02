"""TheSportsDB adapter for tennis data (ATP/WTA basic results).

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
    Surface,
    Team,
)
from src.datasources.base import DataSourceAdapter

logger = logging.getLogger(__name__)

SOURCE_NAME = "thesportsdb_tennis"

# Surface mapping from event venue / description
_SURFACE_MAP = {
    "hard": Surface.HARD,
    "clay": Surface.CLAY,
    "grass": Surface.GRASS,
    "indoor": Surface.INDOOR,
}


class TennisTheSportsDBAdapter(DataSourceAdapter):
    """Adapter for TheSportsDB – tennis tournaments and results."""

    def __init__(self) -> None:
        self._base_url = settings.thesportsdb_base_url

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def fetch_competitions(self, **kwargs: Any) -> list[Competition]:
        """Fetch tennis tournaments (ATP/WTA)."""
        async with self._client() as client:
            resp = await client.get("/searchallleagues.php", params={"s": "Tennis"})
            resp.raise_for_status()
            data = resp.json()

        competitions: list[Competition] = []
        for item in data.get("countrys", []) or []:
            comp = Competition(
                sport=Sport.TENNIS,
                name=item.get("strLeague", ""),
                country=item.get("strCountry"),
                external_id=str(item.get("idLeague", "")),
                source=SOURCE_NAME,
            )
            competitions.append(comp)

        logger.info("TheSportsDB (tennis): fetched %d competitions", len(competitions))
        return competitions

    async def fetch_matches(
        self,
        competition_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **kwargs: Any,
    ) -> list[Match]:
        """Fetch tennis events for a tournament season.

        kwargs:
            season (str): e.g. '2024'.
        """
        if not competition_id:
            return []

        season = kwargs.get("season", "2024")
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

            # In tennis, "home" = player 1, "away" = player 2
            player1 = Team(
                sport=Sport.TENNIS,
                name=item.get("strHomeTeam", ""),
                external_id=str(item.get("idHomeTeam", "")),
                source=SOURCE_NAME,
            )
            player2 = Team(
                sport=Sport.TENNIS,
                name=item.get("strAwayTeam", ""),
                external_id=str(item.get("idAwayTeam", "")),
                source=SOURCE_NAME,
            )

            # Try to detect surface from venue description
            venue = item.get("strVenue", "") or ""
            surface = _detect_surface(venue)

            match = Match(
                sport=Sport.TENNIS,
                date=match_date,
                home_score=_safe_int(item.get("intHomeScore")),
                away_score=_safe_int(item.get("intAwayScore")),
                status="FT" if item.get("intHomeScore") is not None else "NS",
                venue=venue,
                round=item.get("intRound"),
                surface=surface,
                external_id=str(item.get("idEvent", "")),
                source=SOURCE_NAME,
            )
            match._home_team_obj = player1  # type: ignore[attr-defined]
            match._away_team_obj = player2  # type: ignore[attr-defined]
            matches.append(match)

        logger.info("TheSportsDB (tennis): fetched %d matches", len(matches))
        return matches

    async def fetch_team_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLineTeam]:
        """TheSportsDB doesn't provide tennis match stats."""
        return []

    async def fetch_player_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLinePlayer]:
        """TheSportsDB doesn't provide detailed tennis player stats."""
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_surface(venue: str) -> Surface:
    venue_lower = venue.lower()
    for keyword, surface in _SURFACE_MAP.items():
        if keyword in venue_lower:
            return surface
    return Surface.UNKNOWN


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
