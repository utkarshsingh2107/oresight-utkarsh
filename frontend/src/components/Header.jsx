import React from 'react'

export default function Header({ onRefresh, loading }) {
  return (
    <header style={{
      background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
      padding: '0 var(--gap-lg)', marginBottom: 'var(--gap-lg)',
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div className="flex-between page-wrapper" style={{ padding: '14px var(--gap-lg)', maxWidth: 1400 }}>
        <div>
          <div className="flex-row" style={{ gap: 10 }}>
            <span style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent)' }}>OreSight</span>
            <span style={{
              fontSize: '0.7rem', background: 'rgba(88,166,255,.15)',
              color: 'var(--accent)', padding: '2px 7px', borderRadius: 4, fontWeight: 600,
            }}>MVP</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: 1 }}>
            Mine Decision Intelligence — PRISM · EAR · PULSE · RISK · NUDGE
          </p>
        </div>
        <button onClick={onRefresh} disabled={loading} aria-label="Refresh data">
          {loading ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>
    </header>
  )
}
