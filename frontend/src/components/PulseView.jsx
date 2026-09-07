import React from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { fmtT, fmtPct, featureLabel, FEATURE_LABELS } from '../utils/labels.js'

const RISK_COLORS = { LOW: 'var(--risk-low)', MEDIUM: 'var(--risk-medium)', HIGH: 'var(--risk-high)', CRITICAL: 'var(--risk-critical)' }

const fmtDate = (d) => {
  const dt = new Date(d)
  return `${dt.getDate()}/${dt.getMonth() + 1}`
}

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card" style={{ padding: '10px 14px', fontSize: '0.8rem', minWidth: 190 }}>
      <p style={{ fontWeight: 700, marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: {p.value?.toLocaleString(undefined, { maximumFractionDigits: 0 })} t
        </div>
      ))}
    </div>
  )
}

/* Features to exclude from the SHAP driver display */
const EXCLUDE_FEATURES = new Set([
  'planned_t',  // planning input, not operational driver
])

/* Only show the top meaningful drivers for a mine manager */
const MAX_DRIVERS = 6

export default function PulseView({ pulse, risk, shap }) {
  if (!pulse?.forecast || !risk || !shap) return null

  const fs    = pulse.summary?.forecast_summary ?? {}
  const vm    = pulse.summary?.validation_metrics?.P50 ?? {}
  const fp    = pulse.summary?.forecast_period ?? {}

  const planned  = fs.total_planned_production_t ?? 0
  const expected = fs.total_expected_production_t ?? 0
  const shortfall = fs.total_expected_shortfall_t ?? 0
  const prob     = fs.overall_shortfall_probability ?? 0
  const p10      = fs.total_p10_production_t ?? 0
  const p90      = fs.total_p90_production_t ?? 0
  const rl       = risk.risk_level ?? 'CRITICAL'
  const riskColor = RISK_COLORS[rl] ?? 'var(--risk-critical)'

  const chartData = pulse.forecast.map(r => ({
    date:    fmtDate(r.date),
    planned: r.planned_production_t,
    p10:     r.p10_t,
    p50:     r.p50_t,
    p90:     r.p90_t,
  }))

  // Filter and humanise SHAP drivers
  const drivers = shap.drivers
    .filter(d => !EXCLUDE_FEATURES.has(d.feature))
    .slice(0, MAX_DRIVERS)

  const maxShap = drivers[0]?.mean_absolute_shap ?? 1

  return (
    <div className="stage-view">
      <div style={{ marginBottom: 'var(--gap-lg)' }}>
        <div className="section-label">PULSE — Production Forecast</div>
        <h2 style={{ marginBottom: 6 }}>How much can we realistically produce?</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 720, fontSize: '0.9rem' }}>
          PULSE uses a LightGBM model trained on 3 years of historical operational data to forecast
          production over the next 30 days with uncertainty bands.
        </p>
      </div>

      {/* ─── Section A: Forecast chart ─── */}
      <div className="card" style={{ marginBottom: 'var(--gap-lg)' }}>
        <div className="flex-between" style={{ marginBottom: 'var(--gap-md)' }}>
          <div>
            <h3>30-Day Production Forecast</h3>
            <p className="text-muted text-small">{fp.start} → {fp.end}</p>
          </div>
          <div className="flex-row" style={{ gap: 'var(--gap-md)', flexWrap: 'wrap' }}>
            <LegendDot color="var(--yellow)" dash label="Planned target" />
            <LegendDot color="rgba(88,166,255,.3)" fill label="Uncertainty (P10–P90)" />
            <LegendDot color="var(--accent)" label="P50 — expected production" />
          </div>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
            <XAxis dataKey="date" tick={{ fill: '#8b949e', fontSize: 10 }} tickLine={false} axisLine={false} interval={4} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 10 }} axisLine={false} tickLine={false}
              tickFormatter={v => v.toLocaleString()} width={56} />
            <Tooltip content={<ChartTooltip />} />
            <Area dataKey="p90" stroke="none" fill="rgba(88,166,255,.1)" fillOpacity={1} legendType="none" name="P90 band" />
            <Area dataKey="p10" stroke="none" fill="var(--bg-page)" fillOpacity={1} legendType="none" name="P10 band" />
            <Line dataKey="planned" name="Planned target" stroke="var(--yellow)" strokeDasharray="6 3" strokeWidth={1.5} dot={false} />
            <Line dataKey="p10" name="P10 (pessimistic)" stroke="var(--accent)" strokeOpacity={0.35} strokeWidth={1} dot={false} />
            <Line dataKey="p50" name="P50 (expected)" stroke="var(--accent)" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
            <Line dataKey="p90" name="P90 (optimistic)" stroke="var(--green)" strokeOpacity={0.4} strokeWidth={1} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 4, marginTop: 'var(--gap-md)', padding: '8px 0', borderTop: '1px solid var(--border-light)' }}>
          <ScenarioCard label="P10 — Pessimistic"  value={`${(p10/1e3).toFixed(1)} kt`} sub="Lower-bound scenario"    color="rgba(88,166,255,.5)" />
          <ScenarioCard label="P50 — Expected"      value={`${(expected/1e3).toFixed(1)} kt`} sub="Median forecast"     color="var(--accent)" bold />
          <ScenarioCard label="P90 — Optimistic"    value={`${(p90/1e3).toFixed(1)} kt`} sub="Upper-bound scenario"    color="var(--green)" />
        </div>
      </div>

      {/* ─── Section B: Shortfall ─── */}
      <div className="grid-2" style={{ gap: 'var(--gap-lg)', marginBottom: 'var(--gap-lg)' }}>
        {/* Production vs target */}
        <div className="card">
          <h3 style={{ marginBottom: 'var(--gap-md)' }}>Production vs Target</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
            <BarRow label="Planned target"       value={planned}  max={planned} color="var(--border)" textColor="var(--text-secondary)" />
            <BarRow label="P90 (optimistic)"     value={p90}      max={planned} color="var(--green)" />
            <BarRow label="P50 (expected)"       value={expected} max={planned} color="var(--accent)" bold />
            <BarRow label="P10 (pessimistic)"    value={p10}      max={planned} color="rgba(88,166,255,.4)" />
          </div>
          <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: 'var(--gap-md) 0' }} />
          <div className="flex-between" style={{ marginBottom: 4 }}>
            <span className="text-muted text-small">Expected shortfall</span>
            <span style={{ fontWeight: 700, color: 'var(--risk-high)', fontSize: '1.05rem' }}>
              −{fmtT(shortfall)} t
            </span>
          </div>
          <div className="flex-between">
            <span className="text-muted text-small">As % of planned</span>
            <span style={{ fontWeight: 600, color: 'var(--risk-high)' }}>
              {((shortfall/planned)*100).toFixed(1)}% below target
            </span>
          </div>
        </div>

        {/* Shortfall risk */}
        <div className="card" style={{ borderColor: riskColor }}>
          <h3 style={{ marginBottom: 'var(--gap-md)' }}>Shortfall Risk</h3>
          <div style={{ textAlign: 'center', padding: 'var(--gap-md) 0' }}>
            <div className="big-number" style={{ color: riskColor, fontSize: '3rem' }}>
              {fmtPct(prob)}
            </div>
            <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>probability of missing the production target</p>
            <div style={{ marginTop: 10 }}>
              <span className={`badge badge--${rl.toLowerCase()}`} style={{ fontSize: '0.85rem', padding: '4px 14px' }}>
                {rl}
              </span>
            </div>
          </div>
          <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: 'var(--gap-md) 0' }} />
          <p className="text-muted text-small">
            Model: {pulse.summary?.model} · Horizon: 30 days · P50 MAPE: {vm.MAPE?.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* ─── Section C: SHAP — why is production at risk? ─── */}
      <div className="card">
        <div style={{ marginBottom: 'var(--gap-md)' }}>
          <h3>Why is production at risk?</h3>
          <p className="text-muted text-small" style={{ marginTop: 4 }}>
            The model attributes forecast uncertainty to the following operational factors.
            Actionable items can be addressed through operational decisions.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
          {drivers.map(d => {
            const label = featureLabel(d.feature)
            if (!label) return null
            const isActionable = d.driver_type === 'ACTIONABLE'
            const barW = (d.mean_absolute_shap / maxShap) * 100
            return (
              <div key={d.feature} style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-md)' }}>
                <div style={{ width: 200, flexShrink: 0 }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: isActionable ? 600 : 400 }}>{label}</span>
                </div>
                <div className="progress-bar-track" style={{ flex: 1, height: 10 }}>
                  <div className="progress-bar-fill" style={{
                    width: `${barW}%`,
                    background: isActionable ? 'var(--accent)' : 'var(--purple)',
                  }} />
                </div>
                <div style={{ width: 60, textAlign: 'right', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {d.mean_absolute_shap.toFixed(1)}
                </div>
                <span className={`pill pill--${isActionable ? 'actionable' : 'contextual'}`} style={{ flexShrink: 0 }}>
                  {isActionable ? 'Actionable' : 'Contextual'}
                </span>
              </div>
            )
          })}
        </div>

        <p className="text-muted text-small" style={{ marginTop: 'var(--gap-md)', fontStyle: 'italic' }}>
          These are model attribution signals — not proof of causality. Bar length shows relative
          contribution to forecast uncertainty. Blue = actionable (within operational control),
          Purple = contextual (external factors).
        </p>
      </div>
    </div>
  )
}

function LegendDot({ color, label, dash, fill }) {
  return (
    <div className="flex-row" style={{ gap: 5 }}>
      <div style={{
        width: dash ? 16 : 10, height: dash ? 2 : 10,
        background: color, borderRadius: dash ? 1 : '50%',
        opacity: fill ? 0.6 : 1,
      }} />
      <span className="text-muted text-small">{label}</span>
    </div>
  )
}

function ScenarioCard({ label, value, sub, color, bold }) {
  return (
    <div style={{ textAlign: 'center', padding: '8px 4px' }}>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 3 }}>{label}</p>
      <p style={{ fontWeight: bold ? 800 : 600, color, fontSize: bold ? '1.1rem' : '0.95rem' }}>{value}</p>
      <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{sub}</p>
    </div>
  )
}

function BarRow({ label, value, max, color, textColor, bold }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div>
      <div className="flex-between" style={{ marginBottom: 3 }}>
        <span style={{ fontSize: '0.82rem', color: textColor ?? (bold ? 'var(--text-primary)' : 'var(--text-secondary)'), fontWeight: bold ? 700 : 400 }}>
          {label}
        </span>
        <span style={{ fontSize: '0.85rem', fontWeight: bold ? 700 : 600, color: textColor ?? color }}>
          {value.toLocaleString(undefined, { maximumFractionDigits: 0 })} t
        </span>
      </div>
      <div className="progress-bar-track" style={{ height: bold ? 8 : 5 }}>
        <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}
