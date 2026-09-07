import React from 'react'
import { API_BASE } from '../services/api.js'

export default function ErrorBanner({ error, onRetry }) {
  return (
    <div role="alert" style={{
      background: 'rgba(248,81,73,.1)', border: '1px solid var(--risk-critical)',
      borderRadius: 'var(--radius-md)', padding: '24px', margin: '40px auto',
      maxWidth: 600, textAlign: 'center',
    }}>
      <h2 style={{ color: 'var(--risk-critical)', marginBottom: 8 }}>Unable to connect to OreSight API</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
        Backend URL: <code style={{ color: 'var(--text-primary)' }}>{API_BASE}</code>
      </p>
      {error && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>
          {String(error)}
        </p>
      )}
      <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: '0.9rem' }}>
        Make sure the backend is running:
        <br />
        <code style={{ color: 'var(--accent)', fontSize: '0.85rem' }}>
          uvicorn backend.main:app --reload
        </code>
      </p>
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  )
}
