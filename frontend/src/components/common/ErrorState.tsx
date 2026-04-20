import type { CSSProperties } from 'react';

interface ErrorStateProps {
  message: string;
  title?: string;
}

const containerStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '16px 18px',
  borderRadius: '14px',
  background: '#fef3f2',
  border: '1px solid #fecdca',
  color: '#b42318'
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontWeight: 700
};

const textStyle: CSSProperties = {
  margin: 0,
  lineHeight: 1.6
};

export function ErrorState({ message, title = '加载失败' }: ErrorStateProps) {
  return (
    <div style={containerStyle} role="alert">
      <p style={titleStyle}>{title}</p>
      <p style={textStyle}>{message}</p>
    </div>
  );
}
