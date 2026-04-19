import type { CSSProperties } from 'react';

interface SectionPlaceholderPageProps {
  title: string;
  description: string;
}

const cardStyle: CSSProperties = {
  display: 'grid',
  gap: '16px',
  padding: '32px',
  borderRadius: '20px',
  border: '1px solid #d8e0ee',
  background: '#ffffff',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const badgeStyle: CSSProperties = {
  display: 'inline-block',
  width: 'fit-content',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#eef2ff',
  color: '#3745a5',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase'
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: '32px',
  lineHeight: 1.2,
  color: '#162033'
};

const textStyle: CSSProperties = {
  margin: 0,
  fontSize: '16px',
  lineHeight: 1.7,
  color: '#475467'
};

const noteStyle: CSSProperties = {
  padding: '16px 18px',
  borderRadius: '14px',
  background: '#f5f7fb',
  border: '1px dashed #b8c4d9',
  color: '#344054'
};

export function SectionPlaceholderPage({
  title,
  description
}: SectionPlaceholderPageProps) {
  return (
    <section style={cardStyle}>
      <span style={badgeStyle}>Stage 1 Placeholder</span>
      <h1 style={titleStyle}>{title}</h1>
      <p style={textStyle}>{description}</p>
      <div style={noteStyle}>
        阶段 1 只保留正式导航入口，后续阶段再接入真实能力。
      </div>
    </section>
  );
}
