import React, { useCallback, useEffect, useState } from 'react'
import Header        from '../components/Header.jsx'
import PipelineStrip from '../components/PipelineStrip.jsx'
import OverviewPanel from '../components/OverviewPanel.jsx'
import PrismView     from '../components/PrismView.jsx'
import EarView       from '../components/EarView.jsx'
import PulseView     from '../components/PulseView.jsx'
import NudgeView     from '../components/NudgeView.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBanner   from '../components/ErrorBanner.jsx'
import {
  getOverview, getPulse, getRisk, getShap, getNudge, getNudgeCandidates,
} from '../services/api.js'

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [data,    setData]    = useState(null)
  const [stage,   setStage]   = useState('overview')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [overview, pulse, risk, shap, nudge, nudgeCands] = await Promise.all([
        getOverview(), getPulse(), getRisk(), getShap(), getNudge(), getNudgeCandidates(),
      ])
      setData({ overview, pulse, risk, shap, nudge, nudgeCands })
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <>
      <Header onRefresh={load} loading={loading} />

      <main className="page-wrapper">
        {/* Synthetic data disclaimer — visible but subtle */}
        <div role="note" aria-label="Demo disclaimer" style={{
          background: 'rgba(210,153,34,.06)', border: '1px solid rgba(210,153,34,.2)',
          borderRadius: 'var(--radius-sm)', padding: '6px 12px',
          fontSize: '0.75rem', color: 'rgba(210,153,34,.8)', marginBottom: 'var(--gap-md)',
        }}>
          Demo Mode — Synthetic DEMO-01 data. Not actual MOIL operational data.
        </div>

        {loading && !data && <LoadingSpinner />}
        {error   && !data && <ErrorBanner error={error} onRetry={load} />}

        {data && (
          <>
            <PipelineStrip activeStage={stage} onSelect={setStage} />

            {stage === 'overview' && (
              <OverviewPanel
                overview={data.overview}
                onNavigate={setStage}
              />
            )}

            {stage === 'prism' && (
              <PrismView prism={data.overview?.prism} />
            )}

            {stage === 'ear' && (
              <EarView ear={data.overview?.ear} />
            )}

            {stage === 'pulse' && (
              <PulseView
                pulse={data.pulse}
                risk={data.risk}
                shap={data.shap}
              />
            )}

            {stage === 'nudge' && (
              <NudgeView
                nudge={data.nudge}
                nudgeCands={data.nudgeCands}
              />
            )}
          </>
        )}
      </main>
    </>
  )
}
