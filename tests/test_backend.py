"""Tests for Phase 7 — OreSight FastAPI Backend.

Uses FastAPI TestClient (synchronous). All tests read from the existing
Phase 1–6 output files; no models are retrained or rerun.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app, _OUT

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_nan_inf(obj) -> bool:
    """Recursively check that no float value is NaN or Inf."""
    if isinstance(obj, float):
        return not (math.isnan(obj) or math.isinf(obj))
    if isinstance(obj, dict):
        return all(_no_nan_inf(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_no_nan_inf(v) for v in obj)
    return True


# ---------------------------------------------------------------------------
# Test 1 — GET / returns 200
# ---------------------------------------------------------------------------


def test_root_returns_200():
    """Test 1: GET / returns HTTP 200."""
    r = client.get("/")
    assert r.status_code == 200


def test_root_body():
    """GET / contains name, status, version."""
    r = client.get("/")
    body = r.json()
    assert body["name"] == "OreSight API"
    assert body["status"] == "running"
    assert "version" in body


# ---------------------------------------------------------------------------
# Test 2 — GET /api/health returns 200
# ---------------------------------------------------------------------------


def test_health_returns_200():
    """Test 2: GET /api/health returns HTTP 200."""
    r = client.get("/api/health")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Test 3 — Health correctly identifies available phases
# ---------------------------------------------------------------------------


def test_health_identifies_phases():
    """Test 3: health.phases reflects actual output-file availability."""
    r = client.get("/api/health")
    body = r.json()
    assert body["status"] == "healthy"
    phases = body["phases"]
    file_map = {
        "prism":     ["reserve_summary.json", "reserve_blocks.csv"],
        "ear":       ["ear_summary.json", "ear_blocks.csv"],
        "pulse":     ["pulse_summary.json", "pulse_forecast.csv"],
        "risk_shap": ["risk_summary.json", "shap_importance.csv"],
        "nudge":     ["nudge_recommendation.json", "nudge_candidates.csv"],
    }
    for phase in ["prism", "ear", "pulse", "risk_shap", "nudge"]:
        assert phase in phases
        expected = all((_OUT / fname).exists() for fname in file_map[phase])
        assert phases[phase] == expected


# ---------------------------------------------------------------------------
# Test 4 — GET /api/overview returns 200
# ---------------------------------------------------------------------------


def test_overview_returns_200():
    """Test 4: GET /api/overview returns HTTP 200."""
    r = client.get("/api/overview")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Test 5 — Overview contains PRISM metrics
# ---------------------------------------------------------------------------


def test_overview_contains_prism(overview=None):
    """Test 5: overview.prism contains declared_reserve_t and ore_blocks."""
    r = client.get("/api/overview")
    body = r.json()
    assert "prism" in body
    prism = body["prism"]
    assert "declared_reserve_t" in prism
    assert "ore_blocks" in prism
    assert "average_mn_pct" in prism
    assert prism["declared_reserve_t"] > 0
    assert prism["ore_blocks"] == 498


# ---------------------------------------------------------------------------
# Test 6 — Overview contains EAR metrics
# ---------------------------------------------------------------------------


def test_overview_contains_ear():
    """Test 6: overview.ear contains effective_accessible_reserve_t."""
    body = client.get("/api/overview").json()
    ear = body["ear"]
    assert "effective_accessible_reserve_t" in ear
    assert "accessibility_ratio" in ear
    assert "accessible_blocks" in ear
    assert ear["accessible_blocks"] == 339
    assert ear["inaccessible_blocks"] == 159
    assert 0.0 < ear["accessibility_ratio"] < 1.0


# ---------------------------------------------------------------------------
# Test 7 — Overview contains PULSE metrics
# ---------------------------------------------------------------------------


def test_overview_contains_pulse():
    """Test 7: overview.pulse contains forecast summary values."""
    body = client.get("/api/overview").json()
    pulse = body["pulse"]
    for key in ["planned_production_t", "expected_production_t",
                "expected_shortfall_t", "shortfall_probability",
                "p10_production_t", "p50_production_t", "p90_production_t"]:
        assert key in pulse, f"Missing pulse key: {key}"
    assert pulse["planned_production_t"] > 0
    assert 0.0 <= pulse["shortfall_probability"] <= 1.0
    assert pulse["p10_production_t"] <= pulse["p50_production_t"] <= pulse["p90_production_t"]


# ---------------------------------------------------------------------------
# Test 8 — Overview contains risk metrics
# ---------------------------------------------------------------------------


def test_overview_contains_risk():
    """Test 8: overview contains risk_level and shortfall_probability."""
    body = client.get("/api/overview").json()
    assert "risk_level" in body
    assert "shortfall_probability" in body
    assert body["risk_level"] == "CRITICAL"
    assert 0.0 <= body["shortfall_probability"] <= 1.0


# ---------------------------------------------------------------------------
# Test 9 — Overview contains NUDGE recommendation
# ---------------------------------------------------------------------------


def test_overview_contains_nudge():
    """Test 9: overview.nudge contains best action fields."""
    body = client.get("/api/overview").json()
    assert "nudge" in body
    nudge = body["nudge"]
    for key in ["action_name", "feature", "baseline_value",
                "recommended_value", "expected_production_gain_t",
                "expected_shortfall_reduction_t", "new_shortfall_probability",
                "feasible"]:
        assert key in nudge, f"Missing nudge key: {key}"
    assert nudge["feasible"] is True
    assert nudge["expected_production_gain_t"] >= 0


# ---------------------------------------------------------------------------
# Test 10 — GET /api/prism returns valid data
# ---------------------------------------------------------------------------


def test_prism_returns_valid_data():
    """Test 10: /api/prism returns correct PRISM metrics."""
    r = client.get("/api/prism")
    assert r.status_code == 200
    body = r.json()
    assert body["total_blocks"] == 2240
    assert body["ore_blocks"]   == 498
    assert abs(body["declared_reserve_t"] - 48271696.4) < 1.0
    assert body["average_ore_mn_pct"] is not None
    assert "variogram" in body


# ---------------------------------------------------------------------------
# Test 11 — GET /api/ear returns valid data
# ---------------------------------------------------------------------------


def test_ear_returns_valid_data():
    """Test 11: /api/ear returns correct EAR metrics."""
    r = client.get("/api/ear")
    assert r.status_code == 200
    body = r.json()
    assert body["accessible_blocks"]   == 339
    assert body["inaccessible_blocks"] == 159
    assert abs(body["effective_accessible_reserve_t"] - 32736929.4) < 1.0
    assert abs(body["accessibility_ratio"] - 0.6782) < 0.001


# ---------------------------------------------------------------------------
# Test 12 — GET /api/pulse returns valid forecast data
# ---------------------------------------------------------------------------


def test_pulse_returns_valid_forecast():
    """Test 12: /api/pulse returns summary + 30-day forecast."""
    r = client.get("/api/pulse")
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    assert "forecast" in body
    forecast = body["forecast"]
    assert len(forecast) == 30
    # Verify P10 ≤ P50 ≤ P90 for all days
    for day in forecast:
        assert day["p10_t"] <= day["p50_t"] + 1e-6
        assert day["p50_t"] <= day["p90_t"] + 1e-6
        assert day["expected_production_t"] >= 0
        assert "date" in day
        assert "mine_id" in day


# ---------------------------------------------------------------------------
# Test 13 — GET /api/risk returns valid risk data
# ---------------------------------------------------------------------------


def test_risk_returns_valid_data():
    """Test 13: /api/risk returns CRITICAL risk with correct structure."""
    r = client.get("/api/risk")
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] == "CRITICAL"
    assert 0.0 <= body["overall_shortfall_probability"] <= 1.0
    assert isinstance(body["top_risk_drivers"], list)
    assert len(body["top_risk_drivers"]) > 0
    assert isinstance(body["actionable_drivers"], list)
    assert isinstance(body["contextual_drivers"], list)
    # Validate driver structure
    driver = body["top_risk_drivers"][0]
    for key in ["feature", "mean_absolute_shap", "impact_direction",
                "importance_rank", "driver_type"]:
        assert key in driver


# ---------------------------------------------------------------------------
# Test 14 — GET /api/shap returns ranked drivers
# ---------------------------------------------------------------------------


def test_shap_returns_ranked_drivers():
    """Test 14: /api/shap returns drivers sorted by importance_rank ASC."""
    r = client.get("/api/shap")
    assert r.status_code == 200
    body = r.json()
    assert "drivers" in body
    assert "count" in body
    drivers = body["drivers"]
    assert len(drivers) >= 1
    # Verify ascending rank order
    ranks = [d["importance_rank"] for d in drivers]
    assert ranks == sorted(ranks)
    # Verify required fields
    for d in drivers:
        assert d["impact_direction"] in ("UP", "DOWN")
        assert d["driver_type"] in ("ACTIONABLE", "CONTEXTUAL")
        assert d["mean_absolute_shap"] >= 0


# ---------------------------------------------------------------------------
# Test 15 — GET /api/nudge returns best action
# ---------------------------------------------------------------------------


def test_nudge_returns_best_action():
    """Test 15: /api/nudge returns a successful recommendation with all fields."""
    r = client.get("/api/nudge")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    ba = body["best_action"]
    for key in ["action_name", "feature", "baseline_value", "recommended_value",
                "expected_production_gain_t", "expected_shortfall_reduction_t",
                "new_shortfall_probability", "feasible"]:
        assert key in ba, f"Missing best_action key: {key}"
    assert ba["feasible"] is True
    assert ba["expected_production_gain_t"] >= 0
    assert 0.0 <= ba["new_shortfall_probability"] <= 1.0
    assert "constraints" in body
    assert "assumptions" in body


# ---------------------------------------------------------------------------
# Test 16 — GET /api/nudge/candidates returns candidate list
# ---------------------------------------------------------------------------


def test_nudge_candidates_returns_list():
    """Test 16: /api/nudge/candidates returns ranked, non-empty candidate list."""
    r = client.get("/api/nudge/candidates")
    assert r.status_code == 200
    body = r.json()
    assert "candidates" in body
    assert "count" in body
    cands = body["candidates"]
    assert len(cands) >= 1
    for c in cands:
        for key in ["rank", "action_name", "feature", "baseline_value",
                    "recommended_value", "production_gain_t",
                    "shortfall_reduction_t", "feasible"]:
            assert key in c
    # Ranks should be 1-based ascending
    ranks = [c["rank"] for c in cands]
    assert ranks[0] == 1


# ---------------------------------------------------------------------------
# Test 17 — Missing output file returns clean 404
# ---------------------------------------------------------------------------


def test_missing_file_returns_404(tmp_path, monkeypatch):
    """Test 17: if an output file is missing, the endpoint returns 404."""
    # Temporarily remap _OUT to a directory that has no files
    import backend.main as bm
    original_out = bm._OUT
    try:
        bm._OUT = tmp_path  # empty — no files here
        r = client.get("/api/prism")
        assert r.status_code == 404
        error_body = r.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        detail = error_body.get("detail", error_body)
        assert "error" in detail
    finally:
        bm._OUT = original_out


# ---------------------------------------------------------------------------
# Test 18 — Malformed JSON returns clean 500
# ---------------------------------------------------------------------------


def test_malformed_json_returns_500(tmp_path, monkeypatch):
    """Test 18: malformed output JSON returns 500 with a useful message."""
    import backend.main as bm
    original_out = bm._OUT
    try:
        bad_json = tmp_path / "reserve_summary.json"
        bad_json.write_text("{ this is not valid json }", encoding="utf-8")
        bm._OUT = tmp_path
        r = client.get("/api/prism")
        assert r.status_code == 500
        detail = r.json().get("detail", r.json())
        assert "error" in detail
    finally:
        bm._OUT = original_out


# ---------------------------------------------------------------------------
# Test 19 — Responses contain no invalid NaN/Infinity JSON values
# ---------------------------------------------------------------------------


def test_no_nan_infinity_in_responses():
    """Test 19: no endpoint returns NaN or Infinity in its JSON response."""
    endpoints = [
        "/", "/api/health", "/api/overview", "/api/prism", "/api/ear",
        "/api/pulse", "/api/risk", "/api/shap", "/api/nudge",
        "/api/nudge/candidates",
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200, f"Non-200 from {ep}: {r.status_code}"
        body = r.json()
        assert _no_nan_inf(body), f"NaN or Inf found in response from {ep}"


# ---------------------------------------------------------------------------
# Test 20 — CORS is configured for local frontend development
# ---------------------------------------------------------------------------


def test_cors_configured_for_local_frontend():
    """Test 20: CORS headers allow the React dev-server origins."""
    for origin in ["http://localhost:3000", "http://localhost:5173"]:
        r = client.get("/api/health", headers={"Origin": origin})
        assert r.status_code == 200
        # FastAPI/Starlette sets allow-origin when the origin is allowed
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao == origin, (
            f"Expected CORS allow-origin='{origin}', got '{acao}'"
        )


# ---------------------------------------------------------------------------
# Bonus — /docs endpoint is reachable
# ---------------------------------------------------------------------------


def test_swagger_docs_reachable():
    """Bonus: /docs returns 200 (Swagger UI available)."""
    r = client.get("/docs")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Bonus — /redoc endpoint is reachable
# ---------------------------------------------------------------------------


def test_redoc_reachable():
    """Bonus: /redoc returns 200 (ReDoc UI available)."""
    r = client.get("/redoc")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Bonus — overview provenance label is present
# ---------------------------------------------------------------------------


def test_overview_provenance_label():
    """Bonus: overview response carries the synthetic-data provenance label."""
    body = client.get("/api/overview").json()
    assert "provenance" in body
    assert "SYNTHETIC" in body["provenance"].upper() or "DEMO" in body["provenance"].upper()
