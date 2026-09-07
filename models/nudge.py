"""NUDGE — Prescriptive Decision and Intervention Optimization.

NUDGE is the prescriptive layer of OreSight. It consumes the PULSE production
forecast, the RISK shortfall probability, and the SHAP actionable driver list
to identify and recommend THE SINGLE BEST FEASIBLE OPERATIONAL ACTION that
most reduces the expected production shortfall.

Why NUDGE follows SHAP:
    SHAP tells us *which* features most influence the model's prediction.
    NUDGE translates that attribution into a concrete, bounded, operational
    recommendation — one that a mine manager can actually act on today.

How the best action is selected:
    For each controllable intervention candidate:
        1. Build a counterfactual feature matrix (one feature perturbed,
           all others held at baseline).
        2. Score counterfactual with the existing PULSE P50 model.
        3. Measure production gain vs. baseline.
        4. Check all operational constraints.
        5. Rank by shortfall reduction DESC.
    PuLP (CBC) is used as the formal optimizer to confirm the single best
    feasible action among enumerated candidates.

Important scope limitations:
    - NUDGE recommends decision-support actions only (high-level operational
      levers). It does NOT generate blasting parameters, drilling recipes,
      equipment operating instructions, or any hazardous procedures.
    - All recommendations are at strategic/planning level: fleet readiness,
      maintenance scheduling, development pace, workforce deployment.
    - Synthetic DEMO-01 data only — not real MOIL operational data.

Hackathon MVP: straightforward counterfactual scoring + PuLP selection.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pulp

warnings.filterwarnings("ignore", category=UserWarning)

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

OUTPUT_DIR  = Path(__file__).resolve().parent / "output"
PULSE_OUT   = _ROOT / "models" / "output"
RAW         = _ROOT / "data" / "raw"

# ---------------------------------------------------------------------------
# Intervention catalogue
# ---------------------------------------------------------------------------
# Each entry defines one controllable operational lever.
# Bounds are derived from actual historical distributions:
#   fleet_availability : p95 of daily mean across full history  = 0.957
#   fleet_downtime_h   : p10 of daily total across full history = 10.54
#   development_m      : p90 of daily values                    = 19.59
#   available_workers  : observed maximum                        = 92
#
# Excluded levers (with documented reasons):
#   planned_t           — external planning input, not an operational lever
#   delay_h             — baseline already 0.0 in forecast period (optimal)
#   shifts              — baseline already 3 (maximum observed value)
#   lag/rolling columns — derived from actual_t history; not directly settable
# ---------------------------------------------------------------------------
INTERVENTIONS: list[dict] = [
    {
        "action_name": "Improve fleet availability",
        "feature": "fleet_availability",
        "direction": "increase",           # improvement means higher value
        "baseline_key": "fleet_availability",
        "bound": 0.957,                    # p95 of historical daily mean
        "unit": "fraction",
        "description": "Improve preventive maintenance scheduling and spare-parts "
                        "readiness to raise daily fleet availability.",
        "steps": 6,                        # number of candidate levels to evaluate
    },
    {
        "action_name": "Reduce equipment downtime",
        "feature": "fleet_downtime_h",
        "direction": "decrease",           # improvement means lower value
        "baseline_key": "fleet_downtime_h",
        "bound": 10.54,                    # p10 of historical daily total
        "unit": "hours/day",
        "description": "Accelerate maintenance turnaround and reduce unplanned "
                        "stoppages to lower total daily fleet downtime.",
        "steps": 6,
    },
    {
        "action_name": "Increase development progress",
        "feature": "development_m",
        "direction": "increase",
        "baseline_key": "development_m",
        "bound": 19.59,                    # p90 of historical daily metres
        "unit": "m/day",
        "description": "Allocate additional development crews and prioritise "
                        "access headings to increase daily advance.",
        "steps": 6,
    },
    {
        "action_name": "Increase available workforce",
        "feature": "available_workers",
        "direction": "increase",
        "baseline_key": "available_workers",
        "bound": 92.0,                     # observed maximum in history
        "unit": "persons",
        "description": "Reduce absenteeism through standby rosters and "
                        "contractor mobilisation to maximise headcount.",
        "steps": 4,
    },
]


# ---------------------------------------------------------------------------
# Baseline builder
# ---------------------------------------------------------------------------

def build_baseline(test_df: pd.DataFrame, feature_cols: list[str]) -> dict:
    """Compute mean feature values over the forecast (test) period.

    The baseline is the average row of the test set. Counterfactuals modify
    a single feature while keeping all others at baseline.
    """
    numeric_cols = [c for c in feature_cols if c in test_df.columns]
    baseline = {col: float(test_df[col].mean()) for col in numeric_cols}
    return baseline


# ---------------------------------------------------------------------------
# Counterfactual scoring
# ---------------------------------------------------------------------------

def score_counterfactual(
    model,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    feature: str,
    new_value: float,
) -> float:
    """Score a single counterfactual intervention using the PULSE P50 model.

    Modifies `feature` to `new_value` across all rows in the test set,
    keeps all other features at their actual values, then returns mean
    daily predicted production.

    This deliberately avoids retraining and uses the model as a
    response surface for what-if analysis.
    """
    X_cf = test_df[feature_cols].copy()
    X_cf[feature] = new_value
    preds = model.predict(X_cf)
    preds = np.clip(preds, 0, None)
    return float(preds.mean())


# ---------------------------------------------------------------------------
# Feasibility check
# ---------------------------------------------------------------------------

def check_feasibility(
    intervention: dict,
    candidate_value: float,
    baseline_value: float,
) -> tuple[bool, str]:
    """Check whether a candidate value is within defined operational bounds."""
    direction = intervention["direction"]
    bound     = intervention["bound"]

    if direction == "increase":
        if candidate_value <= baseline_value:
            return False, "Candidate does not improve over baseline"
        if candidate_value > bound:
            return False, f"Exceeds bound ({bound:.4f})"
    else:  # decrease
        if candidate_value >= baseline_value:
            return False, "Candidate does not improve over baseline"
        if candidate_value < bound:
            return False, f"Below bound ({bound:.4f})"

    return True, "Within operational bounds"


# ---------------------------------------------------------------------------
# Candidate enumeration
# ---------------------------------------------------------------------------

def enumerate_candidates(
    interventions: list[dict],
    baseline: dict,
    model,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    baseline_production: float,
    planned_production_per_day: float,
    ear_accessible_reserve: float,
    forecast_days: int,
) -> pd.DataFrame:
    """Enumerate all intervention candidates, score, and check feasibility.

    For each intervention, linearly space `steps` candidate values between
    the baseline and the operational bound, score each, and keep the best
    feasible level for that intervention.
    """
    rows = []

    for iv in interventions:
        feat     = iv["feature"]
        direction = iv["direction"]
        bound    = iv["bound"]
        steps    = iv["steps"]
        base_val = baseline.get(feat)

        if base_val is None:
            continue   # feature not in this dataset — skip

        # Generate candidate levels between baseline and bound
        if direction == "increase":
            candidate_levels = np.linspace(base_val, bound, steps + 1)[1:]  # exclude baseline
        else:
            candidate_levels = np.linspace(base_val, bound, steps + 1)[1:]  # exclude baseline

        for level in candidate_levels:
            feasible, note = check_feasibility(iv, float(level), base_val)

            # Score with PULSE model
            mean_daily_cf = score_counterfactual(model, test_df, feature_cols, feat, float(level))
            total_cf      = mean_daily_cf * forecast_days
            gain          = total_cf - baseline_production
            shortfall_cf  = max(0.0, planned_production_per_day * forecast_days - total_cf)
            shortfall_red = max(0.0, (baseline_production - total_cf) * -1)  # ensure positive reduction

            # Simpler: shortfall reduction = baseline shortfall - new shortfall
            baseline_shortfall = max(0.0, planned_production_per_day * forecast_days - baseline_production)
            shortfall_red      = max(0.0, baseline_shortfall - shortfall_cf)

            # EAR constraint: total forecast must not exceed accessible reserve
            ear_ok = total_cf <= ear_accessible_reserve
            if not ear_ok:
                feasible = False
                note = f"Exceeds EAR accessible reserve ({ear_accessible_reserve:,.0f} t)"

            rows.append({
                "action_name":          iv["action_name"],
                "feature":              feat,
                "baseline_value":       round(base_val, 4),
                "recommended_value":    round(float(level), 4),
                "expected_production_t":round(total_cf, 1),
                "production_gain_t":    round(gain, 1),
                "expected_shortfall_t": round(shortfall_cf, 1),
                "shortfall_reduction_t":round(shortfall_red, 1),
                "feasible":             feasible,
                "constraint_notes":     note,
                "rank":                 None,       # filled later
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Keep only the best level per intervention (max shortfall_reduction_t among feasible)
    best_rows = []
    for action in df["action_name"].unique():
        sub = df[df["action_name"] == action]
        feasible_sub = sub[sub["feasible"] == True]
        if not feasible_sub.empty:
            best_rows.append(feasible_sub.loc[feasible_sub["shortfall_reduction_t"].idxmax()])
        else:
            # Include best infeasible for transparency
            best_rows.append(sub.loc[sub["shortfall_reduction_t"].idxmax()])

    best_df = pd.DataFrame(best_rows).reset_index(drop=True)

    # Sort: feasible first, then by shortfall_reduction_t DESC
    best_df = best_df.sort_values(
        ["feasible", "shortfall_reduction_t"],
        ascending=[False, False],
    ).reset_index(drop=True)

    best_df["rank"] = range(1, len(best_df) + 1)
    return best_df


# ---------------------------------------------------------------------------
# PuLP optimizer — formal selection of best single action
# ---------------------------------------------------------------------------

def select_best_action_pulp(candidates_df: pd.DataFrame) -> pd.Series | None:
    """Use PuLP (CBC) to formally select the single best feasible action.

    Objective: maximise shortfall_reduction_t
    Constraint: exactly one intervention selected, must be feasible.

    Returns the winning candidate row, or None if no feasible candidate exists.
    """
    feasible = candidates_df[candidates_df["feasible"] == True].reset_index(drop=True)
    if feasible.empty:
        return None

    n = len(feasible)
    prob = pulp.LpProblem("NUDGE_BestAction", pulp.LpMaximize)

    # Binary selection variables — one per candidate
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objective: maximise expected shortfall reduction
    prob += pulp.lpSum(
        feasible.loc[i, "shortfall_reduction_t"] * x[i] for i in range(n)
    )

    # Constraint: select exactly one action
    prob += pulp.lpSum(x) == 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        # Fallback: return top row by shortfall_reduction_t
        return feasible.iloc[0]

    for i in range(n):
        if pulp.value(x[i]) > 0.5:
            return feasible.iloc[i]

    return feasible.iloc[0]   # safety fallback


# ---------------------------------------------------------------------------
# Shortfall probability estimator for counterfactual scenario
# ---------------------------------------------------------------------------

def estimate_new_shortfall_probability(
    model,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    feature: str,
    new_value: float,
    quantile_models: dict,
) -> float:
    """Re-estimate shortfall probability using P10/P50/P90 under counterfactual.

    Uses the same interpolation logic as PULSE.
    """
    X_cf = test_df[feature_cols].copy()
    X_cf[feature] = new_value

    p10_preds = np.clip(quantile_models[0.1].predict(X_cf), 0, None)
    p50_preds = np.clip(quantile_models[0.5].predict(X_cf), 0, None)
    p90_preds = np.clip(quantile_models[0.9].predict(X_cf), 0, None)
    # enforce monotonicity
    p50_preds = np.maximum(p50_preds, p10_preds)
    p90_preds = np.maximum(p90_preds, p50_preds)

    planned = test_df["planned_t"].values

    probs = []
    for planned_i, p10, p50, p90 in zip(planned, p10_preds, p50_preds, p90_preds):
        if planned_i <= p10:
            probs.append(0.1)
        elif planned_i >= p90:
            probs.append(0.9)
        elif planned_i <= p50:
            probs.append(0.1 + (planned_i - p10) / (p50 - p10 + 1e-6) * 0.4)
        else:
            probs.append(0.5 + (planned_i - p50) / (p90 - p50 + 1e-6) * 0.4)

    return float(np.clip(np.mean(probs), 0.0, 1.0))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_nudge(output_dir: Path | None = None) -> tuple[dict, pd.DataFrame]:
    """Run NUDGE prescriptive optimization.

    Returns:
        (recommendation_dict, candidates_df)
    """
    from models.pulse import run_pulse_with_models

    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: obtain PULSE model, data, forecast ─────────────────────────
    print("Running PULSE to obtain trained models and forecast data...")
    forecast_df, pulse_summary, q_models, train_df, feature_cols = run_pulse_with_models(
        output_dir=output_dir
    )

    p50_model = q_models[0.5]
    fs        = pulse_summary["forecast_summary"]

    # ── Step 2: load test set (forecast period) ────────────────────────────
    from models.pulse import load_operational_data, engineer_features, prepare_train_val_test
    data = load_operational_data()
    data = engineer_features(data)
    _, _, test_df, _ = prepare_train_val_test(data)

    # ── Step 3: load EAR and SHAP outputs ──────────────────────────────────
    with (PULSE_OUT / "ear_summary.json").open() as f:
        ear_summary = json.load(f)
    ear_accessible_reserve = ear_summary["effective_accessible_reserve_t"]

    shap_df   = pd.read_csv(PULSE_OUT / "shap_importance.csv")
    risk_data = json.load((PULSE_OUT / "risk_summary.json").open())

    # ── Step 4: build baseline ─────────────────────────────────────────────
    print("Building baseline...")
    baseline = build_baseline(test_df, feature_cols)

    forecast_days             = int(pulse_summary["forecast_horizon_days"])
    planned_total             = float(fs["total_planned_production_t"])
    planned_per_day           = planned_total / forecast_days
    baseline_production_total = float(fs["total_expected_production_t"])
    baseline_shortfall_total  = float(fs["total_expected_shortfall_t"])
    baseline_prob             = float(fs["overall_shortfall_probability"])

    # ── Step 5: enumerate candidates and score counterfactuals ────────────
    print("Evaluating intervention candidates (counterfactual scoring)...")
    candidates_df = enumerate_candidates(
        interventions          = INTERVENTIONS,
        baseline               = baseline,
        model                  = p50_model,
        test_df                = test_df,
        feature_cols           = feature_cols,
        baseline_production    = baseline_production_total,
        planned_production_per_day = planned_per_day,
        ear_accessible_reserve = ear_accessible_reserve,
        forecast_days          = forecast_days,
    )

    # ── Step 6: PuLP optimizer — pick single best action ──────────────────
    print("Running PuLP optimizer to select best action...")
    best_row = select_best_action_pulp(candidates_df)

    if best_row is None:
        print("WARNING: No feasible action found.")
        status = "no_feasible_action"
        best_action_dict = {}
    else:
        status = "success"
        feat_best    = best_row["feature"]
        new_val_best = float(best_row["recommended_value"])

        # Estimate new shortfall probability using all three quantile models
        new_prob = estimate_new_shortfall_probability(
            p50_model, test_df, feature_cols,
            feat_best, new_val_best, q_models,
        )

        best_action_dict = {
            "action_name":                str(best_row["action_name"]),
            "feature":                    str(feat_best),
            "baseline_value":             float(best_row["baseline_value"]),
            "recommended_value":          float(new_val_best),
            "expected_production_t":      float(best_row["expected_production_t"]),
            "expected_production_gain_t": float(best_row["production_gain_t"]),
            "expected_shortfall_t":       float(best_row["expected_shortfall_t"]),
            "expected_shortfall_reduction_t": float(best_row["shortfall_reduction_t"]),
            "new_expected_shortfall_t":   float(best_row["expected_shortfall_t"]),
            "new_shortfall_probability":  round(new_prob, 4),
            "feasible":                   True,
        }

        # Look up description from INTERVENTIONS catalogue
        for iv in INTERVENTIONS:
            if iv["feature"] == feat_best:
                best_action_dict["rationale"] = iv["description"]
                break

    # ── Step 7: assemble recommendation ───────────────────────────────────
    recommendation = {
        "status": status,
        "provenance": "SYNTHETIC DEMO-01 data — not real MOIL operational data",
        "baseline": {
            "expected_production_t":  round(baseline_production_total, 1),
            "planned_production_t":   round(planned_total, 1),
            "expected_shortfall_t":   round(baseline_shortfall_total, 1),
            "shortfall_probability":  round(baseline_prob, 4),
            "fleet_availability":     round(float(baseline.get("fleet_availability", 0)), 4),
            "fleet_downtime_h":       round(float(baseline.get("fleet_downtime_h", 0)), 2),
            "delay_h":                round(float(baseline.get("delay_h", 0)), 3),
            "development_m":          round(float(baseline.get("development_m", 0)), 2),
            "available_workers":      round(float(baseline.get("available_workers", 0)), 1),
        },
        "best_action": best_action_dict,
        "optimization": {
            "objective":            "minimize_expected_shortfall",
            "method":               "PuLP CBC — binary selection over counterfactual candidates",
            "candidates_evaluated": int(len(candidates_df)),
            "feasible_candidates":  int(candidates_df["feasible"].sum()) if not candidates_df.empty else 0,
        },
        "constraints": [
            f"fleet_availability ≤ {INTERVENTIONS[0]['bound']} (p95 of historical daily mean)",
            f"fleet_downtime_h ≥ {INTERVENTIONS[1]['bound']} h (p10 of historical daily total)",
            f"development_m ≤ {INTERVENTIONS[2]['bound']} m/day (p90 of historical daily metres)",
            f"available_workers ≤ {INTERVENTIONS[3]['bound']:.0f} (historical maximum)",
            f"EAR constraint: 30-day forecast ≤ {ear_accessible_reserve:,.0f} t",
            "All recommendations are single-lever; other features held at baseline",
        ],
        "excluded_levers": {
            "planned_t":  "External planning input; not an operational lever",
            "delay_h":    "Already 0.0 h in forecast period — no upside available",
            "shifts":     "Already at maximum (3 shifts) in forecast period",
            "lag/rolling": "Derived from historical actual_t; not directly controllable",
        },
        "assumptions": [
            "Counterfactual scoring uses the PULSE P50 LightGBM model as response surface",
            "Only the target feature is perturbed; all others held at their actual test-period values",
            "Production gain estimated as mean daily prediction difference × 30 days",
            "New shortfall probability estimated using P10/P50/P90 quantile models",
            "Bounds derived from full historical data distributions (p10/p90/p95/max)",
            "One intervention at a time — combined multi-lever effects not evaluated",
        ],
    }

    # ── Step 8: write outputs ──────────────────────────────────────────────
    with (output_dir / "nudge_recommendation.json").open("w", encoding="utf-8") as f:
        json.dump(recommendation, f, indent=2)

    if not candidates_df.empty:
        candidates_df.to_csv(output_dir / "nudge_candidates.csv", index=False)

    return recommendation, candidates_df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("NUDGE — Prescriptive Decision & Intervention Optimization")
    print("(SYNTHETIC DEMO-01 — not real MOIL data)")
    print("=" * 70)

    rec, cands = run_nudge()

    b = rec["baseline"]
    print("\n" + "=" * 70)
    print("BASELINE")
    print("=" * 70)
    print(f"  Planned production:     {b['planned_production_t']:>12,.1f} t")
    print(f"  Expected production:    {b['expected_production_t']:>12,.1f} t")
    print(f"  Expected shortfall:     {b['expected_shortfall_t']:>12,.1f} t")
    print(f"  Shortfall probability:  {b['shortfall_probability']:>12.1%}")
    print(f"  Fleet availability:     {b['fleet_availability']:>12.4f}")
    print(f"  Fleet downtime (h/day): {b['fleet_downtime_h']:>12.2f}")
    print(f"  Blast delay (h/day):    {b['delay_h']:>12.3f}")
    print(f"  Development (m/day):    {b['development_m']:>12.2f}")
    print(f"  Available workers:      {b['available_workers']:>12.1f}")

    if rec["status"] == "success":
        ba = rec["best_action"]
        print("\n" + "=" * 70)
        print("BEST ACTION")
        print("=" * 70)
        print(f"  Action:               {ba['action_name']}")
        print(f"  Feature:              {ba['feature']}")
        print(f"  Baseline value:       {ba['baseline_value']}")
        print(f"  Recommended value:    {ba['recommended_value']}")
        print(f"  Expected production:  {ba['expected_production_t']:,.1f} t")
        print(f"  Production gain:      {ba['expected_production_gain_t']:,.1f} t")
        print(f"  Expected shortfall:   {ba['expected_shortfall_t']:,.1f} t")
        print(f"  Shortfall reduction:  {ba['expected_shortfall_reduction_t']:,.1f} t")
        print(f"  New shortfall prob:   {ba['new_shortfall_probability']:.1%}")
        print(f"  Feasible:             {ba['feasible']}")
    else:
        print("\n⚠  No feasible action found.")

    print("\n" + "=" * 70)
    print("ALL CANDIDATES")
    print("=" * 70)
    if not cands.empty:
        for _, row in cands.iterrows():
            feas = "✓" if row["feasible"] else "✗"
            print(
                f"  {feas} {int(row['rank']):>2}. {row['action_name']:<35}"
                f"  rec={row['recommended_value']:.4f}"
                f"  gain={row['production_gain_t']:>8,.1f} t"
                f"  Δshortfall={row['shortfall_reduction_t']:>7,.1f} t"
            )

    print(f"\nOutputs written to: {OUTPUT_DIR}")
    print("  - nudge_recommendation.json")
    print("  - nudge_candidates.csv")
    print("=" * 70)


if __name__ == "__main__":
    main()
