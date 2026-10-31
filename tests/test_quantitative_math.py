"""
Unit tests for the quantitative mathematical engine in src/core/math
and integration with compare endpoints.
"""
from __future__ import annotations

import asyncio
import math
import numpy as np
import pytest

from src.core.math.dixon_coles import (
    tau,
    time_decay_weight,
    build_dixon_coles_matrix,
    solve_dixon_coles_mle,
)
from src.core.math.bayesian import (
    fit_gamma_prior_from_league,
    update_gamma_poisson,
)
from src.core.math.calibration import (
    normalize_categorical_market,
    PlattCalibrator,
    IsotonicCalibrator,
)
from src.core.math.kelly import (
    calculate_fractional_kelly,
)
from src.ui.api.compare import (
    FootballCompareRequest,
    FootballTeamStats,
    LeagueStats,
    FootballOdds,
    CompareResponse,
    compare_football,
)


# ==============================================================================
# 1. Tests for Dixon-Coles Matrix and Tau Correction
# ==============================================================================

def test_dixon_coles_tau_correction():
    lam = 1.4
    mu = 1.1
    rho = -0.12

    # Tau checks
    assert tau(0, 0, lam, mu, rho) == pytest.approx(1.0 - lam * mu * rho, abs=1e-7)
    assert tau(0, 1, lam, mu, rho) == pytest.approx(1.0 + lam * rho, abs=1e-7)
    assert tau(1, 0, lam, mu, rho) == pytest.approx(1.0 + mu * rho, abs=1e-7)
    assert tau(1, 1, lam, mu, rho) == pytest.approx(1.0 - rho, abs=1e-7)

    # Any other score must be 1.0
    for x in range(5):
        for y in range(5):
            if (x, y) not in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                assert tau(x, y, lam, mu, rho) == 1.0


def test_dixon_coles_matrix_sums_to_one():
    for lam, mu, rho in [(1.5, 1.2, -0.1), (0.8, 0.5, 0.05), (2.5, 2.0, -0.15)]:
        mat = build_dixon_coles_matrix(lam, mu, rho, max_goals=10)
        assert mat.shape == (11, 11)
        assert np.sum(mat) == pytest.approx(1.0, abs=1e-6)
        assert np.all(mat >= 0.0)


def test_dixon_coles_mle_solver():
    matches = [
        {"home_team": "Team A", "away_team": "Team B", "home_goals": 2, "away_goals": 1, "days_ago": 10},
        {"home_team": "Team B", "away_team": "Team C", "home_goals": 1, "away_goals": 1, "days_ago": 20},
        {"home_team": "Team C", "away_team": "Team A", "home_goals": 0, "away_goals": 2, "days_ago": 30},
        {"home_team": "Team A", "away_team": "Team C", "home_goals": 3, "away_goals": 0, "days_ago": 5},
    ]
    res = solve_dixon_coles_mle(matches)
    assert "attack" in res and "defence" in res
    assert "home_advantage" in res and "rho" in res
    # Identifiability constraint: sum of alphas == 0
    alpha_sum = sum(res["attack"].values())
    assert alpha_sum == pytest.approx(0.0, abs=1e-5)


# ==============================================================================
# 2. Tests for Bayesian Gamma-Poisson Shrinkage
# ==============================================================================

def test_gamma_poisson_shrinkage_behavior():
    # League historical events with mean = 1.5
    league_series = [1.2, 1.4, 1.5, 1.6, 1.7, 1.6, 1.5, 1.3]
    alpha_prior, beta_prior = fit_gamma_prior_from_league(league_series)
    league_mean = alpha_prior / beta_prior
    assert league_mean == pytest.approx(np.mean(league_series), abs=1e-2)

    # Team with only n = 1 match and 3.0 events (extreme outlier)
    post_n1 = update_gamma_poisson(alpha_prior, beta_prior, observed_events=3.0, matches_played=1.0)
    # Must contract strongly towards league mean
    assert abs(post_n1 - league_mean) < abs(3.0 - league_mean)
    assert post_n1 < 2.5

    # Team with n = 25 matches and rate 3.0 (75 total events)
    post_n25 = update_gamma_poisson(alpha_prior, beta_prior, observed_events=75.0, matches_played=25.0)
    # Must give much higher weight to team's empirical rate (3.0)
    assert abs(post_n25 - 3.0) < 0.25
    assert post_n25 > post_n1


# ==============================================================================
# 3. Tests for Market Normalization and Calibration
# ==============================================================================

def test_normalize_categorical_market():
    # 1X2 market
    raw_1x2 = {"home": 0.45, "draw": 0.30, "away": 0.35}  # sums to 1.10
    norm_1x2 = normalize_categorical_market(raw_1x2)
    assert sum(norm_1x2.values()) == pytest.approx(1.0, abs=1e-6)
    assert norm_1x2["home"] == pytest.approx(0.45 / 1.10, abs=1e-6)

    # Over / Under market
    raw_ou = {"over": 0.55, "under": 0.50}  # sums to 1.05
    norm_ou = normalize_categorical_market(raw_ou)
    assert sum(norm_ou.values()) == pytest.approx(1.0, abs=1e-6)


def test_platt_and_isotonic_calibrators():
    probs = np.array([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])
    y_true = np.array([0, 0, 0, 1, 1, 1])

    # Platt
    platt = PlattCalibrator()
    platt.fit(probs, y_true)
    cal_platt = platt.predict_proba([0.15, 0.85])
    assert cal_platt[0] < cal_platt[1]
    assert np.all((cal_platt >= 0.0) & (cal_platt <= 1.0))

    # Isotonic
    iso = IsotonicCalibrator()
    iso.fit(probs, y_true)
    cal_iso = iso.predict_proba([0.15, 0.85])
    assert cal_iso[0] <= cal_iso[1]
    assert np.all((cal_iso >= 0.0) & (cal_iso <= 1.0))


# ==============================================================================
# 4. Tests for Fractional Kelly
# ==============================================================================

def test_calculate_fractional_kelly():
    # Negative EV: p * odds <= 1.0
    stake_neg, edge_neg = calculate_fractional_kelly(calibrated_prob=0.40, odds=2.0)
    assert stake_neg == 0.0
    assert edge_neg <= 0.0

    # Exactly zero EV: p * odds == 1.0
    stake_zero, edge_zero = calculate_fractional_kelly(calibrated_prob=0.50, odds=2.0)
    assert stake_zero == 0.0
    assert edge_zero == pytest.approx(0.0, abs=1e-6)

    # Positive EV: p=0.60, odds=2.0 -> edge = +20%
    stake_pos, edge_pos = calculate_fractional_kelly(calibrated_prob=0.60, odds=2.0, fraction_divisor=8.0, max_stake_cap=0.03)
    # b = 1, f* = (0.6 * 1 - 0.4) / 1 = 0.20
    # 0.20 / 8 = 0.025 (2.5%)
    assert edge_pos == pytest.approx(20.0, abs=1e-6)
    assert stake_pos == pytest.approx(0.025, abs=1e-6)

    # Massive edge capped at max_stake_cap = 0.03 (3%)
    stake_huge, _ = calculate_fractional_kelly(calibrated_prob=0.95, odds=3.0, fraction_divisor=8.0, max_stake_cap=0.03)
    assert stake_huge == 0.03


# ==============================================================================
# 5. Integration Test: Football Compare Endpoint / Handler
# ==============================================================================

def test_compare_football_endpoint_mock_request():
    home_team = FootballTeamStats(
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
    away_team = FootballTeamStats(
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
    league_stats = LeagueStats(
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

    request = FootballCompareRequest(
        sport="football",
        competition="La Liga",
        home=home_team,
        away=away_team,
        league_stats=league_stats,
        odds=odds,
    )

    response = asyncio.run(compare_football(request))
    assert isinstance(response, CompareResponse)
    assert response.home_name == "Real Madrid"
    assert response.away_name == "Barcelona"
    assert response.h_lam is not None and response.h_lam > 0.0
    assert response.a_lam is not None and response.a_lam > 0.0
    assert len(response.values) > 0

    # Ensure 1X2 raw sum check is approximately 100%
    home_val = next((v for v in response.values if v.selection == "Local"), None)
    draw_val = next((v for v in response.values if v.selection == "Empate"), None)
    away_val = next((v for v in response.values if v.selection == "Visitante"), None)

    assert home_val is not None and draw_val is not None and away_val is not None
    sum_1x2 = home_val.model_prob + draw_val.model_prob + away_val.model_prob
    assert sum_1x2 == pytest.approx(100.0, abs=1e-4)

    # Ensure all returned stakes are capped properly
    for val in response.values:
        if val.stake_units is not None:
            assert 0.0 <= val.stake_units <= 3.0

