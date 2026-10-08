import pytest
from src.models.market_probability import (
    blend_model_and_market_probability,
    compute_clv,
    implied_probability,
    remove_vig_three_way,
    remove_vig_two_way,
)


def test_implied_probability():
    assert implied_probability(2.0) == 0.5
    assert implied_probability(1.25) == 0.8
    with pytest.raises(ValueError):
        implied_probability(1.0)


def test_remove_vig_two_way():
    # Odds 1.90 / 1.90 -> total = 0.5263 + 0.5263 = 1.0526 -> 0.50 / 0.50
    pa, pb = remove_vig_two_way(1.90, 1.90)
    assert abs(pa - 0.5) < 1e-4
    assert abs(pb - 0.5) < 1e-4


def test_remove_vig_three_way():
    ph, pd, pa = remove_vig_three_way(2.5, 3.2, 3.0)
    assert abs((ph + pd + pa) - 1.0) < 1e-6


test_clv = compute_clv(2.0, 1.8)
assert test_clv.clv_percent > 0


def test_blend_and_divergence():
    b1 = blend_model_and_market_probability(0.60, 0.55, reliability_score=0.8)
    assert 0.55 <= b1.final_prob <= 0.60
    assert not b1.divergence_warning

    b2 = blend_model_and_market_probability(0.70, 0.40, reliability_score=0.5)
    assert b2.divergence_warning
    assert b2.divergence_blocked
