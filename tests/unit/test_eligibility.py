"""
Tests del dominio de elegibilidad.

Invariante central: la elegibilidad es MONÓTONA DECRECIENTE. Un pick puede
pasar de publicable a bloqueado, nunca al revés. Ninguna secuencia de
reevaluaciones puede limpiar un bloqueo duro.
"""

import pytest

from src.domain.eligibility import (
    BINARY_FAMILIES,
    DEFAULT_THRESHOLDS,
    HARD_BLOCKS,
    HIGH_VARIANCE_FAMILIES,
    POLICY_VERSION,
    BlockReason,
    EligibilityDecision,
    PickSnapshot,
    PublicationThresholds,
    describe,
    evaluate_eligibility,
    evaluate_soft_filters,
    hard_blocks_from_flags,
    is_hard,
)


def good_snapshot(**over) -> PickSnapshot:
    """Un pick que pasa todos los filtros blandos."""
    base = dict(
        market_family="goals", odds=1.90, prob=65.0, edge=8.0,
        data_quality_score=80.0, stake_units=1.5,
        h2h_hit_rate=None, h2h_samples=0, selection="over_2.5_goals",
    )
    base.update(over)
    return PickSnapshot(**base)


# ═══════════════════ clasificación de motivos ══════════════════════════

def test_hard_and_soft_reasons_are_disjoint():
    all_reasons = set(BlockReason)
    soft = all_reasons - HARD_BLOCKS
    assert HARD_BLOCKS & soft == set()
    assert HARD_BLOCKS | soft == all_reasons


def test_every_reason_has_a_human_label():
    for r in BlockReason:
        assert describe(r) and describe(r) != r.value


def test_unknown_reason_is_treated_as_hard():
    """Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo."""
    assert is_hard("motivo_inventado") is True


def test_known_soft_reason_is_not_hard():
    assert is_hard(BlockReason.EDGE_TOO_LOW) is False
    assert is_hard(BlockReason.RULE_BLOCKED) is True


# ═══════════════════ filtros blandos ═══════════════════════════════════

def test_good_pick_has_no_soft_failures():
    assert evaluate_soft_filters(good_snapshot()) == frozenset()


@pytest.mark.parametrize("odds,expected", [
    (None, BlockReason.ODDS_MISSING),
    (1.20, BlockReason.ODDS_TOO_LOW),
    (3.50, BlockReason.ODDS_TOO_HIGH),
])
def test_odds_bounds(odds, expected):
    assert expected in evaluate_soft_filters(good_snapshot(odds=odds))


def test_odds_boundaries_are_inclusive():
    """1.40 y 2.50 deben pasar: eran los límites del código original."""
    assert evaluate_soft_filters(good_snapshot(odds=1.40)) == frozenset()
    assert evaluate_soft_filters(good_snapshot(odds=2.50)) == frozenset()


def test_binary_market_requires_60_percent():
    assert BlockReason.PROB_BELOW_THRESHOLD in evaluate_soft_filters(
        good_snapshot(market_family="result", prob=59.9)
    )
    assert evaluate_soft_filters(
        good_snapshot(market_family="result", prob=60.0)
    ) == frozenset()


def test_high_variance_market_requires_only_20_percent():
    assert evaluate_soft_filters(
        good_snapshot(market_family="cards", prob=20.0)
    ) == frozenset()
    assert BlockReason.PROB_BELOW_THRESHOLD in evaluate_soft_filters(
        good_snapshot(market_family="cards", prob=19.9)
    )


def test_default_market_requires_35_percent():
    assert evaluate_soft_filters(
        good_snapshot(market_family="generic", prob=35.0)
    ) == frozenset()
    assert BlockReason.PROB_BELOW_THRESHOLD in evaluate_soft_filters(
        good_snapshot(market_family="generic", prob=34.9)
    )


def test_threshold_families_match_the_legacy_sets():
    """Centralizar los umbrales no debe cambiar qué mercados se publican."""
    assert BINARY_FAMILIES == {"result", "btts", "goals"}
    assert HIGH_VARIANCE_FAMILIES == {
        "cards", "shots", "shots_target", "fouls", "corners"
    }


@pytest.mark.parametrize("edge,expected", [
    (None, BlockReason.EDGE_MISSING),
    (2.4, BlockReason.EDGE_TOO_LOW),
    (25.1, BlockReason.EDGE_TOO_HIGH),
])
def test_edge_bounds(edge, expected):
    assert expected in evaluate_soft_filters(good_snapshot(edge=edge))


def test_data_quality_floor():
    assert BlockReason.DATA_QUALITY_TOO_LOW in evaluate_soft_filters(
        good_snapshot(data_quality_score=49.9)
    )


def test_stake_floor():
    assert BlockReason.STAKE_TOO_LOW in evaluate_soft_filters(
        good_snapshot(stake_units=0.9)
    )


def test_zero_h2h_with_samples_blocks():
    assert BlockReason.H2H_ZERO_HIT_RATE in evaluate_soft_filters(
        good_snapshot(h2h_hit_rate=0.0, h2h_samples=4)
    )


def test_zero_h2h_without_samples_does_not_block():
    """0% sin muestra no es información, es ausencia de información."""
    assert evaluate_soft_filters(
        good_snapshot(h2h_hit_rate=0.0, h2h_samples=0)
    ) == frozenset()


def test_missing_prob_fails_closed():
    assert BlockReason.PROB_MISSING in evaluate_soft_filters(good_snapshot(prob=None))


def test_multiple_failures_are_all_reported():
    fails = evaluate_soft_filters(good_snapshot(odds=1.1, edge=0.5, stake_units=0.2))
    assert BlockReason.ODDS_TOO_LOW in fails
    assert BlockReason.EDGE_TOO_LOW in fails
    assert BlockReason.STAKE_TOO_LOW in fails


def test_custom_thresholds_are_honoured():
    strict = PublicationThresholds(min_edge=10.0)
    assert BlockReason.EDGE_TOO_LOW in evaluate_soft_filters(
        good_snapshot(edge=8.0), strict
    )
    assert evaluate_soft_filters(good_snapshot(edge=8.0)) == frozenset()


# ═══════════════════ inmutabilidad del bloqueo ═════════════════════════

def test_hard_block_makes_pick_unpublishable():
    d = evaluate_eligibility(good_snapshot(), hard_blocks=[BlockReason.RULE_BLOCKED])
    assert d.publishable is False
    assert d.is_hard_blocked is True


def test_hard_block_survives_reevaluation_with_perfect_pick():
    """
    EL BUG ORIGINAL: recalcular con un pick que pasa todos los filtros
    devolvía publicable y borraba el bloqueo. Debe seguir bloqueado.
    """
    blocked = evaluate_eligibility(
        good_snapshot(), hard_blocks=[BlockReason.RULE_BLOCKED]
    )
    again = evaluate_eligibility(good_snapshot(), previous=blocked)
    assert again.publishable is False
    assert BlockReason.RULE_BLOCKED in again.hard_blocks


def test_hard_blocks_accumulate_across_many_reevaluations():
    d = evaluate_eligibility(good_snapshot(), hard_blocks=[BlockReason.BLACKLISTED])
    for _ in range(50):
        d = evaluate_eligibility(good_snapshot(), previous=d)
    assert d.publishable is False
    assert BlockReason.BLACKLISTED in d.hard_blocks


def test_different_blocks_union_together():
    d = evaluate_eligibility(good_snapshot(), hard_blocks=[BlockReason.RULE_BLOCKED])
    d = evaluate_eligibility(
        good_snapshot(), previous=d, hard_blocks=[BlockReason.CORRELATION_BLOCKED]
    )
    assert d.hard_blocks == {BlockReason.RULE_BLOCKED, BlockReason.CORRELATION_BLOCKED}


def test_soft_failures_are_recomputed_not_accumulated():
    """Un filtro blando SÍ debe poder limpiarse: la cuota puede actualizarse."""
    bad = evaluate_eligibility(good_snapshot(odds=1.1))
    assert bad.publishable is False
    fixed = evaluate_eligibility(good_snapshot(odds=1.9), previous=bad)
    assert fixed.publishable is True


def test_with_hard_block_never_removes():
    d = EligibilityDecision().with_hard_block(BlockReason.RULE_BLOCKED)
    d2 = d.with_hard_block(BlockReason.BLACKLISTED)
    assert BlockReason.RULE_BLOCKED in d2.hard_blocks
    assert len(d2.hard_blocks) == 2


def test_merge_unions_hard_and_takes_latest_soft():
    a = EligibilityDecision(
        hard_blocks=frozenset({BlockReason.RULE_BLOCKED}),
        soft_failures=frozenset({BlockReason.EDGE_TOO_LOW}),
    )
    b = EligibilityDecision(
        hard_blocks=frozenset({BlockReason.BLACKLISTED}),
        soft_failures=frozenset({BlockReason.STAKE_TOO_LOW}),
    )
    m = a.merge(b)
    assert m.hard_blocks == {BlockReason.RULE_BLOCKED, BlockReason.BLACKLISTED}
    assert m.soft_failures == {BlockReason.STAKE_TOO_LOW}


def test_decision_is_immutable():
    d = EligibilityDecision()
    with pytest.raises(Exception):
        d.hard_blocks = frozenset({BlockReason.RULE_BLOCKED})  # type: ignore


def test_monotonicity_property_over_random_sequences():
    """Una vez no publicable por bloqueo duro, nunca vuelve a ser publicable."""
    d = EligibilityDecision()
    seen_block = False
    for i in range(60):
        hard = [BlockReason.RULE_BLOCKED] if i == 17 else []
        d = evaluate_eligibility(good_snapshot(), previous=d, hard_blocks=hard)
        if hard:
            seen_block = True
        if seen_block:
            assert d.publishable is False
    assert seen_block


# ═══════════════════ centinela de quality_score ════════════════════════

def test_quality_sentinel_forced_when_hard_blocked():
    d = evaluate_eligibility(good_snapshot(), hard_blocks=[BlockReason.RULE_BLOCKED])
    assert d.quality_score_sentinel(87) == -1


def test_quality_sentinel_passes_through_when_clean():
    d = evaluate_eligibility(good_snapshot())
    assert d.quality_score_sentinel(87) == 87


def test_quality_sentinel_not_forced_by_soft_failure_only():
    """Un filtro blando no debe marcar el pick como inválido, solo no publicable."""
    d = evaluate_eligibility(good_snapshot(edge=0.5))
    assert d.publishable is False
    assert d.quality_score_sentinel(87) == 87


# ═══════════════════ razones y serialización ═══════════════════════════

def test_reasons_list_hard_before_soft():
    d = evaluate_eligibility(
        good_snapshot(edge=0.1), hard_blocks=[BlockReason.RULE_BLOCKED]
    )
    assert d.reasons[0] == BlockReason.RULE_BLOCKED.value
    assert BlockReason.EDGE_TOO_LOW.value in d.reasons


def test_reasons_are_deterministic():
    d = evaluate_eligibility(
        good_snapshot(odds=1.1, edge=0.1),
        hard_blocks=[BlockReason.RULE_BLOCKED, BlockReason.BLACKLISTED],
    )
    assert d.reasons == evaluate_eligibility(
        good_snapshot(odds=1.1, edge=0.1),
        hard_blocks=[BlockReason.BLACKLISTED, BlockReason.RULE_BLOCKED],
    ).reasons


def test_roundtrip_serialization_preserves_hard_blocks():
    d = evaluate_eligibility(
        good_snapshot(edge=0.1), hard_blocks=[BlockReason.CORRELATION_BLOCKED]
    )
    back = EligibilityDecision.from_dict(d.to_dict())
    assert back.hard_blocks == d.hard_blocks
    assert back.soft_failures == d.soft_failures
    assert back.publishable is False


def test_from_reasons_separates_hard_and_soft():
    d = EligibilityDecision.from_reasons(["rule_blocked", "edge_too_low"])
    assert d.hard_blocks == {BlockReason.RULE_BLOCKED}
    assert d.soft_failures == {BlockReason.EDGE_TOO_LOW}


def test_from_reasons_keeps_unknown_as_hard_block():
    """Rehidratar un motivo desconocido no debe soltar el bloqueo."""
    d = EligibilityDecision.from_reasons(["motivo_de_una_version_futura"])
    assert d.is_hard_blocked is True
    assert d.publishable is False


def test_policy_version_is_recorded():
    d = evaluate_eligibility(good_snapshot())
    assert d.policy_version == POLICY_VERSION
    assert d.to_dict()["policy_version"] == POLICY_VERSION


def test_descriptions_are_human_readable():
    d = evaluate_eligibility(good_snapshot(), hard_blocks=[BlockReason.RULE_BLOCKED])
    assert "regla" in d.descriptions[0].lower()


# ═══════════════════ flags legacy ══════════════════════════════════════

def test_flags_translate_to_reasons():
    assert hard_blocks_from_flags(is_rule_blocked=True) == {BlockReason.RULE_BLOCKED}
    assert hard_blocks_from_flags(is_blacklisted=True) == {BlockReason.BLACKLISTED}
    assert hard_blocks_from_flags(correlation_blocked=True) == {
        BlockReason.CORRELATION_BLOCKED
    }


def test_no_flags_means_no_blocks():
    assert hard_blocks_from_flags() == frozenset()


def test_all_flags_combine():
    out = hard_blocks_from_flags(
        is_blacklisted=True, is_rule_blocked=True, correlation_blocked=True,
        unsettleable=True, exposure_limited=True,
    )
    assert len(out) == 5
    assert out <= HARD_BLOCKS


# ═══════════════════ construcción del snapshot ═════════════════════════

def test_snapshot_prefers_calibrated_prob():
    """
    Se decide con la probabilidad calibrada, la misma que se muestra. Decidir
    con model_prob y mostrar calibrated_prob sería incoherente.
    """
    snap = PickSnapshot.from_pick({"calibrated_prob": 55.0, "model_prob": 70.0})
    assert snap.prob == pytest.approx(55.0)


def test_snapshot_falls_back_to_model_prob():
    snap = PickSnapshot.from_pick({"model_prob": 70.0})
    assert snap.prob == pytest.approx(70.0)


def test_snapshot_reads_from_object():
    class V:
        calibrated_prob = 62.0
        odds = 1.85
        edge = 6.0
        selection = "over_2.5"

    snap = PickSnapshot.from_pick(V(), market_family="goals")
    assert snap.prob == pytest.approx(62.0)
    assert snap.odds == pytest.approx(1.85)
    assert snap.market_family == "goals"


def test_snapshot_handles_camel_case():
    snap = PickSnapshot.from_pick({"calibratedProb": 61.0, "dataQualityScore": 77.0})
    assert snap.prob == pytest.approx(61.0)
    assert snap.data_quality_score == pytest.approx(77.0)


def test_snapshot_tolerates_garbage_values():
    snap = PickSnapshot.from_pick({"odds": "no-es-un-numero", "model_prob": 60.0})
    assert snap.odds is None
    assert BlockReason.ODDS_MISSING in evaluate_soft_filters(snap)


def test_snapshot_of_empty_pick_fails_closed():
    d = evaluate_eligibility(PickSnapshot.from_pick({}))
    assert d.publishable is False
