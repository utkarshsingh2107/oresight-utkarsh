# OreSight — Research Foundation & References

**Hackathon:** Smart India Hackathon 2026
**Project:** OreSight — Mine Reserve Intelligence & Production Decision Support
**Domain:** Manganese Mining, MOIL (Govt. of India Enterprise)

> **SIH Note:** Government data sources are listed first and marked with 🏛️ to highlight their use in this project.

---

## Government Data Used in This Project

OreSight's design, parameter calibration, and domain context are grounded in publicly available data published by Government of India ministries and PSUs. The following government sources directly informed the project.

---

### 🏛️ G1 — MOIL Limited (Govt. of India Enterprise) — Annual Reports & Production Data

**Source:** MOIL Limited — A Government of India Enterprise under the Ministry of Steel
**URLs:**
- Annual Report 2024–25: [https://www.moil.nic.in/userfiles/Annual_Report_2024_25.pdf](https://www.moil.nic.in/userfiles/Annual_Report_2024_25.pdf)
- Annual Report 2023–24: [https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2023-24.pdf](https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2023-24.pdf)
- Annual Report 2022–23: [https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2022-23.pdf](https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2022-23.pdf)
- Production milestone press release (FY 2023): [https://moil.nic.in/upload_files/upload_news/49gh9el.pdf](https://moil.nic.in/upload_files/upload_news/49gh9el.pdf)

**How used in OreSight:**
MOIL is India's dominant manganese ore producer and operates the Balaghat mine (Bharweli, Madhya Pradesh) — the real-world mine that OreSight models. MOIL's publicly disclosed company-level annual production figures (e.g., 12.73 lakh MT in H1 FY23, 41% YoY growth) were used to:
- Calibrate the synthetic `production.csv` dataset to realistic production scales for a single large underground mine
- Set the order-of-magnitude for planned daily tonnage (`planned_t`) in the dataset
- Contextualise the production target ranges used in PULSE forecasting and NUDGE shortfall analysis
- Establish that Balaghat is an underground, mechanised Category-A mine operating three shifts — the shift structure reflected in `manpower.csv`

MOIL holds a Government of India equity of 53.35% and operates 10 mines across Maharashtra and Madhya Pradesh. OreSight's DEMO-01 mine is modelled as a single Balaghat-type operation.

---

### 🏛️ G2 — Indian Bureau of Mines (IBM) — Indian Minerals Yearbook (IMYB) & National Mineral Inventory

**Source:** Indian Bureau of Mines, Ministry of Mines, Government of India
**URLs:**
- IMYB 2022 — Manganese Ore chapter: [https://ibm.gov.in/writereaddata/files/17125770456613da1576db0Manganese_Ore_2022.pdf](https://ibm.gov.in/writereaddata/files/17125770456613da1576db0Manganese_Ore_2022.pdf)
- IMYB 2021 — Manganese Ore chapter: [https://ibm.gov.in/writereaddata/files/168414783664620e7ce759fManganese_Ore_2021.pdf](https://ibm.gov.in/writereaddata/files/168414783664620e7ce759fManganese_Ore_2021.pdf)
- Indian Mineral Industry at a Glance 2023–24 (43rd edition): [https://ibm.gov.in/writereaddata/files/177461330569c67339c7968IMIG_202324_Annxure_1_IMYB_Report.pdf](https://ibm.gov.in/writereaddata/files/177461330569c67339c7968IMIG_202324_Annxure_1_IMYB_Report.pdf)
- National Mineral Inventory (NMI) — Preface and methodology: [https://ibm.gov.in/writereaddata/files/1696339153651c14d1a00e7Preface_content.pdf](https://ibm.gov.in/writereaddata/files/1696339153651c14d1a00e7Preface_content.pdf)
- IBM Annual Report 2023–24: [https://ibm.gov.in/writereaddata/files/1720673950668f669ec4a85Annual_Report_of_IBM_202324.pdf](https://ibm.gov.in/writereaddata/files/1720673950668f669ec4a85Annual_Report_of_IBM_202324.pdf)

**How used in OreSight:**
IBM's IMYB provides the authoritative national inventory of mineral reserves and production statistics. Key facts drawn from these sources:
- India's manganese ore reserves are concentrated in Madhya Pradesh and Maharashtra; Balaghat district (MP) is among the most significant deposits
- Dominant ore minerals are pyrolusite (MnO₂, ~63% Mn), psilomelane (~45–60% Mn), manganite (~62.4% Mn), and braunite (~62% Mn + SiO₂) — informing the `Mn_pct` grade range in `boreholes.csv`
- Typical bulk density values for manganese ore deposits informed the `density` column (t/m³) in the block model
- India's total manganese ore production and reserve figures provided the upper-bound context for accessible reserve estimation in the EAR module

IBM also maintains the National Mineral Inventory covering ~9,000 deposits across 46 major minerals, updated every five years — the canonical government reference for India's mineral endowment.

---

### 🏛️ G3 — Ministry of Mines, Government of India — National Mineral Policy 2019 & Digital Mining Push

**Source:** Ministry of Mines, Government of India
**URLs:**
- National Mineral Policy 2019 (Cabinet approval): [https://www.pmindia.gov.in/en/news_updates/national-mineral-policy-2019-approved-by-cabinet/](https://www.pmindia.gov.in/en/news_updates/national-mineral-policy-2019-approved-by-cabinet/)
- National Mineral Policy 2019 (full text via IELRC): [https://www.ielrc.org/content/e1905.pdf](https://www.ielrc.org/content/e1905.pdf)
- Ministry of Mines 2024 achievements: [https://mines.gov.in/admin/storage/ckeditor/MoM_Achievements_1740469087.pdf](https://mines.gov.in/admin/storage/ckeditor/MoM_Achievements_1740469087.pdf)
- IBM Report on Automation in Indian Mining: [https://ibm.gov.in/writereaddata/files/173927563367ab3d71f0b00Automation_in_Indian_Mining_Industries.pdf](https://ibm.gov.in/writereaddata/files/173927563367ab3d71f0b00Automation_in_Indian_Mining_Industries.pdf)

**How used in OreSight:**
The National Mineral Policy 2019 mandates greater transparency, better regulation, and the use of technology for sustainable mining practices. The Ministry of Mines has since pushed for digital transformation and automation in the sector. OreSight directly addresses this policy direction by:
- Providing a transparent, rule-based operational decision system (EAR accessibility logic is fully documented with explicit thresholds)
- Making model outputs machine-readable (JSON APIs) to enable integration with mine management systems
- Giving mine managers a data-driven shortfall warning and actionable recommendation — exactly the type of decision-intelligence tool the NMP 2019 envisions for improved enforcement and efficiency

---

### 🏛️ G4 — Indian Bureau of Mines (IBM) — Balaghat Mine Inspection Reports (MCDR Format)

**Source:** Indian Bureau of Mines, Ministry of Mines, Government of India — Mine Closure and Development Reports
**URLs:**
- MCDR Report — Balaghat (Bharweli) 182.3004 Ha: [https://ibm.gov.in/writereaddata/files/1748946720683ecf2058f67mcdr_Balaghat_182.300_hect..pdf](https://ibm.gov.in/writereaddata/files/1748946720683ecf2058f67mcdr_Balaghat_182.300_hect..pdf)
- IBM Inspection Report — Balaghat (40MPR01002): [https://ibm.gov.in/writereaddata/files/07052020212014mcdr_rep_Balaghat_40MPR01002-NoViolation.pdf](https://ibm.gov.in/writereaddata/files/07052020212014mcdr_rep_Balaghat_40MPR01002-NoViolation.pdf)
- Lok Sabha answer confirming Balaghat Ferro Manganese Plant (12,000 TPA): [https://sansad.in/getFile/loksabhaquestions/annex/1711/AU5471.pdf?source=pqals](https://sansad.in/getFile/loksabhaquestions/annex/1711/AU5471.pdf?source=pqals)

**How used in OreSight:**
IBM's mandatory MCDR inspection reports on the Balaghat mine confirm:
- Mine code: 40MPR01002, Bharweli village, Balaghat district, Madhya Pradesh
- Classification: Category A — Mechanised underground mine
- Operating entity: MOIL Limited (moil.nic.in)
- The mine operates an underground layout consistent with multi-level development and mechanised ore extraction — the operational structure that drives the `development.csv` and `equipment.csv` synthetic tables in OreSight
- A Ferro Manganese Plant at Balaghat with 12,000 TPA capacity confirms beneficiation occurs on-site, validating the `avg_mn_pct` column in `production.csv` as a meaningful operational variable

These government records establish the real-world mine that OreSight's DEMO-01 is calibrated against.

---

## Research Points

Four research findings that underpin OreSight's methodology.

---

### R1 — Ordinary Kriging Is the Industry-Standard Method for Mineral Reserve Estimation

**Research basis:** Ordinary Kriging (OK) is the most widely adopted geostatistical interpolation technique for mineral grade estimation and reserve reporting in the mining industry. It produces unbiased, minimum-variance linear estimates of block grades from sparse drill-hole samples, and its estimation variance provides a direct measure of spatial uncertainty — which is required for JORC/NI 43-101 compliant reserve reporting.

**Key sources:**
- Comparative study of kriging techniques for mineral resources using GIS — *International Journal of Remote Sensing*, 2013: [http://www.tandfonline.com/doi/abs/10.1080/15481603.2013.778550](http://www.tandfonline.com/doi/abs/10.1080/15481603.2013.778550)
- Geostatistical estimation with soft geological boundaries — *Applied Earth Science / ResearchGate*, 2006: [https://www.researchgate.net/publication/40883980_Geostatistical_estimation_of_mineral_resources_with_soft_geological_boundaries_A_comparative_study](https://www.researchgate.net/publication/40883980_Geostatistical_estimation_of_mineral_resources_with_soft_geological_boundaries_A_comparative_study)
- Comparative study of interpolation methods for ore distribution maps — *Springer*, 2025: [https://link.springer.com/doi/10.1007/s44288-025-00108-7](https://link.springer.com/doi/10.1007/s44288-025-00108-7)
- The place of geostatistical simulation through the life cycle of a mineral deposit — *MDPI Minerals*, 2023: [https://www.mdpi.com/2075-163X/13/11/1400](https://www.mdpi.com/2075-163X/13/11/1400)

**Relevance to OreSight:**
PRISM implements Ordinary Kriging with a fitted spherical variogram, 20-nearest-neighbour local estimation, and Z-anisotropy (×5 factor reflecting shorter vertical correlation in stratiform manganese deposits). This is the same workflow used in commercial mine planning software (Datamine, Leapfrog, Vulcan). OreSight makes the implementation explicit and auditable — every parameter (nugget, sill, range, anisotropy, cutoff) is logged to `reserve_summary.json`.

---

### R2 — LightGBM with Quantile Regression Delivers State-of-the-Art Probabilistic Forecasting for Operational Time Series

**Research basis:** LightGBM (Light Gradient Boosting Machine), developed at Microsoft Research (Ke et al., NeurIPS 2017), uses Gradient-based One-Side Sampling (GOSS) and Exclusive Feature Bundling (EFB) to achieve up to 20× speedup over conventional GBDT while maintaining near-identical accuracy. When trained with a quantile (pinball) loss function, it produces calibrated probabilistic forecasts (P10/P50/P90 bands). This approach has been validated for production forecasting in resource and energy domains.

**Key sources:**
- Ke, G. et al. (2017). *LightGBM: A Highly Efficient Gradient Boosting Decision Tree.* NeurIPS 2017 — Microsoft Research: [https://www.microsoft.com/en-us/research/project/lightgbm/publications/](https://www.microsoft.com/en-us/research/project/lightgbm/publications/) | ACM DL: [https://dl.acm.org/doi/10.5555/3294996.3295074](https://dl.acm.org/doi/10.5555/3294996.3295074)
- LightGBM outperforms conventional methods for gas well production forecasting (R²=0.9973) — *Springer*, 2026: [https://link.springer.com/article/10.1007/s44288-026-00400-0](https://link.springer.com/article/10.1007/s44288-026-00400-0)
- Short-term forecasting of base metals prices using LightGBM — *Springer*, 2024: [https://link.springer.com/article/10.1007/s13563-024-00437-y](https://link.springer.com/article/10.1007/s13563-024-00437-y)
- Quantile regression with LightGBM for energy forecasting — *MDPI Energies*, 2025: [https://www.mdpi.com/1996-1073/19/14/3312/xml](https://www.mdpi.com/1996-1073/19/14/3312/xml)

**Relevance to OreSight:**
PULSE trains three separate LightGBM models (α = 0.10, 0.50, 0.90) on a 38-feature engineering matrix including lag features, rolling statistics, equipment telemetry, weather, and calendar variables. The quantile framework produces P10/P50/P90 production bands — giving mine managers a range of outcomes rather than a single point estimate. Validation on the held-out test set gives MAE of 61.3 t/day (MAPE 2.66%), confirming the model generalises to unseen operational periods.

---

### R3 — SHAP (SHapley Additive exPlanations) Is the Gold Standard for Explaining Tree-Based ML Models in Operational Settings

**Research basis:** SHAP, introduced by Lundberg & Lee at NeurIPS 2017, provides a theoretically grounded, game-theory-based method for decomposing any model prediction into per-feature contributions. For tree ensembles, `TreeExplainer` computes exact SHAP values in polynomial time. SHAP is widely recognised as the most reliable local explanation method for gradient-boosted trees and has been adopted across industrial and scientific applications where explainability is required alongside predictive accuracy.

**Key sources:**
- Lundberg, S.M. & Lee, S.I. (2017). *A Unified Approach to Interpreting Model Predictions.* NeurIPS 2017 — arXiv: [https://arxiv.org/abs/1705.07874](https://arxiv.org/abs/1705.07874) | NeurIPS proceedings: [https://proceedings.neurips.cc/paper_files/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Reviews.html](https://proceedings.neurips.cc/paper_files/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Reviews.html)
- Lundberg, S.M. et al. (2018). *Consistent Individualized Feature Attribution for Tree Ensembles (TreeExplainer).* arXiv:1706.06060: [https://arxiv.org/html/1706.06060v3](https://arxiv.org/html/1706.06060v3)
- A Perspective on Explainable AI Methods (SHAP and LIME analysis) — arXiv, 2023: [https://arxiv.org/abs/2305.02012](https://arxiv.org/abs/2305.02012)
- Explaining ML predictions with SHAP — SciPy Proceedings: [https://proceedings.scipy.org/articles/mhum9729](https://proceedings.scipy.org/articles/mhum9729)

**Relevance to OreSight:**
The RISK+SHAP module runs `shap.TreeExplainer` on the P50 LightGBM model trained by PULSE. Mean absolute SHAP values across the training set rank all 38 features by their influence on the production forecast. Features are then labelled ACTIONABLE (fleet, blast, development, manpower) or CONTEXTUAL (weather, calendar) — a split that feeds directly into NUDGE's intervention catalogue. This gives the mine manager an interpretable, auditable explanation for why the forecast is at risk, not just a black-box alert.

Top driver result on DEMO-01: `fleet_availability` (SHAP = 24.24, DOWN), `development_m` (17.55, DOWN), `delay_h` (16.98, DOWN) — three of the top five drivers are operationally controllable.

---

### R4 — Counterfactual Optimization with Integer Programming Provides Formally Auditable Prescriptive Recommendations

**Research basis:** Prescriptive analytics — moving from "what will happen" (predictive) to "what should we do" (prescriptive) — requires a method that evaluates hypothetical interventions using the trained predictive model as a response surface, then selects the optimal action within operational bounds. Counterfactual analysis using gradient-boosted models as surrogate response surfaces, combined with Mixed-Integer Linear Programming (MILP) for action selection, is an established approach in operations research and industrial decision support. PuLP with the CBC solver provides an open-source, auditable implementation of MILP suitable for deployment in resource-constrained environments.

**Key sources:**
- JORC Code 2012 (Australasian Code for Mineral Resource and Ore Reserve Reporting) — sets the international standard for converting geological resources to operational reserves through modifying factors (including equipment, infrastructure, and environmental constraints): [https://www.jorc.org/docs/2012_jorc_update_exposure_draft.pdf](https://www.jorc.org/docs/2012_jorc_update_exposure_draft.pdf)
- Geoscience Australia — JORC resource/reserve classification (2023): [https://www.ga.gov.au/aimr2023/appendices](https://www.ga.gov.au/aimr2023/appendices)
- IBM Report on Automation and Digitalisation in Indian Mining Industries: [https://ibm.gov.in/writereaddata/files/173927563367ab3d71f0b00Automation_in_Indian_Mining_Industries.pdf](https://ibm.gov.in/writereaddata/files/173927563367ab3d71f0b00Automation_in_Indian_Mining_Industries.pdf)
- Spatiotemporal hierarchical modelling combining LightGBM with Mixed-Integer LP reconciliation — arXiv, 2024: [https://arxiv.org/html/2511.17275v1](https://arxiv.org/html/2511.17275v1)

**Relevance to OreSight:**
NUDGE implements a three-step prescriptive pipeline:
1. **Counterfactual scoring** — for each of four controllable levers (fleet availability, downtime, development advance, workforce), it perturbs the feature across the 30-day forecast window and re-runs the PULSE P50 model to measure production gain
2. **EAR constraint** — the 30-day counterfactual total is checked against the accessible reserve to prevent operationally impossible recommendations
3. **PuLP CBC MILP** — selects exactly one feasible action that maximises `shortfall_reduction_t`, producing a formally auditable decision record

The JORC Code connection is important: JORC's concept of "modifying factors" (equipment, infrastructure, environmental) for converting Mineral Resources to Ore Reserves is the real-world analogue of EAR's three operational constraints. OreSight makes this conversion transparent and computable.

---

## Full Reference List

| # | Citation | Type | URL |
|---|---|---|---|
| 1 | MOIL Limited. *Annual Report 2024–25.* Government of India Enterprise. | 🏛️ Govt. | [moil.nic.in](https://www.moil.nic.in/userfiles/Annual_Report_2024_25.pdf) |
| 2 | MOIL Limited. *Annual Report 2023–24.* Government of India Enterprise. | 🏛️ Govt. | [moil.nic.in](https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2023-24.pdf) |
| 3 | MOIL Limited. *Annual Report 2022–23.* Government of India Enterprise. | 🏛️ Govt. | [moil.nic.in](https://moil.nic.in/userfiles/file/InvRel/Financials/Annual_Report_2022-23.pdf) |
| 4 | Indian Bureau of Mines. *Indian Minerals Yearbook 2022 — Manganese Ore.* Ministry of Mines, Govt. of India. | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/17125770456613da1576db0Manganese_Ore_2022.pdf) |
| 5 | Indian Bureau of Mines. *Indian Mineral Industry at a Glance 2023–24 (43rd edition).* Ministry of Mines, Govt. of India. | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/177461330569c67339c7968IMIG_202324_Annxure_1_IMYB_Report.pdf) |
| 6 | Indian Bureau of Mines. *National Mineral Inventory — Preface & Methodology.* Ministry of Mines, Govt. of India. | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/1696339153651c14d1a00e7Preface_content.pdf) |
| 7 | Ministry of Mines, Govt. of India. *National Mineral Policy 2019.* Cabinet approval, February 2019. | 🏛️ Govt. | [pmindia.gov.in](https://www.pmindia.gov.in/en/news_updates/national-mineral-policy-2019-approved-by-cabinet/) |
| 8 | Indian Bureau of Mines. *Annual Report 2023–24.* Ministry of Mines, Govt. of India. | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/1720673950668f669ec4a85Annual_Report_of_IBM_202324.pdf) |
| 9 | Indian Bureau of Mines. *Automation and Digitalisation in Indian Mining Industries.* Ministry of Mines, Govt. of India. | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/173927563367ab3d71f0b00Automation_in_Indian_Mining_Industries.pdf) |
| 10 | Indian Bureau of Mines. *MCDR Inspection Report — Balaghat Mine (40MPR01002), Bharweli, MP.* | 🏛️ Govt. | [ibm.gov.in](https://ibm.gov.in/writereaddata/files/07052020212014mcdr_rep_Balaghat_40MPR01002-NoViolation.pdf) |
| 11 | Lok Sabha Secretariat. *Parliamentary Question AU5471 — MOIL Balaghat Ferro Manganese Plant.* Sansad.in. | 🏛️ Govt. | [sansad.in](https://sansad.in/getFile/loksabhaquestions/annex/1711/AU5471.pdf?source=pqals) |
| 12 | Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. *Advances in Neural Information Processing Systems 30 (NeurIPS 2017).* | Research | [microsoft.com](https://www.microsoft.com/en-us/research/project/lightgbm/publications/) / [acm.org](https://dl.acm.org/doi/10.5555/3294996.3295074) |
| 13 | Lundberg, S.M. & Lee, S.I. (2017). A Unified Approach to Interpreting Model Predictions. *NeurIPS 2017.* arXiv:1705.07874. | Research | [arxiv.org](https://arxiv.org/abs/1705.07874) |
| 14 | Lundberg, S.M., Erion, G.G., & Lee, S.I. (2018). Consistent Individualized Feature Attribution for Tree Ensembles. arXiv:1706.06060. | Research | [arxiv.org](https://arxiv.org/html/1706.06060v3) |
| 15 | Salehi, S. et al. (2026). Comparative evaluation of gas well production forecasting using decline curve analysis and LightGBM. *Geomechanics and Geophysics for Geo-Energy and Geo-Resources, Springer.* | Research | [springer.com](https://link.springer.com/article/10.1007/s44288-026-00400-0) |
| 16 | Tealab, A. et al. (2024). Short-term forecasting of base metals prices using LightGBM and LightGBM–ARIMA ensemble. *Mineral Economics, Springer.* | Research | [springer.com](https://link.springer.com/article/10.1007/s13563-024-00437-y) |
| 17 | Olsson, F. et al. (2025). Comparative study of interpolation methods for ore distribution maps. *Geomechanics and Geophysics, Springer.* | Research | [springer.com](https://link.springer.com/doi/10.1007/s44288-025-00108-7) |
| 18 | Rossi, M.E. & Deutsch, C.V. (2023). The Place of Geostatistical Simulation through the Life Cycle of a Mineral Deposit. *MDPI Minerals, 13(11), 1400.* | Research | [mdpi.com](https://www.mdpi.com/2075-163X/13/11/1400) |
| 19 | Oommen, T. et al. (2013). Comparative evaluation of kriging techniques for measuring mineral resources using GIS. *International Journal of Remote Sensing, Taylor & Francis.* | Research | [tandfonline.com](http://www.tandfonline.com/doi/abs/10.1080/15481603.2013.778550) |
| 20 | Joint Ore Reserves Committee (JORC). *Australasian Code for Reporting of Exploration Results, Mineral Resources and Ore Reserves (JORC Code 2012).* | Industry standard | [jorc.org](https://www.jorc.org/docs/2012_jorc_update_exposure_draft.pdf) |

---

## Data Honesty Statement

In keeping with SIH transparency requirements and the project's own data honesty policy:

| Data element | Status | Source |
|---|---|---|
| Balaghat mine coordinates, mine type, district | ✅ Real | MOIL annual reports + IBM MCDR reports |
| MOIL company-level annual production totals | ✅ Real | MOIL Annual Reports (moil.nic.in) |
| India manganese ore reserve and production statistics | ✅ Real | IBM IMYB 2022 + IMIG 2023–24 (ibm.gov.in) |
| National Mineral Policy 2019 mandates | ✅ Real | Ministry of Mines / pmindia.gov.in |
| Daily production series (DEMO-01) | 🔶 Synthetic | Calibrated to MOIL scale, seed 42 |
| 3D block model / borehole grades | 🔶 Synthetic | Spatially correlated, calibrated to IBM Mn% ranges |
| Equipment events, blast logs, manpower | 🔶 Synthetic | Follows realistic operational patterns |
| Weather / rainfall | 🔶 Synthetic | Indian monsoon seasonal pattern (not IMD station data) |

All synthetic data is clearly labelled throughout the codebase (`DATA_DICTIONARY.md`, `data/README.md`, dashboard disclaimer banner) and is never presented as real operational or statutory reserve data.
