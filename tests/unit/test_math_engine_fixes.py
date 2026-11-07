import math

from src.models.market_probability import compute_clv, remove_vig_power
from src.ui.api.compare import _calculate_stake_units


def test_vig_power_sums_to_one_and_favours_longshot_correction():
    p = remove_vig_power([1.50, 4.20, 6.50])
    assert abs(sum(p) - 1.0) < 1e-6
    assert all(0 < x < 1 for x in p)


def test_vig_invalid_odds_returns_empty_not_misaligned():
    assert remove_vig_power([1.9, 0.0, 3.0]) == []


def test_clv_sign_consistent():
    r = compute_clv(open_odds=2.20, close_odds=2.00)  # tomamos mejor cuota que el cierre
    assert r.clv_percent > 0 and r.clv_log > 0


def test_stake_from_kelly_no_floor_and_cap():
    assert _calculate_stake_units(0.05, 2.0, 0.001, "goals", 0.5) == 0.0  # sin piso 0.25u
    assert _calculate_stake_units(0.30, 2.0, 0.20, "goals", 0.5) == 3.0  # tope 3%
    assert _calculate_stake_units(0.05, 2.0, 0.02, "corners", 0.5) == 1.0  # corners x0.5
    assert math.isclose(_calculate_stake_units(0.01, 2.0, 0.05, "goals", 0.5), 0.0)  # edge < 2%


def test_correlated_exposure_bounds():
    from types import SimpleNamespace as NS

    from src.domain.portfolio import _correlated_exposure

    a = NS(selection="Over 2.5 Goles", kelly_fraction=0.04)
    b = NS(selection="BTTS Sí", kelly_fraction=0.04)
    e = _correlated_exposure([a, b])
    assert 0.04 < e <= 0.08  # entre un pick solo y la suma lineal
    assert abs(_correlated_exposure([a]) - 0.04) < 1e-9
