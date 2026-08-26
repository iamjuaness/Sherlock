"""
Tests del modelo de conteos determinista.

Corresponden a la "Suite mínima de pruebas -> Modelos" del audit:
  - PMF suma 1 dentro de tolerancia.
  - Masa de cola menor al umbral.
  - Mismo input/versión produce mismo output.
"""

import pytest

from src.domain.settlement import Outcome, Side
from src.models.count_negative_binomial import (
    CountPMF,
    convolve,
    dispersion_r,
    nbinom_pmf,
    nbinom_pmf_vector,
    return_distribution,
    total_count_pmf,
    under_over_probabilities,
)


# ───────────────────────────── PMF ─────────────────────────────────────────

@pytest.mark.parametrize("mu,r", [(1.0, 5.0), (4.5, 8.0), (10.2, 20.0), (0.5, 1.0)])
def test_pmf_sums_to_one(mu, r):
    pmf = nbinom_pmf_vector(mu, r)
    pmf.validate()
    assert pmf.total() == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("mu,r", [(4.5, 8.0), (10.2, 20.0)])
def test_tail_mass_below_threshold(mu, r):
    pmf = nbinom_pmf_vector(mu, r)
    assert pmf.tail_mass < 1e-6


def test_pmf_mean_matches_mu():
    mu, r = 9.5, 15.0
    pmf = nbinom_pmf_vector(mu, r, max_k=200)
    assert pmf.mean == pytest.approx(mu, rel=1e-3)


def test_nbinom_pmf_nonnegative():
    for k in range(0, 40):
        assert nbinom_pmf(k, 4.0, 6.0) >= 0.0


def test_pmf_degenerate_when_mu_zero():
    pmf = nbinom_pmf_vector(0.0, 5.0)
    assert pmf.probs[0] == pytest.approx(1.0)


def test_convolution_sums_to_one_and_adds_means():
    a = nbinom_pmf_vector(4.0, 8.0, max_k=120)
    b = nbinom_pmf_vector(5.0, 9.0, max_k=120)
    tot = convolve(a, b)
    assert tot.total() == pytest.approx(1.0, abs=1e-9)
    assert tot.mean == pytest.approx(9.0, rel=1e-3)


# ───────────────────────────── determinismo ────────────────────────────────

def test_same_input_produces_same_output():
    """
    El bug original: `np.random.negative_binomial` sin semilla hacía que dos
    recálculos idénticos dieran probabilidades y picks distintos.
    """
    args = (9.5, 12.0, 8.5, 11.0)
    first = under_over_probabilities(9.5, *args)
    for _ in range(5):
        assert under_over_probabilities(9.5, *args) == first


def test_determinism_across_lines_and_markets():
    args = (4.2, 7.0, 3.8, 6.5)
    for line in (7.0, 7.25, 7.5, 7.75, 8.0):
        a = under_over_probabilities(line, *args)
        b = under_over_probabilities(line, *args)
        assert a == b


def test_pmf_cache_returns_equal_values():
    a = total_count_pmf(4.0, 8.0, 5.0, 9.0)
    b = total_count_pmf(4.0, 8.0, 5.0, 9.0)
    assert a.probs == b.probs


# ───────────────────────────── mercados ────────────────────────────────────

def test_under_over_push_sum_to_100():
    for line in (8.0, 8.25, 8.5, 8.75, 9.0):
        u, o, p = under_over_probabilities(line, 4.5, 8.0, 4.0, 7.5)
        assert u + o + p == pytest.approx(100.0, abs=1e-6)


def test_integer_line_has_push_and_half_line_does_not():
    _, _, p_int = under_over_probabilities(9.0, 4.5, 8.0, 4.5, 8.0)
    _, _, p_half = under_over_probabilities(9.5, 4.5, 8.0, 4.5, 8.0)
    assert p_int > 0.0
    assert p_half == pytest.approx(0.0, abs=1e-12)


def test_over_probability_decreases_with_line():
    args = (4.5, 8.0, 4.0, 7.5)
    overs = [under_over_probabilities(l, *args)[1]
             for l in (6.5, 7.5, 8.5, 9.5, 10.5)]
    assert overs == sorted(overs, reverse=True)


# ───────────────── distribución de retornos exacta ─────────────────────────

def test_return_distribution_sums_to_one():
    for line in (8.0, 8.25, 8.5, 8.75):
        d = return_distribution(2.0, line, Side.OVER, 4.5, 8.0, 4.0, 7.5)
        d.validate()


def test_quarter_line_produces_half_outcomes():
    """Un Over x.25 debe generar masa real en half_loss, no pérdida completa."""
    d = return_distribution(2.0, 8.25, Side.OVER, 4.5, 8.0, 4.0, 7.5)
    assert d.p_half_loss > 0.0
    assert d.p_half_win == pytest.approx(0.0, abs=1e-12)

    d75 = return_distribution(2.0, 8.75, Side.OVER, 4.5, 8.0, 4.0, 7.5)
    assert d75.p_half_win > 0.0
    assert d75.p_half_loss == pytest.approx(0.0, abs=1e-12)


def test_half_line_has_no_push_or_half_outcomes():
    d = return_distribution(2.0, 8.5, Side.OVER, 4.5, 8.0, 4.0, 7.5)
    assert d.p_push == pytest.approx(0.0, abs=1e-12)
    assert d.p_half_win == pytest.approx(0.0, abs=1e-12)
    assert d.p_half_loss == pytest.approx(0.0, abs=1e-12)


def test_over_under_distributions_are_mirrored():
    over = return_distribution(2.0, 8.25, Side.OVER, 4.5, 8.0, 4.0, 7.5)
    under = return_distribution(2.0, 8.25, Side.UNDER, 4.5, 8.0, 4.0, 7.5)
    assert over.p_win == pytest.approx(under.p_loss)
    assert over.p_half_loss == pytest.approx(under.p_half_win)


# ───────────────────────────── dispersión ──────────────────────────────────

def test_dispersion_r_poisson_limit():
    assert dispersion_r(4.0, 4.0) == 100.0        # varianza == media -> Poisson


def test_dispersion_r_overdispersed():
    r = dispersion_r(4.0, 8.0)
    assert r == pytest.approx(4.0)                 # mu^2/(var-mu) = 16/4


def test_dispersion_r_is_bounded():
    assert 0.1 <= dispersion_r(4.0, 1000.0) <= 100.0
