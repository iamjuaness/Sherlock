from src.ui.api.compare import (
    FootballCompareRequest,
    FootballTeamStats,
    FootballOdds,
    compare_football,
    NBACompareRequest,
    NBATeamStats,
    NBAOdds,
    compare_nba,
    TennisCompareRequest,
    TennisPlayerStats,
    TennisOdds,
    compare_tennis,
)

import pytest

@pytest.mark.asyncio
async def test_compare_football_basic():
    req = FootballCompareRequest(
        home=FootballTeamStats(
            name="Team A",
            goals_per_game=2.5,
            goal_conversion_pct=15.0,
            big_chances_per_game=3.0,
            big_chances_missed_per_game=1.0,
            shots_per_game=15.0,
            shots_on_target_per_game=6.0,
            shots_off_target_per_game=5.0,
            corners_per_game=6.0,
            possession_pct=60.0,
            clean_sheets=10,
            goals_conceded_per_game=0.5,
            balls_recovered_per_game=50.0,
            yellow_cards_per_game=1.5,
            fouls_per_game=10.0,
            offsides_per_game=2.0,
            wins=10,
            draws=3,
            losses=2,
        ),
        away=FootballTeamStats(
            name="Team B",
            goals_per_game=1.0,
            goal_conversion_pct=10.0,
            big_chances_per_game=1.5,
            big_chances_missed_per_game=0.5,
            shots_per_game=10.0,
            shots_on_target_per_game=3.0,
            shots_off_target_per_game=5.0,
            corners_per_game=4.0,
            possession_pct=40.0,
            clean_sheets=5,
            goals_conceded_per_game=1.5,
            balls_recovered_per_game=40.0,
            yellow_cards_per_game=2.5,
            fouls_per_game=12.0,
            offsides_per_game=1.5,
            wins=4,
            draws=5,
            losses=6,
        ),
        odds=FootballOdds(home=2.50, draw=3.20, away=3.10, bookmaker="Bet365")
    )
    
    resp = await compare_football(req)
    assert resp.sport == "football"
    assert resp.home_name == "Team A"
    assert resp.away_name == "Team B"
    
    # 18 stat comparisons
    assert len(resp.comparisons) == 18
    
    # Check value indicators
    assert len(resp.values) == 3
    # Team A has much better stats so model_prob should be high, and odds 2.50 implies 40% probability.
    home_val = next(v for v in resp.values if v.selection == "Local")
    assert home_val.implied_prob == 40.0
    
    # Check summary exists
    assert resp.summary is not None

def test_compare_nba_basic():
    req = NBACompareRequest(
        home=NBATeamStats(
            name="Lakers",
            points=115.0,
            rebounds=45.0,
            assists=25.0,
            turnovers=12.0,
            fg_pct=48.0,
            three_pct=36.0,
            ft_pct=80.0,
            wins=10,
            losses=5,
        ),
        away=NBATeamStats(
            name="Bulls",
            points=105.0,
            rebounds=40.0,
            assists=20.0,
            turnovers=15.0,
            fg_pct=45.0,
            three_pct=33.0,
            ft_pct=75.0,
            wins=6,
            losses=9,
        ),
        odds=NBAOdds(home=1.50, away=2.60, bookmaker="Pinnacle")
    )
    
    resp = compare_nba(req)
    assert resp.sport == "nba"
    assert resp.home_name == "Lakers"
    assert len(resp.comparisons) == 8
    assert len(resp.values) == 2

def test_compare_tennis_basic():
    req = TennisCompareRequest(
        player1=TennisPlayerStats(
            name="Federer",
            win_pct=85.0,
            aces=10.0,
            double_faults=1.5,
            first_serve_pct=65.0,
            break_points_won=3.5,
            surface="grass",
            sets_won=25,
            sets_lost=5,
        ),
        player2=TennisPlayerStats(
            name="Nadal",
            win_pct=80.0,
            aces=5.0,
            double_faults=2.0,
            first_serve_pct=70.0,
            break_points_won=4.0,
            surface="grass",
            sets_won=22,
            sets_lost=8,
        ),
        odds=TennisOdds(player1=1.80, player2=2.10)
    )
    resp = compare_tennis(req)
    assert resp.sport == "tennis"
    assert resp.home_name == "Federer"
    assert len(resp.comparisons) == 6
    assert len(resp.values) == 2
