import { useState, type CSSProperties } from 'react';

import { fetchHealth, type HealthResponse } from '../services/health';

type RequestState = 'idle' | 'loading' | 'success' | 'error';

const pageStyle: CSSProperties = {
  minHeight: '100vh',
  margin: 0,
  padding: '48px 24px',
  background: '#f5f7fb',
  color: '#162033',
  fontFamily:
    'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
};

const containerStyle: CSSProperties = {
  maxWidth: '760px',
  margin: '0 auto',
  display: 'grid',
  gap: '20px'
};

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '16px',
  padding: '24px',
  boxShadow: '0 12px 40px rgba(15, 23, 42, 0.06)'
};

const badgeStyle: CSSProperties = {
  display: 'inline-block',
  padding: '6px 10px',
  borderRadius: '999px',
  background: '#e8f0ff',
  color: '#2247a5',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase'
};

const titleStyle: CSSProperties = {
  margin: '16px 0 12px',
  fontSize: '32px',
  lineHeight: 1.2
};

const textStyle: CSSProperties = {
  margin: 0,
  fontSize: '16px',
  lineHeight: 1.6,
  color: '#475467'
};

const metaRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '12px',
  marginTop: '16px'
};

const metaItemStyle: CSSProperties = {
  padding: '10px 12px',
  borderRadius: '12px',
  background: '#eef2f8',
  fontSize: '14px'
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: '12px',
  marginTop: '16px'
};

const buttonStyle: CSSProperties = {
  border: 0,
  borderRadius: '10px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
};

const statusStyle: CSSProperties = {
  fontSize: '14px',
  color: '#344054'
};

const placeholderStyle: CSSProperties = {
  marginTop: '16px',
  padding: '16px',
  borderRadius: '12px',
  border: '1px dashed #b8c4d9',
  background: '#fafcff',
  color: '#667085'
};

const outputStyle: CSSProperties = {
  marginTop: '16px',
  padding: '16px',
  borderRadius: '12px',
  background: '#0f172a',
  color: '#e2e8f0',
  overflowX: 'auto',
  fontSize: '14px',
  lineHeight: 1.5
};

const errorStyle: CSSProperties = {
  marginTop: '16px',
  color: '#b42318',
  fontSize: '14px'
};

function getStatusLabel(state: RequestState, health: HealthResponse | null) {
  if (state === 'loading') {
    return 'Checking backend health...';
  }

  if (state === 'success') {
    const status = health?.status ?? 'unknown';
    const stage = health?.stage ?? 'n/a';

    return `Backend responded with status="${status}" stage="${stage}".`;
  }

  if (state === 'error') {
    return 'Backend health check failed.';
  }

  return 'Backend health has not been checked yet.';
}

export function HomePage() {
  const [requestState, setRequestState] = useState<RequestState>('idle');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const statusLabel = getStatusLabel(requestState, health);

  async function handleHealthCheck() {
    setRequestState('loading');
    setErrorMessage(null);

    try {
      const payload = await fetchHealth();

      setHealth(payload);
      setRequestState('success');
    } catch (error) {
      setHealth(null);
      setRequestState('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'Unknown health check error.'
      );
    }
  }

  return (
    <main style={pageStyle}>
      <div style={containerStyle}>
        <section style={panelStyle}>
          <span style={badgeStyle}>Stage 0 Spike</span>
          <h1 style={titleStyle}>WebToActions Frontend Skeleton</h1>
          <p style={textStyle}>
            This page keeps the frontend spike intentionally small: verify the
            React + TypeScript + Vite shell, show current spike status, and
            reserve a place for backend integration.
          </p>
          <div style={metaRowStyle}>
            <span style={metaItemStyle}>Frontend shell: ready</span>
            <span style={metaItemStyle}>UI scope: minimal</span>
            <span style={metaItemStyle}>Backend area: health placeholder</span>
          </div>
        </section>

        <section style={panelStyle}>
          <h2 style={{ marginTop: 0 }}>Backend Health Check</h2>
          <p style={textStyle}>
            The frontend calls <code>/api/health</code>. In local development,
            Vite proxies that path to <code>http://127.0.0.1:8000</code>.
          </p>
          <div style={actionRowStyle}>
            <button
              type="button"
              style={buttonStyle}
              onClick={() => void handleHealthCheck()}
              disabled={requestState === 'loading'}
            >
              {requestState === 'loading' ? 'Checking...' : 'Run health check'}
            </button>
            <span style={statusStyle}>{statusLabel}</span>
          </div>

          {health ? (
            <pre style={outputStyle}>{JSON.stringify(health, null, 2)}</pre>
          ) : (
            <div style={placeholderStyle}>
              Health response output will appear here after the check runs.
            </div>
          )}

          {errorMessage ? <div style={errorStyle}>{errorMessage}</div> : null}
        </section>
      </div>
    </main>
  );
}
