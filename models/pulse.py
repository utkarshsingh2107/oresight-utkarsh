"""PULSE — Production Understanding, Learning & Shortfall Estimation.

PULSE forecasts future production using historical operational data and
quantifies shortfall risk relative to planned targets.

Hackathon MVP: lightweight gradient boosting with quantile regression.
Input tables are synthetic demonstration data (not MOIL).

Pipeline: EAR → Historical Operations → PULSE → P10/P50/P90 → Shortfall Risk
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# PULSE configuration
# ---------------------------------------------------------------------------
FORECAST_HORIZON_DAYS = 30
QUANTILES = [0.1, 0.5, 0.9]  # P10, P50, P90
VALIDATION_DAYS = 90  # Use last 90 days for validation
RANDOM_SEED = 42

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
EAR_OUTPUT = ROOT / "models" / "output"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def load_operational_data() -> pd.DataFrame:
    """Load and merge all operational datasets."""
    # Load base production data
    prod = pd.read_csv(RAW / "production.csv", parse_dates=["date"])

    # Load operational drivers
    equipment = pd.read_csv(RAW / "equipment.csv", parse_dates=["date"])
    blast = pd.read_csv(RAW / "blast.csv", parse_dates=["date"])
    development = pd.read_csv(RAW / "development.csv", parse_dates=["date"])
    manpower = pd.read_csv(RAW / "manpower.csv", parse_dates=["date"])
    weather = pd.read_csv(RAW / "weather.csv", parse_dates=["date"])

    # Aggregate equipment to daily mine-wide metrics
    eq_daily = (
        equipment.groupby("date")
        .agg(
            {
                "availability": "mean",
                "downtime_h": "sum",
                "failure": "sum",
                "repair_h": "sum",
            }
        )
        .reset_index()
    )
    eq_daily.columns = ["date", "fleet_availability", "fleet_downtime_h", "fleet_failures", "fleet_repair_h"]

    # Merge all operational data
    data = prod.copy()
    data = data.merge(eq_daily, on="date", how="left")
    data = data.merge(blast, on=["date", "mine_id"], how="left")
    data = data.merge(development, on=["date", "mine_id"], how="left")
    data = data.merge(manpower, on=["date", "mine_id"], how="left")
    data = data.merge(weather, on=["date", "mine_id"], how="left")

    # Verify no missing values after merge
    if data.isna().any().any():
        raise ValueError("Missing values detected after merging operational data")

    return data


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    """Create time-series features for production forecasting."""
    df = data.copy()

    # Temporal features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_year"] = df["date"].dt.dayofyear

    # Lag features for actual production (avoid data leakage)
    for lag in [1, 2, 3, 7, 14, 30]:
        df[f"actual_t_lag_{lag}"] = df["actual_t"].shift(lag)

    # Rolling statistics (using past data only)
    for window in [7, 14, 30]:
        df[f"actual_t_rolling_mean_{window}"] = df["actual_t"].shift(1).rolling(window=window).mean()
        df[f"actual_t_rolling_std_{window}"] = df["actual_t"].shift(1).rolling(window=window).std()
        df[f"fleet_availability_rolling_mean_{window}"] = df["fleet_availability"].shift(1).rolling(window=window).mean()
        df[f"rainfall_rolling_sum_{window}"] = df["rainfall_mm"].shift(1).rolling(window=window).sum()

    # Operational ratios
    df["actual_vs_planned_ratio"] = df["actual_t"] / (df["planned_t"] + 1e-6)

    # Blast efficiency
    df["blast_delay_indicator"] = (df["delay_h"] > 0).astype(int)

    # Drop non-numeric columns that can't be used as features
    df = df.drop(columns=["delay_reason"], errors="ignore")

    return df


def prepare_train_val_test(
    data: pd.DataFrame, validation_days: int = VALIDATION_DAYS, forecast_days: int = FORECAST_HORIZON_DAYS
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Chronological split: train → validation → test (forecast period)."""
    # Remove rows with NaN (from lag/rolling features)
    data_clean = data.dropna().reset_index(drop=True)

    # Split chronologically
    total_days = len(data_clean)
    forecast_start_idx = total_days  # Forecast period is beyond available data
    val_start_idx = total_days - validation_days

    train = data_clean.iloc[:val_start_idx].copy()
    val = data_clean.iloc[val_start_idx:].copy()

    # For forecast period, we need to prepare the last known state
    # In practice, we'll use the validation set's last observations
    # For MVP, create a synthetic test period using the last 30 days of validation
    test_start_idx = len(val) - forecast_days if len(val) >= forecast_days else 0
    test = val.iloc[test_start_idx:].copy()
    val = val.iloc[:test_start_idx].copy() if test_start_idx > 0 else val.copy()

    # Define features (exclude target and metadata)
    exclude_cols = ["date", "mine_id", "actual_t", "avg_mn_pct", "actual_vs_planned_ratio"]
    feature_cols = [c for c in data_clean.columns if c not in exclude_cols]

    features = data_clean[feature_cols]

    return train, val, test, features


def train_quantile_models(
    train: pd.DataFrame, val: pd.DataFrame, feature_cols: list[str]
) -> tuple[dict[float, lgb.Booster], dict]:
    """Train LightGBM quantile regression models for P10, P50, P90."""
    X_train = train[feature_cols]
    y_train = train["actual_t"]
    X_val = val[feature_cols]
    y_val = val["actual_t"]

    models = {}
    val_metrics = {}

    for quantile in QUANTILES:
        # LightGBM quantile regression
        params = {
            "objective": "quantile",
            "alpha": quantile,
            "metric": "quantile",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "random_state": RANDOM_SEED,
            "n_jobs": -1,
        }

        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        model = lgb.train(
            params,
            train_data,
            num_boost_round=200,
            valid_sets=[val_data],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)],
        )

        models[quantile] = model

        # Validation metrics
        val_pred = model.predict(X_val)
        mae = float(np.mean(np.abs(val_pred - y_val)))
        rmse = float(np.sqrt(np.mean((val_pred - y_val) ** 2)))
        mape = float(np.mean(np.abs((val_pred - y_val) / (y_val + 1e-6))) * 100)

        val_metrics[f"P{int(quantile*100)}"] = {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE": round(mape, 2),
        }

    return models, val_metrics


def forecast_production(
    models: dict[float, lgb.Booster], test: pd.DataFrame, feature_cols: list[str], ear_accessible_reserve: float
) -> pd.DataFrame:
    """Generate P10/P50/P90 forecasts with EAR constraint."""
    X_test = test[feature_cols]

    forecast = test[["date", "mine_id", "planned_t"]].copy()
    forecast.rename(columns={"planned_t": "planned_production_t"}, inplace=True)

    # Generate quantile predictions
    forecast["p10_t"] = models[0.1].predict(X_test)
    forecast["p50_t"] = models[0.5].predict(X_test)
    forecast["p90_t"] = models[0.9].predict(X_test)

    # Ensure non-negative and monotonic quantiles
    forecast["p10_t"] = forecast["p10_t"].clip(lower=0)
    forecast["p50_t"] = forecast["p50_t"].clip(lower=forecast["p10_t"])
    forecast["p90_t"] = forecast["p90_t"].clip(lower=forecast["p50_t"])

    # Expected production (use P50 as expected value)
    forecast["expected_production_t"] = forecast["p50_t"]

    # Apply EAR constraint: cumulative production cannot exceed accessible reserve
    # For MVP, show constraint but don't enforce unless it's violated
    cumulative_p50 = forecast["p50_t"].sum()
    if cumulative_p50 > ear_accessible_reserve:
        # Scale down forecast proportionally to respect EAR
        scale_factor = ear_accessible_reserve / cumulative_p50
        forecast["p10_t"] *= scale_factor
        forecast["p50_t"] *= scale_factor
        forecast["p90_t"] *= scale_factor
        forecast["expected_production_t"] = forecast["p50_t"]
        ear_constrained = True
    else:
        ear_constrained = False

    # Calculate shortfall
    forecast["shortfall_t"] = (forecast["planned_production_t"] - forecast["expected_production_t"]).clip(lower=0)

    # Shortfall probability using quantile distribution
    # If P90 < planned: high probability of shortfall
    # If P10 > planned: low probability of shortfall
    # Use linear interpolation between quantiles
    def calculate_shortfall_prob(row):
        planned = row["planned_production_t"]
        p10, p50, p90 = row["p10_t"], row["p50_t"], row["p90_t"]

        if planned <= p10:
            return 0.1  # Very low shortfall risk
        elif planned >= p90:
            return 0.9  # Very high shortfall risk
        elif planned <= p50:
            # Interpolate between P10 and P50
            return 0.1 + (planned - p10) / (p50 - p10 + 1e-6) * 0.4
        else:
            # Interpolate between P50 and P90
            return 0.5 + (planned - p50) / (p90 - p50 + 1e-6) * 0.4

    forecast["shortfall_probability"] = forecast.apply(calculate_shortfall_prob, axis=1)
    forecast["shortfall_probability"] = forecast["shortfall_probability"].clip(0, 1)

    return forecast, ear_constrained


def build_summary(
    train: pd.DataFrame,
    val: pd.DataFrame,
    forecast: pd.DataFrame,
    val_metrics: dict,
    ear_accessible_reserve: float,
    ear_constrained: bool,
) -> dict:
    """Build PULSE summary statistics."""
    summary = {
        "model": "LightGBM Quantile Regression",
        "forecast_horizon_days": len(forecast),
        "training_period": {
            "start": train["date"].min().strftime("%Y-%m-%d"),
            "end": train["date"].max().strftime("%Y-%m-%d"),
            "days": len(train),
        },
        "validation_period": {
            "start": val["date"].min().strftime("%Y-%m-%d"),
            "end": val["date"].max().strftime("%Y-%m-%d"),
            "days": len(val),
        },
        "forecast_period": {
            "start": forecast["date"].min().strftime("%Y-%m-%d"),
            "end": forecast["date"].max().strftime("%Y-%m-%d"),
            "days": len(forecast),
        },
        "validation_metrics": val_metrics,
        "forecast_summary": {
            "total_planned_production_t": round(float(forecast["planned_production_t"].sum()), 1),
            "total_p10_production_t": round(float(forecast["p10_t"].sum()), 1),
            "total_p50_production_t": round(float(forecast["p50_t"].sum()), 1),
            "total_p90_production_t": round(float(forecast["p90_t"].sum()), 1),
            "total_expected_production_t": round(float(forecast["expected_production_t"].sum()), 1),
            "total_expected_shortfall_t": round(float(forecast["shortfall_t"].sum()), 1),
            "overall_shortfall_probability": round(float(forecast["shortfall_probability"].mean()), 4),
        },
        "ear_integration": {
            "accessible_reserve_t": ear_accessible_reserve,
            "ear_constraint_applied": ear_constrained,
            "forecast_respects_ear": float(forecast["p50_t"].sum()) <= ear_accessible_reserve,
        },
        "assumptions": [
            "Production forecast uses historical operational patterns (equipment, weather, development, etc.)",
            "Quantile regression provides P10/P50/P90 uncertainty bands",
            "Chronological train/validation split prevents data leakage",
            "Shortfall probability interpolated from quantile distribution",
            "EAR accessible reserve acts as operational capacity constraint",
            "Forecast period uses last 30 days of validation set for MVP demonstration",
        ],
        "provenance": "Derived from SYNTHETIC DEMO-01 operational data — not real MOIL data",
    }

    return summary


def _run_pulse_core(
    production_path: Path,
    ear_summary_path: Path,
    output_dir: Path,
) -> tuple[pd.DataFrame, dict, dict[float, lgb.Booster], pd.DataFrame, list[str]]:
    """Internal: run the full PULSE pipeline and return models + training data.

    Returns:
        (forecast, summary, models, train_df, feature_cols)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with ear_summary_path.open("r") as f:
        ear_summary = json.load(f)
    ear_accessible_reserve = ear_summary["effective_accessible_reserve_t"]

    print("Loading operational data...")
    data = load_operational_data()

    print("Engineering features...")
    data = engineer_features(data)

    print("Preparing train/validation/test splits...")
    train, val, test, features = prepare_train_val_test(data)

    feature_cols = [c for c in train.columns if c not in ["date", "mine_id", "actual_t", "avg_mn_pct", "actual_vs_planned_ratio"]]

    print(f"Training set: {len(train)} days")
    print(f"Validation set: {len(val)} days")
    print(f"Forecast horizon: {len(test)} days")

    print("\nTraining quantile models (P10, P50, P90)...")
    models, val_metrics = train_quantile_models(train, val, feature_cols)

    print("Generating production forecast...")
    forecast, ear_constrained = forecast_production(models, test, feature_cols, ear_accessible_reserve)

    print("Building summary...")
    summary = build_summary(train, val, forecast, val_metrics, ear_accessible_reserve, ear_constrained)

    forecast.to_csv(output_dir / "pulse_forecast.csv", index=False)
    with (output_dir / "pulse_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return forecast, summary, models, train, feature_cols


def run_pulse(
    production_path: Path | None = None,
    ear_summary_path: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Run PULSE production forecasting and shortfall estimation.

    Returns:
        (forecast_df, summary_dict) — forecast with P10/P50/P90 and summary statistics
    """
    production_path = production_path or (RAW / "production.csv")
    ear_summary_path = ear_summary_path or (EAR_OUTPUT / "ear_summary.json")
    output_dir = output_dir or OUTPUT_DIR

    forecast, summary, _models, _train, _feature_cols = _run_pulse_core(
        production_path, ear_summary_path, output_dir
    )
    return forecast, summary


def run_pulse_with_models(
    production_path: Path | None = None,
    ear_summary_path: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict, dict[float, lgb.Booster], pd.DataFrame, list[str]]:
    """Run PULSE and additionally return trained models, training data, and feature names.

    Used by RISK+SHAP (Phase 5) to compute SHAP values on the same model.

    Returns:
        (forecast, summary, models, train_df, feature_cols)
        models  — {0.1: lgb.Booster, 0.5: lgb.Booster, 0.9: lgb.Booster}
        train_df — training DataFrame with feature_cols + actual_t
        feature_cols — ordered list of feature column names
    """
    production_path = production_path or (RAW / "production.csv")
    ear_summary_path = ear_summary_path or (EAR_OUTPUT / "ear_summary.json")
    output_dir = output_dir or OUTPUT_DIR

    return _run_pulse_core(production_path, ear_summary_path, output_dir)


def main() -> None:
    """Run PULSE and display results."""
    print("=" * 70)
    print("PULSE — Production Understanding, Learning & Shortfall Estimation")
    print("=" * 70)

    forecast, summary = run_pulse()

    print("\n" + "=" * 70)
    print("PULSE RESULTS")
    print("=" * 70)

    print(f"\nModel: {summary['model']}")
    print(f"Training: {summary['training_period']['start']} to {summary['training_period']['end']} ({summary['training_period']['days']} days)")
    print(f"Validation: {summary['validation_period']['start']} to {summary['validation_period']['end']} ({summary['validation_period']['days']} days)")
    print(f"Forecast: {summary['forecast_period']['start']} to {summary['forecast_period']['end']} ({summary['forecast_period']['days']} days)")

    print("\nValidation Metrics:")
    for quantile, metrics in summary["validation_metrics"].items():
        print(f"  {quantile}: MAE={metrics['MAE']:.1f}t, RMSE={metrics['RMSE']:.1f}t, MAPE={metrics['MAPE']:.1f}%")

    fs = summary["forecast_summary"]
    print(f"\nForecast Summary ({summary['forecast_horizon_days']}-day horizon):")
    print(f"  Planned production:      {fs['total_planned_production_t']:>10,.1f} t")
    print(f"  P10 (pessimistic):       {fs['total_p10_production_t']:>10,.1f} t")
    print(f"  P50 (expected):          {fs['total_p50_production_t']:>10,.1f} t")
    print(f"  P90 (optimistic):        {fs['total_p90_production_t']:>10,.1f} t")
    print(f"  Expected shortfall:      {fs['total_expected_shortfall_t']:>10,.1f} t")
    print(f"  Shortfall probability:   {fs['overall_shortfall_probability']:>10.1%}")

    ear = summary["ear_integration"]
    print(f"\nEAR Integration:")
    print(f"  Accessible reserve:      {ear['accessible_reserve_t']:>10,.1f} t")
    print(f"  EAR constraint applied:  {ear['ear_constraint_applied']}")
    print(f"  Forecast respects EAR:   {ear['forecast_respects_ear']}")

    print(f"\nOutputs written to: {OUTPUT_DIR}")
    print(f"  - pulse_forecast.csv")
    print(f"  - pulse_summary.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
