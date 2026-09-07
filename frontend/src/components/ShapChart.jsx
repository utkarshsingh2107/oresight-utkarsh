import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts'

const ACTIONABLE_COLOR = '#58a6ff'
const CONTEXTUAL_COLOR = '#bc8cff'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="card" style={{ padding:'10px 14px', fontSize:'0.82rem', minWidth:220 }}>
      <p style={{ fontWeight:600, marginBottom:4 }}>{d.feature}</p>
      <p>SHAP: <strong>{d.mean_absolute_shap?.toFixed(3)}</strong></p>
      <p>Direction: <strong>{d.impact_direction}</strong></p>
      <p>Type: <span className={`badge badge--${d.driver_type === 'ACTIONABLE' ? 'action' : 'context'}`}>{d.driver_type}</span></p>
    </div>
  )
}

export default function ShapChart({ shap }) {
  if (!shap?.drivers?.length) return null

  const top = shap.drivers.slice(0, 10)

  return (
    <div className="card section">
      <div className="flex-between section-title">
        <h2>Top Model Drivers</h2>
        <div className="flex-row" style={{ gap:10 }}>
          <span style={{ fontSize:'0.75rem' }}><span style={{ color: ACTIONABLE_COLOR }}>■</span> Actionable</span>
          <span style={{ fontSize:'0.75rem' }}><span style={{ color: CONTEXTUAL_COLOR }}>■</span> Contextual</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={top} layout="vertical" margin={{ left:0, right:50, top:0, bottom:0 }}>
          <XAxis type="number" tick={{ fill:'#8b949e', fontSize:10 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="feature" tick={{ fill:'#8b949e', fontSize:10 }} axisLine={false} tickLine={false} width={190} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="mean_absolute_shap" radius={[0,4,4,0]}>
            {top.map(d => (
              <Cell key={d.feature} fill={d.driver_type === 'ACTIONABLE' ? ACTIONABLE_COLOR : CONTEXTUAL_COLOR} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <p className="text-muted text-small mt-md">
        SHAP shows model contribution — not proof of causality. Top 10 of {shap.count} features shown.
      </p>
    </div>
  )
}
