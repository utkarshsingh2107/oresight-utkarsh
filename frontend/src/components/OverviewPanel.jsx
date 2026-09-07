import React from 'react'
import { fmtT, fmtPct } from '../utils/labels.js'

const RISK_COLORS = {
  LOW: 'var(--risk-low)', MEDIUM: 'var(--risk-medium)',
  HIGH: 'var(--risk-high)', CRITICAL: 'var(--risk-critical)',
}

export default function OverviewPanel({ overview, onNavigate }) {
  if (!overview) return null
  const p  = overview.prism
  const e  = overview.ear
  const pu = overview.pulse
  const rl = overview.risk_level
  const n  = overview.nudge
  const rc = RISK_COLORS[rl] ?? 'var(--risk-critical)'

  return (
    <div className="stage-view">
      <div style={{ marginBottom: 'var(--gap-lg)' }}>
        <h1 style={{ marginBottom: 4 }}>Mine Decision Intelligence</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          From geological reserve to the best operational action — DEMO-01, synthetic data.
        </p>
      </div>

      {/* Pipeline flow — clickable */}
      <div className="card" style={{ marginBottom: 'var(--gap-lg)', background: 'var(--bg-card-alt)' }}>
        <div style={{ display: 'flex', alignItems: 'stretch', overflowX: 'auto', gap: 0 }}>
          <FlowStage
            stage="prism" label="PRISM" question="What exists?" onClick={onNavigate}
            value={`${(p.declared_reserve_t/1e6).toFixed(2)} Mt`} sub="Declared reserve"
            color="var(--accent)"
          />
          <FlowArrow />
          <FlowStage
            stage="ear" label="EAR" question="What is accessible?" onClick={onNavigate}
            value={`${(e.effective_accessible_reserve_t/1e6).toFixed(2)} Mt`}
            sub={`${(e.accessibility_ratio*100).toFixed(0)}% accessible`}
            color="var(--green)"
          />
          <FlowArrow />
          <FlowStage
            stage="pulse" label="PULSE" question="What can we produce?" onClick={onNavigate}
            value={`${(pu.expected_production_t/1e3).toFixed(1)} kt`}
            sub={`−${fmtT(pu.expected_shortfall_t)} t shortfall`}
            color="var(--accent)"
          />
          <FlowArrow />
          <FlowStage
            stage="nudge" label="NUDGE" question="What should we do?" onClick={onNavigate}
            value={n.action_name}
            sub={`+${fmtT(n.expected_production_gain_t)} t gain`}
            color="var(--green)" isAction
          />
        </div>
      </div>

      {/* Key metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--gap-md)', marginBottom: 'var(--gap-lg)' }}>
        {/* Reserve pair */}
        <div className="card">
          <div className="section-label">Reserve</div>
          <div style={{ display: 'flex', gap: 'var(--gap-lg)', marginTop: 'var(--gap-sm)' }}>
            <div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Declared (PRISM)</p>
              <p style={{ fontWeight: 800, fontSize: '1.4rem', color: 'var(--accent)' }}>
                {(p.declared_reserve_t/1e6).toFixed(2)} Mt
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>→</div>
            <div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Accessible (EAR)</p>
              <p style={{ fontWeight: 800, fontSize: '1.4rem', color: 'var(--green)' }}>
                {(e.effective_accessible_reserve_t/1e6).toFixed(2)} Mt
              </p>
            </div>
          </div>
          <p className="text-muted text-small" style={{ marginTop: 'var(--gap-sm)' }}>
            {(e.accessibility_ratio*100).toFixed(1)}% of declared reserve is operationally accessible
          </p>
        </div>

        {/* Production forecast */}
        <div className="card">
          <div className="section-label">30-Day Production Forecast</div>
          <div style={{ marginTop: 'var(--gap-sm)' }}>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted text-small">Planned</span>
              <span style={{ fontWeight: 600 }}>{fmtT(pu.planned_production_t)} t</span>
            </div>
            <div className="flex-between" style={{ marginBottom: 6 }}>
              <span className="text-muted text-small">P50 expected</span>
              <span style={{ fontWeight: 700, color: 'var(--accent)' }}>{fmtT(pu.expected_production_t)} t</span>
            </div>
            <div className="flex-between">
              <span className="text-muted text-small">Expected shortfall</span>
              <span style={{ fontWeight: 700, color: 'var(--risk-high)' }}>−{fmtT(pu.expected_shortfall_t)} t</span>
            </div>
          </div>
        </div>

        {/* Risk */}
        <div className="card" style={{ borderColor: rc }}>
          <div className="section-label">Shortfall Risk</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 'var(--gap-sm)' }}>
            <span style={{ fontWeight: 900, fontSize: '2.2rem', color: rc, lineHeight: 1 }}>
              {fmtPct(pu.shortfall_probability)}
            </span>
            <span className={`badge badge--${rl.toLowerCase()}`} style={{ fontSize: '0.8rem', padding: '3px 10px' }}>
              {rl}
            </span>
          </div>
          <p className="text-muted text-small" style={{ marginTop: 6 }}>
            Probability of missing production target
          </p>
        </div>
      </div>

      {/* Best action CTA */}
      <div
        onClick={() => onNavigate('nudge')}
        style={{
          background: 'rgba(88,166,255,.05)', border: '1px solid var(--accent-dim)',
          borderRadius: 'var(--radius-md)', padding: 'var(--gap-md)',
          cursor: 'pointer', transition: 'background 0.15s',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--gap-md)',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(88,166,255,.1)'}
        onMouseLeave={e => e.currentTarget.style.background = 'rgba(88,166,255,.05)'}
        role="button" aria-label="View NUDGE recommendation"
      >
        <div>
          <p style={{ fontSize: '0.72rem', color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 3 }}>
            Recommended action
          </p>
          <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{n.action_name}</p>
          <p className="text-muted text-small" style={{ marginTop: 2 }}>
            Expected: +{fmtT(n.expected_production_gain_t)} t · Shortfall: −{fmtT(n.expected_shortfall_reduction_t)} t
          </p>
        </div>
        <div style={{ color: 'var(--accent)', fontSize: '1.5rem', flexShrink: 0 }}>→</div>
      </div>
    </div>
  )
}

function FlowStage({ stage, label, question, value, sub, color, isAction, onClick }) {
  return (
    <button
      onClick={() => onClick(stage)}
      style={{
        flex: 1, background: 'none', border: 'none', borderRadius: 'var(--radius-sm)',
        padding: 'var(--gap-md) var(--gap-sm)', textAlign: 'center', cursor: 'pointer',
        transition: 'background 0.15s', minWidth: 140,
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(88,166,255,.05)'}
      onMouseLeave={e => e.currentTarget.style.background = 'none'}
      aria-label={`Navigate to ${label}`}
    >
      <p style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
        {label}
      </p>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>{question}</p>
      <p style={{ fontWeight: 800, fontSize: isAction ? '0.85rem' : '1.15rem', color, lineHeight: 1.2 }}>{value}</p>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 3 }}>{sub}</p>
    </button>
  )
}

function FlowArrow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)', fontSize: '1.1rem', padding: '0 2px', flexShrink: 0 }}>
      →
    </div>
  )
}
