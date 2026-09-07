"""RISK + SHAP — Shortfall Risk Quantification and Root-Cause Explanation.

RISK consumes the PULSE forecast to classify production shortfall risk into
transparent severity levels. SHAP explains WHY the forecast predicts that
risk by attributing each prediction to its operational drivers.

Together they answer:
    "Production target is at risk. What are the main operational drivers
    causing that risk?"

Hackathon MVP: transparent rule-based risk levels + SHAP TreeExplainer.
Input data is synthetic demonstration data (not MOIL).

Pipeline: PULSE forecast → RISK level → SHAP attribution → ranked root causes
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import shap

# Ensure project root is importable when run as a script
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# RISK configuration — transparent, documented thresholds
# ---------------------------------------------------------------------------
RISK_THRESHOLDS = {
    "LOW":      (0.00, 0.25),   # 0–25 %   shortfall probability
    "MEDIUM":   (0.25, 0.50),   # 25–50 %
    "HIGH":     (0.50, 0.75),   # 50–75 %
    "CRITICAL": (0.75, 1.00),   # 75–100 %
}

# Features that mining operations can influence (vs. contextual/environmental)
ACTIONABLE_FEATURES = {
    "fleet_availability",
    "fleet_downtime_h",
    "fleet_failures",
    "fleet_repair_h",
    "blast_count",
    "delay_h",
    "blast_delay_indicator",
    "development_m",
    "available_workers",
    "shifts",
    "planned_t",
    # Lag / rolling derivatives of actionable operational series
    "actual_t_lag_1",
    "actual_t_lag_2",
    "actual_t_lag_3",
    "actual_t_lag_7",
    "actual_t_lag_14",
    "actual_t_lag_30",
    "actual_t_rolling_mean_7",
    "actual_t_rolling_mean_14",
    "actual_t_rolling_mean_30",
    "actual_t_rolling_std_7",
    "actual_t_rolling_std_14",
    "actual_t_rolling_std_30",
    "fleet_availability_rolling_mean_7",
    "fleet_availability_rolling_mean_14",
    "fleet_availability_rolling_mean_30",
}

CONTEXTUAL_FEATURES = {
    "rainfall_mm",
    "soil_moisture",
    "NDVI",
    "LST",
    "rainfall_rolling_sum_7",
    "rainfall_rolling_sum_14",
    "rainfall_rolling_sum_30",
    "day_of_week",
    "day_of_month",
    "month",
    "quarter",
    "day_of_year",
}

ROOT = Path(__file__).resolve().parents[1]
PULSE_OUTPUT = ROOT / "models" / "output"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


# ---------------------------------------------------------------------------
# RISK layer
# ---------------------------------------------------------------------------

def classify_risk_level(shortfall_probability: float) -> str:
    """Map a shortfall probability to a risk level string.

    Thresholds (transparent, documented):
        0.00 – <0.25  → LOW
        0.25 – <0.50  → MEDIUM
        0.50 – <0.75  → HIGH
        0.75 –  1.00  → CRITICAL
    """
    p = float(shortfall_probability)
    if p < 0.0 or p > 1.0:
        raise ValueError(f"shortfall_probability must be in [0, 1]; got {p}")
    if p < 0.25:
        return "LOW"
    if p < 0.50:
        return "MEDIUM"
    if p < 0.75:
        return "HIGH"
    return "CRITICAL"


def build_risk_summary_from_pulse(pulse_summary: dict) -> dict:
    """Extract risk indicators directly from the PULSE summary dict."""
    fs = pulse_summary["forecast_summary"]
    overall_prob = fs["overall_shortfall_probability"]
    return {
        "overall_shortfall_probability": overall_prob,
        "risk_level": classify_risk_level(overall_prob),
        "forecast_horizon_days": pulse_summary["forecast_horizon_days"],
        "expected_production_t": fs["total_expected_production_t"],
        "planned_production_t": fs["total_planned_production_t"],
        "expected_shortfall_t": fs["total_expected_shortfall_t"],
    }


# ---------------------------------------------------------------------------
# SHAP explanation
# ---------------------------------------------------------------------------

def compute_shap_importance(
    model,  # lgb.Booster for P50
    train_df: pd.DataFrame,
    feature_cols: list[str],
    n_background: int = 200,
) -> pd.DataFrame:
    """Compute SHAP feature importance using TreeExplainer on the P50 model.

    Uses the training set as background for TreeExplainer, which is the
    standard approach for LightGBM tree models. SHAP values express how
    much each feature pushes individual predictions higher or lower than
    the average prediction. This reflects model attribution, not
    real-world causation.

    Args:
        model:          LightGBM Booster (P50 quantile model from PULSE).
        train_df:       Training DataFrame containing feature_cols + actual_t.
        feature_cols:   Ordered list of feature names, matching model input.
        n_background:   Number of training rows sampled as SHAP background.

    Returns:
        DataFrame sorted by mean_absolute_shap DESC with columns:
            feature, mean_absolute_shap, impact_direction,
            importance_rank, driver_type
    """
    rng = np.random.default_rng(42)
    n_bg = min(n_background, len(train_df))
    bg_idx = rng.choice(len(train_df), size=n_bg, replace=False)
    X_bg = train_df[feature_cols].iloc[bg_idx].reset_index(drop=True)
    X_full = train_df[feature_cols].reset_index(drop=True)

    explainer = shap.TreeExplainer(
        model,
        data=X_bg,
        feature_perturbation="tree_path_dependent",
    )
    # check_additivity=False is required for quantile-objective LightGBM models.
    # SHAP's additivity assumption holds for mean-objective trees; quantile
    # objectives shift the leaf values in a way that breaks the sum check
    # without affecting the correctness of relative feature attributions.
    shap_values = explainer.shap_values(X_full, check_additivity=False)

    mean_abs = np.abs(shap_values).mean(axis=0)    # (n_features,)
    # Mean raw SHAP (signed) tells us impact direction
    mean_signed = shap_values.mean(axis=0)         # positive → pushes UP, negative → pushes DOWN

    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "mean_absolute_shap": mean_abs,
        "mean_signed_shap": mean_signed,
    })

    importance_df = importance_df.sort_values("mean_absolute_shap", ascending=False)
    importance_df["importance_rank"] = range(1, len(importance_df) + 1)
    importance_df["impact_direction"] = importance_df["mean_signed_shap"].apply(
        lambda v: "UP" if v >= 0 else "DOWN"
    )
    importance_df["driver_type"] = importance_df["feature"].apply(
        lambda f: "ACTIONABLE" if f in ACTIONABLE_FEATURES else "CONTEXTUAL"
    )

    return importance_df[
        ["feature", "mean_absolute_shap", "impact_direction", "importance_rank", "driver_type"]
    ].reset_index(drop=True)


def get_driver_type(feature: str) -> str:
    """Return driver type for a single feature name."""
    if feature in ACTIONABLE_FEATURES:
        return "ACTIONABLE"
    if feature in CONTEXTUAL_FEATURES:
        return "CONTEXTUAL"
    return "CONTEXTUAL"   # default-safe for any unlisted feature


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_full_risk_summary(
    risk_base: dict,
    importance_df: pd.DataFrame,
    top_n: int = 5,
) -> dict:
    """Combine RISK indicators with SHAP top drivers into risk_summary.json."""
    top = importance_df.head(top_n)

    def row_to_dict(row: pd.Series) -> dict:
        return {
            "feature":              row["feature"],
            "mean_absolute_shap":   round(float(row["mean_absolute_shap"]), 6),
            "impact_direction":     row["impact_direction"],
            "importance_rank":      int(row["importance_rank"]),
            "driver_type":          row["driver_type"],
        }

    actionable = importance_df[importance_df["driver_type"] == "ACTIONABLE"].head(top_n)
    contextual  = importance_df[importance_df["driver_type"] == "CONTEXTUAL"].head(top_n)

    summary = {
        **risk_base,
        "top_risk_drivers":   [row_to_dict(r) for _, r in top.iterrows()],
        "actionable_drivers": [row_to_dict(r) for _, r in actionable.iterrows()],
        "contextual_drivers": [row_to_dict(r) for _, r in contextual.iterrows()],
        "shap_note": (
            "SHAP values measure model feature attribution. "
            "They reflect learned statistical patterns in the synthetic data, "
            "not proof of real-world causation."
        ),
        "risk_thresholds": RISK_THRESHOLDS,
        "provenance": "Derived from SYNTHETIC DEMO-01 data — not real MOIL data",
    }
    return summary


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_risk_shap(
    pulse_summary_path: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[dict, pd.DataFrame]:
    """Run RISK classification and SHAP explanation for OreSight Phase 5.

    Retrain PULSE internally (via run_pulse_with_models) so SHAP operates
    on exactly the same model object that produced the forecast. No separate
    model is built for SHAP.

    Returns:
        (risk_summary_dict, shap_importance_df)
    """
    # Import here to avoid circular imports at module level
    from models.pulse import run_pulse_with_models

    pulse_summary_path = pulse_summary_path or (PULSE_OUTPUT / "pulse_summary.json")
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: rerun PULSE to obtain live model objects -----------------
    print("Running PULSE to obtain trained models...")
    forecast, pulse_summary, models, train_df, feature_cols = run_pulse_with_models(
        output_dir=output_dir
    )

    # ---- Step 2: RISK layer ------------------------------------------------
    print("Computing RISK indicators...")
    risk_base = build_risk_summary_from_pulse(pulse_summary)
    print(
        f"  Shortfall probability: {risk_base['overall_shortfall_probability']:.1%}  "
        f"→ {risk_base['risk_level']}"
    )

    # ---- Step 3: SHAP explanation on P50 model ----------------------------
    print("Computing SHAP values (TreeExplainer on P50 model)...")
    p50_model = models[0.5]
    importance_df = compute_shap_importance(p50_model, train_df, feature_cols)

    # ---- Step 4: Assemble and write outputs --------------------------------
    risk_summary = build_full_risk_summary(risk_base, importance_df)

    shap_importance_csv = output_dir / "shap_importance.csv"
    risk_summary_json   = output_dir / "risk_summary.json"

    importance_df.to_csv(shap_importance_csv, index=False)

    with risk_summary_json.open("w", encoding="utf-8") as f:
        json.dump(risk_summary, f, indent=2)

    return risk_summary, importance_df


def main() -> None:
    """Run RISK+SHAP and display results."""
    print("=" * 70)
    print("RISK + SHAP — Shortfall Risk & Root-Cause Explanation")
    print("(SYNTHETIC DEMO-01 — not real MOIL data)")
    print("=" * 70)

    risk_summary, importance_df = run_risk_shap()

    print("\n" + "=" * 70)
    print("RISK RESULT")
    print("=" * 70)
    print(f"  Shortfall probability: {risk_summary['overall_shortfall_probability']:.1%}")
    print(f"  Risk level:            {risk_summary['risk_level']}")
    print(f"  Planned production:    {risk_summary['planned_production_t']:>12,.1f} t")
    print(f"  Expected production:   {risk_summary['expected_production_t']:>12,.1f} t")
    print(f"  Expected shortfall:    {risk_summary['expected_shortfall_t']:>12,.1f} t")
    print(f"  Forecast horizon:      {risk_summary['forecast_horizon_days']} days")

    print("\n" + "=" * 70)
    print("TOP ROOT CAUSES (SHAP — model attribution, not causation)")
    print("=" * 70)
    for _, row in importance_df.head(10).iterrows():
        print(
            f"  {int(row['importance_rank']):2}. {row['feature']:<40} "
            f"shap={row['mean_absolute_shap']:.4f}  "
            f"{row['impact_direction']:<4}  {row['driver_type']}"
        )

    print(f"\n{'='*70}")
    print("ACTIONABLE DRIVERS (top 5)")
    print("=" * 70)
    actionable = importance_df[importance_df["driver_type"] == "ACTIONABLE"].head(5)
    for _, row in actionable.iterrows():
        print(
            f"  {int(row['importance_rank']):2}. {row['feature']:<40} "
            f"shap={row['mean_absolute_shap']:.4f}  {row['impact_direction']}"
        )

    print(f"\n{'='*70}")
    print("CONTEXTUAL DRIVERS (top 5)")
    print("=" * 70)
    contextual = importance_df[importance_df["driver_type"] == "CONTEXTUAL"].head(5)
    for _, row in contextual.iterrows():
        print(
            f"  {int(row['importance_rank']):2}. {row['feature']:<40} "
            f"shap={row['mean_absolute_shap']:.4f}  {row['impact_direction']}"
        )

    print(f"\nOutputs written to: {OUTPUT_DIR}")
    print("  - risk_summary.json")
    print("  - shap_importance.csv")
    print("  - pulse_forecast.csv  (refreshed by PULSE rerun)")
    print("  - pulse_summary.json  (refreshed by PULSE rerun)")
    print("=" * 70)


if __name__ == "__main__":
    main()
