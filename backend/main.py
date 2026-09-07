"""OreSight FastAPI Backend — Phase 7.

Pure API/presentation layer. Reads existing Phase 1–6 output files from
models/output/ and exposes them as JSON endpoints for the React frontend.

No model logic lives here. No retraining. No recalculation.
All intelligence is produced by: PRISM → EAR → PULSE → RISK+SHAP → NUDGE.

Startup:
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT        = _BACKEND_DIR.parent
_OUT         = _ROOT / "models" / "output"

# Expected output files (keyed by phase slug)
_OUTPUT_FILES: dict[str, list[Path]] = {
    "prism":     [_OUT / "reserve_summary.json", _OUT / "reserve_blocks.csv"],
    "ear":       [_OUT / "ear_summary.json",     _OUT / "ear_blocks.csv"],
    "pulse":     [_OUT / "pulse_summary.json",   _OUT / "pulse_forecast.csv"],
    "risk_shap": [_OUT / "risk_summary.json",    _OUT / "shap_importance.csv"],
    "nudge":     [_OUT / "nudge_recommendation.json", _OUT / "nudge_candidates.csv"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_json(path: Path) -> dict:
    """Load a JSON output file; raise 404 if missing, 500 if malformed."""
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "Required output file not found", "file": path.name},
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Output file could not be parsed", "file": path.name, "detail": str(exc)},
        ) from exc
    return raw


def _require_csv(path: Path) -> pd.DataFrame:
    """Load a CSV output file; raise 404 if missing, 500 if malformed."""
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "Required output file not found", "file": path.name},
        )
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Output CSV could not be read", "file": path.name, "detail": str(exc)},
        ) from exc
    return df


def _clean(obj: Any) -> Any:
    """Recursively replace NaN/Infinity with None so JSON serialisation is valid."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _phase_healthy(phase: str) -> bool:
    """Return True only when ALL required files for a phase exist."""
    return all(p.exists() for p in _OUTPUT_FILES.get(phase, []))


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OreSight API",
    description=(
        "Mine reserve intelligence API. Exposes outputs from PRISM, EAR, "
        "PULSE, RISK+SHAP, and NUDGE modules. "
        "**SYNTHETIC DEMO-01 data — not real MOIL operational data.**"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Create React App
        "http://localhost:5173",   # Vite
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class RootResponse(BaseModel):
    name: str
    status: str
    version: str


class PhaseHealth(BaseModel):
    prism: bool
    ear: bool
    pulse: bool
    risk_shap: bool
    nudge: bool


class HealthResponse(BaseModel):
    status: str
    phases: PhaseHealth


class PrismMetrics(BaseModel):
    declared_reserve_t: float
    ore_blocks: int
    waste_blocks: int
    average_mn_pct: float | None
    mn_cutoff_pct: float
    total_blocks: int
    provenance: str


class EarMetrics(BaseModel):
    declared_reserve_t: float
    effective_accessible_reserve_t: float
    accessibility_ratio: float
    accessible_blocks: int
    inaccessible_blocks: int
    total_ore_blocks: int
    provenance: str


class PulseMetrics(BaseModel):
    planned_production_t: float
    expected_production_t: float
    expected_shortfall_t: float
    shortfall_probability: float
    p10_production_t: float
    p50_production_t: float
    p90_production_t: float
    forecast_horizon_days: int
    mae: float
    rmse: float
    mape: float


class NudgeSummary(BaseModel):
    action_name: str
    feature: str
    baseline_value: float
    recommended_value: float
    expected_production_gain_t: float
    expected_shortfall_reduction_t: float
    new_shortfall_probability: float
    feasible: bool


class OverviewResponse(BaseModel):
    prism: PrismMetrics
    ear: EarMetrics
    pulse: PulseMetrics
    risk_level: str
    shortfall_probability: float
    nudge: NudgeSummary
    provenance: str


class ShapRecord(BaseModel):
    feature: str
    mean_absolute_shap: float
    impact_direction: str
    importance_rank: int
    driver_type: str


class ForecastRecord(BaseModel):
    date: str
    mine_id: str
    planned_production_t: float
    p10_t: float
    p50_t: float
    p90_t: float
    expected_production_t: float
    shortfall_t: float
    shortfall_probability: float


class NudgeCandidate(BaseModel):
    rank: int
    action_name: str
    feature: str
    baseline_value: float
    recommended_value: float
    expected_production_t: float
    production_gain_t: float
    expected_shortfall_t: float
    shortfall_reduction_t: float
    feasible: bool
    constraint_notes: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_model=RootResponse, summary="API root")
def root():
    """Identify the OreSight API."""
    return RootResponse(name="OreSight API", status="running", version="0.1.0")


@app.get("/api/health", response_model=HealthResponse, summary="Health check")
def health():
    """Return API health and per-phase output-file availability."""
    return HealthResponse(
        status="healthy",
        phases=PhaseHealth(
            prism=_phase_healthy("prism"),
            ear=_phase_healthy("ear"),
            pulse=_phase_healthy("pulse"),
            risk_shap=_phase_healthy("risk_shap"),
            nudge=_phase_healthy("nudge"),
        ),
    )


@app.get("/api/overview", response_model=OverviewResponse, summary="Dashboard overview")
def overview():
    """Combined cross-phase summary for the main dashboard.

    Aggregates key metrics from PRISM, EAR, PULSE, RISK, and NUDGE into a
    single response so the frontend can populate the dashboard in one call.
    """
    prism_raw  = _require_json(_OUT / "reserve_summary.json")
    ear_raw    = _require_json(_OUT / "ear_summary.json")
    pulse_raw  = _require_json(_OUT / "pulse_summary.json")
    risk_raw   = _require_json(_OUT / "risk_summary.json")
    nudge_raw  = _require_json(_OUT / "nudge_recommendation.json")

    fs = pulse_raw["forecast_summary"]
    vm = pulse_raw["validation_metrics"].get("P50", {})

    ba = nudge_raw.get("best_action", {})

    return _clean(OverviewResponse(
        prism=PrismMetrics(
            declared_reserve_t=prism_raw["declared_reserve_t"],
            ore_blocks=prism_raw["ore_blocks"],
            waste_blocks=prism_raw["waste_blocks"],
            average_mn_pct=prism_raw.get("average_ore_mn_pct"),
            mn_cutoff_pct=prism_raw["mn_cutoff_pct"],
            total_blocks=prism_raw["total_blocks"],
            provenance=prism_raw.get("provenance", ""),
        ),
        ear=EarMetrics(
            declared_reserve_t=ear_raw["declared_reserve_t"],
            effective_accessible_reserve_t=ear_raw["effective_accessible_reserve_t"],
            accessibility_ratio=ear_raw["accessibility_ratio"],
            accessible_blocks=ear_raw["accessible_blocks"],
            inaccessible_blocks=ear_raw["inaccessible_blocks"],
            total_ore_blocks=ear_raw.get("total_ore_blocks", ear_raw["accessible_blocks"] + ear_raw["inaccessible_blocks"]),
            provenance=ear_raw.get("provenance", ""),
        ),
        pulse=PulseMetrics(
            planned_production_t=fs["total_planned_production_t"],
            expected_production_t=fs["total_expected_production_t"],
            expected_shortfall_t=fs["total_expected_shortfall_t"],
            shortfall_probability=fs["overall_shortfall_probability"],
            p10_production_t=fs["total_p10_production_t"],
            p50_production_t=fs["total_p50_production_t"],
            p90_production_t=fs["total_p90_production_t"],
            forecast_horizon_days=pulse_raw["forecast_horizon_days"],
            mae=vm.get("MAE", 0.0),
            rmse=vm.get("RMSE", 0.0),
            mape=vm.get("MAPE", 0.0),
        ),
        risk_level=risk_raw["risk_level"],
        shortfall_probability=risk_raw["overall_shortfall_probability"],
        nudge=NudgeSummary(
            action_name=ba.get("action_name", ""),
            feature=ba.get("feature", ""),
            baseline_value=ba.get("baseline_value", 0.0),
            recommended_value=ba.get("recommended_value", 0.0),
            expected_production_gain_t=ba.get("expected_production_gain_t", 0.0),
            expected_shortfall_reduction_t=ba.get("expected_shortfall_reduction_t", 0.0),
            new_shortfall_probability=ba.get("new_shortfall_probability", 0.0),
            feasible=ba.get("feasible", False),
        ),
        provenance="SYNTHETIC DEMO-01 data — not real MOIL operational data",
    ))


@app.get("/api/prism", summary="PRISM reserve summary")
def prism():
    """Geological reserve estimation results from PRISM (Ordinary Kriging).

    Returns the declared reserve, block statistics, grade, and variogram
    parameters. Does not return the full block model to avoid large payloads.
    """
    raw = _require_json(_OUT / "reserve_summary.json")
    return _clean(raw)


@app.get("/api/prism/blocks", summary="PRISM block model (sampled for 3D visualisation)")
def prism_blocks():
    """Return the full PRISM block model with spatial coordinates, Mn grade, and ore flag.

    Returns all 2240 blocks. The frontend renders ore/waste 3D scatter from this.
    """
    df = _require_csv(_OUT / "reserve_blocks.csv")
    cols = ["block_id", "x", "y", "z", "estimated_mn_pct", "kriging_variance", "tonnage_t", "is_ore"]
    df = df[cols]
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return _clean({"blocks": records, "count": len(records)})


@app.get("/api/ear/blocks", summary="EAR ore blocks with accessibility flags (for 3D visualisation)")
def ear_blocks_endpoint():
    """Return ore blocks only with per-block accessibility constraint flags.

    498 ore blocks with: x, y, z, estimated_mn_pct, tonnage_t,
    development_ready, weather_feasible, operationally_accessible.
    """
    df = _require_csv(_OUT / "ear_blocks.csv")
    ore = df[df["is_ore"] == 1].copy()
    cols = [
        "block_id", "x", "y", "z", "estimated_mn_pct", "tonnage_t",
        "development_ready", "equipment_available", "weather_feasible",
        "operationally_accessible", "accessible_tonnage_t",
    ]
    ore = ore[cols]
    records = ore.where(ore.notna(), other=None).to_dict(orient="records")
    return _clean({"blocks": records, "count": len(records)})


@app.get("/api/ear", summary="EAR accessible reserve summary")
def ear():
    """Effective Accessible Reserve results — which ore is operationally reachable.

    Returns accessibility statistics and constraint thresholds.
    Use ?include_blocks=true to get block-level accessibility flags
    (2,240 rows).
    """
    raw = _require_json(_OUT / "ear_summary.json")
    return _clean(raw)


@app.get("/api/pulse", summary="PULSE production forecast")
def pulse():
    """Production forecast with P10/P50/P90 uncertainty bands and shortfall risk.

    Returns summary metrics plus the full 30-day daily forecast from
    pulse_forecast.csv.
    """
    summary_raw = _require_json(_OUT / "pulse_summary.json")
    forecast_df = _require_csv(_OUT / "pulse_forecast.csv")

    # Convert DataFrame to list of dicts; replace NaN
    records = forecast_df.where(forecast_df.notna(), other=None).to_dict(orient="records")

    return _clean({
        "summary": summary_raw,
        "forecast": records,
    })


@app.get("/api/risk", summary="RISK shortfall risk classification")
def risk():
    """Shortfall risk level and top risk drivers from RISK+SHAP.

    Returns the CRITICAL/HIGH/MEDIUM/LOW classification, shortfall metrics,
    and ranked actionable and contextual drivers.
    """
    raw = _require_json(_OUT / "risk_summary.json")
    return _clean(raw)


@app.get("/api/shap", summary="SHAP feature importance")
def shap():
    """SHAP feature importance — ranked production drivers.

    Returns all 38 features sorted by mean absolute SHAP value (DESC).
    Includes impact direction (UP/DOWN) and driver type (ACTIONABLE/CONTEXTUAL).
    SHAP values are model attributions, not proof of causation.
    """
    df = _require_csv(_OUT / "shap_importance.csv")
    df = df.sort_values("importance_rank")
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return _clean({"drivers": records, "count": len(records)})


@app.get("/api/nudge", summary="NUDGE best action recommendation")
def nudge():
    """Best prescriptive action recommendation from NUDGE.

    Returns the single best feasible intervention selected by PuLP
    optimization over counterfactual-scored candidates. Includes baseline,
    best action, constraints, and assumptions.

    Decision-support only — not autonomous mine control.
    """
    raw = _require_json(_OUT / "nudge_recommendation.json")
    return _clean(raw)


@app.get("/api/nudge/candidates", summary="NUDGE intervention candidates")
def nudge_candidates():
    """All NUDGE intervention candidates ranked by expected shortfall reduction.

    Returns every evaluated candidate with feasibility status, production gain,
    and shortfall reduction so the frontend can show the full comparison.
    """
    df = _require_csv(_OUT / "nudge_candidates.csv")
    df = df.sort_values("rank")
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return _clean({"candidates": records, "count": len(records)})
