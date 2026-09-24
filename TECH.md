# OreSight — Tech Stack

A complete reserve-to-production decision intelligence dashboard for manganese mining operations.
The system runs a five-stage ML pipeline offline and serves the results through a REST API to a React frontend.

---

## Architecture Overview

```
data/raw/ (synthetic CSVs)
       ↓
models/ (offline Python pipeline)
  PRISM → EAR → PULSE → RISK+SHAP → NUDGE
       ↓
models/output/ (pre-computed JSON + CSV)
       ↓
backend/ (FastAPI — read-only presentation layer)
       ↓
frontend/ (React + Vite — dashboard UI)
```

---

## Backend

| Component | Library / Version | Purpose |
|---|---|---|
| API framework | FastAPI `>=0.100,<1` | REST API, request validation, OpenAPI docs |
| ASGI server | Uvicorn `>=0.20,<1` | Serves the FastAPI app (`uvicorn backend.main:app`) |
| Data validation | Pydantic `>=2.0,<3` | Response models and schema enforcement |
| HTTP test client | HTTPX `>=0.24,<1` | Used for integration testing of API routes |
| Data I/O | Pandas `>=2.1,<3` | Reads CSV output files for API responses |
| CORS | FastAPI `CORSMiddleware` | Allows requests from `localhost:3000` and `localhost:5173` |
| Language | Python `3.11+` | Required for prebuilt wheels (LightGBM, NumPy) |

**Key design decision:** The backend is purely a presentation layer — it reads pre-computed files from `models/output/` and serves them as typed JSON. No model logic, retraining, or recalculation happens at request time.

---

## ML Pipeline (models/)

### Phase 1 — Data Foundation

| Library | Version | Purpose |
|---|---|---|
| NumPy | `>=1.26,<3` | Numerical arrays, kriging matrix operations |
| Pandas | `>=2.1,<3` | Tabular data loading and feature engineering |
| PyYAML | `>=6.0,<7` | Configuration files |

### Phase 2 — PRISM (Reserve Estimation)

Custom Ordinary Kriging implementation (no third-party geostatistics library).

- Spherical variogram fitting over lag bins
- Z-anisotropy factor (×5) — vertical correlation is shorter than horizontal
- 20 nearest-neighbour search per block
- Solves Kriging system (γ matrix + Lagrange multiplier) via `numpy.linalg.solve`
- Mn cutoff: 20% — classifies each block as ore or waste

### Phase 3 — EAR (Effective Accessible Reserve)

Pure NumPy/Pandas logic. Applies three operational constraints to PRISM's ore blocks:

1. **Development depth** — z ≤ 192 m
2. **Equipment availability** — fleet mean ≥ 85%
3. **Weather feasibility** — rainfall ≤ 30 mm/day, applied probabilistically per block

### Phase 4 — PULSE (Production Forecasting)

| Library | Version | Purpose |
|---|---|---|
| LightGBM | `>=4.0,<5` | Quantile regression models (P10 / P50 / P90) |
| Pandas | `>=2.1,<3` | Feature engineering (~38 features), lag/rolling stats |

- Chronological train/validation/test split
- Early stopping on validation set
- EAR constraint applied post-forecast — caps cumulative P50 at accessible reserve

### Phase 5 — RISK + SHAP (Root-Cause Attribution)

| Library | Version | Purpose |
|---|---|---|
| SHAP | `>=0.46,<1` | `TreeExplainer` on the P50 LightGBM model |

- Risk levels: LOW (<25%), MEDIUM (25–50%), HIGH (50–75%), CRITICAL (≥75%) shortfall probability
- Features labelled ACTIONABLE (operationally controllable) vs CONTEXTUAL (weather, calendar)
- Uses `feature_perturbation="tree_path_dependent"` and `check_additivity=False` for quantile models

### Phase 6 — NUDGE (Prescriptive Optimization)

| Library | Version | Purpose |
|---|---|---|
| PuLP | `>=2.9,<3` | Binary integer program — selects the single best feasible action |
| CBC solver | (bundled with PuLP) | Solves the integer program |

- Four intervention levers: fleet availability, fleet downtime, development advance, available workers
- Counterfactual scoring: perturbs one feature across all forecast rows, re-predicts with P50 model
- EAR constraint: 30-day counterfactual total must not exceed accessible reserve

---

## Frontend

| Component | Library / Version | Purpose |
|---|---|---|
| UI framework | React `18.2.0` | Component-based dashboard UI |
| Build tool | Vite `5.2.13` | Dev server, hot reload, production bundling |
| React plugin | `@vitejs/plugin-react` `4.2.1` | JSX transform and Fast Refresh |
| Charts (2D) | Recharts `2.12.7` | 30-day forecast line/area chart, SHAP bar chart, NUDGE candidates |
| Charts (3D) | Plotly.js Basic `4.0.0` | Interactive 3D scatter plots for PRISM block model and EAR view |
| HTTP client | Native `fetch` | API calls to the FastAPI backend (abstracted in `src/services/api.js`) |
| Language | JavaScript (JSX) | No TypeScript — plain `.jsx` files |
| Styling | Custom CSS | Global stylesheet at `src/styles/global.css` |
| Port | `5173` (Vite default) | Backend proxied via CORS (no Vite proxy configured) |

**Plotly loading strategy:** Loaded lazily via dynamic `import('plotly.js-basic-dist-min')` to keep the initial bundle size small. The 3D views render in two phases — component mounts first, then Plotly initialises into the DOM ref.

---

## Testing

| Layer | Tool | Version | Coverage |
|---|---|---|---|
| Frontend | Vitest | `1.6.0` | `Dashboard.test.jsx` — component render tests |
| Frontend DOM | `@testing-library/react` | `14.3.1` | Component interaction assertions |
| Frontend matchers | `@testing-library/jest-dom` | `6.4.6` | DOM assertion helpers |
| Frontend env | jsdom | `24.1.1` | Browser environment simulation in Node |
| Backend | Pytest | `>=8.0,<9` | `tests/` directory (placeholder, thin coverage) |
| Test runner config | `vite.config.js` | — | `globals: true`, setup via `src/test/setup.js` |

---

## Data Layer

All source data lives in `data/raw/` as CSV files. All data is **synthetic**, generated by `scripts/generate_data.py` with a fixed seed (42) for reproducibility.

| File | Contents |
|---|---|
| `boreholes.csv` | Per-hole composites: x/y/z, depth, Mn%, Fe%, SiO₂%, density |
| `blocks.csv` | 3D block model: block_id, x/y/z, volume_m³, density |
| `production.csv` | Daily planned_t / actual_t / avg_mn_pct (2023–2025) |
| `equipment.csv` | Per-machine per-day: downtime_h, availability, failure flag |
| `blast.csv` | Daily blast_count, delay_h, delay_reason |
| `development.csv` | Daily development advance (metres) |
| `manpower.csv` | Daily available_workers, shifts |
| `weather.csv` | Daily rainfall_mm, soil_moisture, NDVI, LST — monsoon seasonal pattern |

Pre-computed model outputs are written to `models/output/` (10 files: 5 JSON summaries + 5 CSVs).

---

## Dev Environment

| Tool | Version |
|---|---|
| Python | `3.11+` |
| Node.js | `18+` (tested on Node 24 in friend's fork) |
| npm | bundled with Node |
| OS | Windows / macOS / Linux |
| Database | None — flat files only (JSON + CSV) |
| Docker | Not required |

---

## API Surface (FastAPI)

| Method | Route | Returns |
|---|---|---|
| GET | `/` | API identity |
| GET | `/api/health` | Per-phase file availability |
| GET | `/api/overview` | Combined cross-phase summary (main dashboard payload) |
| GET | `/api/prism` | Reserve summary JSON |
| GET | `/api/prism/blocks` | Full 2,240-block model |
| GET | `/api/ear` | EAR accessible reserve summary |
| GET | `/api/ear/blocks` | Ore blocks with per-block accessibility flags |
| GET | `/api/pulse` | PULSE summary + 30-day daily forecast |
| GET | `/api/risk` | Risk level + top SHAP drivers |
| GET | `/api/shap` | All 38 features sorted by SHAP importance |
| GET | `/api/nudge` | Best recommended action |
| GET | `/api/nudge/candidates` | All ranked intervention candidates |
