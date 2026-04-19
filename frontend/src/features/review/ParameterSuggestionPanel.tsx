import type { CSSProperties } from 'react';

import type { ParameterSuggestion } from '../../types/review';

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '20px',
  padding: '24px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)'
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: '16px',
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

const inputStyle: CSSProperties = {
  borderRadius: '10px',
  border: '1px solid #cbd5e1',
  padding: '10px 12px'
};

export interface ParameterSuggestionPanelProps {
  suggestions: ParameterSuggestion[];
  fieldDescriptions: Record<string, string>;
  parameterSourceMap: Record<string, string>;
  onFieldDescriptionChange: (name: string, value: string) => void;
  onParameterSourceChange: (name: string, value: string) => void;
}

export function ParameterSuggestionPanel(props: ParameterSuggestionPanelProps) {
  const {
    fieldDescriptions,
    onFieldDescriptionChange,
    onParameterSourceChange,
    parameterSourceMap,
    suggestions
  } = props;

  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0 }}>参数建议</h2>
      <div style={listStyle}>
        {suggestions.map((item) => (
          <article key={item.name} style={itemStyle}>
            <strong>{item.name}</strong>
            <span>示例值：{item.exampleValue ?? '无'}</span>
            <span>建议理由：{item.reason ?? '无'}</span>
            <label htmlFor={`parameter-source-${item.name}`}>
              参数来源 {item.name}
            </label>
            <input
              id={`parameter-source-${item.name}`}
              style={inputStyle}
              value={parameterSourceMap[item.name] ?? ''}
              onChange={(event) =>
                onParameterSourceChange(item.name, event.target.value)
              }
            />
            <label htmlFor={`field-description-${item.name}`}>
              字段说明 {item.name}
            </label>
            <input
              id={`field-description-${item.name}`}
              style={inputStyle}
              value={fieldDescriptions[item.name] ?? ''}
              onChange={(event) =>
                onFieldDescriptionChange(item.name, event.target.value)
              }
            />
          </article>
        ))}
      </div>
    </section>
  );
}
