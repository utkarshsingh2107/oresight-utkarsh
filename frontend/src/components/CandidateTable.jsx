import React, { useState } from 'react'

const fmtT = v => Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 })

export default function CandidateTable({ candidates }) {
  const [open, setOpen] = useState(false)
  if (!candidates?.length) return null

  return (
    <div className="card section">
      <button
        onClick={() => setOpen(o => !o)}
        style={{ background:'none', border:'none', padding:0, fontSize:'1.05rem',
                 fontWeight:600, color:'var(--text-primary)', cursor:'pointer', marginBottom: open ? 'var(--gap-md)' : 0 }}
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} All Intervention Candidates ({candidates.length})
      </button>

      {open && (
        <div style={{ overflowX:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.82rem' }}>
            <thead>
              <tr style={{ borderBottom:'1px solid var(--border)', color:'var(--text-secondary)', textAlign:'left' }}>
                <Th>Rank</Th><Th>Action</Th><Th>Baseline</Th><Th>Recommended</Th>
                <Th>Gain (t)</Th><Th>Shortfall Δ (t)</Th><Th>Feasible</Th><Th>Notes</Th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.rank} style={{
                  borderBottom:'1px solid var(--border-light)',
                  background: c.rank === 1 ? 'rgba(88,166,255,.04)' : 'transparent',
                }}>
                  <Td>
                    <span style={{ fontWeight: c.rank === 1 ? 700 : 400, color: c.rank === 1 ? 'var(--accent)' : undefined }}>
                      {c.rank}
                    </span>
                  </Td>
                  <Td>{c.action_name}</Td>
                  <Td>{Number(c.baseline_value).toFixed(4)}</Td>
                  <Td>{Number(c.recommended_value).toFixed(4)}</Td>
                  <Td style={{ color:'var(--green)' }}>+{fmtT(c.production_gain_t)}</Td>
                  <Td style={{ color:'var(--green)' }}>-{fmtT(c.shortfall_reduction_t)}</Td>
                  <Td>
                    <span className={`badge badge--${c.feasible ? 'feasible' : 'critical'}`}>
                      {c.feasible ? 'Yes' : 'No'}
                    </span>
                  </Td>
                  <Td style={{ color:'var(--text-muted)' }}>{c.constraint_notes}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const Th = ({ children }) => (
  <th style={{ padding:'6px 10px', fontWeight:600, whiteSpace:'nowrap' }}>{children}</th>
)
const Td = ({ children, style }) => (
  <td style={{ padding:'7px 10px', ...style }}>{children}</td>
)
