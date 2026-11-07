"""Golden test: compare_football output must not change during refactor.

First run (no golden file) writes tests/golden/compare_football_golden.json.
Later runs compare against it. Uses in-memory SQLite, never data/sherlock.db.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.database import Base
from src.ui.api.compare_service import compare_football
from src.ui.api.compare_models import (
    FootballCompareRequest,
    FootballOdds,
    FootballTeamStats,
    LeagueStats,
)

GOLDEN = Path(__file__).parent / "compare_football_golden.json"


def _build_request() -> FootballCompareRequest:
    home = FootballTeamStats(
        name="Real Madrid",
        matches_played=10,
        matches_home=5,
        matches_away=5,
        goals_per_game=2.1,
        goals_conceded_per_game=0.9,
        corners_per_game=6.2,
        corners_conceded_per_game=3.8,
        yellow_cards_per_game=1.8,
        red_cards_total=0,
    )
    away = FootballTeamStats(
        name="Barcelona",
        matches_played=10,
        matches_home=5,
        matches_away=5,
        goals_per_game=2.0,
        goals_conceded_per_game=1.1,
        corners_per_game=5.5,
        corners_conceded_per_game=4.2,
        yellow_cards_per_game=2.2,
        red_cards_total=1,
    )
    league = LeagueStats(
        name="La Liga",
        avg_goals_per_game=2.6,
        avg_corners_per_game=9.5,
        avg_yellow_cards_per_game=4.2,
        avg_red_cards_per_game=0.2,
        home_advantage_factor=1.15,
        away_disadvantage_factor=0.88,
    )
    odds = FootballOdds(
        home=2.10,
        draw=3.40,
        away=3.20,
        btts_yes=1.65,
        btts_no=2.20,
        goals_lines=[2.5],
        goals_over_odds={"2.5": 1.75},
        goals_under_odds={"2.5": 2.10},
    )
    return FootballCompareRequest(
        sport="football",
        competition="La Liga",
        home=home,
        away=away,
        league_stats=league,
        odds=odds,
    )


def _run() -> dict:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        response = asyncio.run(compare_football(_build_request(), db=db))
    data = json.loads(response.model_dump_json())
    for value in data.get("values", []):
        value["predicted_at_utc"] = None  # wall-clock, not part of the model output
    return data


def test_compare_football_matches_golden():
    current = _run()
    if not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(current, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
        )
        pytest.skip("golden baseline written; rerun to compare")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert current == expected
