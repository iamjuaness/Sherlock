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


def test_segment_governance_clv_sample_floor():
    # Issue #56: CLV negativo con clv_n insuficiente (< 20) no debe penalizar por ruido
    st_noise = evaluate_segment_status(
        "Desconocida", "fouls", "over", "high_3_5",
        effective_n=40, calibration_gap_abs=0.01, recent_clv=-0.08, clv_n=5
    )
    assert st_noise == SegmentStatus.ACTIVE

    # Con muestra real (clv_n >= 20), CLV negativo sí penaliza a WATCH / REDUCED / BLOCKED
    st_sig = evaluate_segment_status(
        "Desconocida", "fouls", "over", "high_3_5",
        effective_n=40, calibration_gap_abs=0.01, recent_clv=-0.08, clv_n=25
    )
    assert st_sig == SegmentStatus.REDUCED

