"""
Tests del cableado de elegibilidad en `compare.py`.

Reproducen la secuencia real que resucitaba picks bloqueados:

    block_pick(...)              -> is_publishable=False, quality_score=-1
    v.quality_score = q_score    -> el centinela -1 se pierde
    is_publishable_pick(v)       -> devolvía True (solo miraba is_blacklisted)

El pick bloqueado terminaba publicado.
"""

import pytest

from src.domain.eligibility import BlockReason
from src.ui.api.compare import (
    ValueIndicator,
    block_pick,
    current_eligibility,
    evaluate_pick_eligibility,
    is_publishable_pick,
)


def make_pick(**over) -> ValueIndicator:
    """Un pick que, sin bloqueos, es publicable."""
    base = dict(
        selection="over_2.5_goals",
        odds=1.90,
        model_prob=68.0,
        calibrated_prob=65.0,
        edge=8.0,
        data_quality_score=80.0,
        stake_units=1.5,
    )
    base.update(over)
    return ValueIndicator(**base)


def test_clean_pick_is_publishable():
    assert is_publishable_pick(make_pick()) is True


# ═══════════════════ EL BUG ════════════════════════════════════════════

def test_rule_blocked_pick_stays_blocked_after_quality_recalc():
    """
    REGRESIÓN DEL BUG PRINCIPAL (compare.py:1356 -> 3911 -> 3915).
    """
    v = make_pick()
    block_pick(v, BlockReason.RULE_BLOCKED)
    assert v.is_publishable is False
    assert v.quality_score == -1

    # `_rate_pick_quality` sobrescribe la calidad más adelante...
    v.quality_score = 87

    # ...y el pipeline recalcula la publicabilidad.
    assert is_publishable_pick(v) is False
    assert v.is_publishable is False
    assert v.quality_score == -1, "el centinela debe reponerse, no perderse"


def test_correlation_blocked_pick_cannot_be_resurrected():
    v = make_pick()
    v.correlation_blocked = True
    assert is_publishable_pick(v) is False


def test_blacklisted_pick_cannot_be_resurrected():
    v = make_pick()
    v.is_blacklisted = True
    assert is_publishable_pick(v) is False


def test_legacy_flag_alone_is_enough_to_block():
    """
    Un pick bloqueado por código antiguo que solo movió el flag booleano
    (sin registro de motivos) debe seguir bloqueado.
    """
    v = make_pick()
    v.is_rule_blocked = True
    assert v.eligibility_hard_blocks == []
    assert is_publishable_pick(v) is False
    assert BlockReason.RULE_BLOCKED.value in v.eligibility_hard_blocks


def test_clearing_the_legacy_flag_does_not_unblock():
    """
    Una vez registrado el motivo, borrar el booleano no reabre la publicación:
    el registro inmutable manda.
    """
    v = make_pick()
    block_pick(v, BlockReason.RULE_BLOCKED)
    v.is_rule_blocked = False  # alguien "arregla" el flag
    assert is_publishable_pick(v) is False
    assert v.is_rule_blocked is True, "el flag se repone desde el registro"


def test_repeated_evaluation_is_idempotent():
    v = make_pick()
    block_pick(v, BlockReason.RULE_BLOCKED)
    snapshots = []
    for _ in range(30):
        is_publishable_pick(v)
        snapshots.append((v.is_publishable, v.quality_score, tuple(v.eligibility_hard_blocks)))
    assert len(set(snapshots)) == 1
    assert snapshots[0][0] is False


def test_blocks_accumulate_and_are_all_reported():
    v = make_pick()
    block_pick(v, BlockReason.RULE_BLOCKED)
    block_pick(v, BlockReason.CORRELATION_BLOCKED)
    assert set(v.eligibility_hard_blocks) == {
        BlockReason.RULE_BLOCKED.value,
        BlockReason.CORRELATION_BLOCKED.value,
    }
    assert v.is_rule_blocked is True
    assert v.correlation_blocked is True


# ═══════════════════ filtros blandos siguen vivos ══════════════════════

def test_soft_failure_is_reversible():
    """Corregir la cuota debe volver a habilitar el pick: no es un bloqueo."""
    v = make_pick(odds=1.10)
    assert is_publishable_pick(v) is False
    assert BlockReason.ODDS_TOO_LOW.value in v.eligibility_soft_failures
    v.odds = 1.90
    assert is_publishable_pick(v) is True
    assert v.eligibility_soft_failures == []


def test_soft_failure_does_not_set_quality_sentinel():
    v = make_pick(edge=0.5)
    v.quality_score = 70
    is_publishable_pick(v)
    assert v.is_publishable is False
    assert v.quality_score == 70


def test_low_probability_blocks_binary_market():
    v = make_pick(selection="btts_yes", calibrated_prob=50.0)
    assert is_publishable_pick(v) is False


def test_high_variance_market_passes_with_low_probability():
    v = make_pick(selection="over_4.5_cards", calibrated_prob=25.0)
    assert is_publishable_pick(v) is True


# ═══════════════════ trazabilidad ══════════════════════════════════════

def test_reasons_are_recorded_on_the_pick():
    v = make_pick(odds=1.05)
    block_pick(v, BlockReason.RULE_BLOCKED)
    assert BlockReason.RULE_BLOCKED.value in v.eligibility_reasons
    assert BlockReason.ODDS_TOO_LOW.value in v.eligibility_reasons
    assert v.eligibility_policy_version is not None


def test_current_eligibility_reads_both_sources():
    v = make_pick()
    v.eligibility_hard_blocks = [BlockReason.RULE_BLOCKED.value]
    v.correlation_blocked = True
    d = current_eligibility(v)
    assert d.hard_blocks == {
        BlockReason.RULE_BLOCKED,
        BlockReason.CORRELATION_BLOCKED,
    }


def test_evaluate_returns_the_decision():
    v = make_pick()
    d = evaluate_pick_eligibility(v, new_hard_blocks=[BlockReason.EXPOSURE_LIMIT])
    assert d.publishable is False
    assert d.is_hard_blocked is True


def test_blocked_pick_is_never_value():
    v = make_pick()
    v.is_value = True
    block_pick(v, BlockReason.RULE_BLOCKED)
    assert v.is_value is False


def test_block_pick_with_detail():
    v = make_pick()
    block_pick(v, BlockReason.RULE_BLOCKED, detail="Veto por brecha irreconciliable")
    assert v.is_publishable is False
    assert v.rule_blocked_reason == "Veto por brecha irreconciliable"

