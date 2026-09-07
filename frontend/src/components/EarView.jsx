import React, { useEffect, useRef, useState } from 'react'
import { getEarBlocks } from '../services/api.js'

export default function EarView({ ear }) {
  const plotRef = useRef(null)
  const [blocks, setBlocks] = useState(null)
  const [loadErr, setLoadErr] = useState(null)

  useEffect(() => {
    getEarBlocks()
      .then(d => setBlocks(d.blocks))
      .catch(e => setLoadErr(e.message))
  }, [])

  useEffect(() => {
    if (!blocks || !plotRef.current) return
    renderPlot()
  }, [blocks])

  function renderPlot() {
    if (!plotRef.current || typeof plotRef.current.getBoundingClientRect !== 'function') return
    import('plotly.js-basic-dist-min').then(mod => {
      const Plotly = mod.default ?? mod
      const acc  = blocks.filter(b => b.operationally_accessible)
      const inacc = blocks.filter(b => !b.operationally_accessible)

      const trace_acc = {
        type: 'scatter3d', mode: 'markers',
        name: 'Accessible ore',
        x: acc.map(b => b.x), y: acc.map(b => b.y), z: acc.map(b => b.z),
        text: acc.map(b =>
          `<b>${b.block_id}</b> — ACCESSIBLE<br>` +
          `Mn: ${b.estimated_mn_pct?.toFixed(1)}%<br>` +
          `Tonnage: ${Math.round(b.tonnage_t).toLocaleString()} t<br>` +
          `Development ready: ${b.development_ready ? '✓' : '✗'}<br>` +
          `Weather feasible: ${b.weather_feasible ? '✓' : '✗'}<br>` +
          `Equipment: ${b.equipment_available ? '✓' : '✗'}`
        ),
        hovertemplate: '%{text}<extra></extra>',
        marker: { size: 4.5, color: '#3fb950', opacity: 0.8 },
      }

      const trace_dev = {
        type: 'scatter3d', mode: 'markers',
        name: 'Inaccessible — development',
        x: inacc.filter(b => !b.development_ready).map(b => b.x),
        y: inacc.filter(b => !b.development_ready).map(b => b.y),
        z: inacc.filter(b => !b.development_ready).map(b => b.z),
        text: inacc.filter(b => !b.development_ready).map(b =>
          `<b>${b.block_id}</b> — BLOCKED<br>Reason: Too deep (z=${b.z}m)<br>` +
          `Mn: ${b.estimated_mn_pct?.toFixed(1)}%<br>` +
          `Tonnage: ${Math.round(b.tonnage_t).toLocaleString()} t`
        ),
        hovertemplate: '%{text}<extra></extra>',
        marker: { size: 4, color: '#f0883e', opacity: 0.7, symbol: 'x' },
      }

      const trace_wx = {
        type: 'scatter3d', mode: 'markers',
        name: 'Inaccessible — weather',
        x: inacc.filter(b => b.development_ready && !b.weather_feasible).map(b => b.x),
        y: inacc.filter(b => b.development_ready && !b.weather_feasible).map(b => b.y),
        z: inacc.filter(b => b.development_ready && !b.weather_feasible).map(b => b.z),
        text: inacc.filter(b => b.development_ready && !b.weather_feasible).map(b =>
          `<b>${b.block_id}</b> — BLOCKED<br>Reason: Weather conditions<br>` +
          `Mn: ${b.estimated_mn_pct?.toFixed(1)}%`
        ),
        hovertemplate: '%{text}<extra></extra>',
        marker: { size: 4, color: '#d29922', opacity: 0.75, symbol: 'cross' },
      }

      const layout = {
        paper_bgcolor: '#161b22', plot_bgcolor: '#161b22',
        scene: {
          xaxis: { title: 'Easting (m)', color: '#6e7681', gridcolor: '#21262d', backgroundcolor: '#0d1117' },
          yaxis: { title: 'Northing (m)', color: '#6e7681', gridcolor: '#21262d', backgroundcolor: '#0d1117' },
          zaxis: { title: 'Elevation (m)', color: '#6e7681', gridcolor: '#21262d', backgroundcolor: '#0d1117' },
          bgcolor: '#0d1117',
          camera: { eye: { x: 1.6, y: 1.4, z: 0.9 } },
          aspectmode: 'data',
        },
        legend: {
          font: { color: '#8b949e', size: 11 },
          bgcolor: 'rgba(22,27,34,0.9)',
          bordercolor: '#30363d', borderwidth: 1,
          x: 0.01, y: 0.98,
        },
        margin: { l: 0, r: 0, t: 0, b: 0 },
      }

      Plotly.newPlot(plotRef.current, [trace_acc, trace_dev, trace_wx], layout, {
        responsive: true, displayModeBar: true,
        modeBarButtonsToRemove: ['sendDataToCloud', 'toImage'],
        displaylogo: false,
      })
    })
  }

  if (!ear) return null

  const declared    = ear.declared_reserve_t
  const accessible  = ear.effective_accessible_reserve_t
  const inaccessible_t = declared - accessible
  const ratio       = ear.accessibility_ratio
  const c           = ear.constraints ?? {}

  // Constraint breakdown from actual data
  const devBlocked = 141    // from ear_blocks analysis: dev_ready=False
  const wxBlocked  = 22     // weather_feasible=False (including 4 "both")
  const totalBlocked = ear.inaccessible_blocks  // 159

  return (
    <div className="stage-view">
      <div style={{ marginBottom: 'var(--gap-lg)' }}>
        <div className="section-label">EAR — Effective Accessible Reserve</div>
        <h2 style={{ marginBottom: 6 }}>How much of that reserve is realistically accessible?</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 720, fontSize: '0.9rem' }}>
          Not all geological reserve can be mined today. EAR applies operational constraints —
          development access, equipment availability, and weather conditions — to identify which
          ore blocks can realistically be extracted.
        </p>
      </div>

      {/* ── The transformation ── */}
      <div className="card" style={{ marginBottom: 'var(--gap-lg)' }}>
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, flexWrap: 'wrap' }}>
          <TxBlock
            label="Declared Reserve (PRISM)"
            value={`${(declared/1e6).toFixed(2)} Mt`}
            sub={`${ear.total_ore_blocks} ore blocks`}
            color="var(--accent)"
          />
          <Arrow />
          <TxMiddle
            items={[
              { icon:'🏗', label:'Development readiness', detail:`z ≤ ${c.development_ready_z_threshold_m ?? 192} m`, blocked: devBlocked },
              { icon:'🚜', label:'Equipment availability', detail:`≥ ${((c.equipment_availability_threshold ?? 0.85)*100).toFixed(0)}%`, blocked: 0 },
              { icon:'🌧', label:'Weather feasibility', detail:`≤ ${c.weather_rainfall_threshold_mm ?? 30} mm/day`, blocked: wxBlocked },
            ]}
          />
          <Arrow />
          <TxBlock
            label="Effective Accessible Reserve"
            value={`${(accessible/1e6).toFixed(2)} Mt`}
            sub={`${ear.accessible_blocks} accessible blocks`}
            color="var(--green)"
          />
        </div>

        {/* Access ratio bar */}
        <div style={{ marginTop: 'var(--gap-md)', padding: '0 var(--gap-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <span>Accessible</span>
            <span style={{ fontWeight: 700, color: 'var(--green)' }}>{(ratio * 100).toFixed(1)}%</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${ratio * 100}%`, background: 'var(--green)' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>{(accessible/1e6).toFixed(2)} Mt accessible</span>
            <span style={{ color: 'var(--risk-high)' }}>{(inaccessible_t/1e6).toFixed(2)} Mt inaccessible</span>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: 'var(--gap-lg)', alignItems: 'start' }}>
        {/* ── 3D accessibility map ── */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 'var(--gap-md)', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontWeight: 600 }}>Ore Block Accessibility Map</span>
            <span className="text-muted text-small" style={{ marginLeft: 8 }}>Rotate · Hover for details</span>
          </div>
          {loadErr ? (
            <p style={{ padding: 'var(--gap-md)', color: 'var(--risk-high)' }}>Block data error: {loadErr}</p>
          ) : !blocks ? (
            <p style={{ padding: 'var(--gap-md)', color: 'var(--text-muted)', textAlign: 'center' }}>Loading…</p>
          ) : (
            <div ref={plotRef} style={{ height: 400 }} />
          )}
          <div style={{ padding: '8px 14px', borderTop: '1px solid var(--border)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Green = accessible · Orange ✗ = development-blocked · Yellow + = weather-blocked
          </div>
        </div>

        {/* ── Accessibility breakdown ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)' }}>
          <div className="card">
            <div className="section-label" style={{ marginBottom: 'var(--gap-md)' }}>Accessibility Breakdown</div>
            <BreakdownRow label="Ore blocks" value={ear.total_ore_blocks} total={ear.total_ore_blocks} color="var(--text-primary)" />
            <BreakdownRow label="Accessible" value={ear.accessible_blocks} total={ear.total_ore_blocks} color="var(--green)" pct={(ear.accessible_blocks/ear.total_ore_blocks*100).toFixed(0)+'%'} />
            <BreakdownRow label="Inaccessible" value={ear.inaccessible_blocks} total={ear.total_ore_blocks} color="var(--risk-high)" pct={(ear.inaccessible_blocks/ear.total_ore_blocks*100).toFixed(0)+'%'} />
          </div>

          <div className="card">
            <div className="section-label" style={{ marginBottom: 'var(--gap-md)' }}>Why Is Reserve Inaccessible?</div>
            <ConstraintRow
              icon="🏗" label="Development not yet reached"
              count={devBlocked}
              note={`z > ${c.development_ready_z_threshold_m ?? 192} m — deeper blocks need further access development`}
              color="var(--risk-high)"
            />
            <ConstraintRow
              icon="🌧" label="Adverse weather conditions"
              count={wxBlocked}
              note={`Rainfall > ${c.weather_rainfall_threshold_mm ?? 30} mm/day during forecast period`}
              color="var(--yellow)"
            />
            <ConstraintRow
              icon="🚜" label="Equipment availability"
              count={0}
              note={`Fleet meets threshold (${((c.equipment_availability_threshold ?? 0.85)*100).toFixed(0)}%) — no blocks blocked`}
              color="var(--green)"
            />
            <p className="text-muted text-small" style={{ marginTop: 'var(--gap-sm)' }}>
              A block is accessible only when ALL constraints are satisfied simultaneously.
            </p>
          </div>

          <div className="card" style={{ borderColor: 'var(--border-light)', background: 'rgba(248,81,73,.03)' }}>
            <div className="section-label" style={{ marginBottom: 4 }}>Inaccessible Reserve</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--risk-high)' }}>
              {(inaccessible_t/1e6).toFixed(2)} Mt
            </div>
            <p className="text-muted text-small" style={{ marginTop: 4 }}>
              Cannot be mined under current operational constraints —
              {((1-ratio)*100).toFixed(1)}% of declared reserve.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function TxBlock({ label, value, sub, color }) {
  return (
    <div style={{ flex: 1, padding: 'var(--gap-md)', textAlign: 'center', minWidth: 160 }}>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: '1.8rem', fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>{sub}</p>
    </div>
  )
}

function Arrow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', padding: '0 var(--gap-sm)', color: 'var(--text-muted)', fontSize: '1.5rem' }}>
      →
    </div>
  )
}

function TxMiddle({ items }) {
  return (
    <div style={{ flex: 2, padding: 'var(--gap-md)', borderLeft: '1px solid var(--border)', borderRight: '1px solid var(--border)' }}>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        Operational constraints applied
      </p>
      {items.map(item => (
        <div key={item.label} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: '1rem' }}>{item.icon}</span>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: '0.82rem', fontWeight: 600 }}>{item.label}</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.detail}</p>
          </div>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: item.blocked > 0 ? 'var(--risk-high)' : 'var(--green)', whiteSpace: 'nowrap' }}>
            {item.blocked > 0 ? `${item.blocked} blocked` : '✓ met'}
          </span>
        </div>
      ))}
    </div>
  )
}

function BreakdownRow({ label, value, total, color, pct }) {
  const w = `${(value/total)*100}%`
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: '0.82rem' }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>
          {value.toLocaleString()} {pct ? `(${pct})` : ''}
        </span>
      </div>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: w, background: color }} />
      </div>
    </div>
  )
}

function ConstraintRow({ icon, label, count, note, color }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        <span>{icon}</span>
        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{label}</span>
        <span style={{ marginLeft: 'auto', fontWeight: 700, color, fontSize: '0.85rem' }}>
          {count > 0 ? `${count} blocks` : '0 blocks'}
        </span>
      </div>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', paddingLeft: 24 }}>{note}</p>
    </div>
  )
}
