"""Tests unitarios para el motor estadístico matemático por liga (Sherlock Math Engine)."""

import math
import unittest
from src.core.math_engine import (
    LeagueMathEngine,
    calculate_dixon_coles_matrix,
    calculate_weighted_average,
    estimate_nb_dispersion,
    dixon_coles_tau,
)


class TestLeagueMathEngine(unittest.TestCase):

    def test_dixon_coles_matrix_sums_to_one(self):
        matrix = calculate_dixon_coles_matrix(1.5, 1.2, max_goals=8, rho=-0.05)
        total_prob = sum(sum(row) for row in matrix)
        self.assertAlmostEqual(total_prob, 1.0, places=3)

    def test_dixon_coles_tau_correction(self):
        tau_00 = dixon_coles_tau(0, 0, 1.5, 1.2, rho=-0.05)
        self.assertGreater(tau_00, 1.0)

    def test_calculate_weighted_average(self):
        values = [3.0, 1.0, 0.0]
        avg = calculate_weighted_average(values, half_life=1.0)
        self.assertGreater(avg, 1.5)

    def test_estimate_nb_dispersion(self):
        values = [5, 12, 4, 15, 6, 14]
        alpha = estimate_nb_dispersion(values)
        self.assertGreater(alpha, 0.0)

    def test_league_math_engine_goals(self):
        engine = LeagueMathEngine()
        home_scored = [2.0, 3.0, 1.0, 2.0]
        home_conceded = [0.0, 1.0, 1.0, 0.0]
        away_scored = [1.0, 0.0, 2.0, 1.0]
        away_conceded = [2.0, 3.0, 2.0, 1.0]

        lambda_h, mu_a = engine.calculate_expected_goals(
            home_recent_scored=home_scored,
            home_recent_conceded=home_conceded,
            away_recent_scored=away_scored,
            away_recent_conceded=away_conceded,
            league_home_avg=1.45,
            league_away_avg=1.15
        )

        self.assertGreater(lambda_h, mu_a)
        self.assertTrue(0.2 <= lambda_h <= 4.5)
        self.assertTrue(0.2 <= mu_a <= 4.5)

    def test_compute_league_averages(self):
        matches = [
            {"final_score_home": 2, "final_score_away": 1, "final_corners_home": 6, "final_corners_away": 4},
            {"final_score_home": 1, "final_score_away": 1, "final_corners_home": 5, "final_corners_away": 3},
            {"final_score_home": 3, "final_score_away": 0, "final_corners_home": 7, "final_corners_away": 2},
        ]
        avgs = LeagueMathEngine.compute_league_averages(matches)
        self.assertAlmostEqual(avgs["home_goals"], 2.0, places=2)
        self.assertAlmostEqual(avgs["away_goals"], 0.6666, places=2)
        self.assertAlmostEqual(avgs["home_corners"], 6.0, places=2)

    def test_recent_form_windows(self):
        matches = [
            {"match_title": "Team A vs Team B", "final_score_home": 3, "final_score_away": 1, "final_corners_home": 6, "final_corners_away": 2},
            {"match_title": "Team C vs Team A", "final_score_home": 0, "final_score_away": 2, "final_corners_home": 4, "final_corners_away": 5},
            {"match_title": "Team A vs Team D", "final_score_home": 1, "final_score_away": 1, "final_corners_home": 4, "final_corners_away": 3},
        ]
        windows = LeagueMathEngine.compute_recent_form_windows(matches, "Team A", windows=[5, 10])
        self.assertIn("last_5", windows)
        self.assertEqual(windows["last_5"]["sample_size"], 3)
        self.assertEqual(windows["last_5"]["goals_scored"], 2.0)  # (3+2+1)/3 = 2.0

    def test_pick_hit_rate(self):
        matches = [
            {"match_title": "Team A vs Team B", "final_score_home": 2, "final_score_away": 1, "date": "2024-01-01"}, # Total 3 > 2.5
            {"match_title": "Team A vs Team C", "final_score_home": 1, "final_score_away": 0, "date": "2024-01-02"}, # Total 1 < 2.5
            {"match_title": "Team A vs Team D", "final_score_home": 3, "final_score_away": 0, "date": "2024-01-03"}, # Total 3 > 2.5
        ]
        res = LeagueMathEngine.compute_pick_hit_rate(matches, "Team A", market_family="goals", line=2.5, is_over=True, role_filter="home", current_match_date="2024-02-01")
        self.assertEqual(res["sample_size"], 3)
        self.assertEqual(res["hits"], 2)
    def test_compute_h2h_hit_rate(self):
        matches = [
            {"id": 1, "date": "2024-01-01", "home_team": "Team A", "away_team": "Team B", "final_score_home": 2, "final_score_away": 1}, # Over 2.5 (Hit)
            {"id": 2, "date": "2024-02-01", "home_team": "Team B", "away_team": "Team A", "final_score_home": 0, "final_score_away": 1}, # Under 2.5 (Miss)
            {"id": 3, "date": "2024-03-01", "home_team": "Team A", "away_team": "Team B", "final_score_home": 3, "final_score_away": 1}, # Over 2.5 (Hit)
            {"id": 4, "date": "2024-04-01", "home_team": "Team A", "away_team": "Team B", "final_score_home": 4, "final_score_away": 0}, # Partido futuro/actual (Data Leakage)
        ]
        # Excluyendo id=4 o fecha >= 2024-04-01 para evitar data-leakage
        res = LeagueMathEngine.compute_h2h_hit_rate(matches, "Team A", "Team B", market_family="goals", line=2.5, is_over=True, current_match_date="2024-04-01")
        self.assertEqual(res["sample_size"], 3)
        self.assertEqual(res["hits"], 2)
        self.assertAlmostEqual(res["hit_rate_pct"], 66.7, places=1)
        self.assertIn("h2h_matches", res)
        self.assertEqual(len(res["h2h_matches"]), 3)
        self.assertTrue(res["h2h_matches"][0]["hit"])
        self.assertFalse(res["h2h_matches"][1]["hit"])

    def test_compute_h2h_hit_rate_same_day_filtering(self):
        matches = [
            {"id": 1, "date": "2026-01-23 23:20:00.000000", "home_team": "Inter de Bogotá", "away_team": "Cúcuta", "final_score_home": 2, "final_score_away": 1},
            {"id": 2, "date": "2026-08-19 18:00:00.000000", "home_team": "Cúcuta", "away_team": "Inter de Bogotá", "final_score_home": 1, "final_score_away": 1}, # Mismo día del partido actual
        ]
        # Al pasar current_match_date="2026-08-19T18:00:00", el partido id=2 debe ser excluido por coincidir en el mismo día
        res = LeagueMathEngine.compute_h2h_hit_rate(
            matches,
            "Cúcuta",
            "Inter de Bogotá",
            market_family="goals",
            line=2.5,
            is_over=True,
            current_match_date="2026-08-19T18:00:00",
            exclude_match_id=2
        )
        self.assertEqual(res["sample_size"], 1)
        self.assertEqual(len(res["h2h_matches"]), 1)
        self.assertEqual(res["h2h_matches"][0]["date"], "2026-01-23")

    def test_compute_h2h_venue_strictness_double_chance(self):
        # Ejemplo del usuario: Independiente Petrolero vs GV San José (X2)
        # Partido 1: Ind Petrolero 0 - 1 GV San José -> Sirve (Ind era Home, GV San José era Away)
        # Partido 2: GV San José 2 - 2 Ind Petrolero -> NO sirve para X2 en venue inverso (local/vis diferentes)
        matches = [
            {"id": 10, "date": "2024-01-10", "home_team": "Independiente Petrolero", "away_team": "GV San José", "final_score_home": 0, "final_score_away": 1},
            {"id": 11, "date": "2024-02-10", "home_team": "GV San José", "away_team": "Independiente Petrolero", "final_score_home": 2, "final_score_away": 2},
        ]
        res = LeagueMathEngine.compute_h2h_hit_rate(
            matches,
            home_team_name="Independiente Petrolero",
            away_team_name="GV San José",
            market_family="double_chance",
            target_side="x2",
            current_match_date="2024-03-01"
        )
        # Solo debe evaluar el Partido 10 (mismo orden de localía)
        self.assertEqual(res["sample_size"], 1)
        self.assertEqual(res["hits"], 1)
        self.assertEqual(len(res["h2h_matches"]), 1)
        self.assertEqual(res["h2h_matches"][0]["home_team"], "Independiente Petrolero")
        self.assertEqual(res["h2h_matches"][0]["away_team"], "GV San José")

    def test_apply_calibration_deterministic(self):
        from src.ui.api.compare import apply_calibration
        prob = apply_calibration(65.4, 1.85, "goals")
        self.assertEqual(prob, 65.4)

    def test_h2h_zero_percent_filter(self):
        from src.ui.api.compare import is_publishable_pick, is_underdog_pick, ValueIndicator
        v = ValueIndicator(
            selection="Over 2.5 Goles",
            odds=1.90,
            model_prob=65.0,
            calibrated_prob=65.0,
            edge=10.0,
            edge_ev=0.15,
            data_quality_score=80.0,
            stake_units=1.5,
            h2h_hit_rate=0.0,
            h2h_samples=3
        )
        self.assertFalse(is_publishable_pick(v))

        v_underdog = ValueIndicator(
            selection="Empate",
            odds=3.20,
            model_prob=35.0,
            calibrated_prob=35.0,
            edge=6.0,
            edge_ev=0.10,
            data_quality_score=80.0,
            stake_units=1.5,
            h2h_hit_rate=0.0,
            h2h_samples=2
        )
        self.assertFalse(is_underdog_pick(v_underdog))


if __name__ == "__main__":
    unittest.main()


