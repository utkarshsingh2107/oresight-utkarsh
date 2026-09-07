import React from 'react'

/**
 * Compact metric tile.
 * @param {string} label   — metric name
 * @param {string} value   — primary display value
 * @param {string} [sub]   — secondary line (e.g. unit or context)
 * @param {string} [accent] — CSS color override for value
 */
export default function MetricCard({ label, value, sub, accent }) {
  return (
    <div className="card" style={{ minWidth: 0 }}>
      <h4 style={{ marginBottom: 6 }}>{label}</h4>
      <p style={{
        fontSize: '1.65rem', fontWeight: 700, lineHeight: 1.1,
        color: accent ?? 'var(--text-primary)',
      }}>
        {value}
      </p>
      {sub && <p className="text-muted text-small mt-sm">{sub}</p>}
    </div>
  )
}
