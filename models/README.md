# OreSight Models

This directory contains all reserve estimation, accessibility, forecasting, risk, and explanation modules for the OreSight hackathon MVP.

## PRISM — Probabilistic Reserve Intelligence and Spatial Modeling

**Purpose:** Estimate manganese grades across the 3D block model using Ordinary Kriging.

**Input:**
- `data/raw/boreholes.csv` — Drillhole composites with Mn grades and coordinates
- `data/raw/blocks.csv` — 3D block model centroids, volumes, and densities

**Output:**
- `output/reserve_blocks.csv` — All blocks with estimated Mn grades, kriging variance, tonnage, and ore classification
- `output/reserve_summary.json` — Summary statistics: declared reserve, average grade, variogram parameters

**Method:**
- Spherical variogram fitted via grid search on experimental variogram
- Local Ordinary Kriging with 20 nearest neighbors
- Z-anisotropy factor 5.0 (vertical correlation shorter than horizontal)
- 20% Mn cutoff for ore/waste classification
- Estimates clipped to 0-55% Mn demonstration range

**Run:**
```powershell
python models/prism.py
```

**Tests:**
```powershell
python -m pytest tests/test_prism.py -v
```

---

## EAR — Effective Accessible Reserve

**Purpose:** Determine which PRISM ore blocks are realistically accessible/mineable under current operational constraints.

**Input:**
- `output/reserve_blocks.csv` — PRISM declared reserves
- `data/raw/development.csv` — Daily development metres
- `data/raw/equipment.csv` — Daily equipment availability and downtime
- `data/raw/weather.csv` — Daily rainfall and weather conditions

**Output:**
- `output/ear_blocks.csv` — All blocks with accessibility flags and accessible tonnage
- `output/ear_summary.json` — Accessibility statistics and constraint thresholds

**Method:**
EAR applies three operational constraints to each ore block:

1. **Development Readiness** (block-level, spatial)
   - Blocks with elevation ≤ 192m are development-ready
   - Assumption: Shallower blocks are more accessible in this synthetic dataset
   - In reality, would use actual tunnel/drift access network

2. **Equipment Availability** (mine-wide, temporal aggregate)
   - Mean daily fleet availability must be ≥ 85%
   - Calculated across all equipment types over entire operational period
   - In reality, would be block-specific and time-varying based on scheduling

3. **Weather Feasibility** (mine-wide with spatial variation, probabilistic)
   - Blocks accessible on days with rainfall ≤ 30mm
   - Weather feasibility score: 94.3% of days meet this threshold
   - Applied probabilistically to blocks (deterministic seed for reproducibility)
   - In reality, would use real-time weather forecasts and site-specific limits

**Decision Rule:**
```
accessible_tonnage_t = declared_tonnage_t  IF (development_ready AND equipment_available AND weather_feasible)
                     = 0                   OTHERWISE
```

**Waste blocks:** Always have `accessible_tonnage_t = 0` (only ore can contribute to EAR)

**Thresholds (derived from synthetic data distributions):**
- Development: z ≤ 192m (75th percentile of ore block elevations)
- Equipment: availability ≥ 0.85 (mean - 0.5×std of daily fleet availability)
- Weather: rainfall ≤ 30mm/day (~5.7% exceedance, monsoon peak threshold)

**Run:**
```powershell
python models/ear.py
```

**Tests:**
```powershell
python -m pytest tests/test_ear.py -v
```

**Key Results (DEMO-01):**
- Declared Reserve: 48,271,696.4 tonnes (PRISM)
- Effective Accessible Reserve: 32,736,929.4 tonnes (EAR)
- **Accessibility Ratio: 67.8%**
- 339 accessible blocks out of 498 ore blocks
- 159 ore blocks inaccessible due to constraints

**Gap Analysis:**
The 32% gap between declared and accessible reserve highlights operational constraints:
- ~25% of ore blocks too deep (not development-ready)
- Weather reduces accessibility on ~6% of days
- Equipment availability meets threshold (mine-wide mean 90.6%)

**Important:** This is a transparent, rule-based decision system for hackathon MVP purposes. It uses synthetic demonstration data (not real MOIL data) and simplified assumptions. A production system would require:
- Actual development network and tunnel access data
- Block-specific equipment scheduling and availability
- Real-time weather forecasting integrated with mining operations
- Economic cutoffs and mining sequence optimization
- Geotechnical and safety constraints

---

## Pipeline

```
PRISM (Declared Reserve)
        ↓
    EAR (Effective Accessible Reserve)
        ↓
    PULSE (Production Forecast: P10/P50/P90)
        ↓
    RISK + SHAP (Shortfall Risk & Root-Cause Attribution)
        ↓
    NUDGE (Prescriptive Single-Action Recommendation)
        ↓
    FastAPI / React — not yet implemented
```

## Output Files

All model outputs are written to `models/output/`:

```
output/
├── reserve_blocks.csv       # PRISM: Block-level Mn estimates and ore classification
├── reserve_summary.json     # PRISM: Declared reserve statistics
├── ear_blocks.csv           # EAR: Block-level accessibility flags and accessible tonnage
├── ear_summary.json         # EAR: Accessibility statistics and constraints
├── pulse_forecast.csv       # PULSE: Daily P10/P50/P90 forecasts and shortfall analysis
├── pulse_summary.json       # PULSE: Model validation metrics and forecast summary
├── risk_summary.json        # RISK+SHAP: Risk level, shortfall metrics, top drivers
├── shap_importance.csv      # RISK+SHAP: Full ranked feature importance table
├── nudge_recommendation.json # NUDGE: Best action, baseline, constraints, assumptions
└── nudge_candidates.csv     # NUDGE: All evaluated candidates ranked by shortfall reduction
```

## Testing

Run all model tests:

```powershell
python -m pytest tests/test_prism.py tests/test_ear.py tests/test_pulse.py tests/test_risk_shap.py -v
```

Run complete test suite (data quality + all models):

```powershell
python -m pytest tests/ -v
```

Expected: **112 tests passed** (22 data quality + 7 PRISM + 15 EAR + 23 PULSE + 21 RISK+SHAP + 24 NUDGE)


---

## PULSE — Production Understanding, Learning & Shortfall Estimation

**Purpose:** Forecast future production with uncertainty quantification and assess shortfall risk.

**Input:**
- `output/ear_summary.json` — EAR accessible reserve constraint
- `data/raw/production.csv` — Historical planned vs. actual production
- `data/raw/equipment.csv` — Fleet availability, downtime, failures
- `data/raw/blast.csv` — Blast activity and delays
- `data/raw/development.csv` — Daily development metres
- `data/raw/manpower.csv` — Labor availability and shifts
- `data/raw/weather.csv` — Rainfall and weather conditions

**Output:**
- `output/pulse_forecast.csv` — Daily forecasts with P10/P50/P90 and shortfall analysis
- `output/pulse_summary.json` — Model validation metrics and forecast summary

**Method:**
PULSE uses LightGBM quantile regression to forecast production with uncertainty bands:

1. **Feature Engineering**
   - Lag features (1, 2, 3, 7, 14, 30 days) to capture recent trends
   - Rolling statistics (7, 14, 30-day windows) for patterns
   - Temporal features (day of week, month, quarter, day of year)
   - Operational features (equipment availability, blast delays, weather, etc.)
   - All features use only past data to avoid leakage

2. **Chronological Splitting**
   - Training: 976 days (2023-01-31 to 2025-10-02)
   - Validation: 60 days (2025-10-03 to 2025-12-01)
   - Forecast: 30 days (2025-12-02 to 2025-12-31)
   - No random splitting — maintains temporal order

3. **Quantile Regression**
   - Three separate models for P10, P50, P90
   - P10 = pessimistic/conservative (10th percentile)
   - P50 = expected/median (50th percentile)
   - P90 = optimistic (90th percentile)
   - Monotonicity enforced: P10 ≤ P50 ≤ P90

4. **Shortfall Analysis**
   - Shortfall = max(0, planned - expected)
   - Shortfall probability interpolated from quantile distribution:
     - If P90 < planned → high shortfall risk (~90%)
     - If P10 > planned → low shortfall risk (~10%)
     - Linear interpolation between quantiles

5. **EAR Constraint**
   - Cumulative forecast cannot exceed accessible reserve
   - If violated, forecast scaled proportionally
   - For 30-day horizon: 68,593 t ≪ 32.7M t (no constraint binding)

**Run:**
```powershell
python models/pulse.py
```

**Tests:**
```powershell
python -m pytest tests/test_pulse.py -v
```

**Key Results (30-day forecast, DEMO-01):**
- **Planned production:** 71,988.9 tonnes
- **P10 (pessimistic):** 66,322.2 tonnes
- **P50 (expected):** 68,593.4 tonnes
- **P90 (optimistic):** 71,073.7 tonnes
- **Expected shortfall:** 3,395.5 tonnes (4.7% below plan)
- **Shortfall probability:** 88.4%

**Validation Metrics (P50):**
- MAE: 61.3 tonnes per day
- RMSE: 77.4 tonnes per day
- MAPE: 2.66%

**Interpretation:**
The mine is expected to fall short of planned production by ~3,400 tonnes over the next 30 days, with 88% probability of missing the target. The forecast ranges from 66,322 t (pessimistic) to 71,074 t (optimistic).

**Important:** Uses synthetic demonstration data with simplified feature engineering for hackathon MVP. A production system would require:
- Real-time operational data integration
- More sophisticated feature engineering (e.g., block-level mining sequence)
- Dynamic EAR updates as ore is extracted
- Incorporation of planned maintenance and shutdowns
- Integration with mine planning systems
- Continuous model retraining and monitoring


---

## RISK + SHAP — Shortfall Risk & Root-Cause Explanation

**Purpose:** Classify production shortfall risk into a severity level and identify the operational drivers most responsible for that risk.

**Module:** `models/risk_shap.py`

**Input:**
- Live PULSE model (via `run_pulse_with_models`) — same LightGBM P50 booster that produced the forecast
- `output/pulse_summary.json` — shortfall probability and forecast metrics

**Output:**
- `output/risk_summary.json` — risk level, shortfall metrics, top/actionable/contextual drivers
- `output/shap_importance.csv` — full ranked feature importance (38 features), sorted DESC by mean |SHAP|

---

### RISK layer

**What it measures:** the probability that actual production falls below the planned target.

**Risk level thresholds (transparent, documented):**

| Level | Shortfall probability |
|---|---|
| LOW | < 25% |
| MEDIUM | 25% – < 50% |
| HIGH | 50% – < 75% |
| CRITICAL | ≥ 75% |

RISK does not build a new model. It reads `overall_shortfall_probability` from PULSE and applies the above mapping.

**Verified result:** 88.4% → **CRITICAL**

**Run:**
```powershell
python models/risk_shap.py
```

---

### SHAP layer

**What SHAP does:** SHAP (SHapley Additive exPlanations) decomposes each model prediction into per-feature contributions. The mean absolute SHAP value across the training set measures how much a feature shifts predictions relative to the average. The sign (UP/DOWN) indicates the direction of that shift.

**Method:** `shap.TreeExplainer` on the PULSE P50 LightGBM booster. TreeExplainer is the correct choice for gradient-boosted trees — it is exact, fast, and consistent. `check_additivity=False` is required because the quantile objective shifts leaf values in a way that breaks SHAP's additivity sum check while leaving relative attributions correct.

**Background:** 200 randomly sampled training rows (seed 42) are used as the explainer background.

**Why SHAP is not proof of causation:** SHAP values reflect learned statistical patterns in the synthetic training data. They indicate which features the model relies on most heavily, not which real-world interventions would improve production. Do not claim SHAP establishes causality.

**Driver classification:**

| Type | Meaning | Examples |
|---|---|---|
| ACTIONABLE | Mine operations can influence this | fleet_availability, delay_h, development_m, shifts |
| CONTEXTUAL | Outside operational control | rainfall_mm, soil_moisture, LST, day_of_year |

This split feeds directly into the NUDGE phase, which should only recommend interventions on ACTIONABLE drivers.

**Verified top 5 drivers (synthetic DEMO-01):**

| Rank | Feature | Mean \|SHAP\| | Direction | Type |
|---|---|---|---|---|
| 1 | planned_t | 97.16 | DOWN | ACTIONABLE |
| 2 | rainfall_mm | 41.93 | DOWN | CONTEXTUAL |
| 3 | fleet_availability | 24.24 | DOWN | ACTIONABLE |
| 4 | development_m | 17.55 | DOWN | ACTIONABLE |
| 5 | delay_h | 16.98 | DOWN | ACTIONABLE |

**Interpretation:** Three of the top five drivers are actionable. Fleet availability, development pace, and blast delays are the primary operational levers. Rainfall is the dominant contextual factor, consistent with the monsoon-like seasonality in the synthetic data.

**Tests:**
```powershell
python -m pytest tests/test_risk_shap.py -v
```

**Important:** Uses synthetic demonstration data (not real MOIL). SHAP attributions reflect the synthetic dataset's statistical patterns only.


---

## NUDGE — Prescriptive Decision & Intervention Optimization

**Module:** `models/nudge.py`

**Purpose:** Translate SHAP's actionable driver attribution into the single best feasible operational recommendation for reducing production shortfall.

**Input:**
- Live PULSE models (via `run_pulse_with_models`) — P10/P50/P90 LightGBM boosters
- `output/pulse_summary.json` — baseline forecast and shortfall metrics
- `output/shap_importance.csv` — actionable driver list
- `output/ear_summary.json` — accessible reserve constraint
- `data/raw/equipment.csv`, `development.csv`, `manpower.csv` — historical distributions for bounds

**Output:**
- `output/nudge_recommendation.json` — status, baseline, best action, constraints, assumptions
- `output/nudge_candidates.csv` — all evaluated candidates ranked by shortfall reduction

---

### Why NUDGE follows SHAP

SHAP tells us which features the model attributes most influence to. NUDGE asks: *among the features we can actually control, which single change produces the greatest measurable improvement?* It uses the PULSE model itself as the response surface — no retraining, no second model.

---

### Intervention catalogue

Only controllable operational levers are included. Each bound is derived from the actual historical data distribution.

| Feature | Action | Bound | Source |
|---|---|---|---|
| `fleet_availability` | Improve preventive maintenance | ≤ 0.957 | p95 of daily mean |
| `fleet_downtime_h` | Reduce unplanned stoppages | ≥ 10.54 h | p10 of daily total |
| `development_m` | Increase development advance | ≤ 19.59 m/day | p90 of daily metres |
| `available_workers` | Mobilise standby workforce | ≤ 92 persons | historical maximum |

**Excluded levers:**

| Feature | Reason excluded |
|---|---|
| `planned_t` | External planning input — not an operational lever |
| `delay_h` | Already 0.0 h in forecast period — no upside |
| `shifts` | Already at maximum (3) in forecast period |
| Lag / rolling features | Derived from historical actual_t — not directly settable |

---

### Counterfactual scoring

For each candidate at each improvement level:
1. Copy the test-period feature matrix.
2. Replace the target feature column with the proposed value (all rows).
3. Run the PULSE P50 LightGBM model — get mean daily prediction.
4. Compute 30-day total production, gain, and shortfall reduction.
5. Repeat with P10/P90 models to estimate new shortfall probability.

No retraining. No second model. The PULSE model is the response surface.

---

### Optimization

PuLP (CBC solver) selects exactly one action from the feasible candidates by maximising `shortfall_reduction_t`. This is a trivial MILP (binary selection) but provides a formal, auditable decision record.

---

### Verified result (DEMO-01, 30-day horizon)

| Rank | Action | Rec. value | Gain (t) | Shortfall Δ (t) | Feasible |
|---|---|---|---|---|---|
| **1** | Increase development progress | 19.24 m/day | **+606.6** | **-606.6** | ✅ |
| 2 | Improve fleet availability | 0.957 | +415.2 | -415.2 | ✅ |
| 3 | Reduce equipment downtime | 10.54 h | +163.5 | -163.5 | ✅ |
| 4 | Increase available workforce | 90.97 persons | +30.1 | -30.1 | ✅ |

**Best action:** *Increase development progress from 18.53 → 19.24 m/day*
- Production gain: **+606.6 t**
- Shortfall reduction: **606.6 t** (17.9% of baseline shortfall)
- New shortfall probability: **88.0%** (from 88.4%)
- New expected shortfall: **2,788.9 t** (from 3,395.5 t)

---

### Safety / operational scope

NUDGE generates decision-support recommendations only. It does **not** produce:
- Blast charge parameters or drilling/blasting recipes
- Unsafe equipment operating instructions
- Detailed hazardous operational procedures

All recommendations are high-level strategic levers (fleet readiness, maintenance scheduling, workforce deployment, development pacing). Final operational decisions remain with the mine manager.

**Run:**
```powershell
python models/nudge.py
```

**Tests:**
```powershell
python -m pytest tests/test_nudge.py -v
```

**Important:** Uses synthetic demonstration data (not real MOIL). Results reflect the synthetic dataset's patterns only.
