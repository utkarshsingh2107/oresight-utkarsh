"""Quality checks for OreSight SYNTHETIC raw tables (Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

MN_MIN, MN_MAX = 0.0, 55.0
OPERATIONAL_FILES = [
    "production.csv",
    "equipment.csv",
    "blast.csv",
    "development.csv",
    "manpower.csv",
    "weather.csv",
]


def load(name: str) -> pd.DataFrame:
    path = RAW / name
    assert path.exists(), f"Missing {path}. Run scripts/generate_data.py first."
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def boreholes() -> pd.DataFrame:
    return load("boreholes.csv")


@pytest.fixture(scope="module")
def blocks() -> pd.DataFrame:
    return load("blocks.csv")


@pytest.fixture(scope="module")
def production() -> pd.DataFrame:
    return load("production.csv")


@pytest.fixture(scope="module")
def equipment() -> pd.DataFrame:
    return load("equipment.csv")


@pytest.fixture(scope="module")
def blast() -> pd.DataFrame:
    return load("blast.csv")


@pytest.fixture(scope="module")
def development() -> pd.DataFrame:
    return load("development.csv")


@pytest.fixture(scope="module")
def manpower() -> pd.DataFrame:
    return load("manpower.csv")


@pytest.fixture(scope="module")
def weather() -> pd.DataFrame:
    return load("weather.csv")


def test_required_columns_boreholes(boreholes):
    assert list(boreholes.columns) == [
        "hole_id",
        "x",
        "y",
        "collar_z",
        "depth",
        "Mn_pct",
        "Fe_pct",
        "SiO2_pct",
        "density",
    ]


def test_required_columns_blocks(blocks):
    assert list(blocks.columns) == [
        "block_id",
        "mine_id",
        "x",
        "y",
        "z",
        "volume_m3",
        "density",
    ]


def test_required_columns_operational(
    production, equipment, blast, development, manpower, weather
):
    assert list(production.columns) == ["date", "mine_id", "planned_t", "actual_t", "avg_mn_pct"]
    assert list(equipment.columns) == [
        "date",
        "mine_id",
        "equipment_id",
        "equipment_type",
        "downtime_h",
        "availability",
        "failure",
        "repair_h",
    ]
    assert list(blast.columns) == ["date", "mine_id", "blast_count", "delay_h", "delay_reason"]
    assert list(development.columns) == ["date", "mine_id", "development_m"]
    assert list(manpower.columns) == ["date", "mine_id", "available_workers", "shifts"]
    assert list(weather.columns) == ["date", "mine_id", "rainfall_mm", "soil_moisture", "NDVI", "LST"]


@pytest.mark.parametrize("name", ["boreholes.csv", "blocks.csv", *OPERATIONAL_FILES])
def test_no_unexpected_nulls(name):
    df = load(name)
    assert df.isna().sum().sum() == 0


def test_positive_volumes(blocks):
    assert (blocks["volume_m3"] > 0).all()


def test_positive_density(boreholes, blocks):
    assert (boreholes["density"] > 0).all()
    assert (blocks["density"] > 0).all()


def test_valid_mn_ranges(boreholes, production):
    assert boreholes["Mn_pct"].between(MN_MIN, MN_MAX).all()
    assert production["avg_mn_pct"].between(MN_MIN, MN_MAX).all()
    assert (boreholes["Fe_pct"] >= 0).all()
    assert (boreholes["SiO2_pct"] >= 0).all()


def test_non_negative_rainfall(weather):
    assert (weather["rainfall_mm"] >= 0).all()


def test_non_negative_downtime(equipment):
    assert (equipment["downtime_h"] >= 0).all()
    assert (equipment["repair_h"] >= 0).all()


def test_availability_between_0_and_1(equipment):
    assert equipment["availability"].between(0.0, 1.0).all()


def test_valid_dates(production, equipment, blast, development, manpower, weather):
    tables = [production, equipment, blast, development, manpower, weather]
    parsed = []
    for df in tables:
        dt = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
        assert dt.notna().all()
        parsed.append(set(dt.dt.strftime("%Y-%m-%d")))
    daily = parsed[0]
    assert daily == parsed[2] == parsed[3] == parsed[4] == parsed[5]
    assert parsed[1] == daily
    assert min(daily) == "2023-01-01"
    assert max(daily) == "2025-12-31"


def test_unique_ids(boreholes, blocks, equipment):
    assert boreholes["hole_id"].is_unique
    assert blocks["block_id"].is_unique
    assert not equipment.duplicated(["date", "equipment_id"]).any()


def test_mine_id_consistent(blocks, production, equipment, blast, development, manpower, weather):
    for df in (blocks, production, equipment, blast, development, manpower, weather):
        assert set(df["mine_id"].unique()) == {"DEMO-01"}


def test_row_count_bounds(boreholes, blocks, production):
    assert 50 <= len(boreholes) <= 100
    assert 1000 <= len(blocks) <= 3000
    assert 365 * 2 <= len(production) <= 366 * 3 + 1


def test_non_negative_operational_totals(production, blast, development, manpower):
    assert (production["planned_t"] >= 0).all()
    assert (production["actual_t"] >= 0).all()
    assert (blast["blast_count"] >= 0).all()
    assert (blast["delay_h"] >= 0).all()
    assert (development["development_m"] >= 0).all()
    assert (manpower["available_workers"] >= 0).all()
    assert manpower["shifts"].between(1, 3).all()
    assert (manpower["shifts"] == manpower["shifts"].astype(int)).all()
