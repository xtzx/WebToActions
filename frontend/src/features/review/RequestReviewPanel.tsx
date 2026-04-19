import type { CSSProperties } from 'react';

import type { ReviewRequestSummary } from '../../types/review';

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '20px',
  padding: '24px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: '12px',
  marginTop: '16px'
};

const itemStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '16px',
  borderRadius: '14px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

export interface RequestReviewPanelProps {
  requests: ReviewRequestSummary[];
  requestLabels: Record<string, 'ignored' | 'key' | 'noise'>;
  onLabelChange: (requestId: string, next: 'ignored' | 'key' | 'noise') => void;
}

export function RequestReviewPanel(props: RequestReviewPanelProps) {
  const { onLabelChange, requestLabels, requests } = props;

  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0 }}>请求审核</h2>
      <div style={listStyle}>
        {requests.map((item) => (
          <article key={item.id} style={itemStyle}>
            <strong>{item.id}</strong>
            <span>
              {item.requestMethod} {item.requestUrl}
            </span>
            <span>响应状态：{item.responseStatus ?? '未知'}</span>
            <label htmlFor={`request-label-${item.id}`}>
              请求分类 {item.id}
            </label>
            <select
              id={`request-label-${item.id}`}
              value={requestLabels[item.id] ?? 'ignored'}
              onChange={(event) =>
                onLabelChange(
                  item.id,
                  event.target.value as 'ignored' | 'key' | 'noise'
                )
              }
            >
              <option value="ignored">暂不处理</option>
              <option value="key">关键请求</option>
              <option value="noise">噪音请求</option>
            </select>
          </article>
        ))}
      </div>
    </section>
  );
}
