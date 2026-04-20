import type { CSSProperties } from 'react';

interface EmptyStateProps {
  message: string;
  title?: string;
}

const containerStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '18px',
  borderRadius: '16px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee',
  color: '#344054'
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontWeight: 700
};

const textStyle: CSSProperties = {
  margin: 0,
  lineHeight: 1.6
};

export function EmptyState({ message, title = '暂无数据' }: EmptyStateProps) {
  return (
    <div style={containerStyle}>
      <p style={titleStyle}>{title}</p>
      <p style={textStyle}>{message}</p>
    </div>
  );
}
