import json
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.domain import AnalysisHistory, Base, Sport
from src.core.home_away_stats import apply_split, compute_team_split
from src.core.season_resolver import norm_season_year, same_season, season_key
from src.ui.api.compare_models import FootballTeamStats


@pytest.fixture()
def db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    yield s
    s.close()


def _row(db, home, away, day, score, season_id="100", season_year="2025", corners=(5, 4), **extra):
    payload = {"season_id": season_id, "season_year": season_year}
    payload.update(extra)
    db.add(
        AnalysisHistory(
            sport=Sport.FOOTBALL,
            match_date=datetime(2025, 3, day),
            match_title=f"{home} vs {away}",
            payload=json.dumps(payload),
            final_score_home=score[0],
            final_score_away=score[1],
            final_corners_home=corners[0],
            final_corners_away=corners[1],
        )
    )


def test_season_helpers():
    assert norm_season_year("26/27") == "2026/2027"
    assert season_key(None, None, None) is None
    assert season_key(70681, "2025") == ("id", "70681")
    assert not same_season(None, None)
    assert not same_season(("id", "1"), ("year", "1"))


def test_split_only_role_season_and_cutoff(db):
    for d in range(1, 6):
        _row(db, "Alfa", "Beta", d, (2, 1))  # Alfa local, temporada 100
    _row(db, "Beta", "Alfa", 6, (0, 3), corners=(9, 9))  # Alfa visitante: no cuenta como local
    _row(db, "Alfa", "Beta", 7, (9, 9), season_id="99", season_year="2024")  # otra temporada
    _row(db, "Alfa", "Beta", 20, (7, 7))  # posterior al corte
    db.commit()
    tgt = season_key("100", "2025")

    s = compute_team_split(db, "Alfa", "home", tgt, "2025-03-10")
    assert s["n"] == 5
    assert s["goals"] == 2 and s["goals_against"] == 1
    assert s["corners"] == 5 and s["corners_against"] == 4
    assert compute_team_split(db, "Alfa", "away", tgt, "2025-03-10") is None  # 1 < min_n


def test_fail_closed(db):
    for d in range(1, 7):
        _row(db, "Alfa", "Beta", d, (1, 0))
    db.commit()
    tgt = season_key("100")
    assert compute_team_split(db, "Alfa", "home", None, "2025-03-10") is None  # sin temporada
    assert compute_team_split(db, "Alfa", "home", tgt, None) is None  # sin kickoff
    assert compute_team_split(db, "Alfa", "home", tgt, "2025-03-10")["n"] == 6


def test_apply_split_keeps_unsplittable_and_rescales():
    t = FootballTeamStats(
        name="Alfa", matches_played=20, goals_per_game=1.0, possession_pct=55.0, red_cards_total=4
    )
    out = apply_split(t, {"n": 5, "goals_n": 5, "goals": 2.0, "goals_against": 1.0}, "home")
    assert out.goals_per_game == 2.0 and out.goals_conceded_per_game == 1.0
    assert out.matches_played == 5 and out.matches_home == 5
    assert out.possession_pct == 55.0
    assert out.red_cards_total == pytest.approx(1.0)  # misma tasa por juego (0.2)
    assert out.corners_per_game == t.corners_per_game  # sin muestra -> general
