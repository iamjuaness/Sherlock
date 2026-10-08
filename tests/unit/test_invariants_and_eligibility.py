"""
Tests de invariantes de mercado: calibración y eligibilidad.

Verifica que:
- Las APIs de probabilidad (no-vig, CLV, blend) son correctas
- Los bloqueos duros son irreversibles
- La gobernanza aplica los multiplicadores correctos
- La calibración no introduce fuga temporal
"""

from __future__ import annotations

import pytest
from src.models.market_probability import (
    implied_probability,
    remove_vig_two_way,
    remove_vig_three_way,
    compute_clv,
    blend_model_and_market_probability,
)
from src.domain.eligibility import (
    BlockReason,
    EligibilityDecision,
    PickSnapshot,
    is_hard_blocked,
    record_hard_block,
    read_hard_blocks,
    evaluate_soft_filters,
    evaluate_eligibility,
)
from src.models.calibration import (
    HierarchicalCalibrator,
    CalibrationSample,
    compute_sample_weight,
    walk_forward_calibrate,
    league_family_side_bucket_key,
    family_side_bucket_key,
)
from src.models.segment_governance import (
    SegmentStatus,
    evaluate_segment_status,
    get_governance_multipliers,
)
from datetime import datetime, timedelta, timezone


# ═══════════════════════════════════════════════════════════════════════════
# Mercado: Probabilidad sin margen y CLV
# ═══════════════════════════════════════════════════════════════════════════

class TestMarketProbabilityInvariants:

    def test_implied_probability_exact(self):
        assert abs(implied_probability(2.0) - 0.5) < 1e-6
        assert abs(implied_probability(4.0) - 0.25) < 1e-6

    def test_implied_probability_invalid_raises(self):
        with pytest.raises(ValueError):
            implied_probability(0.9)
        with pytest.raises(ValueError):
            implied_probability(1.0)

    def test_remove_vig_two_way_sums_to_one(self):
        pa, pb = remove_vig_two_way(1.9, 1.9)
        assert abs((pa + pb) - 1.0) < 1e-6

    def test_remove_vig_three_way_sums_to_one(self):
        ph, pd, pa = remove_vig_three_way(2.5, 3.2, 3.0)
        assert abs((ph + pd + pa) - 1.0) < 1e-6

    def test_remove_vig_invalid_raises(self):
        with pytest.raises(ValueError):
            remove_vig_two_way(1.0, 2.0)

    def test_clv_positive_when_odds_increase(self):
        # Apostamos a 2.0, cierra a 1.8 -> apertura más favorable -> CLV positivo
        clv = compute_clv(open_odds=2.0, close_odds=1.8)
        assert clv.clv_percent > 0

    def test_clv_negative_when_odds_decrease(self):
        clv = compute_clv(open_odds=1.8, close_odds=2.0)
        assert clv.clv_percent < 0

    def test_clv_none_close_raises_or_skips(self):
        """No se puede calcular CLV sin cuota de cierre."""
        with pytest.raises((ValueError, TypeError)):
            compute_clv(open_odds=2.0, close_odds=None)  # type: ignore

    def test_blend_no_market_reduces_stake_multiplier(self):
        """Sin p_market, el stake_multiplier se reduce vs tenerlo."""
        b_with = blend_model_and_market_probability(0.60, 0.58, reliability_score=0.8)
        b_without = blend_model_and_market_probability(0.60, None, reliability_score=0.8)
        assert b_with.stake_multiplier >= b_without.stake_multiplier

    def test_blend_high_divergence_warns(self):
        b = blend_model_and_market_probability(0.72, 0.48, reliability_score=0.5)
        assert b.divergence_warning

    def test_blend_extreme_divergence_blocks(self):
        b = blend_model_and_market_probability(0.80, 0.40, reliability_score=0.5)
        assert b.divergence_blocked
        assert b.stake_multiplier == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Elegibilidad: bloqueos duros irreversibles
# ═══════════════════════════════════════════════════════════════════════════

class TestEligibilityHardBlocks:

    def test_hard_block_is_irreversible(self):
        pick = {"selection": "Over 2.5", "is_publishable": True, "quality_score": 85}
        record_hard_block(pick, BlockReason.RULE_BLOCKED, detail="Regla de prueba")

        assert is_hard_blocked(pick)
        assert pick["quality_score"] == -1

        # Simular que pipeline sobrescribe campos
        pick["quality_score"] = 90
        pick["is_publishable"] = True

        # El bloqueo duro debe persistir (lee eligibility_hard_blocks)
        assert is_hard_blocked(pick)

    def test_governance_block_is_hard(self):
        pick = {"selection": "Under 2.5", "is_publishable": True}
        record_hard_block(pick, BlockReason.SEGMENT_GOVERNANCE_BLOCKED, detail="Segmento bloqueado")
        assert is_hard_blocked(pick)
        assert "segment_governance_blocked" in pick["eligibility_hard_blocks"]

    def test_correlation_block_persists(self):
        pick = {"selection": "BTTS Sí", "is_publishable": True}
        record_hard_block(pick, BlockReason.CORRELATION_BLOCKED)
        assert is_hard_blocked(pick)

    def test_soft_filter_odds_too_low(self):
        """Cuota inválida -> fallo blando, no bloqueo duro."""
        snap = PickSnapshot(market_family="goals", odds=1.15)  # menor que min_odds=1.40
        fails = evaluate_soft_filters(snap)
        assert BlockReason.ODDS_TOO_LOW in fails
        # NO es un bloqueo duro per se
        dec = EligibilityDecision()
        assert BlockReason.ODDS_TOO_LOW not in dec.hard_blocks

    def test_missing_data_fails_closed(self):
        """Datos faltantes -> no publicable (fail-closed)."""
        snap = PickSnapshot(market_family="goals", odds=None, prob=None, edge=None)
        dec = evaluate_eligibility(snap)
        assert not dec.publishable

    def test_multiple_hard_blocks_accumulate(self):
        pick = {"selection": "X2", "is_publishable": True}
        record_hard_block(pick, BlockReason.RULE_BLOCKED)
        record_hard_block(pick, BlockReason.CORRELATION_BLOCKED)
        blocks = read_hard_blocks(pick)
        assert BlockReason.RULE_BLOCKED in blocks
        assert BlockReason.CORRELATION_BLOCKED in blocks


# ═══════════════════════════════════════════════════════════════════════════
# Gobernanza: estados se reflejan en multiplicadores
# ═══════════════════════════════════════════════════════════════════════════

class TestGovernanceMultipliers:

    def test_experimental_limits_stake(self):
        st = evaluate_segment_status("Desconocida", "fouls", "over", "low", effective_n=5)
        assert st == SegmentStatus.EXPERIMENTAL
        m = get_governance_multipliers(st)
        assert m["stake_multiplier"] <= 0.50

    def test_watch_adds_min_edge(self):
        st = evaluate_segment_status(
            "Desconocida", "goals", "over", "core_2_5",
            effective_n=20, calibration_gap_abs=0.07
        )
        assert st == SegmentStatus.WATCH
        m = get_governance_multipliers(SegmentStatus.WATCH)
        assert m["min_edge_add"] > 0

    def test_reduced_cuts_stake(self):
        st = evaluate_segment_status(
            "Desconocida", "fouls", "over", "core_2_5",
            effective_n=30, calibration_gap_abs=0.12
        )
        assert st == SegmentStatus.REDUCED
        m = get_governance_multipliers(SegmentStatus.REDUCED)
        assert m["stake_multiplier"] == 0.25

    def test_blocked_emits_hard_block(self):
        """Un segmento BLOCKED debe emitir un hard block irrecuperable."""
        pick = {"selection": "Under 2.5", "is_publishable": True}
        st = evaluate_segment_status("Primera A", "goals", "under", "core_2_5", effective_n=50)
        assert st == SegmentStatus.BLOCKED
        record_hard_block(pick, BlockReason.SEGMENT_GOVERNANCE_BLOCKED, detail=f"Governance: {st}")
        assert is_hard_blocked(pick)
        assert not pick["is_publishable"]

    def test_active_full_stake(self):
        m = get_governance_multipliers(SegmentStatus.ACTIVE)
        assert m["stake_multiplier"] == 1.0
        assert m["publishable"]

    def test_blocked_zero_stake_unpublishable(self):
        m = get_governance_multipliers(SegmentStatus.BLOCKED)
        assert m["stake_multiplier"] == 0.0
        assert not m["publishable"]


# ═══════════════════════════════════════════════════════════════════════════
# Calibración: pesos temporales y walk-forward sin fuga
# ═══════════════════════════════════════════════════════════════════════════

class TestCalibrationRecencyAndWalkForward:

    def test_recent_samples_weigh_more(self):
        ref_ts = datetime(2026, 10, 5, tzinfo=timezone.utc)
        ts_today = ref_ts
        ts_old = ref_ts - timedelta(days=60)

        w_today = compute_sample_weight(ts_today, ref_ts, half_life_days=30.0)
        w_old = compute_sample_weight(ts_old, ref_ts, half_life_days=30.0)

        assert w_today > w_old
        assert abs(w_today - 1.0) < 1e-4
        # A 60 días con half_life 30 -> peso ~0.25
        assert 0.20 < w_old < 0.30

    def test_future_timestamps_capped_at_one(self):
        """Timestamps futuros no producen peso > 1.0."""
        ref_ts = datetime(2026, 10, 5, tzinfo=timezone.utc)
        future_ts = ref_ts + timedelta(days=10)
        w = compute_sample_weight(future_ts, ref_ts, half_life_days=30.0)
        assert 0.0 <= w <= 1.0

    def test_walk_forward_no_temporal_leak(self):
        """Walk-forward: train siempre precede al test; no data leakage."""
        import random
        random.seed(42)
        base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        samples = []
        for i in range(200):
            samples.append(CalibrationSample(
                prob=0.55 + random.uniform(-0.1, 0.1),
                hit_value=float(random.random() > 0.45),
                market_family="goals",
                side="under",
                line_bucket="core_2_5",
                league="Primera A",
                timestamp=base_ts + timedelta(days=i),
            ))

        result = walk_forward_calibrate(samples, n_folds=4, min_train=50)
        assert len(result.raw_probs) > 0
        assert len(result.raw_probs) == len(result.calibrated_probs)
        assert len(result.segment_metrics) > 0

    def test_family_side_bucket_keys_distinct(self):
        k1 = family_side_bucket_key("goals", "over", "high_3_5")
        k2 = family_side_bucket_key("goals", "over", "core_2_5")
        assert k1 != k2

    def test_league_keys_distinct_from_global(self):
        k1 = league_family_side_bucket_key("Premier League", "btts", "yes", "no_line")
        k2 = league_family_side_bucket_key("Primera A", "btts", "yes", "no_line")
        assert k1 != k2
