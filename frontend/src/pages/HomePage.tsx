import { useState, type CSSProperties } from 'react';

import { fetchHealth, type HealthResponse } from '../services/health';

type RequestState = 'idle' | 'loading' | 'success' | 'error';

const containerStyle: CSSProperties = {
  width: '100%',
  maxWidth: '920px',
  display: 'grid',
  gap: '24px'
};

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '20px',
  padding: '32px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const badgeStyle: CSSProperties = {
  display: 'inline-block',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#eef2ff',
  color: '#3745a5',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  width: 'fit-content'
};

const titleStyle: CSSProperties = {
  margin: '16px 0 12px',
  fontSize: '32px',
  lineHeight: 1.2
};

const textStyle: CSSProperties = {
  margin: 0,
  fontSize: '16px',
  lineHeight: 1.7,
  color: '#475467'
};

const metaListStyle: CSSProperties = {
  marginTop: '16px'
};

const metaItemStyle: CSSProperties = {
  marginTop: '8px',
  padding: '10px 14px',
  borderRadius: '12px',
  background: '#eef2f8',
  fontSize: '14px',
  color: '#344054'
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
    return '正在检查后端健康状态...';
  }

  if (state === 'success') {
    const status = health?.status ?? 'unknown';
    const phase = health?.phase ?? 'unknown';
    const targetPython = health?.targetPython ?? 'unknown';

    return `后端响应正常，status="${status}"，phase="${phase}"，targetPython="${targetPython}"。`;
  }

  if (state === 'error') {
    return '后端健康检查失败。';
  }

  return '尚未检查后端健康状态。';
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
        error instanceof Error ? error.message : '未知健康检查错误。'
      );
    }
  }

  return (
    <div style={containerStyle}>
      <section style={panelStyle}>
        <span style={badgeStyle}>Stage 1 Skeleton</span>
        <h1 style={titleStyle}>WebToActions 管理台</h1>
        <p style={textStyle}>
          当前阶段聚焦统一配置、路由、导航、启动方式和测试基线，为后续真实业务能力接入保留正式入口。
        </p>
        <div style={metaListStyle}>
          <div style={metaItemStyle}>统一配置</div>
          <div style={metaItemStyle}>正式路由</div>
          <div style={metaItemStyle}>一级导航</div>
          <div style={metaItemStyle}>统一启动方式</div>
          <div style={metaItemStyle}>测试基线</div>
        </div>
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0, marginBottom: '12px' }}>后端健康检查</h2>
        <p style={textStyle}>
          前端通过 <code>/api/health</code> 连接正式后端契约，确认阶段 1
          骨架已经统一到新的路由和启动方式。
        </p>
        <div style={actionRowStyle}>
          <button
            type="button"
            style={{
              ...buttonStyle,
              opacity: requestState === 'loading' ? 0.72 : 1,
              cursor: requestState === 'loading' ? 'progress' : 'pointer'
            }}
            onClick={() => void handleHealthCheck()}
            disabled={requestState === 'loading'}
          >
            {requestState === 'loading' ? '检查中...' : '检查后端健康状态'}
          </button>
          <span style={statusStyle}>{statusLabel}</span>
        </div>

        {health ? (
          <pre style={outputStyle}>{JSON.stringify(health, null, 2)}</pre>
        ) : (
          <div style={placeholderStyle}>健康检查 JSON 输出会显示在这里。</div>
        )}

        {errorMessage ? <div style={errorStyle}>{errorMessage}</div> : null}
      </section>
    </div>
  );
}
