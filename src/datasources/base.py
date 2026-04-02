"""Abstract base class for all datasource adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.domain import Competition, Match, Player, StatLinePlayer, StatLineTeam, Team


class DataSourceAdapter(ABC):
    """Contract that every datasource must implement.

    Each method returns domain entities ready for persistence.
    Adapters are responsible for mapping external API responses
    to the shared domain model.
    """

    @abstractmethod
    async def fetch_competitions(self, **kwargs: Any) -> list[Competition]:
        """Fetch available leagues / tournaments / cups."""
        ...

    @abstractmethod
    async def fetch_matches(
        self,
        competition_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **kwargs: Any,
    ) -> list[Match]:
        """Fetch matches/fixtures with optional filters."""
        ...

    @abstractmethod
    async def fetch_team_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLineTeam]:
        """Fetch team-level stats for a match or season."""
        ...

    @abstractmethod
    async def fetch_player_stats(
        self, match_id: str | None = None, **kwargs: Any
    ) -> list[StatLinePlayer]:
        """Fetch player-level stats for a match or season."""
        ...
