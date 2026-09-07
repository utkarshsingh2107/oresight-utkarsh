import React from 'react'
import { fmtT, fmtPct, formatFeatureValue } from '../utils/labels.js'

export default function NudgeView({ nudge, nudgeCands }) {
  if (!nudge?.best_action) return null

  const ba    = nudge.best_action
  const base  = nudge.baseline
  const cands = nudgeCands?.candidates ?? []

  const beforeShortfall = base?.expected_shortfall_t ?? 0
  const afterShortfall  = ba.new_expected_shortfall_t ?? 0
  const beforeProb      = base?.shortfall_probability ?? 0
  const afterProb       = ba.new_shortfall_probability ?? 0

  return (
    <div className="stage-view">
      <div style={{ marginBottom: 'var(--gap-lg)' }}>
        <div className="section-label">NUDGE — Prescriptive Optimization</div>
        <h2 style={{ marginBottom: 6 }}>What should we do to reduce the shortfall?</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 720, fontSize: '0.9rem' }}>
          NUDGE evaluates {nudge.optimization?.candidates_evaluated ?? cands.length} feasible operational interventions
          and selects the one with the greatest modelled shortfall reduction.
        </p>
      </div>

      {/* ─── Before / after ─── */}
      <div className="card card--highlight" style={{ marginBottom: 'var(--gap-lg)', borderWidth: 2 }}>
        <div className="section-label" style={{ marginBottom: 'var(--gap-md)' }}>Modelled Impact</div>
        <div className="before-after">
          {/* Before */}
          <div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 'var(--gap-sm)' }}>
              Current forecast
            </p>
            <ImpactRow label="Expected production" value={`${fmtT(base?.expected_production_t ?? 0)} t`} />
            <ImpactRow label="Expected shortfall"  value={`${fmtT(beforeShortfall)} t`}  color="var(--risk-high)" />
            <ImpactRow label="Shortfall probability" value={fmtPct(beforeProb)}            color="var(--risk-critical)" />
          </div>

          {/* Arrow */}
          <div className="arrow-col">↓</div>

          {/* After */}
          <div>
            <p style={{ fontSize: '0.75rem', color: 'var(--green)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 'var(--gap-sm)' }}>
              After intervention
            </p>
            <ImpactRow label="Expected production"  value={`${fmtT((base?.expected_production_t ?? 0) + ba.expected_production_gain_t)} t`} color="var(--green)" />
            <ImpactRow label="Expected shortfall"   value={`${fmtT(afterShortfall)} t`}   color="var(--green)" />
            <ImpactRow label="Shortfall probability" value={fmtPct(afterProb)}             color="var(--yellow)" />
          </div>
        </div>

        <div style={{ marginTop: 'var(--gap-md)', background: 'rgba(63,185,80,.08)', border: '1px solid rgba(63,185,80,.2)', borderRadius: 'var(--radius-sm)', padding: '10px 14px', textAlign: 'center' }}>
          <span style={{ fontWeight: 700, color: 'var(--green)', fontSize: '1.05rem' }}>
            +{fmtT(ba.expected_production_gain_t)} t production gain
          </span>
          <span style={{ color: 'var(--text-muted)', margin: '0 12px' }}>·</span>
          <span style={{ fontWeight: 700, color: 'var(--green)', fontSize: '1.05rem' }}>
            −{fmtT(ba.expected_shortfall_reduction_t)} t shortfall reduction
          </span>
        </div>

        <p className="text-muted text-small" style={{ marginTop: 8, textAlign: 'center', fontStyle: 'italic' }}>
          Modelled counterfactual impact — not an observed real-world result.
        </p>
      </div>

      {/* ─── Best action hero ─── */}
      <div style={{ background: 'var(--bg-card-alt)', border: '2px solid var(--accent-dim)', borderRadius: 'var(--radius-lg)', padding: 'var(--gap-lg)', marginBottom: 'var(--gap-lg)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--gap-md)', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
              ★ Recommended action
            </div>
            <h2 style={{ color: 'var(--text-primary)', marginBottom: 8 }}>{ba.action_name}</h2>
            {ba.rationale && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{ba.rationale}</p>
            )}
          </div>
          <div style={{ display: 'flex', gap: 'var(--gap-lg)', flexShrink: 0 }}>
            <InterventionStat
              label="Current"
              value={formatFeatureValue(ba.feature, ba.baseline_value)}
              sub={featureUnitHint(ba.feature)}
            />
            <div style={{ display: 'flex', alignItems: 'center', fontSize: '1.5rem', color: 'var(--green)' }}>→</div>
            <InterventionStat
              label="Recommended"
              value={formatFeatureValue(ba.feature, ba.recommended_value)}
              sub="target value"
              accent="var(--green)"
            />
          </div>
        </div>
      </div>

      {/* ─── Ranked alternatives ─── */}
      <div>
        <h3 style={{ marginBottom: 'var(--gap-md)' }}>
          All Evaluated Interventions
          <span className="text-muted text-small" style={{ marginLeft: 8, fontWeight: 400 }}>
            Ranked by expected shortfall reduction
          </span>
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
          {cands.map((c, i) => (
            <CandidateCard key={c.rank} candidate={c} isBest={i === 0} />
          ))}
        </div>
        <p className="text-muted text-small" style={{ marginTop: 'var(--gap-md)' }}>
          NUDGE evaluated each intervention independently using the PULSE model as a response surface.
          All {cands.length} candidates are feasible within historical operational bounds.
        </p>
      </div>

      {/* ─── Decision-support disclaimer ─── */}
      <div style={{ marginTop: 'var(--gap-lg)', background: 'rgba(88,166,255,.04)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: 'var(--gap-md)' }}>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Decision support only.</strong>{' '}
          NUDGE evaluates modelled counterfactual scenarios and identifies the intervention with the largest
          expected shortfall reduction. Final operational decisions remain with the mine manager.
          Results are based on synthetic DEMO-01 data and do not represent actual MOIL operational data.
        </p>
      </div>
    </div>
  )
}

function ImpactRow({ label, value, color }) {
  return (
    <div className="flex-between" style={{ marginBottom: 6 }}>
      <span className="text-muted text-small">{label}</span>
      <span style={{ fontWeight: 700, color: color ?? 'var(--text-primary)', fontSize: '0.95rem' }}>{value}</span>
    </div>
  )
}

function InterventionStat({ label, value, sub, accent }) {
  return (
    <div style={{ textAlign: 'center', minWidth: 80 }}>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: '1.4rem', fontWeight: 800, color: accent ?? 'var(--text-primary)', lineHeight: 1 }}>{value}</p>
      <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>{sub}</p>
    </div>
  )
}

function CandidateCard({ candidate: c, isBest }) {
  const gain    = c.production_gain_t
  const reduc   = c.shortfall_reduction_t
  const barW    = Math.min(reduc / 700 * 100, 100)  // 700 t ≈ max reduction

  return (
    <div className={`candidate-card${isBest ? ' candidate-card--best' : ''}`}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--gap-md)', flexWrap: 'wrap' }}>
        {/* rank badge */}
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: isBest ? 'var(--accent-dim)' : 'var(--bg-card)',
          border: `2px solid ${isBest ? 'var(--accent)' : 'var(--border)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 800, fontSize: '0.9rem', flexShrink: 0,
          color: isBest ? 'white' : 'var(--text-secondary)',
        }}>
          #{c.rank}
        </div>

        {/* action details */}
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: isBest ? 700 : 600, fontSize: '0.95rem' }}>{c.action_name}</span>
            {isBest && (
              <span style={{ fontSize: '0.7rem', background: 'var(--accent-dim)', color: 'white', padding: '2px 8px', borderRadius: 10, fontWeight: 700 }}>
                RECOMMENDED
              </span>
            )}
            <span className="badge badge--feasible" style={{ marginLeft: 'auto' }}>Feasible</span>
          </div>
          <p className="text-muted text-small">
            {formatFeatureValue(c.feature, c.baseline_value)} → {formatFeatureValue(c.feature, c.recommended_value)}
          </p>
        </div>

        {/* impact numbers */}
        <div style={{ display: 'flex', gap: 'var(--gap-lg)', flexShrink: 0, flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Production gain</p>
            <p style={{ fontWeight: 700, color: 'var(--green)' }}>+{fmtT(gain)} t</p>
          </div>
          <div style={{ textAlign: 'right', minWidth: 100 }}>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Shortfall reduction</p>
            <p style={{ fontWeight: 700, color: 'var(--green)' }}>−{fmtT(reduc)} t</p>
          </div>
        </div>
      </div>

      {/* relative impact bar */}
      <div className="progress-bar-track" style={{ height: 4, marginTop: 6 }}>
        <div className="progress-bar-fill" style={{
          width: `${barW}%`,
          background: isBest ? 'var(--accent)' : 'var(--green)',
        }} />
      </div>
    </div>
  )
}

function featureUnitHint(feature) {
  const hints = {
    fleet_availability: 'daily fleet availability',
    fleet_downtime_h:   'total downtime per day',
    development_m:      'development advance per day',
    available_workers:  'headcount on shift',
  }
  return hints[feature] ?? 'current value'
}
