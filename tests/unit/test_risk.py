"""
Tests de límites de riesgo, kill switch y exposición por evento.

Principio que se verifica en casi todos: FALLAR SEGURO. Cualquier estado
accidental (variable ausente, mal escrita, JSON corrupto) debe dejar el
sistema en el modo inofensivo, no publicando dinero real.
"""

import json

import pytest

from src.core.pick_rules_engine import resolve_match_picks_correlation
from src.domain.eligibility import BlockReason, is_hard_blocked, record_hard_block
from src.domain.risk import (
    DEFAULT_MAX_PICKS_PER_EVENT,
    DEFAULT_MAX_STAKE_PER_EVENT,
    ENV_MAX_PICKS,
    ENV_MAX_STAKE,
    ENV_PAPER_TRADING,
    ENV_PUBLISHING_ENABLED,
    PublicationMode,
    RiskLimits,
    load_risk_limits,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ninguna variable de riesgo heredada del entorno del test runner."""
    for var in (ENV_PAPER_TRADING, ENV_PUBLISHING_ENABLED, ENV_MAX_PICKS, ENV_MAX_STAKE):
        monkeypatch.delenv(var, raising=False)


# ═══════════════════ defaults seguros ══════════════════════════════════

def test_default_mode_is_paper_not_live():
    """
    El defecto NO puede ser dinero real. La calibración solo está validada
    contra datos sintéticos.
    """
    assert load_risk_limits().mode is PublicationMode.PAPER
    assert load_risk_limits().is_live is False


def test_default_limits_are_two_picks_three_units():
    limits = load_risk_limits()
    assert limits.max_picks_per_event == 2
    assert limits.max_stake_per_event == pytest.approx(3.0)


def test_paper_mode_yields_zero_effective_stake():
    """El stake se muestra como información del modelo, no como dinero."""
    assert load_risk_limits().effective_stake(2.5) == 0.0


def test_live_mode_yields_the_real_stake(monkeypatch):
    monkeypatch.setenv(ENV_PAPER_TRADING, "false")
    limits = load_risk_limits()
    assert limits.is_live is True
    assert limits.effective_stake(2.5) == pytest.approx(2.5)


def test_negative_stake_never_becomes_a_bet(monkeypatch):
    monkeypatch.setenv(ENV_PAPER_TRADING, "false")
    assert load_risk_limits().effective_stake(-4.0) == 0.0


def test_none_stake_is_zero():
    assert load_risk_limits().effective_stake(None) == 0.0


# ═══════════════════ kill switch ═══════════════════════════════════════

def test_kill_switch_halts_publication(monkeypatch):
    monkeypatch.setenv(ENV_PUBLISHING_ENABLED, "false")
    limits = load_risk_limits()
    assert limits.mode is PublicationMode.HALTED
    assert limits.allows_publication is False


def test_kill_switch_wins_over_live_mode(monkeypatch):
    """Detener la publicación no puede ser anulado por pedir modo real."""
    monkeypatch.setenv(ENV_PUBLISHING_ENABLED, "false")
    monkeypatch.setenv(ENV_PAPER_TRADING, "false")
    limits = load_risk_limits()
    assert limits.mode is PublicationMode.HALTED
    assert limits.effective_stake(5.0) == 0.0


def test_halted_mode_blocks_every_pick():
    limits = RiskLimits(publishing_enabled=False)
    assert limits.allows_publication is False


# ═══════════════════ variables de entorno mal puestas ══════════════════

@pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "on", "si", "sí"])
def test_truthy_values_are_accepted(monkeypatch, raw):
    monkeypatch.setenv(ENV_PAPER_TRADING, raw)
    assert load_risk_limits().paper_trading is True


@pytest.mark.parametrize("raw", ["false", "FALSE", "0", "no", "off"])
def test_falsy_values_are_accepted(monkeypatch, raw):
    monkeypatch.setenv(ENV_PAPER_TRADING, raw)
    assert load_risk_limits().paper_trading is False


def test_typo_in_paper_trading_stays_in_paper(monkeypatch):
    """
    Un valor ininteligible no debe abrir la publicación real. `flase` es un
    typo plausible de `false`, y no puede costar dinero.
    """
    monkeypatch.setenv(ENV_PAPER_TRADING, "flase")
    assert load_risk_limits().paper_trading is True


def test_typo_in_kill_switch_keeps_publication_allowed(monkeypatch):
    monkeypatch.setenv(ENV_PUBLISHING_ENABLED, "maybe")
    assert load_risk_limits().publishing_enabled is True


def test_garbage_numeric_limit_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(ENV_MAX_STAKE, "mucho")
    assert load_risk_limits().max_stake_per_event == pytest.approx(3.0)


def test_zero_limit_is_ignored(monkeypatch):
    """Un tope de 0 bloquearía todo silenciosamente: se trata como no puesto."""
    monkeypatch.setenv(ENV_MAX_PICKS, "0")
    assert load_risk_limits().max_picks_per_event == 2


def test_negative_limit_is_ignored(monkeypatch):
    monkeypatch.setenv(ENV_MAX_STAKE, "-5")
    assert load_risk_limits().max_stake_per_event == pytest.approx(3.0)


# ═══════════════════ el JSON solo puede apretar ════════════════════════

def test_json_cannot_raise_exposure_above_the_code_ceiling():
    """
    Editar pick_rules.json no debe poder ampliar la exposición. Era justo el
    problema: el JSON decía 5 picks / 10 unidades y ganaba.
    """
    limits = load_risk_limits({"max_picks_per_event": 99, "max_stake_per_event": 500})
    assert limits.max_picks_per_event == DEFAULT_MAX_PICKS_PER_EVENT
    assert limits.max_stake_per_event == pytest.approx(DEFAULT_MAX_STAKE_PER_EVENT)


def test_json_can_lower_exposure():
    limits = load_risk_limits({"max_picks_per_event": 1, "max_stake_per_event": 1.0})
    assert limits.max_picks_per_event == 1
    assert limits.max_stake_per_event == pytest.approx(1.0)


def test_corrupt_json_values_fall_back_to_defaults():
    limits = load_risk_limits({"max_picks_per_event": None, "max_stake_per_event": "x"})
    assert limits.max_picks_per_event == 2
    assert limits.max_stake_per_event == pytest.approx(3.0)


def test_env_overrides_json():
    """El kill switch y los topes deben poder cambiarse sin desplegar datos."""
    import os

    os.environ[ENV_MAX_PICKS] = "1"
    try:
        assert load_risk_limits({"max_picks_per_event": 2}).max_picks_per_event == 1
    finally:
        del os.environ[ENV_MAX_PICKS]


def test_shipped_pick_rules_json_respects_the_agreed_limits():
    """El fichero versionado debe reflejar la decisión: 2 picks / 3 unidades."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "pick_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cr = data["correlation_rules"]
    assert cr["max_picks_per_event"] == 2
    assert cr["max_stake_per_event"] == 3


def test_shipped_rules_remain_disabled():
    """Decisión del proyecto: las 4 reglas estadísticas siguen inactivas."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "pick_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["rules"], "el fichero debe seguir conteniendo las reglas"
    assert all(r["enabled"] is False for r in data["rules"])


# ═══════════════════ descripción y serialización ═══════════════════════

def test_describe_mentions_the_mode():
    assert "detenida" in RiskLimits(publishing_enabled=False).describe().lower()
    assert "paper" in RiskLimits().describe().lower()
    assert "real" in RiskLimits(paper_trading=False).describe().lower()


def test_to_dict_exposes_the_mode():
    assert RiskLimits().to_dict()["mode"] == "paper"


def test_limits_are_immutable():
    with pytest.raises(Exception):
        RiskLimits().paper_trading = False  # type: ignore


# ═══════════════════ exposición por evento en el motor ═════════════════

def make_pick(selection, stake=1.0, score=50.0):
    return {
        "selection": selection,
        "stake_units": stake,
        "display_score": score,
        "edge_ev": 0.05,
        "edge": 5.0,
        "quality_score": int(score),
        "is_publishable": True,
        "is_value": True,
        "is_underdog": False,
        "is_blacklisted": False,
        "is_rule_blocked": False,
        "correlation_blocked": False,
        "eligibility_hard_blocks": [],
    }


def published(picks):
    return [p for p in picks if p.get("is_publishable")]


def test_event_cap_limits_to_two_picks():
    picks = [
        make_pick("over_2.5_goals", score=90),
        make_pick("home_win", score=80),
        make_pick("over_9.5_corners", score=70),
        make_pick("over_4.5_cards", score=60),
    ]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    assert len(published(out)) == 2


def test_event_stake_cap_is_respected():
    picks = [
        make_pick("over_2.5_goals", stake=2.0, score=90),
        make_pick("home_win", stake=2.0, score=80),
    ]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    total = sum(p["stake_units"] for p in published(out))
    assert total <= 3.0


def test_pick_over_the_cap_is_labelled_exposure_not_correlation():
    picks = [
        make_pick("over_2.5_goals", score=90),
        make_pick("home_win", score=80),
        make_pick("over_9.5_corners", score=70),
    ]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    dropped = [p for p in out if not p.get("is_publishable")]
    assert dropped
    assert any(
        BlockReason.EXPOSURE_LIMIT.value in p.get("eligibility_hard_blocks", [])
        for p in dropped
    )


def test_correlated_pick_is_labelled_correlation():
    picks = [
        make_pick("over_2.5_goals", score=90),
        make_pick("over_3.5_goals", score=80),  # misma familia
    ]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    dropped = [p for p in out if not p.get("is_publishable")]
    assert len(dropped) == 1
    assert BlockReason.CORRELATION_BLOCKED.value in dropped[0]["eligibility_hard_blocks"]


def test_running_correlation_twice_does_not_resurrect_picks():
    """
    REGRESIÓN: `is_candidate_valid` no miraba `correlation_blocked`, así que
    una segunda pasada devolvía a competir picks ya descartados.
    """
    picks = [
        make_pick("over_2.5_goals", score=90),
        make_pick("home_win", score=80),
        make_pick("over_9.5_corners", score=70),
        make_pick("over_4.5_cards", score=60),
    ]
    first = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    ids_first = {p["selection"] for p in published(first)}

    second = resolve_match_picks_correlation(first, correlation_rules={"exclusive_groups": []})
    ids_second = {p["selection"] for p in published(second)}

    assert ids_second <= ids_first, "una segunda pasada no puede añadir publicados"
    assert len(ids_second) <= 2


def test_correlation_is_idempotent_over_many_passes():
    picks = [make_pick(f"over_{i}.5_corners", score=90 - i) for i in range(6)]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    seen = [{p["selection"] for p in published(out)}]
    for _ in range(5):
        out = resolve_match_picks_correlation(out, correlation_rules={"exclusive_groups": []})
        seen.append({p["selection"] for p in published(out)})
    assert all(s == seen[0] for s in seen)


def test_kill_switch_blocks_every_pick_in_the_engine(monkeypatch):
    monkeypatch.setenv(ENV_PUBLISHING_ENABLED, "false")
    picks = [make_pick("over_2.5_goals", score=90), make_pick("home_win", score=80)]
    out = resolve_match_picks_correlation(picks, correlation_rules={"exclusive_groups": []})
    assert published(out) == []
    assert all(is_hard_blocked(p) for p in out)


# ═══════════════════ helper genérico de bloqueo ════════════════════════

def test_record_hard_block_works_on_dict():
    p = make_pick("over_2.5_goals")
    record_hard_block(p, BlockReason.RULE_BLOCKED, detail="motivo")
    assert p["is_publishable"] is False
    assert p["is_rule_blocked"] is True
    assert p["quality_score"] == -1
    assert p["rule_blocked_reason"] == "motivo"


def test_record_hard_block_accumulates():
    p = make_pick("over_2.5_goals")
    record_hard_block(p, BlockReason.RULE_BLOCKED)
    record_hard_block(p, BlockReason.EXPOSURE_LIMIT)
    assert set(p["eligibility_hard_blocks"]) == {
        BlockReason.RULE_BLOCKED.value,
        BlockReason.EXPOSURE_LIMIT.value,
    }


def test_record_hard_block_works_on_object():
    class P:
        is_publishable = True
        is_value = True
        is_underdog = False
        is_blacklisted = False
        is_rule_blocked = False
        correlation_blocked = False
        quality_score = 80
        eligibility_hard_blocks: list = []

    p = P()
    record_hard_block(p, BlockReason.CORRELATION_BLOCKED)
    assert p.is_publishable is False
    assert p.correlation_blocked is True
    assert p.quality_score == -1


def test_is_hard_blocked_detects_legacy_flag_only():
    p = make_pick("over_2.5_goals")
    p["correlation_blocked"] = True
    assert is_hard_blocked(p) is True


def test_clean_pick_is_not_hard_blocked():
    assert is_hard_blocked(make_pick("over_2.5_goals")) is False
