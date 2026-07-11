"""Manual data loader for CSV and Excel files.

Maps tabular data to the shared domain model.
Required columns documented in docs/APIS.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.domain import (
    BettingLine,
    Competition,
    MarketType,
    Match,
    Sport,
    StatLinePlayer,
    StatLineTeam,
    Team,
)
from src.datasources.base import DataSourceAdapter

logger = logging.getLogger(__name__)

SOURCE_NAME = "manual"

# Required columns for match import
REQUIRED_COLUMNS = {"sport", "competition", "date", "home_team", "away_team"}


class ManualLoaderAdapter(DataSourceAdapter):
    """CSV / Excel file loader that maps tabular data to domain entities."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)
        self._df: pd.DataFrame | None = None

    def _load(self) -> pd.DataFrame:
        """Load the file into a DataFrame."""
        if self._df is not None:
            return self._df

        suffix = self._file_path.suffix.lower()
        if suffix == ".csv":
            self._df = pd.read_csv(self._file_path)
        elif suffix in (".xlsx", ".xls"):
            self._df = pd.read_excel(self._file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .xlsx")

        # Normalize column names
        self._df.columns = [c.strip().lower().replace(" ", "_") for c in self._df.columns]

        # Validate required columns
        missing = REQUIRED_COLUMNS - set(self._df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        logger.info("ManualLoader: loaded %d rows from %s", len(self._df), self._file_path.name)
        return self._df

    def _parse_sport(self, value: str) -> Sport:
        mapping = {
            "football": Sport.FOOTBALL,
            "soccer": Sport.FOOTBALL,
            "fútbol": Sport.FOOTBALL,
            "futbol": Sport.FOOTBALL,
        }
        return mapping.get(value.strip().lower(), Sport.FOOTBALL)

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    async def fetch_competitions(self, **kwargs: Any) -> list[Competition]:
        df = self._load()
        comps: list[Competition] = []
        seen: set[tuple[str, str]] = set()

        for _, row in df.iterrows():
            sport = self._parse_sport(str(row["sport"]))
            name = str(row["competition"]).strip()
            key = (sport.value, name)
            if key not in seen:
                seen.add(key)
                comps.append(
                    Competition(sport=sport, name=name, source=SOURCE_NAME)
                )

        logger.info("ManualLoader: found %d unique competitions", len(comps))
        return comps

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
        df = self._load()
        matches: list[Match] = []

        for idx, row in df.iterrows():
            sport = self._parse_sport(str(row["sport"]))

            # Parse date
            try:
                match_date = pd.to_datetime(row["date"]).to_pydatetime()
            except Exception:
                logger.warning("ManualLoader: invalid date in row %d, skipping", idx)
                continue

            # Date filters
            if date_from and match_date < datetime.fromisoformat(date_from):
                continue
            if date_to and match_date > datetime.fromisoformat(date_to):
                continue

            home_team = Team(
                sport=sport,
                name=str(row["home_team"]).strip(),
                source=SOURCE_NAME,
            )
            away_team = Team(
                sport=sport,
                name=str(row["away_team"]).strip(),
                source=SOURCE_NAME,
            )

            match = Match(
                sport=sport,
                date=match_date,
                home_score=_safe_int(row.get("home_score")),
                away_score=_safe_int(row.get("away_score")),
                venue=str(row.get("venue", "")) if pd.notna(row.get("venue")) else None,
                round=str(row.get("round", "")) if pd.notna(row.get("round")) else None,
                source=SOURCE_NAME,
            )
            match._home_team_obj = home_team  # type: ignore[attr-defined]
            match._away_team_obj = away_team  # type: ignore[attr-defined]
            match._competition_name = str(row["competition"]).strip()  # type: ignore[attr-defined]

            # Parse betting lines if present
            betting_lines: list[BettingLine] = []
            bookmaker = str(row.get("bookmaker", "")) if pd.notna(row.get("bookmaker")) else None

            if pd.notna(row.get("odds_home")):
                betting_lines.append(
                    BettingLine(
                        market_type=MarketType.MONEYLINE,
                        selection="home",
                        odds=float(row["odds_home"]),
                        bookmaker=bookmaker,
                    )
                )
            if pd.notna(row.get("odds_draw")):
                betting_lines.append(
                    BettingLine(
                        market_type=MarketType.MONEYLINE,
                        selection="draw",
                        odds=float(row["odds_draw"]),
                        bookmaker=bookmaker,
                    )
                )
            if pd.notna(row.get("odds_away")):
                betting_lines.append(
                    BettingLine(
                        market_type=MarketType.MONEYLINE,
                        selection="away",
                        odds=float(row["odds_away"]),
                        bookmaker=bookmaker,
                    )
                )
            if pd.notna(row.get("over_under_line")) and pd.notna(row.get("over_odds")):
                betting_lines.append(
                    BettingLine(
                        market_type=MarketType.OVER_UNDER,
                        selection="over",
                        line=float(row["over_under_line"]),
                        odds=float(row["over_odds"]),
                        bookmaker=bookmaker,
                    )
                )
            if pd.notna(row.get("over_under_line")) and pd.notna(row.get("under_odds")):
                betting_lines.append(
                    BettingLine(
                        market_type=MarketType.OVER_UNDER,
                        selection="under",
                        line=float(row["over_under_line"]),
                        odds=float(row["under_odds"]),
                        bookmaker=bookmaker,
                    )
                )

            match._betting_lines = betting_lines  # type: ignore[attr-defined]
            matches.append(match)

        logger.info("ManualLoader: parsed %d matches", len(matches))
        return matches

    # ------------------------------------------------------------------
    # Stats (not available from manual files by default)
    # ------------------------------------------------------------------


def _safe_int(value: Any) -> int | None:
    if value is None or (hasattr(value, "__class__") and pd.isna(value)):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
