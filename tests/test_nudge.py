"""Tests for Phase 6 — NUDGE (Prescriptive Decision & Intervention Optimization)."""

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

from models.nudge import (
    INTERVENTIONS,
    OUTPUT_DIR,
    build_baseline,
    check_feasibility,
    enumerate_candidates,
    run_nudge,
    select_best_action_pulp,
)

PULSE_OUT = ROOT / "models" / "output"
RAW       = ROOT / "data" / "raw"


# ---------------------------------------------------------------------------
# Module-scoped fixtures — run NUDGE once for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def nudge_run():
    """Run NUDGE once and cache results."""
    return run_nudge()


@pytest.fixture(scope="module")
def recommendation(nudge_run) -> dict:
    return nudge_run[0]


@pytest.fixture(scope="module")
def candidates(nudge_run) -> pd.DataFrame:
    return nudge_run[1]


@pytest.fixture(scope="module")
def pulse_summary() -> dict:
    with (PULSE_OUT / "pulse_summary.json").open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ear_summary() -> dict:
    with (PULSE_OUT / "ear_summary.json").open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def shap_importance() -> pd.DataFrame:
    return pd.read_csv(PULSE_OUT / "shap_importance.csv")


# ---------------------------------------------------------------------------
# Test 1 — NUDGE loads PULSE output correctly
# ---------------------------------------------------------------------------


def test_nudge_loads_pulse_output(pulse_summary):
    """Test 1: NUDGE can consume the PULSE summary output."""
    fs = pulse_summary["forecast_summary"]
    assert "overall_shortfall_probability" in fs
    assert "total_expected_production_t"   in fs
    assert "total_planned_production_t"    in fs
    assert fs["total_planned_production_t"] > 0


# ---------------------------------------------------------------------------
# Test 2 — NUDGE loads SHAP actionable drivers
# ---------------------------------------------------------------------------


def test_nudge_loads_shap_actionable_drivers(shap_importance):
    """Test 2: NUDGE can read the SHAP importance table and find actionable drivers."""
    actionable = shap_importance[shap_importance["driver_type"] == "ACTIONABLE"]
    assert len(actionable) > 0

    # Every feature used by NUDGE interventions must exist in SHAP table
    shap_features = set(shap_importance["feature"])
    for iv in INTERVENTIONS:
        assert iv["feature"] in shap_features, (
            f"NUDGE feature '{iv['feature']}' not found in SHAP importance table"
        )


# ---------------------------------------------------------------------------
# Test 3 — Candidates generated only for available actionable features
# ---------------------------------------------------------------------------


def test_candidates_generated_for_actionable_features_only(candidates, shap_importance):
    """Test 3: all candidate features are present in SHAP actionable driver list."""
    actionable_features = set(
        shap_importance[shap_importance["driver_type"] == "ACTIONABLE"]["feature"]
    )
    for feat in candidates["feature"].unique():
        assert feat in actionable_features, (
            f"Candidate feature '{feat}' is not in SHAP actionable list"
        )


# ---------------------------------------------------------------------------
# Test 4 — Baseline is calculated correctly
# ---------------------------------------------------------------------------


def test_baseline_calculated_correctly(recommendation):
    """Test 4: baseline values are consistent with PULSE forecast."""
    b = recommendation["baseline"]
    assert b["expected_production_t"] > 0
    assert b["planned_production_t"]  > 0
    assert b["expected_shortfall_t"]  >= 0
    assert 0.0 <= b["shortfall_probability"] <= 1.0
    # Shortfall = planned - expected (clamped at 0)
    expected_sf = max(0.0, b["planned_production_t"] - b["expected_production_t"])
    assert abs(b["expected_shortfall_t"] - expected_sf) < 1.0


# ---------------------------------------------------------------------------
# Test 5 — Candidate values stay within defined bounds
# ---------------------------------------------------------------------------


def test_candidate_values_within_bounds(candidates):
    """Test 5: every recommended_value respects the intervention bound."""
    # Build lookup from INTERVENTIONS catalogue
    bound_lookup = {iv["feature"]: (iv["direction"], iv["bound"]) for iv in INTERVENTIONS}

    for _, row in candidates.iterrows():
        feat = row["feature"]
        if feat not in bound_lookup:
            continue
        direction, bound = bound_lookup[feat]
        rec_val = float(row["recommended_value"])
        if direction == "increase":
            assert rec_val <= bound + 1e-6, (
                f"{feat}: recommended={rec_val:.4f} exceeds bound={bound:.4f}"
            )
        else:
            assert rec_val >= bound - 1e-6, (
                f"{feat}: recommended={rec_val:.4f} below bound={bound:.4f}"
            )


# ---------------------------------------------------------------------------
# Test 6 — Infeasible candidates are correctly identified
# ---------------------------------------------------------------------------


def test_infeasible_candidates_rejected():
    """Test 6: check_feasibility correctly rejects out-of-bound values."""
    iv_increase = {
        "feature": "fleet_availability",
        "direction": "increase",
        "bound": 0.957,
    }
    iv_decrease = {
        "feature": "fleet_downtime_h",
        "direction": "decrease",
        "bound": 10.54,
    }
    # Exceeds upper bound for increase
    feasible, note = check_feasibility(iv_increase, 0.99, 0.90)
    assert not feasible

    # Below lower bound for decrease
    feasible, note = check_feasibility(iv_decrease, 5.0, 15.0)
    assert not feasible

    # Does not improve over baseline (same direction)
    feasible, note = check_feasibility(iv_increase, 0.85, 0.90)
    assert not feasible

    # Valid cases
    feasible, _ = check_feasibility(iv_increase, 0.95, 0.90)
    assert feasible

    feasible, _ = check_feasibility(iv_decrease, 12.0, 15.0)
    assert feasible


# ---------------------------------------------------------------------------
# Test 7 — Feasible candidates are ranked correctly
# ---------------------------------------------------------------------------


def test_feasible_candidates_ranked_correctly(candidates):
    """Test 7: feasible candidates appear before infeasible; within feasible,
    shortfall_reduction_t is descending."""
    if candidates.empty:
        return

    feasible_mask = candidates["feasible"] == True
    feasible_df   = candidates[feasible_mask]
    infeasible_df = candidates[~feasible_mask]

    # Feasible ranks must all be lower (better) than infeasible ranks
    if len(feasible_df) > 0 and len(infeasible_df) > 0:
        assert feasible_df["rank"].max() < infeasible_df["rank"].min()

    # Within feasible, shortfall_reduction_t must be non-increasing
    reductions = feasible_df["shortfall_reduction_t"].to_numpy()
    assert (reductions[:-1] >= reductions[1:]).all()


# ---------------------------------------------------------------------------
# Test 8 — Production gain is calculated correctly
# ---------------------------------------------------------------------------


def test_production_gain_calculated_correctly(candidates, recommendation):
    """Test 8: production_gain_t = expected_production_t - baseline_expected."""
    baseline_prod = recommendation["baseline"]["expected_production_t"]
    for _, row in candidates.iterrows():
        expected_gain = round(row["expected_production_t"] - baseline_prod, 1)
        assert abs(row["production_gain_t"] - expected_gain) < 1.0, (
            f"Gain mismatch for {row['action_name']}: "
            f"computed={expected_gain}, stored={row['production_gain_t']}"
        )


# ---------------------------------------------------------------------------
# Test 9 — Shortfall reduction is calculated correctly
# ---------------------------------------------------------------------------


def test_shortfall_reduction_calculated_correctly(candidates, recommendation):
    """Test 9: shortfall_reduction_t = baseline_shortfall - candidate_shortfall (≥ 0)."""
    baseline_sf = recommendation["baseline"]["expected_shortfall_t"]
    for _, row in candidates.iterrows():
        expected_reduction = max(0.0, round(baseline_sf - row["expected_shortfall_t"], 1))
        assert abs(row["shortfall_reduction_t"] - expected_reduction) < 1.5, (
            f"Reduction mismatch for {row['action_name']}"
        )


# ---------------------------------------------------------------------------
# Test 10 — Best action maximises feasible shortfall reduction
# ---------------------------------------------------------------------------


def test_best_action_maximises_shortfall_reduction(recommendation, candidates):
    """Test 10: the selected best action has the highest shortfall_reduction_t
    among all feasible candidates."""
    if recommendation["status"] != "success":
        pytest.skip("No feasible action produced")

    ba_feat = recommendation["best_action"]["feature"]
    ba_red  = recommendation["best_action"]["expected_shortfall_reduction_t"]

    feasible = candidates[candidates["feasible"] == True]
    assert len(feasible) > 0

    max_reduction = feasible["shortfall_reduction_t"].max()
    assert abs(ba_red - max_reduction) < 1.0, (
        f"Best action reduction ({ba_red}) != max feasible ({max_reduction})"
    )


# ---------------------------------------------------------------------------
# Test 11 — Best action is feasible
# ---------------------------------------------------------------------------


def test_best_action_is_feasible(recommendation):
    """Test 11: the recommended best action is marked feasible."""
    if recommendation["status"] != "success":
        pytest.skip("No feasible action produced")
    assert recommendation["best_action"]["feasible"] is True


# ---------------------------------------------------------------------------
# Test 12 — EAR constraint is respected
# ---------------------------------------------------------------------------


def test_ear_constraint_respected(candidates, ear_summary):
    """Test 12: no candidate's expected_production_t exceeds accessible reserve."""
    ear_limit = ear_summary["effective_accessible_reserve_t"]
    for _, row in candidates.iterrows():
        assert row["expected_production_t"] <= ear_limit + 1.0, (
            f"{row['action_name']}: {row['expected_production_t']:,.1f} t > EAR {ear_limit:,.1f} t"
        )


# ---------------------------------------------------------------------------
# Test 13 — No recommended value exceeds its operational bound
# ---------------------------------------------------------------------------


def test_no_recommended_value_exceeds_bound(candidates):
    """Test 13: all recommended values are within their catalogue-defined bounds."""
    bound_map = {iv["feature"]: (iv["direction"], iv["bound"]) for iv in INTERVENTIONS}
    for _, row in candidates[candidates["feasible"] == True].iterrows():
        feat = row["feature"]
        if feat not in bound_map:
            continue
        direction, bound = bound_map[feat]
        rec = float(row["recommended_value"])
        if direction == "increase":
            assert rec <= bound + 1e-6
        else:
            assert rec >= bound - 1e-6


# ---------------------------------------------------------------------------
# Test 14 — nudge_recommendation.json is generated
# ---------------------------------------------------------------------------


def test_nudge_recommendation_json_generated(nudge_run):
    """Test 14: nudge_recommendation.json exists with required keys."""
    path = OUTPUT_DIR / "nudge_recommendation.json"
    assert path.exists(), "nudge_recommendation.json was not created"

    with path.open() as f:
        data = json.load(f)

    required_keys = [
        "status", "baseline", "best_action", "optimization",
        "constraints", "assumptions",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: '{key}'"

    baseline_keys = [
        "expected_production_t", "planned_production_t",
        "expected_shortfall_t", "shortfall_probability",
    ]
    for key in baseline_keys:
        assert key in data["baseline"], f"Missing baseline key: '{key}'"

    _ = nudge_run


# ---------------------------------------------------------------------------
# Test 15 — nudge_candidates.csv is generated
# ---------------------------------------------------------------------------


def test_nudge_candidates_csv_generated(nudge_run):
    """Test 15: nudge_candidates.csv exists with required columns."""
    path = OUTPUT_DIR / "nudge_candidates.csv"
    assert path.exists(), "nudge_candidates.csv was not created"

    df = pd.read_csv(path)
    required_cols = [
        "action_name", "feature", "baseline_value", "recommended_value",
        "expected_production_t", "production_gain_t", "expected_shortfall_t",
        "shortfall_reduction_t", "feasible", "constraint_notes", "rank",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: '{col}'"

    assert len(df) >= 1

    _ = nudge_run


# ---------------------------------------------------------------------------
# Test 16 — No null values in critical output fields
# ---------------------------------------------------------------------------


def test_no_null_critical_values(recommendation, candidates):
    """Test 16: critical fields contain no null values."""
    b = recommendation["baseline"]
    for key in ["expected_production_t", "planned_production_t",
                "expected_shortfall_t", "shortfall_probability"]:
        assert b[key] is not None

    if recommendation["status"] == "success":
        ba = recommendation["best_action"]
        for key in ["action_name", "feature", "baseline_value",
                    "recommended_value", "expected_production_gain_t",
                    "expected_shortfall_reduction_t", "feasible"]:
            assert ba[key] is not None

    if not candidates.empty:
        for col in ["action_name", "feature", "recommended_value",
                    "production_gain_t", "shortfall_reduction_t", "feasible"]:
            assert not candidates[col].isna().any(), f"Nulls in candidates['{col}']"


# ---------------------------------------------------------------------------
# Tests 17–21 — Previous phase outputs unchanged
# ---------------------------------------------------------------------------


def test_phase1_data_intact():
    """Test 17: Phase 1 raw data files are untouched."""
    for fname in ["boreholes.csv", "blocks.csv", "production.csv",
                  "equipment.csv", "blast.csv", "development.csv",
                  "manpower.csv", "weather.csv"]:
        df = pd.read_csv(RAW / fname)
        assert len(df) > 0
        assert df.isna().sum().sum() == 0


def test_prism_outputs_unchanged():
    """Test 18: PRISM reserve summary unchanged."""
    with (PULSE_OUT / "reserve_summary.json").open() as f:
        rsv = json.load(f)
    assert rsv["total_blocks"] == 2240
    assert rsv["ore_blocks"]   == 498
    assert abs(rsv["declared_reserve_t"] - 48271696.4) < 1.0


def test_ear_outputs_unchanged():
    """Test 19: EAR accessible reserve unchanged."""
    with (PULSE_OUT / "ear_summary.json").open() as f:
        ear = json.load(f)
    assert ear["accessible_blocks"]   == 339
    assert ear["inaccessible_blocks"] == 159
    assert abs(ear["effective_accessible_reserve_t"] - 32736929.4) < 1.0


def test_pulse_outputs_unchanged(nudge_run):
    """Test 20: PULSE forecast still valid (30 days, P10≤P50≤P90)."""
    forecast = pd.read_csv(PULSE_OUT / "pulse_forecast.csv")
    assert len(forecast) == 30
    assert (forecast["p10_t"] <= forecast["p50_t"]).all()
    assert (forecast["p50_t"] <= forecast["p90_t"]).all()
    _ = nudge_run


def test_risk_shap_outputs_unchanged(nudge_run):
    """Test 21: RISK+SHAP outputs still present and valid."""
    with (PULSE_OUT / "risk_summary.json").open() as f:
        risk = json.load(f)
    assert risk["risk_level"] == "CRITICAL"
    assert 0.0 <= risk["overall_shortfall_probability"] <= 1.0

    shap_df = pd.read_csv(PULSE_OUT / "shap_importance.csv")
    assert len(shap_df) >= 1
    assert "feature" in shap_df.columns
    _ = nudge_run


# ---------------------------------------------------------------------------
# Bonus — new shortfall probability is in valid range
# ---------------------------------------------------------------------------


def test_new_shortfall_probability_valid(recommendation):
    """Bonus: new_shortfall_probability after best action is in [0, 1]."""
    if recommendation["status"] != "success":
        pytest.skip("No feasible action produced")
    p = recommendation["best_action"]["new_shortfall_probability"]
    assert 0.0 <= p <= 1.0


# ---------------------------------------------------------------------------
# Bonus — best action produces non-negative production gain
# ---------------------------------------------------------------------------


def test_best_action_positive_gain(recommendation):
    """Bonus: best action must produce production gain ≥ 0."""
    if recommendation["status"] != "success":
        pytest.skip("No feasible action produced")
    assert recommendation["best_action"]["expected_production_gain_t"] >= 0


# ---------------------------------------------------------------------------
# Bonus — optimization block documents candidates evaluated
# ---------------------------------------------------------------------------


def test_optimization_metadata(recommendation):
    """Bonus: optimization block contains expected metadata."""
    opt = recommendation["optimization"]
    assert opt["objective"] == "minimize_expected_shortfall"
    assert opt["candidates_evaluated"] >= 1
    assert opt["feasible_candidates"] >= 0
    assert "PuLP" in opt["method"]
