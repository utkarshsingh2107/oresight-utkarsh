"""Tests for PRISM Ordinary Kriging outputs."""

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

from models.prism import MN_CUTOFF_PCT, OUTPUT_DIR, run_prism

RAW = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def prism_run():
    return run_prism()


@pytest.fixture(scope="module")
def blocks_in() -> pd.DataFrame:
    return pd.read_csv(RAW / "blocks.csv")


@pytest.fixture(scope="module")
def result(prism_run) -> pd.DataFrame:
    return prism_run[0]


@pytest.fixture(scope="module")
def summary(prism_run) -> dict:
    return prism_run[1]


def test_output_contains_every_input_block(blocks_in, result):
    assert len(result) == len(blocks_in)
    assert set(result["block_id"]) == set(blocks_in["block_id"])


def test_block_ids_preserved(blocks_in, result):
    assert result["block_id"].tolist() == blocks_in["block_id"].tolist()
    assert result["mine_id"].tolist() == blocks_in["mine_id"].tolist()


def test_estimated_mn_numeric(result):
    assert pd.api.types.is_numeric_dtype(result["estimated_mn_pct"])
    assert pd.api.types.is_numeric_dtype(result["kriging_variance"])
    assert np.isfinite(result["estimated_mn_pct"]).all()
    assert np.isfinite(result["kriging_variance"]).all()


def test_tonnage_non_negative(result, blocks_in):
    assert (result["tonnage_t"] >= 0).all()
    expected = (blocks_in["volume_m3"] * blocks_in["density"]).to_numpy()
    np.testing.assert_allclose(result["tonnage_t"].to_numpy(), expected, rtol=1e-5, atol=0.15)


def test_ore_waste_classification(result):
    ore = result["is_ore"].eq(1)
    waste = result["is_ore"].eq(0)
    assert ore.sum() + waste.sum() == len(result)
    assert (result.loc[ore, "estimated_mn_pct"] >= MN_CUTOFF_PCT).all()
    assert (result.loc[waste, "estimated_mn_pct"] < MN_CUTOFF_PCT).all()
    assert set(result["is_ore"].unique()).issubset({0, 1})


def test_summary_totals_consistent(result, summary):
    ore = result["is_ore"].eq(1)
    assert summary["total_blocks"] == len(result)
    assert summary["ore_blocks"] == int(ore.sum())
    assert summary["waste_blocks"] == int((~ore).sum())
    assert summary["ore_blocks"] + summary["waste_blocks"] == summary["total_blocks"]
    declared = float(result.loc[ore, "tonnage_t"].sum()) if ore.any() else 0.0
    assert abs(summary["declared_reserve_t"] - declared) < 1.0
    if ore.any():
        avg = float(
            np.average(result.loc[ore, "estimated_mn_pct"], weights=result.loc[ore, "tonnage_t"])
        )
        assert abs(summary["average_ore_mn_pct"] - avg) < 0.02
    assert summary["min_estimated_mn_pct"] == pytest.approx(result["estimated_mn_pct"].min(), abs=0.01)
    assert summary["max_estimated_mn_pct"] == pytest.approx(result["estimated_mn_pct"].max(), abs=0.01)


def test_no_unexpected_nulls(result, summary):
    extra = ["estimated_mn_pct", "kriging_variance", "tonnage_t", "is_ore"]
    assert result.isna().sum().sum() == 0
    for col in extra:
        assert col in result.columns
    path = OUTPUT_DIR / "reserve_summary.json"
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    for key in (
        "total_blocks",
        "ore_blocks",
        "waste_blocks",
        "declared_reserve_t",
        "average_ore_mn_pct",
        "min_estimated_mn_pct",
        "max_estimated_mn_pct",
        "mean_kriging_variance",
    ):
        assert key in saved
        assert saved[key] is not None or key == "average_ore_mn_pct"
    csv_path = OUTPUT_DIR / "reserve_blocks.csv"
    assert csv_path.exists()
    disk = pd.read_csv(csv_path)
    assert len(disk) == len(result)
    assert disk.isna().sum().sum() == 0
    _ = summary
