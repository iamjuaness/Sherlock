"""
Regresión a nivel de `compare.py`: verifica que las correcciones P0 están
efectivamente conectadas al motor que usa la API, no solo en los módulos nuevos.
"""

import pytest

compare = pytest.importorskip("src.ui.api.compare")


# ───────────────────────── determinismo ────────────────────────────────────

def test_nbinom_market_is_deterministic():
    """Dos recálculos idénticos deben dar exactamente el mismo resultado."""
    args = (9.0, 4.5, 8.0, 4.0, 7.5)
    first = compare.get_nbinom_under_over_prob(*args)
    for _ in range(10):
        assert compare.get_nbinom_under_over_prob(*args) == first


def test_nbinom_probabilities_sum_to_100():
    for line in (8.0, 8.25, 8.5, 8.75, 9.0):
        u, o, p = compare.get_nbinom_under_over_prob(line, 4.5, 8.0, 4.0, 7.5)
        assert u + o + p == pytest.approx(100.0, abs=1e-6)


def test_quarter_line_halves_the_push():
    """
    Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con
    la mitad del push, porque la otra mitad es half-loss.
    """
    u0, o0, p0 = compare.get_nbinom_under_over_prob(9.0, 4.5, 8.0, 4.0, 7.5)
    u25, o25, p25 = compare.get_nbinom_under_over_prob(9.25, 4.5, 8.0, 4.0, 7.5)
    assert o25 == pytest.approx(o0, abs=1e-9)
    assert p25 == pytest.approx(p0 / 2.0, abs=1e-9)
    assert u25 == pytest.approx(u0 + p0 / 2.0, abs=1e-9)


def test_num_sim_argument_is_ignored():
    a = compare.get_nbinom_under_over_prob(9.5, 4.5, 8.0, 4.0, 7.5, 1000)
    b = compare.get_nbinom_under_over_prob(9.5, 4.5, 8.0, 4.0, 7.5, 999999)
    assert a == b


# ───────────────────────── Kelly ───────────────────────────────────────────

def test_kelly_without_push_matches_legacy_closed_form():
    """Sin pushes el resultado no cambia: no rompemos el comportamiento previo."""
    for prob, odds in ((60.0, 2.0), (82.1, 1.55), (28.7, 5.40)):
        p, b = prob / 100.0, odds - 1.0
        legacy_full = (b * p - (1 - p)) / b
        expected = round(min(max(legacy_full, 0.0) * 0.25, 0.25), 6)
        got = compare._calculate_kelly_fraction(prob, odds)
        assert got == pytest.approx(expected, abs=1e-6)


def test_kelly_no_value_returns_zero():
    """EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo."""
    assert compare._calculate_kelly_fraction(40.0, 2.46) == 0.0
    assert compare._calculate_kelly_fraction(50.0, 2.0) == 0.0   # EV exactamente 0


def test_kelly_tiny_edge_is_tiny_but_positive():
    """40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño."""
    kf = compare._calculate_kelly_fraction(40.7, 2.46)
    assert 0.0 < kf < 0.001


def test_kelly_with_push_is_higher_than_bernoulli():
    """El push no consume banca, así que el stake óptimo es mayor."""
    prob, odds, push = 50.0, 2.2, 15.0
    with_push = compare._calculate_kelly_fraction(prob, odds, push_prob=push)
    without = compare._calculate_kelly_fraction(prob, odds)
    assert with_push > without > 0.0


def test_kelly_invalid_inputs():
    assert compare._calculate_kelly_fraction(60.0, None) == 0.0
    assert compare._calculate_kelly_fraction(60.0, 1.0) == 0.0
    assert compare._calculate_kelly_fraction(None, 2.0) == 0.0


# ───────────────────────── EV con push ─────────────────────────────────────

def test_value_indicator_ev_treats_push_as_zero_return():
    """
    El bug: EV se calculaba como (p·odds - 1)·(1 - p_push), tratando el push
    como pérdida. El EV correcto es P(win)·(odds-1) - P(loss).
    """
    prob, odds, push = 45.0, 2.5, 10.0
    v = compare._value_indicator("Over 2.0 Goles", odds, prob, push_p=push)

    p_win, p_push = prob / 100.0, push / 100.0
    # calibrated_prob puede diferir de model_prob; recalculamos con la que usó.
    cal = v.calibrated_prob / 100.0
    expected = cal * (odds - 1.0) - (1.0 - cal - p_push)
    assert v.edge_ev == pytest.approx(round(expected, 3), abs=2e-3)

    legacy = ((cal * odds) - 1.0) * (1.0 - p_push)
    assert v.edge_ev != pytest.approx(round(legacy, 3), abs=1e-4)


def test_value_indicator_without_push_is_stable():
    """Sin push, EV sigue siendo (p·odds) - 1."""
    v = compare._value_indicator("Over 2.5 Goles", 2.5, 45.0, push_p=0.0)
    cal = v.calibrated_prob / 100.0
    assert v.edge_ev == pytest.approx(round(cal * 2.5 - 1.0, 3), abs=2e-3)


def test_value_indicator_fair_odds_consistent():
    v = compare._value_indicator("Over 2.0 Goles", 2.5, 45.0, push_p=10.0)
    assert v.fair_odds is not None
    assert v.fair_odds > 1.0


def test_value_indicator_is_deterministic():
    fixed_date = "2024-06-01T12:00:00Z"
    a = compare._value_indicator("Over 2.0 Goles", 2.5, 45.0, push_p=10.0, match_date=fixed_date)
    b = compare._value_indicator("Over 2.0 Goles", 2.5, 45.0, push_p=10.0, match_date=fixed_date)
    assert a.model_dump() == b.model_dump()


def test_invalid_odds_returns_neutral_indicator():
    v = compare._value_indicator("Over 2.5 Goles", None, 45.0)
    assert v.is_value is False
    assert v.odds is None
