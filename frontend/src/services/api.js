/**
 * OreSight API service layer.
 * All fetch calls go through this module — no component should import fetch directly.
 *
 * Base URL reads from VITE_API_BASE_URL env variable; falls back to localhost:8000.
 */

const BASE = import.meta.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    const msg = detail?.detail?.error ?? detail?.detail ?? `HTTP ${res.status}`
    throw new Error(msg)
  }
  return res.json()
}

export const getOverview        = () => get('/api/overview')
export const getPrism           = () => get('/api/prism')
export const getPrismBlocks     = () => get('/api/prism/blocks')
export const getEar             = () => get('/api/ear')
export const getEarBlocks       = () => get('/api/ear/blocks')
export const getPulse           = () => get('/api/pulse')
export const getRisk            = () => get('/api/risk')
export const getShap            = () => get('/api/shap')
export const getNudge           = () => get('/api/nudge')
export const getNudgeCandidates = () => get('/api/nudge/candidates')

export const API_BASE = BASE
