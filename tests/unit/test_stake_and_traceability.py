"""
Tests del motor de stake y trazabilidad.
"""

from __future__ import annotations

import pytest
from src.domain.stake_engine import (
    RiskPolicy,
    StakeFactors,
    EdgeResult,
    compute_edge,
    kelly_fractional,
    compute_stake_final,
    compute_risk_decision,
)
from src.domain.traceability import (
    PickTrace,
    SegmentReport,
    compute_segment_report,
    generate_segment_reports,
)


# ═══════════════════════════════════════════════════════════════════════════
# Kelly Fraccionado
# ═══════════════════════════════════════════════════════════════════════════

class TestKellyFractional:

    def test_kelly_zero_when_no_edge(self):
        # p=0.45, odds=2.0 -> expected value < 0 -> Kelly <= 0
        k = kelly_fractional(p=0.45, odds=2.0, fraction=0.25)
        assert k == 0.0

    def test_kelly_positive_with_edge(self):
        # p=0.55, odds=2.0 -> edge real -> Kelly > 0
        k = kelly_fractional(p=0.55, odds=2.0, fraction=0.25)
        assert k > 0.0

    def test_kelly_proportional_to_fraction(self):
        k_quarter = kelly_fractional(p=0.60, odds=2.0, fraction=0.25)
        k_half = kelly_fractional(p=0.60, odds=2.0, fraction=0.50)
        assert abs(k_half - 2 * k_quarter) < 1e-6

    def test_kelly_invalid_odds(self):
        k = kelly_fractional(p=0.60, odds=0.9, fraction=0.25)
        assert k == 0.0

    def test_kelly_full_stays_below_one(self):
        k = kelly_fractional(p=0.99, odds=100.0, fraction=1.0)
        assert 0.0 <= k <= 1.0


# ═══════════════════════════════════════════════════════════════════════════
# Edge: raw / calibrado / final
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeComputation:

    def test_edge_final_uses_p_final_not_raw(self):
        e = compute_edge(
            p_final=0.62,
            odds=2.0,
            p_model_raw=0.55,
            p_calibrated=0.60,
        )
        expected_final = (0.62 * 2.0 - 1.0) * 100.0
        assert abs(e.edge_final - expected_final) < 1e-4

    def test_edge_raw_uses_model_raw(self):
        e = compute_edge(
            p_final=0.62,
            odds=2.0,
            p_model_raw=0.55,
        )
        expected_raw = (0.55 * 2.0 - 1.0) * 100.0
        assert abs(e.edge_raw - expected_raw) < 1e-4

    def test_edge_zero_when_no_raw(self):
        e = compute_edge(p_final=0.62, odds=2.0, p_model_raw=None)
        assert e.edge_raw == 0.0

    def test_edge_negative_when_below_breakeven(self):
        e = compute_edge(p_final=0.40, odds=2.0)
        assert e.edge_final < 0.0

    def test_edge_invalid_odds_raises(self):
        with pytest.raises(ValueError):
            compute_edge(p_final=0.60, odds=0.9)

    def test_breakeven_correct(self):
        e = compute_edge(p_final=0.60, odds=2.5)
        assert abs(e.breakeven_prob - (1.0 / 2.5)) < 1e-6


# ═══════════════════════════════════════════════════════════════════════════
# Stake final con factores
# ═══════════════════════════════════════════════════════════════════════════

class TestStakeEngine:

    def _default_policy(self) -> RiskPolicy:
        return RiskPolicy()

    def _default_factors(self, **kwargs) -> StakeFactors:
        base = dict(
            kelly_base=0.02,
            reliability_score=0.80,
            data_quality_factor=1.0,
            drift_factor=1.0,
            correlation_factor=1.0,
            exposure_factor=1.0,
            governance_multiplier=1.0,
            segment_status="active",
        )
        base.update(kwargs)
        return StakeFactors(**base)

    def test_normal_stake_within_limits(self):
        stake, reason = compute_stake_final(
            self._default_factors(),
            self._default_policy(),
        )
        assert stake > 0.0
        assert 0.005 <= stake <= 0.05

    def test_blocked_governance_zeroes_stake(self):
        factors = self._default_factors(governance_multiplier=0.0)
        stake, _ = compute_stake_final(factors, self._default_policy())
        assert stake == 0.0

    def test_low_reliability_zeroes_stake(self):
        factors = self._default_factors(reliability_score=0.30)
        stake, reason = compute_stake_final(factors, self._default_policy())
        assert stake == 0.0
        assert "reliability" in reason.lower()

    def test_experimental_capped(self):
        factors = self._default_factors(kelly_base=0.05, segment_status="experimental")
        policy = RiskPolicy(experimental_stake_cap=0.015)
        stake, _ = compute_stake_final(factors, policy)
        assert stake <= 0.015

    def test_match_exposure_cap(self):
        factors = self._default_factors(kelly_base=0.03)
        policy = RiskPolicy(max_stake_per_match=0.08)
        # Ya tenemos 0.07 apostado en este partido -> solo queda 0.01
        stake, reason = compute_stake_final(
            factors, policy, existing_match_stake=0.07
        )
        assert stake <= 0.01

    def test_below_min_stake_returns_zero(self):
        factors = self._default_factors(kelly_base=0.001, reliability_score=0.80)
        policy = RiskPolicy(min_stake=0.005)
        stake, reason = compute_stake_final(factors, policy)
        assert stake == 0.0
        assert "min_stake" in reason.lower()

    def test_all_factors_multiply(self):
        factors = StakeFactors(
            kelly_base=0.10,
            reliability_score=0.8,
            data_quality_factor=0.9,
            drift_factor=0.8,
            correlation_factor=0.7,
            exposure_factor=1.0,
            governance_multiplier=0.5,
            segment_status="reduced",
        )
        raw = 0.10 * 0.8 * 0.9 * 0.8 * 0.7 * 1.0 * 0.5
        policy = RiskPolicy(min_stake=0.001, max_stake=1.0)
        stake, _ = compute_stake_final(factors, policy)
        assert abs(stake - min(raw, policy.max_stake)) < 1e-4

    def test_risk_decision_not_publishable_when_blocked(self):
        from src.domain.stake_engine import compute_risk_decision
        factors = self._default_factors(governance_multiplier=0.0)
        rd = compute_risk_decision(
            p_final=0.60, odds=2.0,
            policy=self._default_policy(),
            factors=factors,
        )
        assert not rd.is_publishable
        assert rd.block_reason == "governance_blocked"

    def test_risk_decision_publishable_with_edge(self):
        rd = compute_risk_decision(
            p_final=0.62, odds=2.0,
            policy=self._default_policy(),
            factors=self._default_factors(),
        )
        assert rd.is_publishable
        assert rd.edge_final > 0.0
        assert rd.stake_final > 0.0

    def test_risk_decision_not_publishable_without_edge(self):
        rd = compute_risk_decision(
            p_final=0.40, odds=2.0,
            policy=self._default_policy(),
            factors=self._default_factors(),
        )
        assert not rd.is_publishable
        assert rd.edge_final < 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Trazabilidad y Reportes de Segmento
# ═══════════════════════════════════════════════════════════════════════════

def _make_trace(
    segment_key: str = "league:prem|family:goals|side:over|bucket:core_2_5",
    final_probability: float = 0.60,
    open_odds: float = 2.0,
    stake_final: float = 0.02,
    clv_percent: float = 3.5,
    segment_status: str = "active",
) -> PickTrace:
    return PickTrace(
        market_family="goals",
        market_side="over",
        line=2.5,
        line_bucket="core_2_5",
        segment_key=segment_key,
        league="Premier League",
        model_probability_raw=0.58,
        calibrated_probability=0.59,
        market_probability_no_vig=0.52,
        final_probability=final_probability,
        edge_raw=16.0,
        edge_calibrated=18.0,
        edge_final=20.0,
        ev=(final_probability * open_odds) - 1.0,
        kelly_base=0.025,
        stake_pre_risk=0.025,
        stake_final=stake_final,
        reliability_score=0.80,
        reliability_components={"base": 0.80},
        segment_status=segment_status,
        open_odds=open_odds,
        clv_percent=clv_percent,
        policy_version="1.0",
    )


class TestPickTrace:

    def test_publishable_when_no_hard_blocks(self):
        t = _make_trace()
        assert t.is_publishable

    def test_not_publishable_with_hard_block(self):
        t = _make_trace()
        t.hard_blocks.append("rule_blocked")
        assert not t.is_publishable

    def test_to_dict_has_all_required_fields(self):
        t = _make_trace()
        d = t.to_dict()
        required_fields = [
            "market_family", "market_side", "line", "line_bucket", "segment_key",
            "model_probability_raw", "calibrated_probability", "market_probability_no_vig",
            "final_probability", "edge_raw", "edge_calibrated", "edge_final", "ev",
            "kelly_base", "stake_pre_risk", "stake_final", "reliability_score",
            "segment_status", "policy_version", "open_odds", "clv_percent",
            "hard_blocks", "soft_failures", "is_publishable",
        ]
        for f in required_fields:
            assert f in d, f"Campo faltante: {f}"


class TestSegmentReports:

    def _traces_and_outcomes(self, n: int = 30, hit_rate: float = 0.55):
        import random
        random.seed(42)
        traces = [_make_trace() for _ in range(n)]
        outcomes = [1.0 if random.random() < hit_rate else 0.0 for _ in range(n)]
        return traces, outcomes

    def test_report_hits_match_outcomes(self):
        traces, outcomes = self._traces_and_outcomes(30, 0.6)
        rep = compute_segment_report(
            segment_key="seg1",
            league="Premier League",
            market_family="goals",
            market_side="over",
            line_bucket="core_2_5",
            traces=traces,
            outcomes=outcomes,
        )
        assert rep.n_settled == 30
        assert abs(rep.hit_rate - sum(outcomes) / 30) < 1e-6

    def test_brier_score_bounded(self):
        traces, outcomes = self._traces_and_outcomes(50)
        rep = compute_segment_report(
            "seg2", "PL", "goals", "over", "core_2_5", traces, outcomes
        )
        assert 0.0 <= rep.brier_score <= 1.0

    def test_recommendation_blocked_segment(self):
        traces, outcomes = self._traces_and_outcomes(20)
        rep = compute_segment_report(
            "seg3", "PL", "goals", "over", "core_2_5", traces, outcomes,
            segment_status="blocked"
        )
        assert rep.recommendation == "blocked"

    def test_recommendation_small_sample_observes(self):
        traces, outcomes = self._traces_and_outcomes(5)
        rep = compute_segment_report(
            "seg4", "PL", "goals", "over", "core_2_5", traces, outcomes[:5]
        )
        assert rep.recommendation == "observe"

    def test_generate_segment_reports_groups_correctly(self):
        seg_key = "league:prem|family:goals|side:over|bucket:core_2_5"
        traces = [_make_trace(segment_key=seg_key) for _ in range(10)]
        outcomes: list = [1.0] * 6 + [0.0] * 4
        reports = generate_segment_reports(traces, outcomes)
        assert seg_key in reports
        assert reports[seg_key].n_picks == 10

    def test_pending_outcomes_excluded(self):
        traces, outcomes = self._traces_and_outcomes(20)
        # Marcar la mitad como pending
        mixed_outcomes = [o if i % 2 == 0 else None for i, o in enumerate(outcomes)]
        rep = compute_segment_report(
            "seg5", "PL", "goals", "over", "core_2_5", traces, mixed_outcomes
        )
        assert rep.n_settled == 10  # solo los settled
        assert rep.n_picks == 20

    def test_to_dict_has_all_metric_fields(self):
        traces, outcomes = self._traces_and_outcomes(20)
        rep = compute_segment_report(
            "seg6", "PL", "goals", "over", "core_2_5", traces, outcomes
        )
        d = rep.to_dict()
        for field in ["roi", "yield_pct", "profit", "staked", "hit_rate",
                      "breakeven_rate", "avg_clv", "brier_score", "log_loss",
                      "ece", "calibration_gap", "drift_score", "recommendation"]:
            assert field in d, f"Campo faltante: {field}"
