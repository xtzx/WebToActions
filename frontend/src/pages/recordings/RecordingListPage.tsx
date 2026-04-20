import { useEffect, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { fetchRecordings } from '../../services/recordings';
import type { RecordingSummary } from '../../types/recording';

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

const titleRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: '16px',
  flexWrap: 'wrap'
};

const buttonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '12px 16px',
  borderRadius: '12px',
  background: '#2247a5',
  color: '#ffffff',
  textDecoration: 'none',
  fontWeight: 700
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: '16px',
  marginTop: '20px'
};

const itemStyle: CSSProperties = {
  display: 'grid',
  gap: '10px',
  padding: '18px',
  borderRadius: '16px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

const itemMetaStyle: CSSProperties = {
  margin: 0,
  color: '#475467',
  lineHeight: 1.6
};

const linkStyle: CSSProperties = {
  color: '#2247a5',
  fontWeight: 700,
  textDecoration: 'none'
};

export function RecordingListPage() {
  const [items, setItems] = useState<RecordingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetchRecordings();
        if (!cancelled) {
          setItems(response.items);
          setErrorMessage(null);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : '录制列表加载失败。'
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

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <div style={titleRowStyle}>
          <div>
            <h1 style={{ margin: 0 }}>录制中心</h1>
            <p style={{ marginBottom: 0, color: '#475467' }}>
              查看已有录制，并从这里进入新的录制流程。
            </p>
          </div>
          <Link to="/recordings/new" style={buttonStyle}>
            新建录制
          </Link>
        </div>

        {loading ? <p style={itemMetaStyle}>正在加载录制列表...</p> : null}
        {errorMessage ? (
          <ErrorState message={errorMessage} title="录制列表加载失败" />
        ) : null}

        {!loading && !errorMessage ? (
          <div style={listStyle}>
            {items.length > 0 ? (
              items.map((item) => (
                <article key={item.id} style={itemStyle}>
                  <Link to={`/recordings/${item.id}`} style={linkStyle}>
                    {item.name}
                  </Link>
                  <p style={itemMetaStyle}>录制状态：{item.status}</p>
                  <p style={itemMetaStyle}>当前页面：{item.currentUrl}</p>
                  <p style={itemMetaStyle}>
                    请求数：{item.requestCount}，页面阶段：{item.pageStageCount}，文件传输：
                    {item.fileTransferCount}
                  </p>
                </article>
              ))
            ) : (
              <EmptyState message="还没有录制，先创建第一条录制。" />
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}
