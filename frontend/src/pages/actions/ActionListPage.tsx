import { useEffect, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { fetchActions } from '../../services/actions';
import type { ActionSummary } from '../../types/action';

const containerStyle: CSSProperties = {
  width: '100%',
  maxWidth: '960px',
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

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  width: 'fit-content',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#eef2ff',
  color: '#3745a5',
  fontWeight: 700
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: '14px',
  marginTop: '20px'
};

const itemStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '18px',
  borderRadius: '16px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

const linkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  width: 'fit-content',
  padding: '10px 14px',
  borderRadius: '12px',
  border: '1px solid #cbd5e1',
  color: '#344054',
  textDecoration: 'none'
};

export function ActionListPage() {
  const [items, setItems] = useState<ActionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetchActions();
        if (!cancelled) {
          setItems(response.items);
          setErrorMessage(null);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '动作列表加载失败。');
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

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <span style={badgeStyle}>Stage 7 Stabilization</span>
        <h1 style={{ marginBottom: '12px' }}>动作库</h1>
        <p style={{ margin: 0, color: '#475467' }}>
          查看基于已审核录制生成的动作宏，并进入参数化执行入口。
        </p>

        {loading ? <p style={{ marginTop: '20px' }}>正在加载动作列表...</p> : null}
        {errorMessage ? (
          <div style={{ marginTop: '20px' }}>
            <ErrorState message={errorMessage} title="动作列表加载失败" />
          </div>
        ) : null}

        {!loading && !errorMessage ? (
          <div style={listStyle}>
            {items.length > 0 ? (
              items.map((item) => (
                <div key={item.id} style={itemStyle}>
                  <strong>{item.name}</strong>
                  <span>录制来源：{item.recordingId}</span>
                  <span>动作步骤：{item.stepCount}</span>
                  <span>参数数量：{item.parameterCount}</span>
                  {item.description ? <span>{item.description}</span> : null}
                  <Link to={`/actions/${item.id}`} style={linkStyle}>
                    查看动作详情
                  </Link>
                </div>
              ))
            ) : (
              <EmptyState message="当前还没有动作宏，请先在审核页生成动作宏。" />
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}
