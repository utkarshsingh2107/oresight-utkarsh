"""Tests for Phase 5 — RISK + SHAP (Shortfall Risk & Root-Cause Explanation)."""

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

from models.risk_shap import (
    ACTIONABLE_FEATURES,
    CONTEXTUAL_FEATURES,
    OUTPUT_DIR,
    RISK_THRESHOLDS,
    classify_risk_level,
    run_risk_shap,
)

PULSE_OUTPUT = ROOT / "models" / "output"

# ---------------------------------------------------------------------------
# Module-scoped fixtures — run RISK+SHAP once for the whole test session.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def risk_run():
    """Run RISK+SHAP once and cache results."""
    return run_risk_shap()


@pytest.fixture(scope="module")
def risk_summary(risk_run) -> dict:
    return risk_run[0]


@pytest.fixture(scope="module")
def importance_df(risk_run) -> pd.DataFrame:
    return risk_run[1]


@pytest.fixture(scope="module")
def pulse_summary() -> dict:
    path = PULSE_OUTPUT / "pulse_summary.json"
    assert path.exists(), "pulse_summary.json must exist before running RISK tests"
    with path.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1 — RISK loads PULSE output correctly
# ---------------------------------------------------------------------------


def test_risk_loads_pulse_output(pulse_summary):
    """Test 1: RISK can read and use the PULSE summary correctly."""
    fs = pulse_summary["forecast_summary"]
    assert "overall_shortfall_probability" in fs
    assert "total_planned_production_t" in fs
    assert "total_expected_production_t" in fs
    assert "total_expected_shortfall_t" in fs
    # Values must be numeric and finite
    assert np.isfinite(fs["overall_shortfall_probability"])
    assert np.isfinite(fs["total_planned_production_t"])


# ---------------------------------------------------------------------------
# Test 2 — Shortfall probability is between 0 and 1
# ---------------------------------------------------------------------------


def test_shortfall_probability_bounds(risk_summary):
    """Test 2: overall_shortfall_probability ∈ [0, 1]."""
    p = risk_summary["overall_shortfall_probability"]
    assert 0.0 <= p <= 1.0


# ---------------------------------------------------------------------------
# Test 3 — Risk level mapping works for all four thresholds
# ---------------------------------------------------------------------------


def test_risk_level_mapping_all_levels():
    """Test 3: classify_risk_level produces the correct label for each band."""
    # LOW: [0.00, 0.25)
    assert classify_risk_level(0.00) == "LOW"
    assert classify_risk_level(0.10) == "LOW"
    assert classify_risk_level(0.24) == "LOW"
    # MEDIUM: [0.25, 0.50)
    assert classify_risk_level(0.25) == "MEDIUM"
    assert classify_risk_level(0.49) == "MEDIUM"
    # HIGH: [0.50, 0.75)
    assert classify_risk_level(0.50) == "HIGH"
    assert classify_risk_level(0.74) == "HIGH"
    # CRITICAL: [0.75, 1.00]
    assert classify_risk_level(0.75) == "CRITICAL"
    assert classify_risk_level(0.88) == "CRITICAL"
    assert classify_risk_level(1.00) == "CRITICAL"


# ---------------------------------------------------------------------------
# Test 4 — 88.4 % maps to CRITICAL
# ---------------------------------------------------------------------------


def test_884_maps_to_critical(risk_summary):
    """Test 4: the known 88.4 % shortfall probability is classified as CRITICAL."""
    assert risk_summary["risk_level"] == "CRITICAL"
    assert classify_risk_level(risk_summary["overall_shortfall_probability"]) == "CRITICAL"


# ---------------------------------------------------------------------------
# Test 5 — SHAP uses the PULSE model / features
# ---------------------------------------------------------------------------


def test_shap_uses_pulse_features(importance_df):
    """Test 5: every feature in the importance table comes from PULSE feature set."""
    from models.pulse import load_operational_data, engineer_features

    data = load_operational_data()
    data = engineer_features(data)
    exclude = {"date", "mine_id", "actual_t", "avg_mn_pct", "actual_vs_planned_ratio"}
    pulse_features = set(data.dropna().columns) - exclude

    for feat in importance_df["feature"]:
        assert feat in pulse_features, f"'{feat}' is not a PULSE feature"


# ---------------------------------------------------------------------------
# Test 6 — SHAP values generated successfully
# ---------------------------------------------------------------------------


def test_shap_values_generated(importance_df):
    """Test 6: SHAP importance table is non-empty and has expected columns."""
    assert len(importance_df) > 0
    for col in ["feature", "mean_absolute_shap", "impact_direction", "importance_rank", "driver_type"]:
        assert col in importance_df.columns


# ---------------------------------------------------------------------------
# Test 7 — Feature importance is non-empty
# ---------------------------------------------------------------------------


def test_feature_importance_non_empty(importance_df):
    """Test 7: importance table has at least one row with positive SHAP value."""
    assert len(importance_df) >= 1
    assert (importance_df["mean_absolute_shap"] >= 0).all()
    assert importance_df["mean_absolute_shap"].max() > 0


# ---------------------------------------------------------------------------
# Test 8 — Importance ranking is correctly sorted (DESC by mean_absolute_shap)
# ---------------------------------------------------------------------------


def test_importance_ranking_sorted(importance_df):
    """Test 8: rows are sorted descending by mean_absolute_shap."""
    values = importance_df["mean_absolute_shap"].to_numpy()
    assert (values[:-1] >= values[1:]).all(), "Rows must be sorted by SHAP DESC"
    ranks = importance_df["importance_rank"].to_numpy()
    assert list(ranks) == list(range(1, len(ranks) + 1)), "importance_rank must be 1-based sequential"


# ---------------------------------------------------------------------------
# Test 9 — Every reported feature exists in PULSE feature set
# ---------------------------------------------------------------------------


def test_every_feature_in_pulse_set(importance_df):
    """Test 9: no phantom features appear in the importance table."""
    all_known = ACTIONABLE_FEATURES | CONTEXTUAL_FEATURES
    for feat in importance_df["feature"]:
        assert feat in all_known, (
            f"Feature '{feat}' is not classified in ACTIONABLE_FEATURES or CONTEXTUAL_FEATURES"
        )


# ---------------------------------------------------------------------------
# Test 10 — Impact direction values are valid
# ---------------------------------------------------------------------------


def test_impact_direction_valid(importance_df):
    """Test 10: impact_direction is either 'UP' or 'DOWN' for every row."""
    valid = {"UP", "DOWN"}
    for val in importance_df["impact_direction"]:
        assert val in valid, f"Invalid impact_direction: '{val}'"


# ---------------------------------------------------------------------------
# Test 11 — Driver type values are valid
# ---------------------------------------------------------------------------


def test_driver_type_valid(importance_df):
    """Test 11: driver_type is either 'ACTIONABLE' or 'CONTEXTUAL' for every row."""
    valid = {"ACTIONABLE", "CONTEXTUAL"}
    for val in importance_df["driver_type"]:
        assert val in valid, f"Invalid driver_type: '{val}'"


# ---------------------------------------------------------------------------
# Test 12 — risk_summary.json is generated with required keys
# ---------------------------------------------------------------------------


def test_risk_summary_json_generated():
    """Test 12: risk_summary.json exists and contains all required top-level keys."""
    path = OUTPUT_DIR / "risk_summary.json"
    assert path.exists(), "risk_summary.json was not created"
    with path.open() as f:
        data = json.load(f)
    required = [
        "overall_shortfall_probability",
        "risk_level",
        "forecast_horizon_days",
        "expected_production_t",
        "planned_production_t",
        "expected_shortfall_t",
        "top_risk_drivers",
        "actionable_drivers",
        "contextual_drivers",
    ]
    for key in required:
        assert key in data, f"Missing key in risk_summary.json: '{key}'"


# ---------------------------------------------------------------------------
# Test 13 — shap_importance.csv is generated with required columns
# ---------------------------------------------------------------------------


def test_shap_importance_csv_generated():
    """Test 13: shap_importance.csv exists with required columns and ≥1 row."""
    path = OUTPUT_DIR / "shap_importance.csv"
    assert path.exists(), "shap_importance.csv was not created"
    df = pd.read_csv(path)
    for col in ["feature", "mean_absolute_shap", "impact_direction", "importance_rank", "driver_type"]:
        assert col in df.columns, f"Missing column in shap_importance.csv: '{col}'"
    assert len(df) >= 1


# ---------------------------------------------------------------------------
# Test 14 — No null values in critical output fields
# ---------------------------------------------------------------------------


def test_no_null_values_in_outputs(risk_summary, importance_df):
    """Test 14: critical fields contain no null/NaN values."""
    # risk_summary scalar fields
    for key in ["overall_shortfall_probability", "risk_level", "expected_production_t",
                "planned_production_t", "expected_shortfall_t"]:
        assert risk_summary[key] is not None, f"Null value for '{key}' in risk_summary"

    # importance_df columns
    for col in ["feature", "mean_absolute_shap", "impact_direction", "importance_rank", "driver_type"]:
        assert not importance_df[col].isna().any(), f"Null values in importance_df['{col}']"


# ---------------------------------------------------------------------------
# Test 15 — Phase 1 data quality tests still pass (data unchanged)
# ---------------------------------------------------------------------------


def test_phase1_data_intact():
    """Test 15: Phase 1 raw data files are untouched."""
    raw = ROOT / "data" / "raw"
    for fname in ["boreholes.csv", "blocks.csv", "production.csv",
                  "equipment.csv", "blast.csv", "development.csv",
                  "manpower.csv", "weather.csv"]:
        df = pd.read_csv(raw / fname)
        assert len(df) > 0, f"{fname} should not be empty"
        assert df.isna().sum().sum() == 0, f"{fname} should have no nulls"


# ---------------------------------------------------------------------------
# Test 16 — PRISM outputs unchanged
# ---------------------------------------------------------------------------


def test_prism_outputs_unchanged():
    """Test 16: PRISM output files exist and have correct block count."""
    reserve_blocks = pd.read_csv(PULSE_OUTPUT / "reserve_blocks.csv")
    assert len(reserve_blocks) == 2240
    with (PULSE_OUTPUT / "reserve_summary.json").open() as f:
        rsv = json.load(f)
    assert rsv["total_blocks"] == 2240
    assert rsv["ore_blocks"] == 498
    assert abs(rsv["declared_reserve_t"] - 48271696.4) < 1.0


# ---------------------------------------------------------------------------
# Test 17 — EAR outputs unchanged
# ---------------------------------------------------------------------------


def test_ear_outputs_unchanged():
    """Test 17: EAR output files exist and accessible reserve is unchanged."""
    ear_blocks = pd.read_csv(PULSE_OUTPUT / "ear_blocks.csv")
    assert len(ear_blocks) == 2240
    with (PULSE_OUTPUT / "ear_summary.json").open() as f:
        ear = json.load(f)
    assert ear["accessible_blocks"] == 339
    assert ear["inaccessible_blocks"] == 159
    assert abs(ear["effective_accessible_reserve_t"] - 32736929.4) < 1.0


# ---------------------------------------------------------------------------
# Test 18 — PULSE outputs unchanged (risk_shap rerun does not corrupt them)
# ---------------------------------------------------------------------------


def test_pulse_outputs_unchanged(risk_run):
    """Test 18: PULSE forecast and summary are still valid after RISK+SHAP rerun."""
    forecast = pd.read_csv(PULSE_OUTPUT / "pulse_forecast.csv")
    assert len(forecast) == 30
    # P10 ≤ P50 ≤ P90 still holds
    assert (forecast["p10_t"] <= forecast["p50_t"]).all()
    assert (forecast["p50_t"] <= forecast["p90_t"]).all()
    with (PULSE_OUTPUT / "pulse_summary.json").open() as f:
        ps = json.load(f)
    assert ps["forecast_horizon_days"] == 30
    assert 0.0 <= ps["forecast_summary"]["overall_shortfall_probability"] <= 1.0
    _ = risk_run  # ensure fixture order


# ---------------------------------------------------------------------------
# Bonus: risk summary values match PULSE summary values
# ---------------------------------------------------------------------------


def test_risk_summary_values_match_pulse(risk_summary, pulse_summary):
    """Risk summary monetary values must match PULSE forecast_summary."""
    fs = pulse_summary["forecast_summary"]
    assert abs(risk_summary["planned_production_t"] - fs["total_planned_production_t"]) < 1.0
    assert abs(risk_summary["expected_production_t"] - fs["total_expected_production_t"]) < 1.0
    assert abs(risk_summary["expected_shortfall_t"] - fs["total_expected_shortfall_t"]) < 1.0
    assert abs(
        risk_summary["overall_shortfall_probability"] - fs["overall_shortfall_probability"]
    ) < 1e-4


# ---------------------------------------------------------------------------
# Bonus: actionable + contextual lists are non-empty and disjoint
# ---------------------------------------------------------------------------


def test_actionable_and_contextual_lists(risk_summary):
    """Actionable and contextual driver lists must be non-empty and non-overlapping."""
    act_names = {d["feature"] for d in risk_summary["actionable_drivers"]}
    ctx_names = {d["feature"] for d in risk_summary["contextual_drivers"]}
    assert len(act_names) > 0, "actionable_drivers must not be empty"
    assert len(ctx_names) > 0, "contextual_drivers must not be empty"
    overlap = act_names & ctx_names
    assert len(overlap) == 0, f"Driver appears in both lists: {overlap}"


# ---------------------------------------------------------------------------
# Bonus: classify_risk_level rejects out-of-range input
# ---------------------------------------------------------------------------


def test_classify_risk_level_rejects_invalid():
    """classify_risk_level must raise ValueError for probabilities outside [0, 1]."""
    with pytest.raises(ValueError):
        classify_risk_level(-0.01)
    with pytest.raises(ValueError):
        classify_risk_level(1.01)
