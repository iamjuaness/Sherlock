import math
import pytest
from src.ui.api.compare import LeagueStats, _compute_league_reliability_score


def test_lrs_zero_matches_no_metrics():
    # matches = 0, no metrics -> S_matches ~ 0.0237, S_integrity = 0.0 -> LRS_base = max(0.15, ...) = 0.15
    league = LeagueStats(
        historical_matches=0,
        historical_picks=0,
        avg_xg_per_game=0.0,
        avg_shots_target_per_game=0.0,
        avg_corners_per_game=0.0,
        avg_cards_per_game=0.0,
        avg_yellow_cards_per_game=0.0,
    )
    score = _compute_league_reliability_score(league)
    assert score == 0.15


def test_lrs_high_matches_with_metrics_no_picks():
    # matches = 300 -> S_matches = 0.50 / (1 + exp(-3.0)) ~ 0.476
    # All 5 metrics present: avg_xg, avg_shots_target, avg_corners, avg_fouls, avg_cards
    # S_integrity = 0.35 * 1.0 = 0.35
    # LRS_base = 0.476 + 0.35 = 0.826 (clipped in [0.15, 0.85])
    # picks = 0 (< 50) -> A_perf = 0.0
    # Final LRS ~ 0.826
    league = LeagueStats(
        historical_matches=300,
        historical_picks=0,
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
        avg_cards_per_game=4.5,
    )
    # Give avg_xg_per_game and avg_fouls_per_game
    setattr(league, "avg_xg_per_game", 2.5)
    setattr(league, "avg_fouls_per_game", 22.0)

    score = _compute_league_reliability_score(league)
    expected_s_matches = 0.50 / (1.0 + math.exp(-3.0))
    expected_s_integrity = 0.35
    expected_lrs = min(0.85, expected_s_matches + expected_s_integrity)
    assert score == pytest.approx(round(expected_lrs, 3), abs=1e-3)
    assert 0.82 <= score <= 0.83


def test_lrs_historical_performance_adjustment():
    # If picks < 50, no performance adjustment regardless of ROI
    league_low_picks = LeagueStats(
        historical_matches=200,
        historical_picks=49,
        roi=25.0,
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
    )
    score_low_picks = _compute_league_reliability_score(league_low_picks)

    league_zero_picks = LeagueStats(
        historical_matches=200,
        historical_picks=0,
        roi=0.0,
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
    )
    score_zero_picks = _compute_league_reliability_score(league_zero_picks)
    assert score_low_picks == score_zero_picks

    # When picks >= 50, A_perf = clip(0.5 * roi, -0.10, +0.10)
    # Case 1: Positive ROI = 10% (0.10) -> A_perf = 0.05
    league_pos_roi = LeagueStats(
        historical_matches=200,
        historical_picks=60,
        roi=10.0,  # 10%
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
    )
    score_pos = _compute_league_reliability_score(league_pos_roi)
    assert score_pos == pytest.approx(round(score_zero_picks + 0.05, 3), abs=1e-3)

    # Case 2: Max positive ROI capped at +0.10
    league_max_roi = LeagueStats(
        historical_matches=200,
        historical_picks=100,
        roi=50.0,  # 50% -> 0.5 * 0.5 = 0.25 -> capped to +0.10
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
    )
    score_max = _compute_league_reliability_score(league_max_roi)
    assert score_max == pytest.approx(round(score_zero_picks + 0.10, 3), abs=1e-3)

    # Case 3: Negative ROI = -20% -> 0.5 * (-0.20) = -0.10 -> capped to -0.10
    league_neg_roi = LeagueStats(
        historical_matches=200,
        historical_picks=100,
        roi=-20.0,
        avg_shots_target_per_game=8.5,
        avg_corners_per_game=9.5,
    )
    score_neg = _compute_league_reliability_score(league_neg_roi)
    assert score_neg == pytest.approx(round(score_zero_picks - 0.10, 3), abs=1e-3)


def test_lrs_bounds():
    # Never below 0.15
    league_horrible = LeagueStats(
        historical_matches=0,
        historical_picks=100,
        roi=-80.0,
        avg_shots_target_per_game=0.0,
        avg_corners_per_game=0.0,
        avg_cards_per_game=0.0,
    )
    assert _compute_league_reliability_score(league_horrible) >= 0.15

    # Never above 1.00
    league_stellar = LeagueStats(
        historical_matches=1000,
        historical_picks=500,
        roi=50.0,
        avg_shots_target_per_game=10.0,
        avg_corners_per_game=10.0,
        avg_cards_per_game=4.0,
    )
    setattr(league_stellar, "avg_xg_per_game", 3.0)
    setattr(league_stellar, "avg_fouls_per_game", 20.0)
    assert _compute_league_reliability_score(league_stellar) <= 1.00

