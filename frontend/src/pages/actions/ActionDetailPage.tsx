import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties
} from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ErrorState } from '../../components/common/ErrorState';
import { fetchActionDetail, startActionExecution } from '../../services/actions';
import { fetchSessions } from '../../services/sessions';
import type { ActionDetail, ActionParameterDefinition } from '../../types/action';
import type { BrowserSessionSummary } from '../../types/session';

const containerStyle: CSSProperties = {
  width: '100%',
  maxWidth: '1080px',
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

const summaryStyle: CSSProperties = {
  display: 'grid',
  gap: '10px',
  marginTop: '16px'
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  gap: '12px',
  flexWrap: 'wrap',
  marginTop: '20px'
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

const primaryButtonStyle: CSSProperties = {
  border: 0,
  borderRadius: '12px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontWeight: 700,
  cursor: 'pointer'
};

const fieldGridStyle: CSSProperties = {
  display: 'grid',
  gap: '14px'
};

const labelStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  color: '#344054',
  fontWeight: 600
};

const inputStyle: CSSProperties = {
  borderRadius: '10px',
  border: '1px solid #cbd5e1',
  padding: '10px 12px'
};

const readonlyInputStyle: CSSProperties = {
  ...inputStyle,
  background: '#f8fafc',
  color: '#667085'
};

const itemStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  padding: '16px',
  borderRadius: '14px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

export function ActionDetailPage() {
  const { actionId } = useParams();
  const navigate = useNavigate();
  const [action, setAction] = useState<ActionDetail | null>(null);
  const [sessions, setSessions] = useState<BrowserSessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!actionId) {
        setLoading(false);
        return;
      }

      try {
        const [actionResponse, sessionsResponse] = await Promise.all([
          fetchActionDetail(actionId),
          fetchSessions()
        ]);
        if (!cancelled) {
          const defaultAvailableSessionId =
            sessionsResponse.items.find((item) => item.status === 'available')?.id ?? '';
          setAction(actionResponse);
          setSessions(sessionsResponse.items);
          setSelectedSessionId((current) => {
            const currentSession = sessionsResponse.items.find((item) => item.id === current);
            if (currentSession?.status === 'available') {
              return currentSession.id;
            }
            return defaultAvailableSessionId;
          });
          setParameterValues(buildInitialParameterValues(actionResponse.parameterDefinitions));
          setErrorMessage(null);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '动作详情加载失败。');
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
  }, [actionId]);

  const sessionOptions = useMemo(
    () =>
      sessions.map((item) => ({
        id: item.id,
        label: `${item.id} (${item.status})`,
        available: item.status === 'available'
      })),
    [sessions]
  );

  async function handleStartExecution() {
    if (!actionId || !action) {
      return;
    }

    if (!selectedSessionId) {
      setErrorMessage('请先选择一个可用浏览器会话。');
      return;
    }

    try {
      setExecuting(true);
      const parameters = buildExecutionParameters(action.parameterDefinitions, parameterValues);
      const run = await startActionExecution(actionId, {
        browserSessionId: selectedSessionId,
        parameters
      });
      setErrorMessage(null);
      navigate(`/execution/${run.id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '执行任务发起失败。');
    } finally {
      setExecuting(false);
    }
  }

  if (loading) {
    return <section style={panelStyle}>正在加载动作详情...</section>;
  }

  if (!actionId || !action) {
    return (
      <section style={panelStyle}>
        <ErrorState message={errorMessage ?? '未找到动作详情。'} title="动作详情不可用" />
      </section>
    );
  }

  return (
    <section style={containerStyle}>
      <section style={panelStyle}>
        <span style={badgeStyle}>Stage 7 Stabilization</span>
        <h1 style={{ marginBottom: '12px' }}>动作详情</h1>
        <p style={{ margin: 0, color: '#475467' }}>{action.name}</p>
        {action.description ? <p style={{ margin: 0, color: '#475467' }}>{action.description}</p> : null}

        <div style={summaryStyle}>
          <span>录制来源：{action.recordingId}</span>
          <span>动作版本：v{action.version}</span>
          <span>动作步骤：{action.stepCount}</span>
          <span>参数数量：{action.parameterCount}</span>
          <span>
            会话要求：
            {action.sessionRequirements.length > 0
              ? action.sessionRequirements.join(', ')
              : '无'}
          </span>
        </div>

        <div style={actionRowStyle}>
          <Link to="/actions" style={secondaryLinkStyle}>
            返回动作库
          </Link>
          <Link to="/execution" style={secondaryLinkStyle}>
            查看执行中心
          </Link>
        </div>

        {errorMessage ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>{errorMessage}</p>
        ) : null}
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>执行参数</h2>
        <div style={fieldGridStyle}>
          <label style={labelStyle}>
            浏览器会话
            <select
              aria-label="浏览器会话"
              style={inputStyle}
              value={selectedSessionId}
              onChange={(event) => setSelectedSessionId(event.target.value)}
            >
              <option value="">请选择会话</option>
              {sessionOptions.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.available}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {sessionOptions.some((item) => !item.available) ? (
            <p style={{ margin: 0, color: '#667085' }}>
              仅 available 会话可直接执行；若导入会话显示 relogin_required，请先到会话管理准备新的可用会话。
            </p>
          ) : null}

          {action.parameterDefinitions.map((definition) => (
            <div key={definition.id} style={itemStyle}>
              <label style={labelStyle}>
                参数 {definition.name}
                <input
                  aria-label={`参数 ${definition.name}`}
                  style={inputStyle}
                  value={parameterValues[definition.name] ?? ''}
                  onChange={(event) =>
                    setParameterValues((previous) => ({
                      ...previous,
                      [definition.name]: event.target.value
                    }))
                  }
                />
              </label>

              <label style={labelStyle}>
                注入目标 {definition.name}
                <input
                  readOnly
                  style={readonlyInputStyle}
                  value={definition.injectionTarget}
                  aria-label={`注入目标 ${definition.name}`}
                />
              </label>
            </div>
          ))}
        </div>

        <div style={actionRowStyle}>
          <button
            type="button"
            style={{
              ...primaryButtonStyle,
              opacity: executing ? 0.72 : 1,
              cursor: executing ? 'progress' : 'pointer'
            }}
            onClick={() => void handleStartExecution()}
            disabled={executing}
          >
            {executing ? '执行中...' : '开始执行'}
          </button>
        </div>
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>动作步骤</h2>
        <div style={fieldGridStyle}>
          {action.steps.map((step) => (
            <div key={step.id} style={itemStyle}>
              <strong>{step.title}</strong>
              <span>请求方法：{step.requestMethod}</span>
              <span>请求地址：{step.requestUrl}</span>
              <span>页面阶段：{step.pageStageId ?? '未绑定'}</span>
              <span>导航目标：{step.navigateUrl ?? '沿用当前页面'}</span>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}

function buildInitialParameterValues(
  definitions: ActionParameterDefinition[]
): Record<string, string> {
  return Object.fromEntries(
    definitions.map((definition) => [
      definition.name,
      definition.defaultValue === null || definition.defaultValue === undefined
        ? ''
        : String(definition.defaultValue)
    ])
  );
}

function buildExecutionParameters(
  definitions: ActionParameterDefinition[],
  values: Record<string, string>
): Record<string, unknown> {
  return Object.fromEntries(
    definitions.flatMap((definition) => {
      const rawValue = values[definition.name] ?? '';
      const trimmedValue = rawValue.trim();

      if (trimmedValue.length === 0 && !definition.required) {
        return [];
      }

      if (trimmedValue.length === 0) {
        throw new Error(`参数 ${definition.name} 不能为空。`);
      }

      return [[definition.name, trimmedValue]];
    })
  );
}
