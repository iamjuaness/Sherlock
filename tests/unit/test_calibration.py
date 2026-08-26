"""
Tests de la calibración probabilística jerárquica (sin GLM).

Invariantes clave:
  - Sin muestra suficiente, la calibración es la IDENTIDAD (nunca empeora).
  - La curva es monótona no decreciente.
  - Con sobreconfianza sistemática, la calibración la corrige.
  - Un segmento con poca muestra apenas se mueve del padre (no amplifica ruido).
  - El ajuste es determinista y serializable sin pérdida.
  - Walk-forward nunca entrena con datos del fold que evalúa.
"""

import math
import random

import pytest

from src.models.calibration import (
    DEFAULT_MIN_SAMPLES,
    ROOT_KEY,
    CalibrationCurve,
    CalibrationSample,
    HierarchicalCalibrator,
    brier_score,
    expected_calibration_error,
    family_key,
    fit_curve,
    league_key,
    log_loss,
    pava,
    reliability_table,
    samples_from_settlements,
    walk_forward_calibrate,
)


def make_samples(n, true_rate_fn, market="goals", league="L1", seed=42, prob_fn=None):
    """Genera muestras sintéticas con una relación conocida prob->acierto."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        p = prob_fn(i) if prob_fn else rng.uniform(0.15, 0.9)
        true_p = true_rate_fn(p)
        hit = 1.0 if rng.random() < true_p else 0.0
        out.append(CalibrationSample(prob=p, hit_value=hit,
                                     market_family=market, league=league))
    return out


# ───────────────────────────── PAVA ────────────────────────────────────────

def test_pava_already_monotone_is_unchanged():
    vals = [0.1, 0.3, 0.5, 0.8]
    assert pava(vals, [1, 1, 1, 1]) == pytest.approx(vals)


def test_pava_enforces_monotonicity():
    out = pava([0.5, 0.2, 0.8], [1, 1, 1])
    assert out == sorted(out)
    assert out[0] == pytest.approx(0.35)     # 0.5 y 0.2 se agrupan
    assert out[1] == pytest.approx(0.35)


def test_pava_respects_weights():
    out = pava([0.9, 0.1], [9.0, 1.0])
    assert out[0] == pytest.approx(0.82)     # media ponderada
    assert out[0] == out[1]


def test_pava_preserves_length():
    for vals in ([0.3, 0.1], [0.9, 0.4, 0.6, 0.2, 0.8]):
        assert len(pava(vals, [1] * len(vals))) == len(vals)


def test_pava_empty():
    assert pava([], []) == []


# ───────────────────────────── curva ───────────────────────────────────────

def test_identity_curve_is_a_noop():
    c = CalibrationCurve.identity()
    assert c.is_identity
    for p in (0.0, 0.1, 0.5, 0.83, 1.0):
        # Tolerancia 1e-5: la curva recorta a [eps, 1-eps] a propósito, porque
        # una probabilidad de exactamente 0 o 1 rompe log loss y Kelly.
        assert c.apply(p) == pytest.approx(p, abs=1e-5)


def test_curve_never_returns_exactly_zero_or_one():
    """Cuotas justas infinitas y log loss infinito son fallos de producción."""
    c = CalibrationCurve.identity()
    assert 0.0 < c.apply(0.0) < 1.0
    assert 0.0 < c.apply(1.0) < 1.0


def test_curve_preserves_scale():
    """0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale."""
    c = CalibrationCurve.identity()
    assert c.apply(60.0) == pytest.approx(60.0, abs=1e-3)
    assert c.apply(0.6) == pytest.approx(0.6, abs=1e-6)


def test_curve_is_monotone_after_fit():
    samples = make_samples(400, lambda p: p * 0.7)
    curve = fit_curve(samples)
    curve.validate()
    ys = [curve.apply(x / 100.0) for x in range(0, 101)]
    for a, b in zip(ys, ys[1:]):
        assert b >= a - 1e-9


def test_curve_clamps_to_unit_interval():
    samples = make_samples(300, lambda p: 0.0)     # nunca acierta
    curve = fit_curve(samples)
    for p in (0.0, 0.5, 1.0):
        v = curve.apply(p)
        assert 0.0 <= v <= 1.0


def test_empty_samples_gives_identity():
    assert fit_curve([]).is_identity


def test_curve_roundtrip_serialization():
    curve = fit_curve(make_samples(300, lambda p: p * 0.8))
    back = CalibrationCurve.from_dict(curve.to_dict())
    for p in (0.1, 0.35, 0.6, 0.9):
        assert back.apply(p) == pytest.approx(curve.apply(p), abs=1e-5)


def test_curve_rejects_non_monotone_knots():
    bad = CalibrationCurve(knots_x=(0.0, 0.5, 1.0), knots_y=(0.0, 0.8, 0.4))
    with pytest.raises(ValueError):
        bad.validate()


# ─────────────────── corrección de sobreconfianza ──────────────────────────

def test_corrects_systematic_overconfidence():
    """
    El audit: 'la curva de calibración muestra sobreconfianza fuerte en
    probabilidades altas'. Simulamos exactamente eso: el modelo dice 0.8 pero
    la realidad es 0.6. La calibración debe bajar las probabilidades altas.
    """
    samples = make_samples(2000, lambda p: p * 0.75, seed=7)
    curve = fit_curve(samples, prior_strength=5.0)
    # En la zona alta la calibrada debe quedar por debajo de la raw.
    assert curve.apply(0.85) < 0.85
    assert curve.apply(0.85) == pytest.approx(0.85 * 0.75, abs=0.10)


def test_calibration_improves_brier_and_log_loss():
    samples = make_samples(3000, lambda p: p * 0.75, seed=11)
    curve = fit_curve(samples, prior_strength=5.0)

    raw = [s.normalized_prob() for s in samples]
    cal = [curve.apply(p) for p in raw]
    out = [s.hit_value for s in samples]

    assert brier_score(cal, out) < brier_score(raw, out)
    assert log_loss(cal, out) < log_loss(raw, out)
    assert expected_calibration_error(cal, out) < expected_calibration_error(raw, out)


def test_well_calibrated_model_is_barely_touched():
    """Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad."""
    samples = make_samples(3000, lambda p: p, seed=5)
    curve = fit_curve(samples, prior_strength=25.0)
    for p in (0.3, 0.5, 0.7):
        assert curve.apply(p) == pytest.approx(p, abs=0.06)


# ───────────────── shrinkage: poca muestra no manda ────────────────────────

def test_small_sample_barely_moves_from_prior():
    """
    Clave del diseño: con poca muestra el ruido NO puede dominar.
    8 observaciones extremas apenas deben mover la curva.
    """
    noisy = [
        CalibrationSample(prob=0.5, hit_value=1.0, market_family="goals")
        for _ in range(8)
    ]
    curve = fit_curve(noisy, prior_strength=25.0)
    # La tasa cruda es 1.0, pero el prior (identidad -> 0.5) debe dominar.
    assert curve.apply(0.5) < 0.65


def test_large_sample_does_move():
    strong = [
        CalibrationSample(prob=0.5, hit_value=1.0, market_family="goals")
        for _ in range(1000)
    ]
    curve = fit_curve(strong, prior_strength=25.0)
    assert curve.apply(0.5) > 0.9


def test_prior_strength_controls_shrinkage():
    samples = [
        CalibrationSample(prob=0.5, hit_value=1.0, market_family="goals")
        for _ in range(50)
    ]
    loose = fit_curve(samples, prior_strength=1.0).apply(0.5)
    tight = fit_curve(samples, prior_strength=500.0).apply(0.5)
    assert loose > tight
    assert tight == pytest.approx(0.5, abs=0.06)


# ───────────────────── calibrador jerárquico ───────────────────────────────

def test_untrained_calibrator_is_identity():
    cal = HierarchicalCalibrator.identity()
    assert cal.is_trained is False
    for p in (10.0, 55.0, 92.0):
        assert cal.apply(p, "goals", "L1") == pytest.approx(p, abs=1e-3)


def test_insufficient_data_yields_identity():
    """Menos de min_samples -> identidad, nunca una corrección inventada."""
    cal = HierarchicalCalibrator.fit(
        make_samples(5, lambda p: 0.1), min_samples=DEFAULT_MIN_SAMPLES
    )
    assert cal.curves[ROOT_KEY].is_identity
    assert cal.apply(0.8, "goals", "L1") == pytest.approx(0.8, abs=1e-6)


def test_hierarchy_creates_expected_segments():
    samples = (
        make_samples(300, lambda p: p * 0.8, market="goals", league="Premier", seed=1)
        + make_samples(300, lambda p: p * 0.9, market="corners", league="Premier", seed=2)
    )
    cal = HierarchicalCalibrator.fit(samples, min_samples=40)
    assert ROOT_KEY in cal.curves
    assert family_key("goals") in cal.curves
    assert family_key("corners") in cal.curves
    assert league_key("Premier", "goals") in cal.curves


def test_small_segment_inherits_parent():
    """Una liga con 3 picks no obtiene curva propia: hereda la de la familia."""
    samples = (
        make_samples(400, lambda p: p * 0.8, market="goals", league="Big", seed=3)
        + make_samples(3, lambda p: 0.0, market="goals", league="Tiny", seed=4)
    )
    cal = HierarchicalCalibrator.fit(samples, min_samples=40)
    assert league_key("Tiny", "goals") not in cal.curves
    # Resuelve a la curva de familia, no a algo degenerado.
    assert cal.resolve_curve("goals", "Tiny").segment == family_key("goals")


def test_resolution_prefers_most_specific():
    samples = make_samples(400, lambda p: p * 0.8, market="goals", league="Premier")
    cal = HierarchicalCalibrator.fit(samples, min_samples=40)
    assert cal.resolve_curve("goals", "Premier").segment == league_key("Premier", "goals")
    assert cal.resolve_curve("goals", "Desconocida").segment == family_key("goals")
    assert cal.resolve_curve("mercado_nuevo", None).segment == ROOT_KEY


def test_unknown_league_and_market_falls_back_safely():
    samples = make_samples(400, lambda p: p * 0.8, market="goals", league="Premier")
    cal = HierarchicalCalibrator.fit(samples, min_samples=40)
    v = cal.apply(0.7, "mercado_inexistente", "liga_inexistente")
    assert 0.0 < v < 1.0


# ───────────────────────── determinismo ────────────────────────────────────

def test_fit_is_deterministic():
    samples = make_samples(500, lambda p: p * 0.8, seed=99)
    a = HierarchicalCalibrator.fit(samples, min_samples=40)
    b = HierarchicalCalibrator.fit(samples, min_samples=40)
    assert a.curves.keys() == b.curves.keys()
    for k in a.curves:
        assert a.curves[k].knots_x == b.curves[k].knots_x
        assert a.curves[k].knots_y == b.curves[k].knots_y


def test_apply_is_deterministic():
    cal = HierarchicalCalibrator.fit(
        make_samples(500, lambda p: p * 0.8, seed=13), min_samples=40
    )
    vals = {cal.apply(0.63, "goals", "L1") for _ in range(20)}
    assert len(vals) == 1


# ───────────────────────── persistencia ───────────────────────────────────

def test_save_load_roundtrip(tmp_path):
    cal = HierarchicalCalibrator.fit(
        make_samples(500, lambda p: p * 0.8, seed=21), min_samples=40
    )
    path = cal.save(tmp_path / "cal.json")
    back = HierarchicalCalibrator.load(path)
    assert back.version == cal.version
    for p in (0.2, 0.5, 0.85):
        assert back.apply(p, "goals", "L1") == pytest.approx(
            cal.apply(p, "goals", "L1"), abs=1e-5
        )


def test_load_rejects_unknown_format_version():
    with pytest.raises(ValueError):
        HierarchicalCalibrator.from_dict({"format_version": 999, "curves": {}})


def test_artifact_is_versioned():
    cal = HierarchicalCalibrator.fit(make_samples(300, lambda p: p), min_samples=40)
    d = cal.to_dict()
    assert d["version"].startswith("cal-")
    assert d["fitted_at"] is not None
    assert d["metadata"]["n_samples"] == 300


# ───────────────────────── métricas ───────────────────────────────────────

def test_brier_perfect_and_worst():
    assert brier_score([1.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
    assert brier_score([0.0, 1.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_log_loss_penalizes_confident_errors():
    assert log_loss([0.99], [0.0]) > log_loss([0.6], [0.0])


def test_log_loss_is_finite_at_extremes():
    assert math.isfinite(log_loss([0.0], [1.0]))
    assert math.isfinite(log_loss([1.0], [0.0]))


def test_ece_zero_when_calibrated():
    probs = [0.5] * 100
    outcomes = [1.0] * 50 + [0.0] * 50
    assert expected_calibration_error(probs, outcomes) == pytest.approx(0.0, abs=1e-9)


def test_ece_detects_overconfidence():
    probs = [0.9] * 100
    outcomes = [1.0] * 50 + [0.0] * 50
    assert expected_calibration_error(probs, outcomes) == pytest.approx(0.4, abs=1e-9)


def test_reliability_table_reports_gap():
    probs = [0.85] * 40
    outcomes = [1.0] * 20 + [0.0] * 20
    rows = [r for r in reliability_table(probs, outcomes) if r["n"] > 0]
    assert len(rows) == 1
    assert rows[0]["confidence"] == pytest.approx(0.85)
    assert rows[0]["accuracy"] == pytest.approx(0.5)
    assert rows[0]["gap"] == pytest.approx(-0.35)


# ───────────────────────── walk-forward ───────────────────────────────────

def test_walk_forward_produces_oof_predictions():
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [
        CalibrationSample(
            prob=s.prob, hit_value=s.hit_value, market_family="goals",
            league="L1", timestamp=base + timedelta(hours=i),
        )
        for i, s in enumerate(make_samples(1000, lambda p: p * 0.75, seed=31))
    ]
    res = walk_forward_calibrate(samples, n_folds=5, prior_strength=5.0, min_train=40)
    assert len(res.outcomes) > 0
    assert len(res.raw_probs) == len(res.calibrated_probs) == len(res.outcomes)

    m = res.metrics()
    assert m["calibrated"]["brier"] < m["raw"]["brier"]
    assert res.improved() is True


def test_walk_forward_skips_folds_without_enough_training_data():
    res = walk_forward_calibrate(
        make_samples(10, lambda p: p), n_folds=5, min_train=1000
    )
    assert res.skipped > 0
    assert res.outcomes == []


def test_walk_forward_empty_input():
    res = walk_forward_calibrate([], n_folds=5)
    assert res.outcomes == []
    assert res.improved() is False


def test_improved_is_false_when_calibration_hurts():
    res = walk_forward_calibrate([], n_folds=5)
    res.raw_probs = [0.5, 0.5]
    res.calibrated_probs = [0.99, 0.01]
    res.outcomes = [0.0, 1.0]
    assert res.improved() is False


# ─────────────── construcción desde liquidaciones ─────────────────────────

def test_samples_from_settlements_excludes_push_and_unsettled():
    rows = [
        {"model_prob": 60.0, "outcome": "win", "market_family": "goals"},
        {"model_prob": 55.0, "outcome": "loss", "market_family": "goals"},
        {"model_prob": 50.0, "outcome": "push", "market_family": "goals"},
        {"model_prob": 50.0, "outcome": "unsettled", "market_family": "goals"},
        {"model_prob": 70.0, "outcome": "half_win", "market_family": "goals"},
    ]
    out = samples_from_settlements(rows)
    assert len(out) == 3                       # push y unsettled fuera
    assert sorted(s.hit_value for s in out) == [0.0, 0.5, 1.0]


def test_samples_from_settlements_parses_timestamps():
    rows = [{"model_prob": 60.0, "outcome": "win",
             "kickoff_utc": "2026-03-01T18:00:00Z"}]
    out = samples_from_settlements(rows)
    assert out[0].timestamp is not None
    assert out[0].timestamp.year == 2026


def test_samples_from_settlements_skips_malformed():
    rows = [
        {"model_prob": None, "outcome": "win"},
        {"model_prob": 60.0, "outcome": None},
        {"model_prob": 60.0, "outcome": "no_es_un_outcome"},
    ]
    assert samples_from_settlements(rows) == []
