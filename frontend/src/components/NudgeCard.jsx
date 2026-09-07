import React from 'react'

const fmtT = v => Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 })
const pct  = v => (Number(v)*100).toFixed(1)+'%'
const fmt4 = v => Number(v).toFixed(4)

export default function NudgeCard({ nudge }) {
  if (!nudge?.best_action) return null

  const ba      = nudge.best_action
  const base    = nudge.baseline

  return (
    <div className="card card--highlight section" style={{ borderWidth:2 }} aria-label="NUDGE recommendation">
      <div className="flex-between section-title">
        <h2>Recommended Action</h2>
        <span className="badge badge--feasible">FEASIBLE</span>
      </div>

      {/* headline */}
      <div style={{
        background:'var(--bg-card-alt)', borderRadius:'var(--radius-md)',
        padding:'var(--gap-md)', marginBottom:'var(--gap-md)', textAlign:'center',
      }}>
        <h4 style={{ color:'var(--text-secondary)', marginBottom:4 }}>BEST ACTION</h4>
        <p style={{ fontSize:'1.3rem', fontWeight:700, color:'var(--accent)' }}>{ba.action_name}</p>
        <p style={{ color:'var(--text-muted)', fontSize:'0.82rem', marginTop:4 }}>
          Feature: <code style={{ color:'var(--text-primary)' }}>{ba.feature}</code>
        </p>
        {ba.rationale && (
          <p style={{ color:'var(--text-secondary)', fontSize:'0.82rem', marginTop:6, fontStyle:'italic' }}>
            {ba.rationale}
          </p>
        )}
      </div>

      <div className="grid-2" style={{ gap:'var(--gap-md)' }}>
        {/* intervention details */}
        <div>
          <h4 style={{ marginBottom:8 }}>Intervention</h4>
          <Row label="Baseline value"     value={fmt4(ba.baseline_value)} />
          <Row label="Recommended value"  value={fmt4(ba.recommended_value)} accent="var(--green)" />
          <Row label="Production gain"    value={'+'+fmtT(ba.expected_production_gain_t)+' t'} accent="var(--green)" />
          <Row label="Shortfall reduction" value={fmtT(ba.expected_shortfall_reduction_t)+' t'} accent="var(--green)" />
        </div>

        {/* impact on shortfall */}
        <div>
          <h4 style={{ marginBottom:8 }}>Impact on Shortfall</h4>
          <Row label="Before shortfall"  value={fmtT(base?.expected_shortfall_t ?? 0)+' t'} />
          <Row label="After shortfall"   value={fmtT(ba.new_expected_shortfall_t)+' t'} accent="var(--green)" />
          <Row label="Before shortfall prob." value={pct(base?.shortfall_probability ?? 0)} />
          <Row label="After shortfall prob."  value={pct(ba.new_shortfall_probability)} accent="var(--green)" />
        </div>
      </div>

      <hr className="divider" />
      <p className="text-muted text-small">
        Optimization: {nudge.optimization?.method} · Objective: {nudge.optimization?.objective?.replace(/_/g,' ')}
        · {nudge.optimization?.candidates_evaluated} candidates evaluated.
      </p>
      <p className="text-muted text-small mt-sm">
        Decision-support only — not autonomous mine control. Based on synthetic DEMO-01 data.
      </p>
    </div>
  )
}

function Row({ label, value, accent }) {
  return (
    <div className="flex-between" style={{ marginBottom:6 }}>
      <span className="text-muted text-small">{label}</span>
      <span style={{ fontWeight:600, color: accent ?? 'var(--text-primary)', fontSize:'0.9rem' }}>{value}</span>
    </div>
  )
}
