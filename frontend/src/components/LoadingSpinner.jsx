import React from 'react'

export default function LoadingSpinner({ message = 'Loading OreSight intelligence…' }) {
  return (
    <div style={{ textAlign: 'center', padding: '80px 24px', color: 'var(--text-secondary)' }}>
      <div aria-label="loading" style={{
        width: 40, height: 40, border: '3px solid var(--border)',
        borderTopColor: 'var(--accent)', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite', margin: '0 auto 16px',
      }} />
      <p>{message}</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
