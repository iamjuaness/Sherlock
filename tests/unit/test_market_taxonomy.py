import pytest
from src.domain.market_taxonomy import (
    MarketFamily,
    MarketSide,
    extract_market_line,
    line_bucket_for,
    market_group_key,
    normalize_market_family,
    normalize_market_side,
    parse_market,
)


def test_market_taxonomy_parsing():
    m1 = parse_market("Under 2.5 Goles")
    assert m1.family == MarketFamily.GOALS
    assert m1.side == MarketSide.UNDER
    assert m1.line == 2.5
    assert m1.line_bucket == "core_2_5"

    m2 = parse_market("BTTS Sí")
    assert m2.family == MarketFamily.BTTS
    assert m2.side == MarketSide.YES
    assert m2.line is None
    assert m2.line_bucket == "no_line"

    m3 = parse_market("Doble Oportunidad X2")
    assert m3.family == MarketFamily.DOUBLE_CHANCE
    assert m3.side == MarketSide.DRAW_AWAY
    assert m3.line is None
    assert m3.line_bucket == "no_line"

    m4 = parse_market("Visitante")
    assert m4.family == MarketFamily.RESULT
    assert m4.side == MarketSide.AWAY
    assert m4.line is None
    assert m4.line_bucket == "no_line"


def test_line_buckets():
    assert line_bucket_for("goals", 1.5) == "low_0_5_1_5"
    assert line_bucket_for("goals", 2.5) == "core_2_5"
    assert line_bucket_for("goals", 3.5) == "high_3_5"
    assert line_bucket_for("goals", 4.5) == "extreme_4_plus"
    assert line_bucket_for("cards", 4.5) == "core_4_5"
    assert line_bucket_for("corners", 9.5) == "core"


def test_market_group_key():
    key = market_group_key("Primera A", "goals", "under", "core_2_5")
    assert key == "league:primera a|family:goals|side:under|bucket:core_2_5"
