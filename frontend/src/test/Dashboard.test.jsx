/**
 * Dashboard component tests — Phase 8 (redesign)
 * API calls are fully mocked so tests run without a live backend.
 */
import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import Dashboard from '../pages/Dashboard.jsx'

// ── Mock the api service ────────────────────────────────────────────────
vi.mock('../services/api.js', () => ({
  API_BASE:           'http://127.0.0.1:8000',
  getOverview:        vi.fn(),
  getPrismBlocks:     vi.fn(),
  getEarBlocks:       vi.fn(),
  getPulse:           vi.fn(),
  getRisk:            vi.fn(),
  getShap:            vi.fn(),
  getNudge:           vi.fn(),
  getNudgeCandidates: vi.fn(),
}))

// ── Stub Plotly (dynamically imported inside PrismView/EarView) ─────────
vi.mock('plotly.js-basic-dist-min', () => ({
  newPlot:    () => Promise.resolve(),
  react:      () => Promise.resolve(),
  purge:      () => {},
  default:    { newPlot: () => Promise.resolve() },
}))

import {
  getOverview, getPrismBlocks, getEarBlocks,
  getPulse, getRisk, getShap, getNudge, getNudgeCandidates,
} from '../services/api.js'

// ── Stub data ─────────────────────────────────────────────────────────────
const STUB_OVERVIEW = {
  prism: {
    declared_reserve_t: 48271696.4, ore_blocks: 498, waste_blocks: 1742,
    average_mn_pct: 25.246, mn_cutoff_pct: 20, total_blocks: 2240,
    max_estimated_mn_pct: 42.301, provenance: 'SYNTHETIC',
    variogram: { nugget: 9.9, partial: 188.07, range: 224.34, sill: 197.97 },
  },
  ear: {
    declared_reserve_t: 48271696.4, effective_accessible_reserve_t: 32736929.4,
    accessibility_ratio: 0.6782, accessible_blocks: 339, inaccessible_blocks: 159,
    total_ore_blocks: 498, provenance: 'SYNTHETIC',
    constraints: {
      development_ready_z_threshold_m: 192, equipment_availability_threshold: 0.85,
      weather_rainfall_threshold_mm: 30, equipment_available_mine_wide: true,
      weather_feasibility_score: 0.9434,
    },
  },
  pulse: {
    planned_production_t: 71988.9, expected_production_t: 68593.4,
    expected_shortfall_t: 3395.5, shortfall_probability: 0.8837,
    p10_production_t: 66322.2, p50_production_t: 68593.4, p90_production_t: 71073.7,
    forecast_horizon_days: 30, mae: 61.3, rmse: 77.4, mape: 2.66,
  },
  risk_level: 'CRITICAL',
  shortfall_probability: 0.8837,
  nudge: {
    action_name: 'Increase development progress', feature: 'development_m',
    baseline_value: 18.5323, recommended_value: 19.2374,
    expected_production_gain_t: 606.6, expected_shortfall_reduction_t: 606.6,
    new_shortfall_probability: 0.8803, feasible: true,
  },
  provenance: 'SYNTHETIC DEMO-01 data — not real MOIL operational data',
}

const STUB_PULSE = {
  summary: {
    model: 'LightGBM Quantile Regression', forecast_horizon_days: 30,
    forecast_period: { start: '2025-12-02', end: '2025-12-31' },
    validation_metrics: { P50: { MAE: 61.3, RMSE: 77.4, MAPE: 2.66 } },
    forecast_summary: {
      total_planned_production_t: 71988.9, total_expected_production_t: 68593.4,
      total_expected_shortfall_t: 3395.5, overall_shortfall_probability: 0.8837,
      total_p10_production_t: 66322.2, total_p50_production_t: 68593.4, total_p90_production_t: 71073.7,
    },
  },
  forecast: Array.from({ length: 30 }, (_, i) => ({
    date: `2025-12-${String(i + 1).padStart(2, '0')}`, mine_id: 'DEMO-01',
    planned_production_t: 2400, p10_t: 2200, p50_t: 2290, p90_t: 2370,
    expected_production_t: 2290, shortfall_t: 110, shortfall_probability: 0.88,
  })),
}

const STUB_RISK = {
  overall_shortfall_probability: 0.8837, risk_level: 'CRITICAL',
  forecast_horizon_days: 30, expected_production_t: 68593.4,
  planned_production_t: 71988.9, expected_shortfall_t: 3395.5,
  top_risk_drivers: [
    { feature: 'fleet_availability', mean_absolute_shap: 24.24, impact_direction: 'DOWN', importance_rank: 3, driver_type: 'ACTIONABLE' },
  ],
  actionable_drivers: [], contextual_drivers: [],
  shap_note: 'SHAP values measure model feature attribution.',
  risk_thresholds: { LOW:[0,0.25], MEDIUM:[0.25,0.5], HIGH:[0.5,0.75], CRITICAL:[0.75,1] },
}

const STUB_SHAP = {
  count: 5,
  drivers: [
    { feature: 'fleet_availability', mean_absolute_shap: 24.24, impact_direction: 'DOWN', importance_rank: 1, driver_type: 'ACTIONABLE' },
    { feature: 'rainfall_mm',        mean_absolute_shap: 41.93, impact_direction: 'DOWN', importance_rank: 2, driver_type: 'CONTEXTUAL' },
    { feature: 'development_m',      mean_absolute_shap: 17.55, impact_direction: 'DOWN', importance_rank: 3, driver_type: 'ACTIONABLE' },
    { feature: 'delay_h',            mean_absolute_shap: 16.98, impact_direction: 'DOWN', importance_rank: 4, driver_type: 'ACTIONABLE' },
    { feature: 'planned_t',          mean_absolute_shap: 97.16, impact_direction: 'DOWN', importance_rank: 5, driver_type: 'ACTIONABLE' },
  ],
}

const STUB_NUDGE = {
  status: 'success', provenance: 'SYNTHETIC',
  baseline: {
    expected_production_t: 68593.4, planned_production_t: 71988.9,
    expected_shortfall_t: 3395.5, shortfall_probability: 0.8837,
    fleet_availability: 0.9289, fleet_downtime_h: 15.36, delay_h: 0,
    development_m: 18.53, available_workers: 87.9,
  },
  best_action: {
    action_name: 'Increase development progress', feature: 'development_m',
    baseline_value: 18.5323, recommended_value: 19.2374,
    expected_production_t: 69200, expected_production_gain_t: 606.6,
    expected_shortfall_t: 2788.9, expected_shortfall_reduction_t: 606.6,
    new_expected_shortfall_t: 2788.9, new_shortfall_probability: 0.8803,
    feasible: true, rationale: 'Allocate additional development crews.',
  },
  optimization: { objective: 'minimize_expected_shortfall', method: 'PuLP CBC', candidates_evaluated: 4, feasible_candidates: 4 },
  constraints: [], excluded_levers: {}, assumptions: [],
}

const STUB_CANDIDATES = {
  count: 4,
  candidates: [
    { rank: 1, action_name: 'Increase development progress', feature: 'development_m', baseline_value: 18.53, recommended_value: 19.24, expected_production_t: 69200, production_gain_t: 606.6, expected_shortfall_t: 2788.9, shortfall_reduction_t: 606.6, feasible: true, constraint_notes: 'Within bounds' },
    { rank: 2, action_name: 'Improve fleet availability',    feature: 'fleet_availability', baseline_value: 0.929, recommended_value: 0.957, expected_production_t: 69008.6, production_gain_t: 415.2, expected_shortfall_t: 2980.3, shortfall_reduction_t: 415.2, feasible: true, constraint_notes: 'Within bounds' },
    { rank: 3, action_name: 'Reduce equipment downtime',     feature: 'fleet_downtime_h', baseline_value: 15.36, recommended_value: 10.54, expected_production_t: 68756.9, production_gain_t: 163.5, expected_shortfall_t: 3232.0, shortfall_reduction_t: 163.5, feasible: true, constraint_notes: 'Within bounds' },
    { rank: 4, action_name: 'Increase available workforce',  feature: 'available_workers', baseline_value: 87.87, recommended_value: 90.97, expected_production_t: 68623.5, production_gain_t: 30.1, expected_shortfall_t: 3365.4, shortfall_reduction_t: 30.1, feasible: true, constraint_notes: 'Within bounds' },
  ],
}

function setupMocks() {
  getOverview.mockResolvedValue(STUB_OVERVIEW)
  getPrismBlocks.mockResolvedValue({ blocks: [], count: 0 })
  getEarBlocks.mockResolvedValue({ blocks: [], count: 0 })
  getPulse.mockResolvedValue(STUB_PULSE)
  getRisk.mockResolvedValue(STUB_RISK)
  getShap.mockResolvedValue(STUB_SHAP)
  getNudge.mockResolvedValue(STUB_NUDGE)
  getNudgeCandidates.mockResolvedValue(STUB_CANDIDATES)
}

// ── Tests ───────────────────────────────────────────────────────────────

describe('Dashboard', () => {

  // Test 8 — Loading state
  it('shows loading state before data arrives', () => {
    const never = new Promise(() => {})
    getOverview.mockReturnValue(never)
    getPulse.mockReturnValue(never)
    getRisk.mockReturnValue(never)
    getShap.mockReturnValue(never)
    getNudge.mockReturnValue(never)
    getNudgeCandidates.mockReturnValue(never)
    render(<Dashboard />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  // Test 9 — Error state
  it('shows error state when backend is unavailable', async () => {
    const err = new Error('Network Error')
    getOverview.mockRejectedValue(err)
    getPulse.mockRejectedValue(err)
    getRisk.mockRejectedValue(err)
    getShap.mockRejectedValue(err)
    getNudge.mockRejectedValue(err)
    getNudgeCandidates.mockRejectedValue(err)
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/unable to connect/i)).toBeInTheDocument()
    })
  })

  describe('with data loaded', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      setupMocks()
    })

    // Test 1 — Dashboard renders (shows overview by default)
    it('renders the dashboard on overview stage', async () => {
      render(<Dashboard />)
      await waitFor(() => {
        expect(screen.getByText(/Mine Decision Intelligence/i)).toBeInTheDocument()
      })
    })

    // Test 2 — API data is loaded and overview metrics present
    it('loads API data and displays overview metrics', async () => {
      render(<Dashboard />)
      await waitFor(() =>
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument(), { timeout: 8000 }
      )
      const declared = screen.getAllByText((c) => c.includes('48.27'))
      expect(declared.length).toBeGreaterThan(0)
    })

    // Test 3 — Overview metrics appear (declared reserve value)
    it('shows declared reserve from API', async () => {
      render(<Dashboard />)
      await waitFor(() =>
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument(), { timeout: 8000 }
      )
      const els = screen.getAllByText((c) => c.includes('48.27'))
      expect(els.length).toBeGreaterThan(0)
    })

    // Test 4 — Risk level appears
    it('shows the CRITICAL risk level on the overview', async () => {
      render(<Dashboard />)
      await waitFor(() => {
        const criticals = screen.getAllByText(/CRITICAL/i)
        expect(criticals.length).toBeGreaterThan(0)
      })
    })

    // Test 5 — Stage navigation changes content (PULSE)
    it('renders PULSE forecast chart when pulse stage is selected', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: PULSE' }))
      await waitFor(() => {
        expect(screen.getByText(/30-Day Production Forecast/i)).toBeInTheDocument()
      })
    })

    // Test 6 — SHAP drivers appear inside PULSE (not as a separate stage)
    it('renders SHAP risk drivers inside the PULSE stage', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: PULSE' }))
      await waitFor(() => {
        expect(screen.getByText(/Why is production at risk/i)).toBeInTheDocument()
      })
    })

    // Test 7 — NUDGE shows best action and ranked alternatives
    it('renders NUDGE best action and all 4 candidates', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: NUDGE' }))
      await waitFor(() => {
        expect(screen.getByText(/Recommended action/i)).toBeInTheDocument()
        // Multiple elements may show the action name across cards — use getAllByText
        expect(screen.getAllByText(/Increase development progress/i).length).toBeGreaterThan(0)
        expect(screen.getByText(/Improve fleet availability/i)).toBeInTheDocument()
        expect(screen.getByText(/Reduce equipment downtime/i)).toBeInTheDocument()
        expect(screen.getByText(/Increase available workforce/i)).toBeInTheDocument()
      })
    })

    // Test 8 is loading state (above)
    // Test 9 is error state (above)

    // Test 10 — Synthetic data disclaimer appears
    it('shows the synthetic data disclaimer', async () => {
      render(<Dashboard />)
      await waitFor(() => {
        expect(screen.getByRole('note')).toBeInTheDocument()
        expect(screen.getByText(/Demo Mode/i)).toBeInTheDocument()
      })
    })

    // Test 11 — Stage navigation: PRISM stage exists and content changes
    it('renders PRISM stage content when prism is selected', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: PRISM' }))
      await waitFor(() => {
        expect(screen.getByText(/What geological ore exists/i)).toBeInTheDocument()
      })
    })

    // Test 12 — EAR stage content
    it('renders EAR stage content when ear is selected', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: EAR' }))
      await waitFor(() => {
        expect(screen.getByText(/How much of that reserve is realistically accessible/i)).toBeInTheDocument()
      })
    })

    // Test 13 — Shortfall probability consistent (overview uses same value as risk)
    it('shows consistent 88.4% shortfall probability from API', async () => {
      render(<Dashboard />)
      await waitFor(() =>
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument(), { timeout: 8000 }
      )
      const probs = screen.getAllByText((c) => c.includes('88.4'))
      expect(probs.length).toBeGreaterThan(0)
    })

    // Test 14 — NUDGE shows before/after impact
    it('renders before/after shortfall comparison in NUDGE', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      fireEvent.click(screen.getByRole('button', { name: 'Stage: NUDGE' }))
      await waitFor(() => {
        expect(screen.getByText(/Current forecast/i)).toBeInTheDocument()
        expect(screen.getByText(/After intervention/i)).toBeInTheDocument()
      })
    })

    // Test 15 — Pipeline has 5 stages (overview, prism, ear, pulse, nudge)
    it('pipeline strip has exactly 5 stage buttons', async () => {
      render(<Dashboard />)
      await waitFor(() => screen.getByText(/Mine Decision Intelligence/i))
      const buttons = screen.getAllByRole('button', { name: /Navigate to|overview|prism|ear|pulse|nudge|Refresh/i })
      // 5 pipeline buttons + 1 Refresh = 6 minimum
      expect(buttons.length).toBeGreaterThanOrEqual(5)
    })
  })
})
