"""Tests for EAR (Effective Accessible Reserve) outputs."""

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

from models.ear import OUTPUT_DIR, calculate_ear

PRISM_OUTPUT = ROOT / "models" / "output"


@pytest.fixture(scope="module")
def ear_run():
    """Run EAR calculation once for all tests."""
    return calculate_ear()


@pytest.fixture(scope="module")
def reserve_blocks() -> pd.DataFrame:
    """Load PRISM reserve blocks."""
    return pd.read_csv(PRISM_OUTPUT / "reserve_blocks.csv")


@pytest.fixture(scope="module")
def ear_blocks(ear_run) -> pd.DataFrame:
    """EAR blocks output."""
    return ear_run[0]


@pytest.fixture(scope="module")
def ear_summary(ear_run) -> dict:
    """EAR summary output."""
    return ear_run[1]


def test_only_ore_blocks_contribute_to_ear(ear_blocks, reserve_blocks):
    """Test 1: Only ore blocks can contribute to EAR."""
    waste = reserve_blocks["is_ore"] == 0
    waste_indices = reserve_blocks[waste].index
    assert (ear_blocks.loc[waste_indices, "accessible_tonnage_t"] == 0).all()
    assert (ear_blocks.loc[waste_indices, "operationally_accessible"] == False).all()


def test_inaccessible_blocks_have_zero_accessible_tonnage(ear_blocks):
    """Test 2: Inaccessible blocks have accessible_tonnage_t = 0."""
    inaccessible = ear_blocks["operationally_accessible"] == False
    assert (ear_blocks.loc[inaccessible, "accessible_tonnage_t"] == 0).all()


def test_accessible_blocks_retain_declared_tonnage(ear_blocks):
    """Test 3: Accessible blocks retain their declared tonnage."""
    accessible = ear_blocks["operationally_accessible"] == True
    if accessible.any():
        declared = ear_blocks.loc[accessible, "declared_tonnage_t"]
        accessible_t = ear_blocks.loc[accessible, "accessible_tonnage_t"]
        np.testing.assert_allclose(accessible_t.to_numpy(), declared.to_numpy(), rtol=1e-9)


def test_ear_does_not_exceed_declared_reserve(ear_blocks, ear_summary):
    """Test 4: Effective accessible reserve <= declared reserve."""
    assert ear_summary["effective_accessible_reserve_t"] <= ear_summary["declared_reserve_t"]
    ear_total = float(ear_blocks["accessible_tonnage_t"].sum())
    assert ear_total <= ear_summary["declared_reserve_t"]


def test_accessibility_ratio_bounds(ear_summary):
    """Test 5: Accessibility ratio is between 0 and 1."""
    ratio = ear_summary["accessibility_ratio"]
    assert 0.0 <= ratio <= 1.0
    if ear_summary["declared_reserve_t"] > 0:
        expected = (
            ear_summary["effective_accessible_reserve_t"] / ear_summary["declared_reserve_t"]
        )
        assert abs(ratio - expected) < 1e-4  # Tolerance for rounding


def test_development_constraint_affects_accessibility(ear_blocks, reserve_blocks):
    """Test 6: Development constraint affects accessibility."""
    ore = reserve_blocks["is_ore"] == 1
    ore_blocks = ear_blocks[ore]

    # Some ore blocks should not be development-ready
    assert ore_blocks["development_ready"].sum() < len(ore_blocks)
    # Some ore blocks should be development-ready
    assert ore_blocks["development_ready"].sum() > 0

    # Blocks not development-ready cannot be accessible
    not_dev_ready = ore_blocks["development_ready"] == False
    not_accessible_due_to_dev = ore_blocks.loc[not_dev_ready, "operationally_accessible"]
    # At least some blocks should be blocked by development constraint
    assert (not_accessible_due_to_dev == False).any()


def test_equipment_constraint_affects_accessibility(ear_blocks, ear_summary):
    """Test 7: Equipment constraint affects accessibility."""
    # Equipment availability is mine-wide in MVP
    equipment_available = ear_summary["constraints"]["equipment_available_mine_wide"]

    # If equipment is not available, no blocks should be accessible
    if not equipment_available:
        assert ear_blocks["operationally_accessible"].sum() == 0

    # Equipment availability column should reflect mine-wide status
    if ear_blocks["equipment_available"].any():
        assert ear_blocks["equipment_available"].all() == equipment_available


def test_weather_constraint_affects_accessibility(ear_blocks, reserve_blocks):
    """Test 8: Weather constraint affects accessibility."""
    ore = reserve_blocks["is_ore"] == 1
    ore_blocks = ear_blocks[ore]

    # Weather should affect some but not all ore blocks (probabilistic)
    weather_feasible_count = ore_blocks["weather_feasible"].sum()
    assert 0 < weather_feasible_count < len(ore_blocks)

    # Blocks not weather-feasible cannot be accessible
    not_weather_feasible = ore_blocks["weather_feasible"] == False
    if not_weather_feasible.any():
        not_accessible_due_to_weather = ore_blocks.loc[
            not_weather_feasible, "operationally_accessible"
        ]
        # Blocks without weather feasibility cannot be accessible
        assert (not_accessible_due_to_weather == False).all()


def test_summary_values_match_blocks(ear_blocks, ear_summary, reserve_blocks):
    """Test 9: Summary values match the block-level output."""
    ore = reserve_blocks["is_ore"] == 1

    # Declared reserve
    declared = float(reserve_blocks.loc[ore, "tonnage_t"].sum()) if ore.any() else 0.0
    assert abs(ear_summary["declared_reserve_t"] - declared) < 1.0

    # Effective accessible reserve
    accessible = float(ear_blocks["accessible_tonnage_t"].sum())
    assert abs(ear_summary["effective_accessible_reserve_t"] - accessible) < 1.0

    # Block counts
    accessible_blocks = int((ear_blocks["accessible_tonnage_t"] > 0).sum())
    assert ear_summary["accessible_blocks"] == accessible_blocks

    total_ore = int(ore.sum())
    assert ear_summary["total_ore_blocks"] == total_ore

    inaccessible = total_ore - accessible_blocks
    assert ear_summary["inaccessible_blocks"] == inaccessible

    # Accessibility ratio
    if declared > 0:
        ratio = accessible / declared
        assert abs(ear_summary["accessibility_ratio"] - ratio) < 1e-4  # Tolerance for rounding


def test_output_files_exist(ear_run):
    """Test 10: Running EAR produces the expected output files."""
    csv_path = OUTPUT_DIR / "ear_blocks.csv"
    json_path = OUTPUT_DIR / "ear_summary.json"

    assert csv_path.exists(), "ear_blocks.csv not created"
    assert json_path.exists(), "ear_summary.json not created"

    # Verify CSV can be read and has expected columns
    disk_blocks = pd.read_csv(csv_path)
    required_cols = [
        "block_id",
        "development_ready",
        "equipment_available",
        "weather_feasible",
        "operationally_accessible",
        "declared_tonnage_t",
        "accessible_tonnage_t",
    ]
    for col in required_cols:
        assert col in disk_blocks.columns, f"Missing column: {col}"

    # Verify JSON can be read and has expected keys
    with json_path.open("r", encoding="utf-8") as f:
        disk_summary = json.load(f)
    required_keys = [
        "declared_reserve_t",
        "effective_accessible_reserve_t",
        "accessibility_ratio",
        "accessible_blocks",
        "total_ore_blocks",
        "inaccessible_blocks",
    ]
    for key in required_keys:
        assert key in disk_summary, f"Missing summary key: {key}"

    _ = ear_run


def test_no_unexpected_nulls(ear_blocks):
    """Verify no unexpected null values in EAR outputs."""
    critical_cols = [
        "block_id",
        "development_ready",
        "equipment_available",
        "weather_feasible",
        "operationally_accessible",
        "declared_tonnage_t",
        "accessible_tonnage_t",
    ]
    for col in critical_cols:
        assert not ear_blocks[col].isna().any(), f"Unexpected nulls in {col}"


def test_declared_tonnage_matches_prism(ear_blocks, reserve_blocks):
    """Verify declared_tonnage_t matches PRISM tonnage_t."""
    np.testing.assert_allclose(
        ear_blocks["declared_tonnage_t"].to_numpy(),
        reserve_blocks["tonnage_t"].to_numpy(),
        rtol=1e-9,
    )


def test_all_constraints_required_for_accessibility(ear_blocks, reserve_blocks):
    """Verify that ALL constraints must be satisfied for accessibility."""
    ore = reserve_blocks["is_ore"] == 1
    ore_blocks = ear_blocks[ore]

    accessible = ore_blocks["operationally_accessible"] == True
    if accessible.any():
        # All accessible blocks must satisfy all three constraints
        assert ore_blocks.loc[accessible, "development_ready"].all()
        assert ore_blocks.loc[accessible, "equipment_available"].all()
        assert ore_blocks.loc[accessible, "weather_feasible"].all()

    # If any constraint is false, block cannot be accessible
    for idx in ore_blocks.index:
        if not ore_blocks.loc[idx, "development_ready"]:
            assert not ore_blocks.loc[idx, "operationally_accessible"]
        if not ore_blocks.loc[idx, "equipment_available"]:
            assert not ore_blocks.loc[idx, "operationally_accessible"]
        if not ore_blocks.loc[idx, "weather_feasible"]:
            assert not ore_blocks.loc[idx, "operationally_accessible"]


def test_meaningful_accessibility_gap(ear_summary):
    """Verify demo shows meaningful gap between declared and accessible reserve."""
    ratio = ear_summary["accessibility_ratio"]
    # Should not be 0% (some ore accessible) or 100% (all ore accessible)
    assert 0.0 < ratio < 1.0, "Accessibility ratio should show a meaningful gap"
    # Should be a substantial gap (not >95%)
    assert ratio < 0.95, "Gap between declared and accessible should be substantial"


def test_summary_contains_constraints_and_assumptions(ear_summary):
    """Verify summary contains constraint details and assumptions."""
    assert "constraints" in ear_summary
    assert "assumptions" in ear_summary
    assert "provenance" in ear_summary

    constraints = ear_summary["constraints"]
    assert "development_ready_z_threshold_m" in constraints
    assert "equipment_availability_threshold" in constraints
    assert "weather_rainfall_threshold_mm" in constraints
    assert "equipment_available_mine_wide" in constraints
    assert "weather_feasibility_score" in constraints

    assert isinstance(ear_summary["assumptions"], list)
    assert len(ear_summary["assumptions"]) > 0
