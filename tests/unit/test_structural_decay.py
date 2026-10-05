"""
Pruebas unitarias completas para las mejoras estructurales de reciencia temporal,
perfiles de competición, promedios ponderados y recién ascendidos (planning.txt).
"""

import unittest
from datetime import datetime, timezone, timedelta
from src.core.math_engine import (
    LeagueMathEngine,
    calculate_time_decay_weight,
    estimate_nb_dispersion,
    get_league_profile,
    LEAGUE_HISTORY_PROFILES,
)
from src.core.backtesting import TemporalParameterOptimizer


class TestStructuralDecayAndProfiles(unittest.TestCase):
    
    def test_time_decay_weight_exact_points(self):
        ref = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        h = 365.0

        # Exact reference date -> 1.0
        w0 = calculate_time_decay_weight(ref, reference_date=ref, half_life_days=h)
        self.assertAlmostEqual(w0, 1.0, places=5)

        # 1 half_life ago -> 0.5
        m1 = ref - timedelta(days=365)
        w1 = calculate_time_decay_weight(m1, reference_date=ref, half_life_days=h)
        self.assertAlmostEqual(w1, 0.5, places=5)

        # 2 half_lives ago -> 0.25
        m2 = ref - timedelta(days=730)
        w2 = calculate_time_decay_weight(m2, reference_date=ref, half_life_days=h)
        self.assertAlmostEqual(w2, 0.25, places=5)

    def test_time_decay_weight_boundary_and_invalid_inputs(self):
        ref = "2026-10-01T12:00:00Z"

        # Future match date -> 0.0
        future = "2026-10-02T12:00:00Z"
        self.assertEqual(calculate_time_decay_weight(future, reference_date=ref), 0.0)

        # Invalid or null dates -> 0.0
        self.assertEqual(calculate_time_decay_weight(None, reference_date=ref), 0.0)
        self.assertEqual(calculate_time_decay_weight("invalid-date-string", reference_date=ref), 0.0)
        w_now = calculate_time_decay_weight("2026-05-01", reference_date=None)
        if datetime.now(timezone.utc) < datetime(2026, 5, 1, tzinfo=timezone.utc):
            self.assertEqual(w_now, 0.0)
        else:
            self.assertGreater(w_now, 0.0)

        # Zero or negative half_life_days -> 0.0
        self.assertEqual(calculate_time_decay_weight("2026-09-01", reference_date=ref, half_life_days=0.0), 0.0)
        self.assertEqual(calculate_time_decay_weight("2026-09-01", reference_date=ref, half_life_days=-10.0), 0.0)

    def test_league_profiles_lookup(self):
        p_stable = get_league_profile(profile_name="stable_high_volume")
        self.assertEqual(p_stable["league_prior_half_life_days"], 420.0)
        self.assertEqual(p_stable["team_half_life_matches"], 17.5)

        p_short = get_league_profile(profile_name="small_or_short_format")
        self.assertEqual(p_short["league_prior_half_life_days"], 600.0)

        p_turnover = get_league_profile(profile_name="high_turnover_or_structural_change")
        self.assertEqual(p_turnover["league_prior_half_life_days"], 270.0)

        # Unknown profile name defaults to stable_high_volume
        p_default = get_league_profile(competition_id="unknown_comp_999")
        self.assertEqual(p_default["league_prior_half_life_days"], 420.0)

    def test_compute_league_averages_weighted_and_no_leakage(self):
        ref_date = "2026-06-01T00:00:00Z"
        
        # Match 1: 3 years old (low weight) -> 1 home goal
        # Match 2: 1 day old (high weight) -> 4 home goals
        # Match 3: Future match (after ref_date) -> 10 home goals (MUST BE EXCLUDED)
        matches = [
            {
                "match_date": "2023-06-01T00:00:00Z",
                "final_score_home": 1, "final_score_away": 0,
                "final_corners_home": 4, "final_corners_away": 3,
            },
            {
                "match_date": "2026-05-31T00:00:00Z",
                "final_score_home": 4, "final_score_away": 1,
                "final_corners_home": 8, "final_corners_away": 2,
            },
            {
                "match_date": "2026-06-05T00:00:00Z",
                "final_score_home": 10, "final_score_away": 10,
                "final_corners_home": 20, "final_corners_away": 20,
            },
        ]

        avgs = LeagueMathEngine.compute_league_averages(
            matches,
            reference_date=ref_date,
            half_life_days=365.0,
            min_effective_sample_size=1.0,
        )

        # Home goals should be close to 4.0 (recent match dominates match 1), and strictly NOT affected by match 3
        self.assertGreater(avgs["home_goals"], 3.0)
        self.assertLess(avgs["home_goals"], 4.5)
        self.assertEqual(avgs["sample_size"], 2)
        self.assertIn("effective_sample_size", avgs)
        self.assertIn("source", avgs)
        self.assertEqual(avgs["source"], "mixed_with_defaults")

        # Check required backwards compatibility keys exist
        for key in ["home_goals", "away_goals", "home_corners", "away_corners", "home_cards", "away_cards"]:
            self.assertIn(key, avgs)

    def test_per_metric_fallback_and_independent_counts(self):
        ref_date = "2026-06-01T00:00:00Z"
        matches = [
            {
                "match_date": "2026-05-01T00:00:00Z",
                "final_score_home": 2, "final_score_away": 1,
                # corners, cards, fouls are missing
            },
            {
                "match_date": "2026-05-02T00:00:00Z",
                "final_score_home": 3, "final_score_away": 0,
            }
        ]

        avgs = LeagueMathEngine.compute_league_averages(
            matches,
            reference_date=ref_date,
            fallback_defaults={"home_corners": 5.2, "away_corners": 4.1},
        )

        # Goals should come from history
        self.assertAlmostEqual(avgs["home_goals"], 2.5, places=1)
        # Corners missing -> fallback to default
        self.assertEqual(avgs["home_corners"], 5.2)
        self.assertEqual(avgs["away_corners"], 4.1)
        self.assertEqual(avgs["source"], "mixed_with_defaults")

    def test_newly_promoted_shrinkage_and_metadata(self):
        engine = LeagueMathEngine()

        # Newly promoted home team with only 2 matches
        home_scored = [2.0, 1.0]
        home_conceded = [0.0, 1.0]
        away_scored = [1.5] * 15
        away_conceded = [1.0] * 15

        l_h, l_a, meta = engine.calculate_expected_goals_with_meta(
            home_recent_scored=home_scored,
            home_recent_conceded=home_conceded,
            away_recent_scored=away_scored,
            away_recent_conceded=away_conceded,
            league_home_avg=1.45,
            league_away_avg=1.15,
            is_home_newly_promoted=True,
            is_away_newly_promoted=False,
            home_lower_div_scored=[3.0, 2.5, 2.0],
            home_lower_div_conceded=[0.5, 0.5, 1.0],
        )

        self.assertTrue(meta["home"]["is_newly_promoted"])
        self.assertEqual(meta["home"]["top_division_matches"], 2)
        self.assertEqual(meta["home"]["shrinkage_weight"], 0.2)
        self.assertTrue(meta["home"]["used_lower_division_auxiliary_signal"])

        self.assertFalse(meta["away"]["is_newly_promoted"])
        self.assertEqual(meta["away"]["shrinkage_weight"], 1.0)
        self.assertFalse(meta["away"]["used_lower_division_auxiliary_signal"])

    def test_nb_dispersion_weighted(self):
        values = [10.0, 2.0, 12.0, 3.0, 15.0]
        weights = [1.0, 0.8, 0.5, 0.2, 0.1]
        
        alpha = estimate_nb_dispersion(values, weights=weights)
        self.assertGreater(alpha, 0.001)
        self.assertLessEqual(alpha, 0.5)

    def test_temporal_parameter_optimizer_grid(self):
        matches = [
            {"match_date": f"2025-01-{i+1:02d}T00:00:00Z", "final_score_home": (i % 3) + 1, "final_score_away": (i % 2)}
            for i in range(35)
        ]
        
        optimizer = TemporalParameterOptimizer(matches=matches, competition_id="test_comp", market="goals")
        res = optimizer.run_grid_search(
            grid={
                "league_prior_half_life_days": [270.0, 420.0],
                "team_half_life_matches": [15.0],
                "team_max_matches": [30],
                "league_prior_strength": [18.0],
            },
            min_history_matches=10,
            limit_combinations=5,
        )

        self.assertEqual(res["competition_id"], "test_comp")
        self.assertIn("best_parameters", res)
        self.assertIn("all_results", res)
        self.assertGreater(len(res["all_results"]), 0)

    def test_load_calculated_league_params_and_fallback(self):
        from src.core.math_engine import load_calculated_league_params
        
        # Test loading from data/calculated_league_params.json
        params = load_calculated_league_params("LaLiga")
        if params is not None:
            self.assertIn("averages", params)
            self.assertIn("dispersions", params)

        # Test compute_league_averages with empty matches fallback to calculated params
        avgs = LeagueMathEngine.compute_league_averages(
            historical_matches=[],
            competition_id="LaLiga"
        )
        self.assertIn("home_goals", avgs)
        self.assertIn("away_goals", avgs)
        self.assertIn("source", avgs)


if __name__ == "__main__":
    unittest.main()
