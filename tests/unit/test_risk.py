"""
Tests de límites de riesgo, kill switch y exposición por evento.

Principio que se verifica en casi todos: FALLAR SEGURO. Cualquier estado
accidental (variable ausente, mal escrita) debe dejar el
sistema en el modo inofensivo, no publicando dinero real.
"""

import json

import pytest

from src.core.pick_rules_engine import resolve_match_picks_correlation
from src.domain.eligibility import BlockReason, is_hard_blocked, record_hard_block
from src.domain.risk import (
    ENV_PAPER_TRADING,
    ENV_PUBLISHING_ENABLED,
    PublicationMode,
    RiskLimits,
    load_risk_limits,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ninguna variable de riesgo heredada del entorno del test runner."""
    for var in (ENV_PAPER_TRADING, ENV_PUBLISHING_ENABLED):
        monkeypatch.delenv(var, raising=False)


# ═══════════════════ defaults seguros ══════════════════════════════════

def test_default_mode_is_paper_not_live():
    """
    El defecto NO puede ser dinero real. La calibración solo está validada
    contra datos sintéticos.
    """
    assert load_risk_limits().mode is PublicationMode.PAPER
    assert load_risk_limits().is_live is False


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


def test_shipped_rules_exist():
    """Verifica que el archivo pick_rules.json contiene la lista de reglas."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "pick_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["rules"], "el fichero debe seguir conteniendo las reglas"


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

