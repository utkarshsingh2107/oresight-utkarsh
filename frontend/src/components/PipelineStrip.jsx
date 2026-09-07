import React from 'react'

const STAGES = [
  { id: 'overview', label: 'Overview',  q: 'Executive summary' },
  { id: 'prism',    label: 'PRISM',     q: 'What exists?' },
  { id: 'ear',      label: 'EAR',       q: 'What is accessible?' },
  { id: 'pulse',    label: 'PULSE',     q: 'What can we produce?' },
  { id: 'nudge',    label: 'NUDGE',     q: 'What should we do?' },
]

export default function PipelineStrip({ activeStage, onSelect }) {
  return (
    <nav aria-label="Pipeline stages" style={{
      display: 'flex', alignItems: 'stretch', gap: 0,
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)', overflow: 'hidden', marginBottom: 'var(--gap-lg)',
    }}>
      {STAGES.map((s, i) => {
        const active = activeStage === s.id
        return (
          <React.Fragment key={s.id}>
            {i > 0 && i < STAGES.length && (
              <div style={{
                width: 1, background: 'var(--border)', flexShrink: 0,
                alignSelf: 'stretch',
              }} />
            )}
            <button
              onClick={() => onSelect(s.id)}
              aria-pressed={active}
              aria-label={`Stage: ${s.label}`}
              style={{
                flex: 1, padding: '10px 12px', border: 'none',
                borderRadius: 0, textAlign: 'center', cursor: 'pointer',
                borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                backgroundColor: active ? 'rgba(88,166,255,.06)' : 'transparent',
                transition: 'background-color 0.15s',
              }}
            >
              <div style={{
                fontWeight: 700, fontSize: '0.85rem',
                color: active ? 'var(--accent)' : 'var(--text-primary)',
              }}>
                {s.label}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {s.q}
              </div>
            </button>
          </React.Fragment>
        )
      })}
    </nav>
  )
}
