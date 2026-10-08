import pytest
from src.core.pick_rules_engine import evaluate_pick_rules, StatSource
from src.domain.eligibility import is_hard_blocked, BlockReason, record_hard_block


def test_rule_block_persistence_on_recalculate():
    pick = {
        "selection": "Over 2.5 Goles",
        "market_family": "goals",
        "is_publishable": True,
        "is_value": True,
        "quality_score": 85,
    }

    # Bloquear el pick por regla
    record_hard_block(pick, BlockReason.RULE_BLOCKED, detail="Regla de prueba")

    assert pick["is_rule_blocked"] is True
    assert pick["is_publishable"] is False
    assert is_hard_blocked(pick) is True
    assert pick["quality_score"] == -1

    # Recalcular score o publicación (simular paso posterior del pipeline)
    pick["quality_score"] = 90
    pick["is_publishable"] = True

    # Verificar que el bloqueo duro persiste
    assert is_hard_blocked(pick) is True
    assert BlockReason.RULE_BLOCKED.value in pick["eligibility_hard_blocks"]
