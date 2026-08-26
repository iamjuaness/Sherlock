"""
Tests del cableado de la calibración en compare.py.

Contrato:
  - Sin artefacto -> identidad + recorte heurístico 0.82 (comportamiento previo).
  - Con artefacto -> la curva jerárquica manda y el 0.82 NO se aplica (no se
    castiga dos veces el mismo sesgo de sobreconfianza).
  - Artefacto corrupto o versión incompatible -> identidad, sin excepción.
  - El artefacto se recarga cuando cambia en disco.
"""

import json

import pytest

from src.models.calibration import (
    CalibrationSample,
    HierarchicalCalibrator,
)
from src.ui.api import compare as C


@pytest.fixture(autouse=True)
def _clean_calibrator(monkeypatch, tmp_path):
    """Aísla cada test con su propia ruta de artefacto y caché limpia."""
    monkeypatch.setattr(C, "CALIBRATION_ARTIFACT_PATH", str(tmp_path / "active.json"))
    C.reset_calibrator_cache()
    yield
    C.reset_calibrator_cache()


def _trained_artifact(path, shrink=0.70):
    """Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p."""
    samples = [
        CalibrationSample(
            prob=p / 100.0,
            hit_value=1.0 if (i % 100) < int(shrink * p) else 0.0,
            market_family="goals",
            league="Premier",
        )
        for i, p in enumerate([30, 45, 60, 75, 90] * 400)
    ]
    cal = HierarchicalCalibrator.fit(samples, prior_strength=5.0, min_samples=40)
    cal.save(path)
    return cal


# ─────────────────── sin artefacto = identidad ────────────────────────────

def test_no_artifact_means_identity():
    assert C.calibration_is_active() is False
    for p in (25.0, 55.0, 88.0):
        assert C.apply_calibration(p, 2.0, "goals") == pytest.approx(p, abs=1e-3)


def test_no_artifact_keeps_legacy_082_shrink():
    """Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo."""
    v = C._value_indicator("over_2.5_goals", 2.0, 85.0)   # implied 50%, edge 35
    assert v.calibrated_prob == pytest.approx(85.0 * 0.82, abs=0.6)


def test_no_artifact_small_edge_is_untouched():
    v = C._value_indicator("over_2.5_goals", 2.0, 55.0)   # edge 5 -> sin recorte
    assert v.calibrated_prob == pytest.approx(55.0, abs=0.6)


# ─────────────────── con artefacto = la curva manda ───────────────────────

def test_trained_artifact_activates_calibration(tmp_path):
    _trained_artifact(tmp_path / "active.json")
    assert C.calibration_is_active() is True


def test_trained_artifact_corrects_overconfidence(tmp_path):
    _trained_artifact(tmp_path / "active.json", shrink=0.70)
    out = C.apply_calibration(90.0, 2.0, "goals", league_name="Premier")
    assert out < 90.0
    assert 50.0 < out < 80.0


def test_trained_artifact_disables_082_double_penalty(tmp_path):
    """
    El 0.82 y la curva corrigen el MISMO sesgo. Aplicar ambos lo castiga dos
    veces, así que con curva entrenada el heurístico debe desactivarse.
    """
    _trained_artifact(tmp_path / "active.json", shrink=0.70)
    curve_only = C.apply_calibration(85.0, 2.0, "goals", league_name="Premier")
    v = C._value_indicator("over_2.5_goals", 2.0, 85.0, league_name="Premier")
    assert v.calibrated_prob == pytest.approx(curve_only, abs=0.15)
    assert v.calibrated_prob > curve_only * 0.82 + 0.5     # no hubo doble recorte


def test_scale_is_preserved_as_percentage(tmp_path):
    _trained_artifact(tmp_path / "active.json")
    out = C.apply_calibration(60.0, 2.0, "goals", league_name="Premier")
    assert 1.0 < out <= 100.0        # sigue en 0-100, no se convirtió a 0-1


# ─────────────────── robustez: fallar cerrado ─────────────────────────────

def test_corrupt_artifact_degrades_to_identity(tmp_path):
    (tmp_path / "active.json").write_text("{no es json válido", encoding="utf-8")
    assert C.calibration_is_active() is False
    assert C.apply_calibration(70.0, 2.0, "goals") == pytest.approx(70.0, abs=1e-3)


def test_incompatible_format_version_degrades_to_identity(tmp_path):
    (tmp_path / "active.json").write_text(
        json.dumps({"format_version": 999, "curves": {}}), encoding="utf-8"
    )
    assert C.calibration_is_active() is False
    assert C.apply_calibration(70.0, 2.0, "goals") == pytest.approx(70.0, abs=1e-3)


def test_none_prob_is_passed_through():
    assert C.apply_calibration(None, 2.0, "goals") is None


def test_unknown_market_and_league_do_not_raise(tmp_path):
    _trained_artifact(tmp_path / "active.json")
    out = C.apply_calibration(60.0, 2.0, "mercado_raro", league_name="liga_rara")
    assert 0.0 < out <= 100.0


# ─────────────────── recarga en caliente ──────────────────────────────────

def test_artifact_reloads_when_file_changes(tmp_path):
    path = tmp_path / "active.json"
    assert C.calibration_is_active() is False      # cachea la identidad
    _trained_artifact(path)
    assert C.calibration_is_active() is True       # detecta el artefacto nuevo


def test_calibrator_is_cached_between_calls(tmp_path):
    _trained_artifact(tmp_path / "active.json")
    assert C.get_calibrator() is C.get_calibrator()


def test_calibration_is_deterministic_across_calls(tmp_path):
    _trained_artifact(tmp_path / "active.json")
    vals = {
        C.apply_calibration(72.0, 2.1, "goals", league_name="Premier")
        for _ in range(20)
    }
    assert len(vals) == 1


# ─────────────────── coherencia con EV / Kelly ────────────────────────────

def test_calibration_flows_into_ev_and_kelly(tmp_path):
    """
    Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la
    calibración no llegase al EV, el pick seguiría publicándose igual.
    """
    v_raw = C._value_indicator("over_2.5_goals", 2.0, 90.0, league_name="Premier")
    _trained_artifact(tmp_path / "active.json", shrink=0.70)
    C.reset_calibrator_cache()
    v_cal = C._value_indicator("over_2.5_goals", 2.0, 90.0, league_name="Premier")

    assert v_cal.calibrated_prob < v_raw.calibrated_prob
    assert v_cal.edge_ev < v_raw.edge_ev
    assert v_cal.kelly_fraction <= v_raw.kelly_fraction
