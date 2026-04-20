import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties
} from 'react';
import { Link, useParams } from 'react-router-dom';

import { ErrorState } from '../../components/common/ErrorState';
import { subscribeToExecutionStream } from '../../services/events/sseClient';
import { fetchExecutionDetail } from '../../services/executions';
import type {
  ExecutionRunDetail,
  ExecutionStepOutcome,
  ExecutionStreamSnapshot
} from '../../types/execution';

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

export function ExecutionDetailPage() {
  const { executionId } = useParams();
  const [detail, setDetail] = useState<ExecutionRunDetail | null>(null);
  const [liveSnapshot, setLiveSnapshot] = useState<ExecutionStreamSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [streamAttempt, setStreamAttempt] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const subscriptionRef = useRef<{ close: () => void } | null>(null);
  const retryTimerRef = useRef<number | null>(null);

  const loadDetail = useCallback(
    async (options?: { preserveLoading?: boolean }) => {
      if (!executionId) {
        return;
      }

      if (!options?.preserveLoading) {
        setLoading(true);
      }

      try {
        const response = await fetchExecutionDetail(executionId);
        if (retryTimerRef.current !== null) {
          window.clearTimeout(retryTimerRef.current);
          retryTimerRef.current = null;
        }
        setDetail(response);
        setErrorMessage(null);
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : '执行详情加载失败。');
      } finally {
        if (!options?.preserveLoading) {
          setLoading(false);
        }
      }
    },
    [executionId]
  );

  const scheduleReconnect = useCallback(() => {
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
    }

    retryTimerRef.current = window.setTimeout(() => {
      retryTimerRef.current = null;
      setStreamAttempt((current) => current + 1);
    }, 1000);
  }, []);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    subscriptionRef.current?.close();
    subscriptionRef.current = null;

    if (!executionId || !detail || isTerminalStatus(detail.status)) {
      return;
    }

    const subscription = subscribeToExecutionStream(
      executionId,
      (snapshot) => {
        if (retryTimerRef.current !== null) {
          window.clearTimeout(retryTimerRef.current);
          retryTimerRef.current = null;
        }
        setLiveSnapshot(snapshot);
        void loadDetail({ preserveLoading: true });
      },
      () => {
        setErrorMessage('执行状态流已中断，正在重新获取最新状态。');
        void loadDetail({ preserveLoading: true });
        scheduleReconnect();
      }
    );
    subscriptionRef.current = subscription;

    return () => {
      subscription.close();
    };
  }, [detail, executionId, loadDetail, scheduleReconnect, streamAttempt]);

  useEffect(() => {
    return () => {
      if (retryTimerRef.current !== null) {
        window.clearTimeout(retryTimerRef.current);
      }
    };
  }, []);

  const effectiveStatus = liveSnapshot?.status ?? detail?.status ?? 'unknown';
  const diagnostics = detail?.diagnostics ?? {};
  const stepOutcomes = useMemo(
    () => normalizeStepOutcomes(diagnostics.stepOutcomes),
    [diagnostics.stepOutcomes]
  );

  if (loading) {
    return <section style={panelStyle}>正在加载执行详情...</section>;
  }

  if (!executionId || !detail) {
    return (
      <section style={panelStyle}>
        <ErrorState message={errorMessage ?? '未找到执行详情。'} title="执行详情不可用" />
      </section>
    );
  }

  return (
    <section style={containerStyle}>
      <section style={panelStyle}>
        <span style={badgeStyle}>Stage 7 Stabilization</span>
        <h1 style={{ marginBottom: '12px' }}>执行详情</h1>
        <p style={{ margin: 0, color: '#475467' }}>执行任务：{detail.id}</p>

        <div style={summaryStyle}>
          <span>执行状态：{effectiveStatus}</span>
          <span>动作来源：{detail.actionId}</span>
          <span>浏览器会话：{detail.browserSessionId}</span>
          {diagnostics.currentStepTitle ? (
            <span>当前步骤：{diagnostics.currentStepTitle}</span>
          ) : null}
          {detail.failureReason ? <span>失败原因：{detail.failureReason}</span> : null}
          {diagnostics.finalUrl ? <span>最终页面：{diagnostics.finalUrl}</span> : null}
          {!diagnostics.finalUrl && diagnostics.currentUrl ? (
            <span>当前页面：{diagnostics.currentUrl}</span>
          ) : null}
        </div>

        <div style={actionRowStyle}>
          <Link to="/execution" style={secondaryLinkStyle}>
            返回执行中心
          </Link>
          <Link to={`/actions/${detail.actionId}`} style={secondaryLinkStyle}>
            返回动作详情
          </Link>
        </div>

        {errorMessage ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>{errorMessage}</p>
        ) : null}
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>执行日志</h2>
        <div style={listStyle}>
          {detail.stepLogs.length > 0 ? (
            detail.stepLogs.map((log, index) => (
              <div key={`${index + 1}-${log}`} style={itemStyle}>
                <span>{log}</span>
              </div>
            ))
          ) : (
            <div style={itemStyle}>当前还没有执行日志。</div>
          )}
        </div>
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>步骤结果</h2>
        <div style={listStyle}>
          {stepOutcomes.length > 0 ? (
            stepOutcomes.map((item) => (
              <div key={`${item.stepId}-${item.requestId ?? 'none'}`} style={itemStyle}>
                <strong>{item.stepId}</strong>
                <span>请求 ID：{item.requestId ?? '无'}</span>
                <span>响应状态：{item.responseStatus ?? '未知'}</span>
                {item.requestBodyPreview ? (
                  <span>请求体预览：{item.requestBodyPreview}</span>
                ) : null}
              </div>
            ))
          ) : (
            <div style={itemStyle}>当前还没有步骤结果。</div>
          )}
        </div>
      </section>
    </section>
  );
}

function isTerminalStatus(status: string) {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled';
}

function normalizeStepOutcomes(value: unknown): ExecutionStepOutcome[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isExecutionStepOutcome);
}

function isExecutionStepOutcome(value: unknown): value is ExecutionStepOutcome {
  if (!value || typeof value !== 'object') {
    return false;
  }

  return 'stepId' in value;
}
