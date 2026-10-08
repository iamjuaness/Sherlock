import pytest
from src.models.joint_match_distribution import (
    derive_joint_match_probabilities,
    guardrail_away_win_recommendation,
)


def test_joint_match_invariants():
    probs = derive_joint_match_probabilities(lambda_home=1.6, mu_away=1.1)
    assert probs.validate_invariants()
    assert abs((probs.p_home_win + probs.p_draw + probs.p_away_win) - 1.0) < 1e-4
    assert abs(probs.p_1x - (probs.p_home_win + probs.p_draw)) < 1e-4
    assert abs((probs.p_btts_yes + probs.p_btts_no) - 1.0) < 1e-4


def test_guardrail_away_win():
    # Caso 1: Empate dominante -> rechazado
    ok, reason = guardrail_away_win_recommendation(
        p_away=0.35, p_draw=0.38, p_x2=0.73, away_odds=2.8
    )
    assert not ok
    assert "empate domina" in reason.lower()

    # Caso 2: Aprobado
    ok2, reason2 = guardrail_away_win_recommendation(
        p_away=0.45, p_draw=0.25, p_x2=0.70, away_odds=2.5, segment_reliability=0.8, has_clv_confirmation=True
    )
    assert ok2
