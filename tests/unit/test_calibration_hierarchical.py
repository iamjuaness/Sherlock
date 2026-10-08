from datetime import datetime, timedelta, timezone
import pytest
from src.models.calibration import (
    CalibrationSample,
    HierarchicalCalibrator,
    compute_sample_weight,
    family_side_bucket_key,
    league_family_side_bucket_key,
    walk_forward_calibrate,
)


def test_calibration_keys():
    k1 = league_family_side_bucket_key("Primera A", "goals", "under", "core_2_5")
    assert k1 == "league:primera a|family:goals|side:under|bucket:core_2_5"

    k2 = family_side_bucket_key("goals", "under", "core_2_5")
    assert k2 == "family:goals|side:under|bucket:core_2_5"


def test_recency_weighting():
    ref_ts = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    ts_now = ref_ts
    ts_old = ref_ts - timedelta(days=30)

    w_now = compute_sample_weight(ts_now, ref_ts, half_life_days=30.0)
    w_old = compute_sample_weight(ts_old, ref_ts, half_life_days=30.0)

    assert abs(w_now - 1.0) < 1e-4
    assert abs(w_old - 0.5) < 1e-4


def test_hierarchical_resolution():
    samples = []
    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(100):
        samples.append(
            CalibrationSample(
                prob=0.6,
                hit_value=1.0 if i % 2 == 0 else 0.0,
                market_family="goals",
                side="under",
                line_bucket="core_2_5",
                league="Primera A",
                timestamp=base_ts + timedelta(days=i),
            )
        )

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
    assert curve.segment == "league:primera a|family:goals|side:under|bucket:core_2_5"
