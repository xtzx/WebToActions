import { useEffect, useState, type CSSProperties } from 'react';

import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { createSession, fetchSessions } from '../../services/sessions';
import type { BrowserSessionSummary } from '../../types/session';

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
  padding: '28px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const buttonStyle: CSSProperties = {
  border: 0,
  borderRadius: '12px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontWeight: 700,
  cursor: 'pointer'
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: '14px',
  marginTop: '20px'
};

const itemStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '16px',
  borderRadius: '14px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

export function SessionListPage() {
  const [items, setItems] = useState<BrowserSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetchSessions();
        if (!cancelled) {
          setItems(response.items);
          setErrorMessage(null);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : '会话列表加载失败。'
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreateSession() {
    setCreating(true);
    try {
      const session = await createSession();
      setItems((current) => [session, ...current]);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '创建会话失败。');
    } finally {
      setCreating(false);
    }
  }

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <h1 style={{ marginTop: 0 }}>会话管理</h1>
        <p style={{ color: '#475467' }}>
          查看受控浏览器会话，并在必要时创建新的隔离会话。若导入会话显示
          `relogin_required` 或 `expired`，请创建新的可用会话继续录制或执行。
        </p>
        <button
          type="button"
          style={{
            ...buttonStyle,
            opacity: creating ? 0.72 : 1,
            cursor: creating ? 'progress' : 'pointer'
          }}
          onClick={() => void handleCreateSession()}
          disabled={creating}
        >
          {creating ? '创建中...' : '创建新会话'}
        </button>

        {loading ? <p>正在加载会话列表...</p> : null}
        {errorMessage ? <ErrorState message={errorMessage} title="会话列表加载失败" /> : null}

        {!loading && !errorMessage ? (
          <div style={listStyle}>
            {items.length > 0 ? (
              items.map((item) => (
                <div key={item.id} style={itemStyle}>
                  <strong>{item.id}</strong>
                  <span>状态：{item.status}</span>
                  <span>
                    已登录站点：
                    {item.loginSiteSummaries.length > 0
                      ? item.loginSiteSummaries.join(', ')
                      : '暂无'}
                  </span>
                </div>
              ))
            ) : (
              <EmptyState message="当前还没有会话，先创建一个新的浏览器会话。" />
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}
