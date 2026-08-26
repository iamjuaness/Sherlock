"""
Tests de invariantes de liquidación, EV y Kelly.

Corresponden a la "Suite mínima de pruebas -> Settlement" del audit:
  - Over/Under 2.0 con win, push y loss.
  - Over/Under 2.25 y 2.75 con half-win / half-loss.
  - Handicap asiático positivo y negativo.
  - Convención de tarjetas explícita.
  - Campos faltantes devuelven `unsettled`.
  - Invariante: suma de probabilidades de estados = 1.
  - Invariante: EV por suma de retornos coincide con enumeración manual.
"""

import math

import pytest

from src.domain.settlement import (
    CardsConvention,
    Outcome,
    ReturnDistribution,
    Side,
    line_legs,
    outcome_hit_value,
    outcome_return,
    settle_asian_handicap,
    settle_binary,
    settle_pick,
    settle_total,
)


# ───────────────────────────── líneas enteras ─────────────────────────────

@pytest.mark.parametrize(
    "total,expected",
    [(3, Outcome.WIN), (2, Outcome.PUSH), (1, Outcome.LOSS)],
)
def test_over_2_0_win_push_loss(total, expected):
    assert settle_total(2.0, total, Side.OVER) is expected


@pytest.mark.parametrize(
    "total,expected",
    [(1, Outcome.WIN), (2, Outcome.PUSH), (3, Outcome.LOSS)],
)
def test_under_2_0_win_push_loss(total, expected):
    assert settle_total(2.0, total, Side.UNDER) is expected


def test_half_line_never_pushes():
    for total in range(0, 8):
        assert settle_total(2.5, total, Side.OVER) in (Outcome.WIN, Outcome.LOSS)


# ───────────────────────────── líneas de cuarto ────────────────────────────

@pytest.mark.parametrize(
    "total,expected",
    [
        (3, Outcome.WIN),        # supera 2.0 y 2.5
        (2, Outcome.HALF_LOSS),  # push en 2.0, pierde 2.5  <-- bug del audit
        (1, Outcome.LOSS),
    ],
)
def test_over_2_25(total, expected):
    assert settle_total(2.25, total, Side.OVER) is expected


@pytest.mark.parametrize(
    "total,expected",
    [
        (4, Outcome.WIN),
        (3, Outcome.HALF_WIN),   # gana 2.5, push en 3.0
        (2, Outcome.LOSS),
    ],
)
def test_over_2_75(total, expected):
    assert settle_total(2.75, total, Side.OVER) is expected


@pytest.mark.parametrize(
    "total,expected",
    [(1, Outcome.WIN), (2, Outcome.HALF_WIN), (3, Outcome.LOSS)],
)
def test_under_2_25(total, expected):
    assert settle_total(2.25, total, Side.UNDER) is expected


@pytest.mark.parametrize(
    "total,expected",
    [(2, Outcome.WIN), (3, Outcome.HALF_LOSS), (4, Outcome.LOSS)],
)
def test_under_2_75(total, expected):
    assert settle_total(2.75, total, Side.UNDER) is expected


def test_line_legs_decomposition():
    assert line_legs(2.0) == (2.0,)
    assert line_legs(2.5) == (2.5,)
    assert line_legs(2.25) == (2.0, 2.5)
    assert line_legs(2.75) == (2.5, 3.0)


def test_over_and_under_are_complementary():
    """Un lado gana exactamente lo que el otro pierde."""
    mirror = {
        Outcome.WIN: Outcome.LOSS,
        Outcome.LOSS: Outcome.WIN,
        Outcome.HALF_WIN: Outcome.HALF_LOSS,
        Outcome.HALF_LOSS: Outcome.HALF_WIN,
        Outcome.PUSH: Outcome.PUSH,
    }
    for line in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0):
        for total in range(0, 8):
            o = settle_total(line, total, Side.OVER)
            u = settle_total(line, total, Side.UNDER)
            assert u is mirror[o], f"línea {line}, total {total}"


# ───────────────────────────── hándicap asiático ───────────────────────────

@pytest.mark.parametrize(
    "line,margin,expected",
    [
        (-1.0, 2, Outcome.WIN),
        (-1.0, 1, Outcome.PUSH),
        (-1.0, 0, Outcome.LOSS),
        (-0.75, 1, Outcome.HALF_WIN),    # gana -0.5, push en -1.0
        (-0.25, 0, Outcome.HALF_LOSS),   # push en 0.0, pierde -0.5
        (+0.25, -1, Outcome.LOSS),
        (+0.25, 0, Outcome.HALF_WIN),    # push en 0.0, gana +0.5
        (+0.25, 1, Outcome.WIN),
        (+0.75, -1, Outcome.HALF_LOSS),  # pierde +0.5, push en +1.0
        (+1.0, -1, Outcome.PUSH),
        (+1.25, -1, Outcome.HALF_WIN),   # push en +1.0, gana +1.5
    ],
)
def test_asian_handicap(line, margin, expected):
    assert settle_asian_handicap(line, margin) is expected


# ───────────────────────────── fallar cerrado ──────────────────────────────

def test_missing_stat_is_unsettled():
    assert settle_total(2.5, None, Side.OVER) is Outcome.UNSETTLED
    assert settle_asian_handicap(-1.0, None) is Outcome.UNSETTLED
    assert settle_binary(True, None) is Outcome.UNSETTLED


def test_unknown_line_convention_is_unsettled():
    """Una línea que no es múltiplo de 0.25 no se liquida a ciegas."""
    assert settle_total(2.3, 2, Side.OVER) is Outcome.UNSETTLED


def test_unsettled_has_no_return():
    with pytest.raises(ValueError):
        outcome_return(Outcome.UNSETTLED, 2.0)


def test_settle_pick_excludes_unsettled_from_roi():
    res = settle_pick(Outcome.UNSETTLED, 2.0)
    assert res.profit_units is None       # nunca un 0 inventado
    assert res.is_settled is False
    assert "estadistica_faltante" in res.reasons


def test_settle_pick_rejects_invalid_odds():
    assert settle_pick(Outcome.WIN, 1.0).profit_units is None
    assert settle_pick(Outcome.WIN, None).profit_units is None


# ───────────────────────────── retornos ────────────────────────────────────

def test_returns_at_odds_2():
    assert outcome_return(Outcome.WIN, 2.0) == pytest.approx(1.0)
    assert outcome_return(Outcome.HALF_WIN, 2.0) == pytest.approx(0.5)
    assert outcome_return(Outcome.PUSH, 2.0) == pytest.approx(0.0)
    assert outcome_return(Outcome.HALF_LOSS, 2.0) == pytest.approx(-0.5)
    assert outcome_return(Outcome.LOSS, 2.0) == pytest.approx(-1.0)


def test_push_returns_zero_not_negative():
    """El bug original trataba el push como pérdida."""
    for odds in (1.5, 2.0, 3.4, 10.0):
        assert outcome_return(Outcome.PUSH, odds) == 0.0


def test_half_win_is_not_a_full_hit():
    assert outcome_hit_value(Outcome.HALF_WIN) == 0.5
    assert outcome_hit_value(Outcome.WIN) == 1.0
    assert outcome_hit_value(Outcome.PUSH) is None      # fuera del hit rate
    assert outcome_hit_value(Outcome.UNSETTLED) is None


# ───────────────────────────── EV y Kelly ──────────────────────────────────

def test_probabilities_sum_to_one_invariant():
    d = ReturnDistribution(odds=2.0, p_win=0.5, p_push=0.2, p_loss=0.3)
    d.validate()
    bad = ReturnDistribution(odds=2.0, p_win=0.5, p_loss=0.2)
    with pytest.raises(ValueError):
        bad.validate()


def test_ev_matches_manual_enumeration():
    """Invariante del audit: EV por suma de retornos == enumeración manual."""
    d = ReturnDistribution(odds=2.5, p_win=0.45, p_push=0.10, p_loss=0.45)
    manual = 0.45 * 1.5 + 0.10 * 0.0 + 0.45 * -1.0
    assert d.expected_value == pytest.approx(manual)


def test_ev_with_push_is_not_scaled_legacy_way():
    """
    El código anterior calculaba  ev = (p*odds - 1) * (1 - p_push),
    que subestima el EV cuando hay push. Comprobamos la diferencia.
    """
    p_win, p_push, odds = 0.45, 0.10, 2.5
    d = ReturnDistribution(odds=odds, p_win=p_win, p_push=p_push,
                           p_loss=1 - p_win - p_push)
    correct = p_win * (odds - 1) - (1 - p_win - p_push)
    legacy = ((p_win * odds) - 1.0) * (1.0 - p_push)
    assert d.expected_value == pytest.approx(correct)
    assert not math.isclose(d.expected_value, legacy, abs_tol=1e-6)


def test_ev_quarter_line_uses_half_returns():
    d = ReturnDistribution(odds=2.0, p_win=0.40, p_half_win=0.15,
                           p_half_loss=0.15, p_loss=0.30)
    d.validate()
    manual = 0.40 * 1.0 + 0.15 * 0.5 + 0.15 * -0.5 + 0.30 * -1.0
    assert d.expected_value == pytest.approx(manual)


def test_kelly_zero_when_no_edge():
    d = ReturnDistribution.simple(odds=2.0, p_win=0.50)   # EV = 0
    assert d.kelly_fraction() == 0.0
    d2 = ReturnDistribution.simple(odds=2.0, p_win=0.40)  # EV < 0
    assert d2.kelly_fraction() == 0.0


def test_kelly_matches_bernoulli_closed_form_without_push():
    """Sin pushes, Kelly numérico == fórmula cerrada (b·p - q)/b."""
    p, odds = 0.60, 2.0
    b, q = odds - 1.0, 1.0 - p
    expected_full = (b * p - q) / b
    d = ReturnDistribution.simple(odds=odds, p_win=p)
    assert d.kelly_fraction(multiplier=1.0, hard_cap=1.0) == pytest.approx(
        expected_full, abs=1e-6
    )


def test_kelly_with_push_exceeds_naive_bernoulli():
    """
    Un push no consume bankroll, así que el Kelly correcto es MAYOR que el
    que trataba el push como pérdida (q = 1 - p).
    """
    p_win, p_push, odds = 0.50, 0.15, 2.2
    d = ReturnDistribution(odds=odds, p_win=p_win, p_push=p_push,
                           p_loss=1 - p_win - p_push)
    correct = d.kelly_fraction(multiplier=1.0, hard_cap=1.0)

    b, q = odds - 1.0, 1.0 - p_win        # el bug: push contado como pérdida
    naive = max(0.0, (b * p_win - q) / b)
    assert correct > naive


def test_kelly_respects_hard_cap():
    d = ReturnDistribution.simple(odds=5.0, p_win=0.90)
    assert d.kelly_fraction(multiplier=1.0, hard_cap=0.25) == pytest.approx(0.25)


def test_kelly_never_risks_ruin():
    """1 + f·r > 0 para todos los outcomes posibles."""
    d = ReturnDistribution(odds=1.5, p_win=0.80, p_half_loss=0.10, p_loss=0.10)
    f = d.kelly_fraction(multiplier=1.0, hard_cap=1.0)
    for _, r in d.outcomes():
        assert 1.0 + f * r > 0


def test_fair_odds_makes_ev_zero():
    d = ReturnDistribution(odds=2.0, p_win=0.45, p_push=0.10, p_loss=0.45)
    fair = d.fair_odds
    at_fair = ReturnDistribution(odds=fair, p_win=0.45, p_push=0.10, p_loss=0.45)
    assert at_fair.expected_value == pytest.approx(0.0, abs=1e-9)


# ───────────────────────────── tarjetas ────────────────────────────────────

def test_cards_convention_explicit():
    reds_as_one = CardsConvention(red_weight=1.0)
    reds_as_two = CardsConvention(red_weight=2.0)
    assert reds_as_one.total(yellows=4, reds=1) == 5.0
    assert reds_as_two.total(yellows=4, reds=1) == 6.0


def test_cards_missing_yellows_is_none_not_zero():
    """El audit: estadísticas de tarjetas ausentes se convertían en cero."""
    assert CardsConvention().total(yellows=None, reds=1) is None


def test_cards_settlement_end_to_end():
    conv = CardsConvention(red_weight=2.0)
    total = conv.total(yellows=3, reds=1)          # 5.0
    assert settle_total(4.5, total, Side.OVER) is Outcome.WIN
    assert settle_total(5.0, total, Side.OVER) is Outcome.PUSH
    # sin dato -> no se liquida
    assert settle_total(4.5, conv.total(None), Side.OVER) is Outcome.UNSETTLED
