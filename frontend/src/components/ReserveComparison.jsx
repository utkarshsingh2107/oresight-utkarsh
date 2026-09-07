import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, LabelList } from 'recharts'

const fmt = (n) => (n / 1e6).toFixed(2) + ' Mt'

export default function ReserveComparison({ ear }) {
  if (!ear) return null

  const declared   = ear.declared_reserve_t
  const accessible = ear.effective_accessible_reserve_t
  const ratio      = (ear.accessibility_ratio * 100).toFixed(1)

  const data = [
    { name: 'Declared Reserve',   value: declared,   fill: '#58a6ff' },
    { name: 'Accessible Reserve', value: accessible,  fill: '#3fb950' },
  ]

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="card" style={{ padding: '8px 12px', fontSize: '0.85rem' }}>
        <strong>{payload[0].name}</strong>
        <br />{fmt(payload[0].value)}
      </div>
    )
  }

  return (
    <div className="card section">
      <div className="flex-between section-title">
        <h2>Reserve Accessibility</h2>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          {ratio}% accessible
        </span>
      </div>

      <div className="grid-2" style={{ gap: 'var(--gap-lg)', alignItems: 'center' }}>
        <div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data} layout="vertical" margin={{ left: 0, right: 40 }}>
              <XAxis type="number" tickFormatter={v => (v/1e6).toFixed(0)+'M'} tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} width={140} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {data.map((d) => <Cell key={d.name} fill={d.fill} />)}
                <LabelList dataKey="value" position="right" formatter={fmt} style={{ fill: '#e6edf3', fontSize: 12 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <StatRow label="Declared Reserve"   value={fmt(declared)}   color="var(--accent)" />
          <StatRow label="Accessible Reserve" value={fmt(accessible)} color="var(--green)" />
          <StatRow label="Accessibility Ratio" value={`${ratio}%`} />
          <StatRow label="Accessible Blocks"   value={ear.accessible_blocks} />
          <StatRow label="Inaccessible Blocks" value={ear.inaccessible_blocks} color="var(--risk-high)" />
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 4 }}>
            Not all geological reserve is operationally accessible under current constraints.
          </p>
        </div>
      </div>
    </div>
  )
}

function StatRow({ label, value, color }) {
  return (
    <div className="flex-between">
      <span className="text-muted text-small">{label}</span>
      <span style={{ fontWeight: 600, color: color ?? 'var(--text-primary)', fontSize: '0.95rem' }}>{value}</span>
    </div>
  )
}
