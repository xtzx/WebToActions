import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { startRecording } from '../../services/recordings';
import { fetchSessions } from '../../services/sessions';
import type { BrowserSessionSummary } from '../../types/session';

const containerStyle: CSSProperties = {
  width: '100%',
  maxWidth: '860px',
  display: 'grid',
  gap: '24px'
};

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '20px',
  padding: '28px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const formStyle: CSSProperties = {
  display: 'grid',
  gap: '18px',
  marginTop: '20px'
};

const fieldStyle: CSSProperties = {
  display: 'grid',
  gap: '8px'
};

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: '12px',
  border: '1px solid #cbd5e1',
  fontSize: '14px'
};

const rowStyle: CSSProperties = {
  display: 'flex',
  gap: '12px',
  flexWrap: 'wrap'
};

const primaryButtonStyle: CSSProperties = {
  border: 0,
  borderRadius: '12px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontWeight: 700,
  cursor: 'pointer'
};

const secondaryLinkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '12px 16px',
  borderRadius: '12px',
  border: '1px solid #cbd5e1',
  color: '#344054',
  textDecoration: 'none'
};

export function NewRecordingPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [startUrl, setStartUrl] = useState('');
  const [browserSessionId, setBrowserSessionId] = useState('');
  const [sessions, setSessions] = useState<BrowserSessionSummary[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      try {
        const response = await fetchSessions();
        if (!cancelled) {
          setSessions(response.items);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : '会话列表加载失败。'
          );
        }
      }
    }

    void loadSessions();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const summary = await startRecording({
        name,
        startUrl,
        ...(browserSessionId ? { browserSessionId } : {})
      });
      navigate(`/recordings/${summary.id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '开始录制失败。');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <h1 style={{ marginTop: 0 }}>新建录制</h1>
        <p style={{ color: '#475467' }}>
          指定录制名称、起始 URL 和浏览器会话后，就会直接进入录制详情页。
        </p>

        <form style={formStyle} onSubmit={(event) => void handleSubmit(event)}>
          <label style={fieldStyle}>
            <span>录制名称</span>
            <input
              aria-label="录制名称"
              style={inputStyle}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：提交报销单"
              required
            />
          </label>

          <label style={fieldStyle}>
            <span>起始 URL</span>
            <input
              aria-label="起始 URL"
              style={inputStyle}
              value={startUrl}
              onChange={(event) => setStartUrl(event.target.value)}
              placeholder="https://example.com/expense/new"
              required
            />
          </label>

          <label style={fieldStyle}>
            <span>浏览器会话</span>
            <select
              aria-label="浏览器会话"
              style={inputStyle}
              value={browserSessionId}
              onChange={(event) => setBrowserSessionId(event.target.value)}
            >
              <option value="">自动创建新会话</option>
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.id}
                </option>
              ))}
            </select>
          </label>

          <div style={rowStyle}>
            <button
              type="submit"
              style={{
                ...primaryButtonStyle,
                opacity: submitting ? 0.72 : 1,
                cursor: submitting ? 'progress' : 'pointer'
              }}
              disabled={submitting}
            >
              {submitting ? '启动中...' : '开始录制'}
            </button>
            <Link to="/recordings" style={secondaryLinkStyle}>
              返回录制列表
            </Link>
          </div>
        </form>

        {errorMessage ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>{errorMessage}</p>
        ) : null}
      </div>
    </section>
  );
}
