# OreSight — Architecture Diagrams

> These diagrams render in VS Code (with Mermaid Preview), GitHub, and Notion.
> In VS Code: install **"Markdown Preview Mermaid Support"** extension, then open preview with `Ctrl+Shift+V`.

---

## 1. Full System Architecture

```mermaid
flowchart TD
    subgraph DATA["📁 DATA LAYER — data/raw/"]
        D1[boreholes.csv\ndrillhole Mn grades]
        D2[blocks.csv\n3D block centroids]
        D3[production.csv\ndaily planned vs actual]
        D4[equipment.csv\nfleet availability]
        D5[blast.csv\nblast delays]
        D6[development.csv\ndaily metres]
        D7[manpower.csv\nworkers & shifts]
        D8[weather.csv\nrainfall & NDVI]
    end

    subgraph PIPELINE["⚙️ ML PIPELINE — models/"]
        P1["🔷 PRISM\nOrdinary Kriging\nGeological Reserve"]
        P2["🔶 EAR\nConstraint Filter\nAccessible Reserve"]
        P3["🟢 PULSE\nLightGBM Quantile\nP10 / P50 / P90"]
        P4["🔴 RISK + SHAP\nRisk Classification\n+ Root-Cause Attribution"]
        P5["⭐ NUDGE\nPuLP Counterfactual\nBest Action"]
    end

    subgraph OUTPUTS["💾 PRECOMPUTED OUTPUTS — models/output/"]
        O1[reserve_blocks.csv\nreserve_summary.json]
        O2[ear_blocks.csv\near_summary.json]
        O3[pulse_forecast.csv\npulse_summary.json]
        O4[risk_summary.json\nshap_importance.csv]
        O5[nudge_recommendation.json\nnudge_candidates.csv]
    end

    subgraph BACKEND["🚀 BACKEND — FastAPI / Uvicorn\nhttp://127.0.0.1:8000"]
        B1["/api/overview\n/api/prism\n/api/prism/blocks"]
        B2["/api/ear\n/api/ear/blocks"]
        B3["/api/pulse\n/api/risk\n/api/shap"]
        B4["/api/nudge\n/api/nudge/candidates"]
    end

    subgraph FRONTEND["🖥️ FRONTEND — React + Vite\nhttp://localhost:5173"]
        F1["Overview Panel\nPipeline flow + KPI cards"]
        F2["PRISM View\n3D block scatter — Plotly"]
        F3["EAR View\n3D accessibility scatter — Plotly"]
        F4["PULSE View\nForecast chart — Recharts\nSHAP bar chart"]
        F5["NUDGE View\nBefore/after + candidates table"]
    end

    %% Data → Pipeline
    D1 & D2 --> P1
    D4 & D6 & D8 --> P2
    D3 & D4 & D5 & D6 & D7 & D8 --> P3

    %% Pipeline chain
    P1 -->|"48.27 Mt declared"| P2
    P2 -->|"32.74 Mt accessible\near_summary.json"| P3
    P3 -->|"models in-memory\npulse_summary.json"| P4
    P4 -->|"models in-memory\nshap_importance.csv"| P5

    %% Pipeline → Outputs
    P1 --> O1
    P2 --> O2
    P3 --> O3
    P4 --> O4
    P5 --> O5

    %% Outputs → Backend
    O1 --> B1
    O2 --> B2
    O3 & O4 --> B3
    O5 --> B4

    %% Backend → Frontend
    B1 --> F1 & F2
    B2 --> F3
    B3 --> F4
    B4 --> F5
```

---

## 2. ML Pipeline — Stage by Stage

```mermaid
flowchart LR
    subgraph PRISM["PRISM — Geological Reserve"]
        PR1[Borehole composites\nsparse Mn grades]
        PR2[Spherical variogram\nfitted by grid search]
        PR3[Ordinary Kriging\n20 nearest neighbours\nZ-anisotropy ×5]
        PR4[Ore classification\nMn ≥ 20% cutoff]
        PR5["48.27 Mt declared\n498 ore blocks"]
        PR1 --> PR2 --> PR3 --> PR4 --> PR5
    end

    subgraph EAR["EAR — Effective Accessible Reserve"]
        E1[PRISM ore blocks\n498 blocks]
        E2{Depth ≤ 192m?\nDev. readiness}
        E3{Fleet avail.\n≥ 85%?}
        E4{Rainfall\n≤ 30mm/day?}
        E5["32.74 Mt accessible\n339/498 blocks\n67.8% ratio"]
        E1 --> E2
        E2 -->|pass| E3
        E3 -->|pass| E4
        E4 -->|pass| E5
        E2 -->|fail ❌| BLOCKED1[inaccessible]
        E3 -->|fail ❌| BLOCKED2[inaccessible]
        E4 -->|fail ❌| BLOCKED3[inaccessible]
    end

    subgraph PULSE["PULSE — Production Forecast"]
        PU1[38-feature matrix\nlags + rolling + ops + weather]
        PU2[LightGBM α=0.10\nP10 pessimistic]
        PU3[LightGBM α=0.50\nP50 expected]
        PU4[LightGBM α=0.90\nP90 optimistic]
        PU5["30-day forecast\nShortfall prob: 88.4%\nExpected gap: 3,396 t"]
        PU1 --> PU2 & PU3 & PU4 --> PU5
    end

    subgraph RISK_SHAP["RISK + SHAP"]
        RS1[Shortfall probability\n88.4%]
        RS2["Risk level\nCRITICAL ≥75%"]
        RS3[TreeExplainer\non P50 LightGBM]
        RS4["Top driver:\nfleet_availability\ndevelopment_m\ndelay_h"]
        RS1 --> RS2
        RS3 --> RS4
    end

    subgraph NUDGE["NUDGE — Best Action"]
        N1[Counterfactual scoring\n4 levers × 5 levels]
        N2[PuLP CBC\nbinary selection]
        N3["Best: development_m\n18.53 → 19.24 m/day\n+606.6 t gain"]
        N1 --> N2 --> N3
    end

    PRISM --> EAR --> PULSE --> RISK_SHAP --> NUDGE
```

---

## 3. Data Flow Through the API

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant FE as React Frontend<br/>localhost:5173
    participant BE as FastAPI Backend<br/>:8000
    participant FS as models/output/<br/>(flat files)

    User->>FE: Opens dashboard

    par Parallel API calls on mount
        FE->>BE: GET /api/overview
        FE->>BE: GET /api/pulse
        FE->>BE: GET /api/risk
        FE->>BE: GET /api/shap
        FE->>BE: GET /api/nudge
        FE->>BE: GET /api/nudge/candidates
    end

    BE->>FS: Read reserve_summary.json
    BE->>FS: Read ear_summary.json
    BE->>FS: Read pulse_summary.json + pulse_forecast.csv
    BE->>FS: Read risk_summary.json + shap_importance.csv
    BE->>FS: Read nudge_recommendation.json + nudge_candidates.csv

    FS-->>BE: File contents
    BE-->>FE: JSON responses (all 6 calls)

    FE->>User: Renders Overview Panel\n(KPI cards + pipeline diagram)

    User->>FE: Clicks PRISM tab
    FE->>BE: GET /api/prism/blocks (lazy)
    BE->>FS: Read reserve_blocks.csv (2,240 rows)
    FS-->>BE: CSV data
    BE-->>FE: JSON block array
    FE->>User: Renders 3D Plotly scatter\n(coloured by Mn grade)

    User->>FE: Clicks EAR tab
    FE->>BE: GET /api/ear/blocks (lazy)
    BE->>FS: Read ear_blocks.csv (498 rows)
    FS-->>BE: CSV data
    BE-->>FE: JSON block array
    FE->>User: Renders 3D Plotly scatter\n(coloured by accessibility)
```

---

## 4. Frontend Component Tree

```mermaid
flowchart TD
    MAIN[main.jsx] --> APP[App.jsx]
    APP --> DASH[Dashboard.jsx\nState: loading / error / data / stage]

    DASH --> HDR[Header.jsx\nRefresh button]
    DASH --> STRIP[PipelineStrip.jsx\nTab navigation]
    DASH --> LOADING[LoadingSpinner.jsx]
    DASH --> ERROR[ErrorBanner.jsx]

    DASH --> OV[OverviewPanel.jsx]
    DASH --> PR[PrismView.jsx]
    DASH --> EA[EarView.jsx]
    DASH --> PU[PulseView.jsx]
    DASH --> NU[NudgeView.jsx]

    OV --> MC[MetricCard.jsx\n× 3 KPI cards]
    OV --> RC[RiskCard.jsx]
    OV --> NC[NudgeCard.jsx]
    OV --> RESC[ReserveComparison.jsx]

    PU --> FC[ForecastChart.jsx\nRecharts area]
    PU --> SC[ShapChart.jsx\nRecharts bar]
    PU --> RC2[RiskCard.jsx]

    NU --> CT[CandidateTable.jsx]

    PR --> PLOTLY1[Plotly 3D Scatter\nlazy import]
    EA --> PLOTLY2[Plotly 3D Scatter\nlazy import]

    API[services/api.js\n6 fetch functions] -.->|feeds data| DASH
```

---

## 5. Key Numbers Flow

```mermaid
flowchart LR
    A["🔷 PRISM\n2,240 blocks\n498 ore blocks\n48.27 Mt declared\nAvg Mn: 25.2%"]
    B["🔶 EAR\n339 accessible blocks\n32.74 Mt accessible\n67.8% ratio\n159 blocks blocked"]
    C["🟢 PULSE\nP10: 66,322 t\nP50: 68,593 t\nP90: 71,074 t\nPlanned: 71,989 t"]
    D["🔴 RISK\nShortfall: 3,396 t\nProb: 88.4%\nLevel: CRITICAL"]
    E["⭐ NUDGE\ndev_m: 18.53→19.24\nGain: +606.6 t\nNew prob: 88.0%\nNew gap: 2,789 t"]

    A -->|"caps forecast\nat 32.74 Mt"| B
    B -->|"EAR constraint\npassed to"| C
    C -->|"shortfall prob\nfeeds"| D
    D -->|"actionable drivers\nfeed"| E

    style A fill:#1e3a5f,color:#fff
    style B fill:#7c4e00,color:#fff
    style C fill:#1a5c1a,color:#fff
    style D fill:#7c0000,color:#fff
    style E fill:#4a0072,color:#fff
```

---

## How to View These Diagrams

| Tool | How |
|---|---|
| **VS Code / Kiro** | Install [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid), open this file, press `Ctrl+Shift+V` |
| **GitHub** | Push to any repo — GitHub renders Mermaid in `.md` files natively |
| **Mermaid Live Editor** | Paste any diagram block at [mermaid.live](https://mermaid.live) to edit and export as PNG/SVG |
| **Notion** | Paste the code block inside a `/code` block and set language to `mermaid` |
| **draw.io / Lucidchart** | Use [mermaid.live](https://mermaid.live) → export as SVG → import into draw.io |
