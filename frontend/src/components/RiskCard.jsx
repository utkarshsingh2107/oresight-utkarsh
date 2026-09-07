import React from 'react'

const COLORS = {
  LOW:      'var(--risk-low)',
  MEDIUM:   'var(--risk-medium)',
  HIGH:     'var(--risk-high)',
  CRITICAL: 'var(--risk-critical)',
}
const DESCRIPTIONS = {
  LOW:      'Production target is unlikely to be missed.',
  MEDIUM:   'Some risk of missing the production target.',
  HIGH:     'Elevated risk of missing the production target.',
  CRITICAL: 'The current forecast indicates a high probability of missing the production target.',
}

export default function RiskCard({ risk }) {
  if (!risk) return null
  const level = risk.risk_level
  const color = COLORS[level] ?? 'var(--text-primary)'
  const prob  = (risk.overall_shortfall_probability * 100).toFixed(1)
  const fmtT  = v => Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })

  return (
    <div className="card section" style={{ borderColor: color }} aria-label="Risk card">
      <div className="flex-between section-title">
        <h2>Shortfall Risk</h2>
        <span className={`badge badge--${level.toLowerCase()}`}>{level}</span>
      </div>

      <div className="grid-2" style={{ gap:'var(--gap-lg)' }}>
        {/* big probability display */}
        <div style={{ textAlign:'center', padding:'var(--gap-md) 0' }}>
          <p style={{ fontSize:'3.5rem', fontWeight:700, lineHeight:1, color }} aria-label={`Shortfall probability ${prob} percent`}>
            {prob}%
          </p>
          <p style={{ color:'var(--text-secondary)', marginTop:8 }}>Shortfall probability</p>
          <p style={{ color, fontWeight:700, fontSize:'1.2rem', marginTop:4 }}>{level}</p>
        </div>

        {/* stats */}
        <div style={{ display:'flex', flexDirection:'column', gap:10, justifyContent:'center' }}>
          <Row label="Planned production"  value={fmtT(risk.planned_production_t)+' t'} />
          <Row label="Expected production" value={fmtT(risk.expected_production_t)+' t'} />
          <Row label="Expected shortfall"  value={fmtT(risk.expected_shortfall_t)+' t'} accent={color} />
          <Row label="Forecast horizon"    value={`${risk.forecast_horizon_days} days`} />
          <p style={{ color:'var(--text-secondary)', fontSize:'0.82rem', marginTop:4 }}>
            {DESCRIPTIONS[level] ?? ''}
          </p>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, accent }) {
  return (
    <div className="flex-between">
      <span className="text-muted text-small">{label}</span>
      <span style={{ fontWeight:600, color: accent ?? 'var(--text-primary)' }}>{value}</span>
    </div>
  )
}
