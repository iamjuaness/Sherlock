"""
Tests de regresión para evitar reintroducir los sesgos detectados históricamente.
"""

from __future__ import annotations

import pytest
from src.domain.market_taxonomy import (
    line_bucket_for,
    market_group_key,
    normalize_market_family,
    normalize_market_side,
    parse_market,
    MarketFamily,
    MarketSide,
)
from src.models.segment_governance import (
    SegmentStatus,
    evaluate_segment_status,
    get_governance_multipliers,
)
from src.models.calibration import (
    HierarchicalCalibrator,
    CalibrationSample,
    league_family_side_bucket_key,
    family_side_bucket_key,
)
from src.models.joint_match_distribution import (
    derive_joint_match_probabilities,
    guardrail_away_win_recommendation,
)
from datetime import datetime, timedelta, timezone


# ═══════════════════════════════════════════════════════════════════════════
# 1. Primera A + Under 2.5
# ═══════════════════════════════════════════════════════════════════════════

class TestPrimeraAUnder25:
    """Regression: El segmento debe resolver su curva específica y ser bloqueable."""

    def test_bucket_resolves_core_2_5(self):
        bkt = line_bucket_for("goals", 2.5)
        assert bkt == "core_2_5"

    def test_segment_key_canonical(self):
        key = market_group_key("Primera A", "goals", "under", "core_2_5")
        assert key == "league:primera a|family:goals|side:under|bucket:core_2_5"

    def test_segment_is_blocked_by_governance(self):
        st = evaluate_segment_status("Primera A", "goals", "under", "core_2_5", effective_n=50)
        assert st == SegmentStatus.BLOCKED

    def test_blocked_segment_hard_blocks_pick(self):
        st = evaluate_segment_status("Primera A", "goals", "under", "core_2_5", effective_n=50)
        mult = get_governance_multipliers(st)
        assert mult["stake_multiplier"] == 0.0
        assert not mult["publishable"]

    def test_hierarchy_resolves_specific_curve(self):
        """league+family+side+bucket se prioriza sobre curvas menos específicas."""
        base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        samples = [
            CalibrationSample(
                prob=0.6,
                hit_value=1.0 if i % 2 == 0 else 0.0,
                market_family="goals",
                side="under",
                line_bucket="core_2_5",
                league="Primera A",
                timestamp=base_ts + timedelta(days=i),
            )
            for i in range(100)
        ]
        cal = HierarchicalCalibrator.fit(
            samples,
            min_samples_global=50,
            min_samples_family=50,
            min_samples_family_side=50,
            min_samples_family_side_bucket=50,
            min_samples_league=50,
            min_samples_league_family=50,
            min_samples_league_family_side=50,
            min_samples_league_family_side_bucket=50,
        )
        curve = cal.resolve_curve("goals", "under", "core_2_5", "Primera A")
        assert "primera a" in curve.segment
        assert "core_2_5" in curve.segment


# ═══════════════════════════════════════════════════════════════════════════
# 2. Argentina + Visitante 1X2 -> No derivar solo de X2
# ═══════════════════════════════════════════════════════════════════════════

class TestArgentinaAwayrResultGuardrail:
    """Regression: No puede derivarse la victoria visitante simplemente de X2."""

    def test_away_guardrail_rejected_when_draw_dominates(self):
        # Caso donde el empate domina la X2 -> rechazar Away Win
        ok, reason = guardrail_away_win_recommendation(
            p_away=0.30,
            p_draw=0.45,  # El empate domina (>45% de X2)
            p_x2=0.75,
            away_odds=3.0,
            segment_reliability=0.7,
        )
        assert not ok
        assert "empate domina" in reason.lower()

    def test_away_guardrail_approved_when_away_clear(self):
        ok, _ = guardrail_away_win_recommendation(
            p_away=0.48,
            p_draw=0.22,
            p_x2=0.70,
            away_odds=2.2,
            segment_reliability=0.8,
            has_clv_confirmation=True,
        )
        assert ok

    def test_away_guardrail_blocked_segment(self):
        """Liga Profesional de Fútbol + result + away está bloqueada por config."""
        st = evaluate_segment_status("Liga Profesional de Fútbol", "result", "away", "no_line", effective_n=50)
        assert st == SegmentStatus.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════
# 3. Argentina + Tiros a puerta Under 7.5-8.5 -> banda core correcta
# ═══════════════════════════════════════════════════════════════════════════

class TestArgentinaShotsTargetUnderCore:
    """Regression: Debe resolverse con banda core y calibración específica."""

    def test_shots_target_under_75_bucket(self):
        bkt = line_bucket_for("shots_target", 7.5)
        assert bkt == "core_7_5_8_5"

    def test_shots_target_under_85_bucket(self):
        bkt = line_bucket_for("shots_target", 8.5)
        assert bkt == "core_7_5_8_5"

    def test_shots_target_segment_blocked(self):
        st = evaluate_segment_status(
            "Liga Profesional de Fútbol", "shots_target", "under", "core_7_5_8_5", effective_n=50
        )
        assert st == SegmentStatus.BLOCKED

    def test_shots_target_parse_market(self):
        mk = parse_market("Tiros a Puerta Under 7.5")
        assert mk.family == MarketFamily.SHOTS_TARGET
        assert mk.side == MarketSide.UNDER
        assert mk.line == 7.5
        assert mk.line_bucket == "core_7_5_8_5"


# ═══════════════════════════════════════════════════════════════════════════
# 4. MLS + Over 3.5/4.5 goles -> high/extreme bucket, no curva genérica
# ═══════════════════════════════════════════════════════════════════════════

class TestMLSGoalsOverHighExtreme:
    """Regression: Debe usar high/extreme bucket, no la curva genérica de goals over."""

    def test_goals_35_bucket_is_high(self):
        bkt = line_bucket_for("goals", 3.5)
        assert bkt == "high_3_5"

    def test_goals_45_bucket_is_extreme(self):
        bkt = line_bucket_for("goals", 4.5)
        assert bkt == "extreme_4_plus"

    def test_mls_goals_over_35_blocked(self):
        st = evaluate_segment_status("MLS", "goals", "over", "high_3_5", effective_n=50)
        assert st == SegmentStatus.BLOCKED

    def test_mls_goals_over_45_blocked(self):
        st = evaluate_segment_status("MLS", "goals", "over", "extreme_4_plus", effective_n=50)
        assert st == SegmentStatus.BLOCKED

    def test_family_side_bucket_key_is_distinct_from_generic(self):
        key_high = family_side_bucket_key("goals", "over", "high_3_5")
        key_generic = family_side_bucket_key("goals", "over", "core_2_5")
        assert key_high != key_generic


# ═══════════════════════════════════════════════════════════════════════════
# 5. Premier League + BTTS Sí -> estado e calibración independientes
# ═══════════════════════════════════════════════════════════════════════════

class TestPremierLeagueBTTSYes:
    """Regression: Debe tener status y calibración independiente."""

    def test_btts_yes_parse(self):
        mk = parse_market("BTTS Sí")
        assert mk.family == MarketFamily.BTTS
        assert mk.side == MarketSide.YES
        assert mk.line is None
        assert mk.line_bucket == "no_line"

    def test_premier_btts_yes_blocked(self):
        st = evaluate_segment_status("Premier League", "btts", "yes", "no_line", effective_n=50)
        assert st == SegmentStatus.BLOCKED

    def test_league_family_side_bucket_key_unique(self):
        k1 = league_family_side_bucket_key("Premier League", "btts", "yes", "no_line")
        k2 = league_family_side_bucket_key("Primera A", "btts", "yes", "no_line")
        assert k1 != k2


# ═══════════════════════════════════════════════════════════════════════════
# 6. Invariantes de probabilidad en modelo conjunto
# ═══════════════════════════════════════════════════════════════════════════

class TestJointModelInvariants:
    """Regression: Los invariantes probabilísticos deben conservarse siempre."""

    @pytest.mark.parametrize("lh,mu", [
        (1.2, 0.9),
        (1.6, 1.1),
        (2.0, 1.5),
        (0.8, 0.8),
    ])
    def test_1x2_sums_to_one(self, lh, mu):
        probs = derive_joint_match_probabilities(lambda_home=lh, mu_away=mu)
        assert abs((probs.p_home_win + probs.p_draw + probs.p_away_win) - 1.0) < 1e-4

    @pytest.mark.parametrize("lh,mu", [
        (1.2, 0.9),
        (1.6, 1.1),
    ])
    def test_double_chance_consistent_with_1x2(self, lh, mu):
        probs = derive_joint_match_probabilities(lambda_home=lh, mu_away=mu)
        assert abs(probs.p_1x - (probs.p_home_win + probs.p_draw)) < 1e-4
        assert abs(probs.p_x2 - (probs.p_draw + probs.p_away_win)) < 1e-4

    @pytest.mark.parametrize("lh,mu", [
        (1.2, 0.9),
        (2.0, 1.5),
    ])
    def test_btts_sums_to_one(self, lh, mu):
        probs = derive_joint_match_probabilities(lambda_home=lh, mu_away=mu)
        assert abs((probs.p_btts_yes + probs.p_btts_no) - 1.0) < 1e-4

    @pytest.mark.parametrize("line", [0.5, 1.5, 2.5, 3.5, 4.5])
    def test_over_under_push_sums_to_one(self, line):
        probs = derive_joint_match_probabilities(lambda_home=1.6, mu_away=1.1, lines=(line,))
        over, under, push = probs.over_under_lines[line]
        assert abs((over + under + push) - 1.0) < 1e-4
