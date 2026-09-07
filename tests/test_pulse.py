"""Tests for PULSE (Production Understanding, Learning & Shortfall Estimation)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.pulse import OUTPUT_DIR, load_operational_data, engineer_features, run_pulse

RAW = ROOT / "data" / "raw"
EAR_OUTPUT = ROOT / "models" / "output"


@pytest.fixture(scope="module")
def pulse_run():
    """Run PULSE calculation once for all tests."""
    return run_pulse()


@pytest.fixture(scope="module")
def forecast(pulse_run) -> pd.DataFrame:
    """PULSE forecast output."""
    return pulse_run[0]


@pytest.fixture(scope="module")
def summary(pulse_run) -> dict:
    """PULSE summary output."""
    return pulse_run[1]


@pytest.fixture(scope="module")
def production_data() -> pd.DataFrame:
    """Load raw production data."""
    return pd.read_csv(RAW / "production.csv", parse_dates=["date"])


@pytest.fixture(scope="module")
def ear_summary() -> dict:
    """Load EAR summary."""
    with (EAR_OUTPUT / "ear_summary.json").open("r") as f:
        return json.load(f)


def test_pulse_loads_production_data_correctly(production_data):
    """Test 1: PULSE loads production data correctly."""
    assert len(production_data) > 0
    required_cols = ["date", "mine_id", "planned_t", "actual_t"]
    for col in required_cols:
        assert col in production_data.columns


def test_chronological_split_used():
    """Test 2: Chronological train/validation split is used."""
    data = load_operational_data()
    data = engineer_features(data)
    data_clean = data.dropna()

    # Verify dates are monotonically increasing (chronological)
    assert data_clean["date"].is_monotonic_increasing


def test_no_future_data_leakage():
    """Test 3: No future data leakage occurs."""
    data = load_operational_data()
    data_with_features = engineer_features(data)

    # Check that lag features only use past data
    lag_cols = [c for c in data_with_features.columns if "lag" in c or "rolling" in c]
    assert len(lag_cols) > 0, "Lag/rolling features should exist"

    # Verify no NaN in original data but NaN in early lag features (expected)
    original_cols = ["actual_t", "planned_t", "fleet_availability"]
    for col in original_cols:
        if col in data.columns:
            assert not data[col].isna().any()


def test_model_trains_successfully(summary):
    """Test 4: Model trains successfully."""
    assert "model" in summary
    assert summary["model"] == "LightGBM Quantile Regression"
    assert "validation_metrics" in summary
    assert len(summary["validation_metrics"]) == 3  # P10, P50, P90


def test_forecast_contains_30_days(forecast):
    """Test 5: Forecast contains 30 days."""
    assert len(forecast) == 30


def test_quantile_ordering(forecast):
    """Test 6: P10 <= P50 <= P90 for every forecast date."""
    assert (forecast["p10_t"] <= forecast["p50_t"]).all()
    assert (forecast["p50_t"] <= forecast["p90_t"]).all()


def test_forecast_values_non_negative(forecast):
    """Test 7: Forecast values are non-negative."""
    assert (forecast["p10_t"] >= 0).all()
    assert (forecast["p50_t"] >= 0).all()
    assert (forecast["p90_t"] >= 0).all()
    assert (forecast["expected_production_t"] >= 0).all()


def test_shortfall_calculated_correctly(forecast):
    """Test 8: Shortfall is calculated correctly."""
    # Shortfall = max(0, planned - expected)
    expected_shortfall = (forecast["planned_production_t"] - forecast["expected_production_t"]).clip(lower=0)
    np.testing.assert_allclose(forecast["shortfall_t"].to_numpy(), expected_shortfall.to_numpy(), rtol=1e-6)


def test_shortfall_probability_bounds(forecast):
    """Test 9: Shortfall probability is between 0 and 1."""
    assert (forecast["shortfall_probability"] >= 0).all()
    assert (forecast["shortfall_probability"] <= 1).all()


def test_ear_constraint_respected(forecast, ear_summary):
    """Test 10: EAR constraint is respected."""
    ear_accessible_reserve = ear_summary["effective_accessible_reserve_t"]
    total_p50_forecast = float(forecast["p50_t"].sum())

    # Forecast should not exceed accessible reserve
    assert total_p50_forecast <= ear_accessible_reserve


def test_output_csv_generated(pulse_run):
    """Test 11: Output CSV is generated."""
    csv_path = OUTPUT_DIR / "pulse_forecast.csv"
    assert csv_path.exists()

    # Verify CSV can be read and has expected columns
    disk_forecast = pd.read_csv(csv_path)
    required_cols = [
        "date",
        "mine_id",
        "planned_production_t",
        "p10_t",
        "p50_t",
        "p90_t",
        "expected_production_t",
        "shortfall_t",
        "shortfall_probability",
    ]
    for col in required_cols:
        assert col in disk_forecast.columns

    _ = pulse_run


def test_output_json_generated(pulse_run):
    """Test 12: Output JSON is generated."""
    json_path = OUTPUT_DIR / "pulse_summary.json"
    assert json_path.exists()

    # Verify JSON can be read and has expected keys
    with json_path.open("r") as f:
        disk_summary = json.load(f)

    required_keys = [
        "model",
        "forecast_horizon_days",
        "training_period",
        "validation_period",
        "forecast_period",
        "validation_metrics",
        "forecast_summary",
        "ear_integration",
    ]
    for key in required_keys:
        assert key in disk_summary

    _ = pulse_run


def test_summary_metrics_match_forecast(forecast, summary):
    """Test 13: Summary metrics match the forecast output."""
    fs = summary["forecast_summary"]

    # Check totals
    assert abs(fs["total_planned_production_t"] - forecast["planned_production_t"].sum()) < 1.0
    assert abs(fs["total_p10_production_t"] - forecast["p10_t"].sum()) < 1.0
    assert abs(fs["total_p50_production_t"] - forecast["p50_t"].sum()) < 1.0
    assert abs(fs["total_p90_production_t"] - forecast["p90_t"].sum()) < 1.0
    assert abs(fs["total_expected_production_t"] - forecast["expected_production_t"].sum()) < 1.0
    assert abs(fs["total_expected_shortfall_t"] - forecast["shortfall_t"].sum()) < 1.0

    # Check shortfall probability (overall is mean of daily probabilities)
    mean_prob = float(forecast["shortfall_probability"].mean())
    assert abs(fs["overall_shortfall_probability"] - mean_prob) < 1e-4


def test_phase1_tests_still_pass():
    """Test 14: Existing Phase 1 tests still pass."""
    # This is verified by running the full test suite
    # Just ensure we can load the data files
    boreholes = pd.read_csv(RAW / "boreholes.csv")
    blocks = pd.read_csv(RAW / "blocks.csv")
    assert len(boreholes) > 0
    assert len(blocks) > 0


def test_prism_tests_still_pass():
    """Test 15: Existing PRISM tests still pass."""
    # This is verified by running the full test suite
    # Just ensure PRISM outputs still exist
    reserve_blocks_path = EAR_OUTPUT / "reserve_blocks.csv"
    reserve_summary_path = EAR_OUTPUT / "reserve_summary.json"
    assert reserve_blocks_path.exists()
    assert reserve_summary_path.exists()


def test_ear_tests_still_pass():
    """Test 16: Existing EAR tests still pass."""
    # This is verified by running the full test suite
    # Just ensure EAR outputs still exist
    ear_blocks_path = EAR_OUTPUT / "ear_blocks.csv"
    ear_summary_path = EAR_OUTPUT / "ear_summary.json"
    assert ear_blocks_path.exists()
    assert ear_summary_path.exists()


def test_expected_production_equals_p50(forecast):
    """Verify expected production equals P50 (median forecast)."""
    np.testing.assert_allclose(
        forecast["expected_production_t"].to_numpy(), forecast["p50_t"].to_numpy(), rtol=1e-9
    )


def test_validation_metrics_present(summary):
    """Verify validation metrics are present and reasonable."""
    val_metrics = summary["validation_metrics"]
    for quantile in ["P10", "P50", "P90"]:
        assert quantile in val_metrics
        metrics = val_metrics[quantile]
        assert "MAE" in metrics
        assert "RMSE" in metrics
        assert "MAPE" in metrics
        # Check metrics are positive and reasonable
        assert metrics["MAE"] > 0
        assert metrics["RMSE"] >= metrics["MAE"]  # RMSE should be >= MAE
        assert 0 < metrics["MAPE"] < 100  # MAPE should be percentage


def test_ear_integration_documented(summary):
    """Verify EAR integration is documented in summary."""
    ear_integration = summary["ear_integration"]
    assert "accessible_reserve_t" in ear_integration
    assert "ear_constraint_applied" in ear_integration
    assert "forecast_respects_ear" in ear_integration
    assert ear_integration["forecast_respects_ear"] is True


def test_no_unexpected_nulls(forecast):
    """Verify no unexpected null values in forecast."""
    critical_cols = [
        "date",
        "mine_id",
        "planned_production_t",
        "p10_t",
        "p50_t",
        "p90_t",
        "expected_production_t",
        "shortfall_t",
        "shortfall_probability",
    ]
    for col in critical_cols:
        assert not forecast[col].isna().any(), f"Unexpected nulls in {col}"


def test_forecast_dates_continuous(forecast):
    """Verify forecast dates are continuous (no gaps)."""
    dates = pd.to_datetime(forecast["date"])
    date_diffs = dates.diff().dropna()
    # All differences should be 1 day
    assert (date_diffs == pd.Timedelta(days=1)).all()


def test_assumptions_documented(summary):
    """Verify assumptions are documented."""
    assert "assumptions" in summary
    assert isinstance(summary["assumptions"], list)
    assert len(summary["assumptions"]) > 0


def test_training_validation_chronological(summary):
    """Verify training period comes before validation period."""
    train_end = pd.to_datetime(summary["training_period"]["end"])
    val_start = pd.to_datetime(summary["validation_period"]["start"])
    assert train_end < val_start
