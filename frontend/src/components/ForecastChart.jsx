import React from 'react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const fmtDate = (d) => { const dt = new Date(d); return `${dt.getDate()}/${dt.getMonth()+1}` }
const fmtT    = (v) => v == null ? '-' : Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }) + ' t'
const pct     = (v) => v == null ? '-' : (Number(v)*100).toFixed(1) + '%'

function MiniStat({ label, value, accent }) {
  return (
    <div style={{ background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
      <p style={{ fontSize:'0.72rem', color:'var(--text-secondary)', textTransform:'uppercase', letterSpacing:'0.04em' }}>{label}</p>
      <p style={{ fontSize:'1.05rem', fontWeight:700, color: accent ?? 'var(--text-primary)', marginTop:2 }}>{value}</p>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card" style={{ padding:'10px 14px', fontSize:'0.8rem', minWidth:170 }}>
      <p style={{ fontWeight:600, marginBottom:6 }}>{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom:2 }}>
          {p.name}: {fmtT(p.value)}
        </div>
      ))}
    </div>
  )
}

export default function ForecastChart({ pulse }) {
  if (!pulse?.forecast) return null

  const data = pulse.forecast.map(r => ({
    date:    fmtDate(r.date),
    planned: r.planned_production_t,
    p10:     r.p10_t,
    p50:     r.p50_t,
    p90:     r.p90_t,
  }))

  const fs = pulse.summary?.forecast_summary ?? {}

  return (
    <div className="card section">
      <div className="flex-between section-title">
        <h2>30-Day Production Forecast</h2>
        <span className="text-muted text-small">P10 · P50 · P90 uncertainty bands</span>
      </div>

      <div className="grid-4" style={{ marginBottom:'var(--gap-md)' }}>
        <MiniStat label="Planned"        value={fmtT(fs.total_planned_production_t)} />
        <MiniStat label="P50 (Expected)" value={fmtT(fs.total_p50_production_t)}     accent="var(--accent)" />
        <MiniStat label="Expected Shortfall" value={fmtT(fs.total_expected_shortfall_t)} accent="var(--risk-high)" />
        <MiniStat label="Shortfall Prob." value={pct(fs.overall_shortfall_probability)} accent="var(--risk-critical)" />
      </div>

      <ResponsiveContainer width="100%" height={270}>
        <ComposedChart data={data} margin={{ top:4, right:16, bottom:0, left:0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey="date" tick={{ fill:'#8b949e', fontSize:10 }} tickLine={false} axisLine={false} interval={4} />
          <YAxis tick={{ fill:'#8b949e', fontSize:10 }} axisLine={false} tickLine={false}
            tickFormatter={v => v.toLocaleString()} width={56} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize:'0.78rem', paddingTop:8 }} />
          {/* shaded band P10–P90 */}
          <Area dataKey="p90" stroke="none" fill="rgba(88,166,255,.08)" fillOpacity={1} legendType="none" name="P90 band" />
          <Area dataKey="p10" stroke="none" fill="var(--bg-page)"        fillOpacity={1} legendType="none" name="P10 band" />
          <Line dataKey="planned" name="Planned target" stroke="var(--yellow)" strokeDasharray="5 3" strokeWidth={1.5} dot={false} />
          <Line dataKey="p10" name="P10 (pessimistic)" stroke="#58a6ff" strokeOpacity={0.5} strokeWidth={1} dot={false} />
          <Line dataKey="p50" name="P50 (expected)"    stroke="var(--accent)" strokeWidth={2} dot={false} activeDot={{ r:4 }} />
          <Line dataKey="p90" name="P90 (optimistic)"  stroke="var(--green)" strokeOpacity={0.5} strokeWidth={1} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="text-muted text-small mt-md">
        Shaded region shows P10–P90 uncertainty band. Dashed line = planned production target.
        Model accuracy (P50): MAPE {pulse.summary?.validation_metrics?.P50?.MAPE?.toFixed(1)}%.
      </p>
    </div>
  )
}
