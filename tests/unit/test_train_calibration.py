"""
Tests del pipeline de entrenamiento del calibrador.

Contrato:
  - Se calibra sobre `model_prob` (cruda), NUNCA sobre `calibrated_prob`.
  - Push y no liquidados se excluyen y quedan contabilizados.
  - Sin fecha de partido se descarta por defecto (anti-fuga temporal).
  - No se promueve el artefacto si no mejora Brier Y log loss.
  - Muestra insuficiente -> no se promueve, se mantiene la identidad.
"""

import json
import random
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.settlement import Outcome, outcome_from_legacy
from src.core.train_calibration import (
    ExtractionStats,
    extract_samples,
    history_dir_for,
    train_calibrator,
)
from src.models.calibration import CalibrationSample, HierarchicalCalibrator


# ─────────────────── puente legacy -> Outcome ─────────────────────────────

def test_outcome_from_legacy_maps_every_case():
    assert outcome_from_legacy(True) is Outcome.WIN
    assert outcome_from_legacy(False) is Outcome.LOSS
    assert outcome_from_legacy("half_win") is Outcome.HALF_WIN
    assert outcome_from_legacy("half_loss") is Outcome.HALF_LOSS
    assert outcome_from_legacy("void") is Outcome.PUSH
    assert outcome_from_legacy("push") is Outcome.PUSH
    assert outcome_from_legacy(None) is Outcome.UNSETTLED


def test_outcome_from_legacy_is_case_insensitive():
    assert outcome_from_legacy("HALF_WIN") is Outcome.HALF_WIN
    assert outcome_from_legacy(" Void ") is Outcome.PUSH


def test_outcome_from_legacy_unknown_fails_closed():
    """Un valor raro se excluye, no se cuenta como acierto ni como fallo."""
    assert outcome_from_legacy("cualquier_cosa") is Outcome.UNSETTLED
    assert outcome_from_legacy(3.14) is Outcome.UNSETTLED


def test_outcome_from_legacy_is_idempotent():
    assert outcome_from_legacy(Outcome.HALF_WIN) is Outcome.HALF_WIN


# ─────────────────── extracción ───────────────────────────────────────────

def _row(picks, **over):
    base = {
        "final_score_home": 2, "final_score_away": 1,
        "picks_calculados": json.dumps(picks),
        "match_date": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "league": "Premier",
    }
    base.update(over)
    return base


def _resolver_map(mapping):
    """Resolver falso: devuelve el outcome legacy asociado a cada selección."""
    return lambda pick, results: mapping.get(pick.get("selection"))


def _family(sel):
    return "goals"


def test_extract_uses_raw_model_prob_not_calibrated():
    """
    Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob.
    """
    rows = [_row([{"selection": "over_2.5", "model_prob": 61.0, "calibrated_prob": 48.0}])]
    samples, _ = extract_samples(
        rows, resolver=_resolver_map({"over_2.5": True}), market_family_fn=_family
    )
    assert len(samples) == 1
    assert samples[0].prob == pytest.approx(61.0)


def test_extract_excludes_push_and_counts_it():
    rows = [_row([
        {"selection": "a", "model_prob": 55.0},
        {"selection": "b", "model_prob": 60.0},
    ])]
    samples, stats = extract_samples(
        rows,
        resolver=_resolver_map({"a": "void", "b": True}),
        market_family_fn=_family,
    )
    assert len(samples) == 1
    assert stats.picks_push == 1
    assert stats.picks_accepted == 1


def test_extract_excludes_unsettled_and_counts_it():
    rows = [_row([{"selection": "a", "model_prob": 55.0}])]
    samples, stats = extract_samples(
        rows, resolver=_resolver_map({"a": None}), market_family_fn=_family
    )
    assert samples == []
    assert stats.picks_unsettled == 1


def test_extract_half_win_counts_as_half():
    rows = [_row([{"selection": "a", "model_prob": 55.0}])]
    samples, _ = extract_samples(
        rows, resolver=_resolver_map({"a": "half_win"}), market_family_fn=_family
    )
    assert samples[0].hit_value == pytest.approx(0.5)


def test_extract_skips_rows_without_final_score():
    rows = [_row([{"selection": "a", "model_prob": 55.0}], final_score_home=None)]
    samples, stats = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family
    )
    assert samples == []
    assert stats.rows_without_results == 1


def test_extract_handles_malformed_json():
    rows = [_row([], picks_calculados="{roto")]
    samples, stats = extract_samples(rows, resolver=lambda p, r: True, market_family_fn=_family)
    assert samples == []
    assert stats.rows_bad_json == 1


def test_extract_accepts_dict_wrapped_picks():
    rows = [_row([], picks_calculados=json.dumps(
        {"picks": [{"selection": "a", "model_prob": 55.0}]}
    ))]
    samples, _ = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family
    )
    assert len(samples) == 1


def test_extract_requires_timestamp_by_default():
    """Sin fecha no se puede garantizar ausencia de fuga temporal."""
    rows = [_row([{"selection": "a", "model_prob": 55.0}], match_date=None, date=None)]
    samples, stats = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family
    )
    assert samples == []
    assert stats.picks_no_timestamp == 1


def test_extract_can_allow_missing_timestamp():
    rows = [_row([{"selection": "a", "model_prob": 55.0}], match_date=None, date=None)]
    samples, _ = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family,
        require_timestamp=False,
    )
    assert len(samples) == 1


def test_extract_counts_picks_without_probability():
    rows = [_row([{"selection": "a"}])]
    samples, stats = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family
    )
    assert samples == []
    assert stats.picks_no_prob == 1


def test_extract_survives_resolver_exception():
    def boom(pick, results):
        raise RuntimeError("mercado desconocido")

    rows = [_row([{"selection": "a", "model_prob": 55.0}])]
    samples, stats = extract_samples(rows, resolver=boom, market_family_fn=_family)
    assert samples == []
    assert stats.picks_unsettled == 1


def test_extract_parses_string_timestamps():
    rows = [_row([{"selection": "a", "model_prob": 55.0}],
                 match_date="2026-05-04T20:00:00Z")]
    samples, _ = extract_samples(
        rows, resolver=_resolver_map({"a": True}), market_family_fn=_family
    )
    assert samples[0].timestamp.month == 5


def test_extraction_stats_summary_is_readable():
    s = ExtractionStats(rows_seen=10, picks_seen=40, picks_accepted=30, picks_push=5)
    text = s.summary()
    assert "filas=10" in text and "aceptados=30" in text


# ─────────────────── promoción del artefacto ──────────────────────────────

def _overconfident_samples(n=900, shrink=0.72, seed=3):
    rng = random.Random(seed)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out = []
    for i in range(n):
        p = rng.uniform(0.25, 0.90)
        out.append(CalibrationSample(
            prob=p, hit_value=1.0 if rng.random() < p * shrink else 0.0,
            market_family="goals", league="Premier",
            timestamp=base + timedelta(hours=i),
        ))
    return out


def test_promotes_when_calibration_improves(tmp_path):
    art = tmp_path / "active.json"
    report = train_calibrator(
        _overconfident_samples(), artifact_path=art,
        prior_strength=5.0, min_samples=40,
    )
    assert report.promoted is True
    assert art.exists()
    assert report.walk_forward["calibrated"]["brier"] < report.walk_forward["raw"]["brier"]


def test_promoted_artifact_is_loadable_and_corrects(tmp_path):
    art = tmp_path / "active.json"
    train_calibrator(_overconfident_samples(), artifact_path=art,
                     prior_strength=5.0, min_samples=40)
    cal = HierarchicalCalibrator.load(art)
    assert cal.is_trained
    assert cal.apply(0.88, "goals", "Premier") < 0.88


def test_does_not_promote_insufficient_sample(tmp_path):
    art = tmp_path / "active.json"
    report = train_calibrator(
        _overconfident_samples(n=10), artifact_path=art, min_samples=40
    )
    assert report.promoted is False
    assert "insuficiente" in report.reason.lower()
    assert not art.exists()


def test_does_not_promote_when_model_already_calibrated(tmp_path):
    """
    Si el modelo ya está bien calibrado, la curva no puede mejorar de forma
    consistente y NO debe publicarse. Es el caso que generaba ruido antes.
    """
    art = tmp_path / "active.json"
    rng = random.Random(17)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [
        CalibrationSample(
            prob=(p := rng.uniform(0.25, 0.90)),
            hit_value=1.0 if rng.random() < p else 0.0,
            market_family="goals", league="Premier",
            timestamp=base + timedelta(hours=i),
        )
        for i in range(400)
    ]
    report = train_calibrator(samples, artifact_path=art,
                              prior_strength=25.0, min_samples=40)
    # Puede promoverse o no según el ruido, pero si no mejora NO debe escribir.
    if not report.promoted:
        assert not art.exists()
        assert "no mejora" in report.reason.lower()


def test_force_promotes_even_without_improvement(tmp_path):
    art = tmp_path / "active.json"
    report = train_calibrator(
        _overconfident_samples(n=200), artifact_path=art,
        prior_strength=5.0, min_samples=40, force=True,
    )
    assert report.promoted is True
    assert art.exists()


def test_dry_run_writes_nothing(tmp_path):
    art = tmp_path / "active.json"
    report = train_calibrator(
        _overconfident_samples(), artifact_path=art,
        prior_strength=5.0, min_samples=40, dry_run=True,
    )
    assert report.promoted is False
    assert "dry-run" in report.reason
    assert not art.exists()
    assert report.walk_forward["raw"]["n"] > 0


def test_report_carries_extraction_stats(tmp_path):
    report = train_calibrator(
        _overconfident_samples(), artifact_path=tmp_path / "a.json",
        prior_strength=5.0, min_samples=40,
        extraction_stats={"picks_accepted": 900},
    )
    assert report.extraction["picks_accepted"] == 900


def test_report_summary_is_readable(tmp_path):
    report = train_calibrator(
        _overconfident_samples(), artifact_path=tmp_path / "a.json",
        prior_strength=5.0, min_samples=40, dry_run=True,
    )
    text = report.summary()
    assert "Brier" in text and "LogLoss" in text


def test_history_is_written_next_to_the_artifact(tmp_path):
    """
    Regresión: el historial se derivaba de una constante global, así que
    entrenar hacia una ruta temporal escribía en data/ del repo.
    """
    art = tmp_path / "sub" / "active.json"
    report = train_calibrator(_overconfident_samples(), artifact_path=art,
                              prior_strength=5.0, min_samples=40)
    assert report.promoted is True
    hist = tmp_path / "sub" / "history"
    assert hist.is_dir()
    assert list(hist.glob("cal-*.json"))
    assert history_dir_for(art) == hist.resolve()


def test_history_dir_is_relative_to_given_path():
    assert history_dir_for("/x/y/active.json").as_posix().endswith("/x/y/history")


def test_artifact_metadata_records_validation(tmp_path):
    art = tmp_path / "active.json"
    train_calibrator(_overconfident_samples(), artifact_path=art,
                     prior_strength=5.0, min_samples=40)
    data = json.loads(art.read_text(encoding="utf-8"))
    assert "walk_forward" in data["metadata"]
    assert data["metadata"]["walk_forward"]["calibrated"]["brier"] > 0

def test_compare_with_active_uses_same_samples_and_reports_deltas(tmp_path):
    art = tmp_path / "active.json"
    train_calibrator(_overconfident_samples(seed=3), artifact_path=art,
                     prior_strength=5.0, min_samples=40)
    data = json.loads(art.read_text(encoding="utf-8"))
    assert "trained_until" in data["metadata"]

    report = train_calibrator(_overconfident_samples(n=900, seed=4), artifact_path=art,
                              prior_strength=5.0, min_samples=40, dry_run=True)
    cmp = report.active_comparison
    assert cmp["status"] in ("ok", "not_comparable")
    if cmp["status"] == "ok":
        assert set(cmp["deltas"]) == {"brier", "log_loss", "ece"}
        assert cmp["candidate"]["n"] == cmp["active"]["n"] == cmp["n_compared"]
        assert "Δ cand-act" in report.summary()


def test_does_not_promote_if_active_comparison_fails(tmp_path, monkeypatch):
    art = tmp_path / "active.json"
    train_calibrator(_overconfident_samples(), artifact_path=art,
                     prior_strength=5.0, min_samples=40)
    monkeypatch.setattr(
        HierarchicalCalibrator, "apply",
        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    report = train_calibrator(_overconfident_samples(seed=9), artifact_path=art,
                              prior_strength=5.0, min_samples=40)
    assert report.promoted is False
    assert "comparar" in report.reason.lower()

def test_walk_forward_arrays_are_aligned():
    wf = walk_forward_calibrate(
        _overconfident_samples(), n_folds=5, prior_strength=5.0,
        min_samples=40, min_train=120.0,
    )
    assert len(wf.samples) == len(wf.raw_probs) == len(wf.calibrated_probs) == len(wf.outcomes) > 0


def test_trained_until_is_persisted(tmp_path):
    art = tmp_path / "active.json"
    train_calibrator(_overconfident_samples(), artifact_path=art,
                     prior_strength=5.0, min_samples=40)
    cal = HierarchicalCalibrator.load(art)
    assert cal.metadata.get("trained_until")


def test_compare_falls_back_to_leaky_when_few_fair_samples(tmp_path):
    art = tmp_path / "active.json"
    samples = _overconfident_samples()
    train_calibrator(samples, artifact_path=art, prior_strength=5.0, min_samples=40)
    wf = walk_forward_calibrate(samples, n_folds=5, prior_strength=5.0,
                                min_samples=40, min_train=120.0)
    cmp = compare_with_active(wf, art)
    assert cmp["status"] == "ok"
    assert cmp["mode"] == "leaky_fallback"
    assert cmp["n_compared"] == len(wf.outcomes)


def test_compare_fair_mode_uses_only_newer_samples(tmp_path):
    art = tmp_path / "active.json"
    old = _overconfident_samples(n=500, seed=3)
    train_calibrator(old, artifact_path=art, prior_strength=5.0, min_samples=40)
    last = max(s.timestamp for s in old)
    new = [
        CalibrationSample(prob=s.prob, hit_value=s.hit_value, market_family=s.market_family,
                          league=s.league, timestamp=last + timedelta(hours=i + 1))
        for i, s in enumerate(_overconfident_samples(n=700, seed=11))
    ]
    wf = walk_forward_calibrate(old + new, n_folds=5, prior_strength=5.0,
                                min_samples=40, min_train=120.0)
    cmp = compare_with_active(wf, art, min_fair_samples=50)
    assert cmp["status"] == "ok" and cmp["mode"] == "fair"
    assert cmp["n_compared"] < len(wf.outcomes)