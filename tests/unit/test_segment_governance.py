import pytest
from src.models.segment_governance import SegmentStatus, evaluate_segment_status, get_governance_multipliers


def test_segment_governance_config():
    st = evaluate_segment_status("Primera A", "goals", "under", "core_2_5", effective_n=50)
    assert st == SegmentStatus.BLOCKED

    st2 = evaluate_segment_status("MLS", "cards", "over", "high_3_5", effective_n=50)
    assert st2 == SegmentStatus.REDUCED


def test_segment_governance_dynamic():
    st_exp = evaluate_segment_status("Desconocida", "fouls", "over", "high_3_5", effective_n=10)
    assert st_exp == SegmentStatus.EXPERIMENTAL

    st_act = evaluate_segment_status("Desconocida", "fouls", "over", "high_3_5", effective_n=40)
    assert st_act == SegmentStatus.ACTIVE


def test_governance_multipliers():
    m_blk = get_governance_multipliers(SegmentStatus.BLOCKED)
    assert m_blk["stake_multiplier"] == 0.0
    assert not m_blk["publishable"]

    m_red = get_governance_multipliers(SegmentStatus.REDUCED)
    assert m_red["stake_multiplier"] == 0.25
