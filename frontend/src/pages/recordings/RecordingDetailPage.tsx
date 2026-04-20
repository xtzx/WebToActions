import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties
} from 'react';
import { Link, useParams } from 'react-router-dom';

import { subscribeToRecordingStream } from '../../services/events/sseClient';
import {
  fetchRecordingDetail,
  stopRecording
} from '../../services/recordings';
import type {
  RecordingDetail,
  RecordingStreamSnapshot
} from '../../types/recording';

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

const infoListStyle: CSSProperties = {
  display: 'grid',
  gap: '10px',
  marginTop: '20px'
};

const chipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#eef2ff',
  color: '#3745a5',
  fontWeight: 700,
  width: 'fit-content'
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  gap: '12px',
  flexWrap: 'wrap',
  marginTop: '20px'
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

export function RecordingDetailPage() {
  const { recordingId } = useParams();
  const [detail, setDetail] = useState<RecordingDetail | null>(null);
  const [liveSnapshot, setLiveSnapshot] = useState<RecordingStreamSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [stopping, setStopping] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const subscriptionRef = useRef<{ close: () => void } | null>(null);

  const loadDetail = useCallback(
    async (options?: { preserveLoading?: boolean }) => {
      if (!recordingId) {
        return;
      }

      if (!options?.preserveLoading) {
        setLoading(true);
      }

      try {
        const response = await fetchRecordingDetail(recordingId);
        setDetail(response);
        setErrorMessage(null);
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : '录制详情加载失败。'
        );
      } finally {
        if (!options?.preserveLoading) {
          setLoading(false);
        }
      }
    },
    [recordingId]
  );

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      await loadDetail();
      if (cancelled) {
        return;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [loadDetail]);

  useEffect(() => {
    subscriptionRef.current?.close();
    subscriptionRef.current = null;

    if (!recordingId || !detail || detail.status !== 'recording') {
      return;
    }

    const subscription = subscribeToRecordingStream(recordingId, (payload) => {
      setLiveSnapshot(payload);
      void loadDetail({ preserveLoading: true });
    });
    subscriptionRef.current = subscription;

    return () => {
      subscription.close();
    };
  }, [detail, loadDetail, recordingId]);

  const effectiveSummary = useMemo(() => {
    if (!detail) {
      return null;
    }
    return {
      status: liveSnapshot?.status ?? detail.status,
      currentUrl: liveSnapshot?.currentUrl ?? detail.currentUrl,
      requestCount: liveSnapshot?.requestCount ?? detail.requestCount,
      pageStageCount: liveSnapshot?.pageStageCount ?? detail.pageStageCount,
      fileTransferCount: liveSnapshot?.fileTransferCount ?? detail.fileTransferCount
    };
  }, [detail, liveSnapshot]);

  async function handleStop() {
    if (!recordingId) {
      return;
    }

    setStopping(true);
    try {
      const response = await stopRecording(recordingId);
      subscriptionRef.current?.close();
      subscriptionRef.current = null;
      setLiveSnapshot(null);
      setDetail(response);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '结束录制失败。');
    } finally {
      setStopping(false);
    }
  }

  if (loading) {
    return <section style={panelStyle}>正在加载录制详情...</section>;
  }

  if (!detail || !effectiveSummary) {
    return <section style={panelStyle}>未找到录制详情。</section>;
  }

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <span style={chipStyle}>Stage 7 Stabilization</span>
        <h1 style={{ marginBottom: '12px' }}>{detail.name}</h1>
        <p style={{ color: '#475467', marginTop: 0 }}>
          会话：{detail.browserSessionId}，起始 URL：{detail.startUrl}
        </p>

        <div style={infoListStyle}>
          <p style={{ margin: 0 }}>录制状态：{effectiveSummary.status}</p>
          <p style={{ margin: 0 }}>当前页面：{effectiveSummary.currentUrl}</p>
          <p style={{ margin: 0 }}>请求数：{effectiveSummary.requestCount}</p>
          <p style={{ margin: 0 }}>页面阶段数：{effectiveSummary.pageStageCount}</p>
          <p style={{ margin: 0 }}>文件传输数：{effectiveSummary.fileTransferCount}</p>
        </div>

        <div style={actionRowStyle}>
          {effectiveSummary.status === 'recording' ? (
            <button
              type="button"
              style={{
                ...primaryButtonStyle,
                opacity: stopping ? 0.72 : 1,
                cursor: stopping ? 'progress' : 'pointer'
              }}
              onClick={() => void handleStop()}
              disabled={stopping}
            >
              {stopping ? '结束中...' : '结束录制'}
            </button>
          ) : null}
          {effectiveSummary.status !== 'recording' ? (
            <Link to={`/review/${detail.id}`} style={secondaryLinkStyle}>
              进入审核
            </Link>
          ) : null}
          <Link to="/recordings" style={secondaryLinkStyle}>
            返回录制列表
          </Link>
        </div>

        {errorMessage ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>{errorMessage}</p>
        ) : null}
      </div>

      <div style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>页面阶段</h2>
        <div style={listStyle}>
          {detail.pageStages.length > 0 ? (
            detail.pageStages.map((item) => (
              <div key={item.id} style={itemStyle}>
                <strong>{item.name}</strong>
                <span>{item.url}</span>
              </div>
            ))
          ) : (
            <div style={itemStyle}>录制进行中时，这里会逐步出现页面阶段。</div>
          )}
        </div>
      </div>

      <div style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>请求索引</h2>
        <div style={listStyle}>
          {detail.requests.length > 0 ? (
            detail.requests.map((item) => (
              <div key={item.id} style={itemStyle}>
                <strong>
                  {item.requestMethod} {item.requestUrl}
                </strong>
                <span>响应状态：{item.responseStatus ?? '等待中'}</span>
              </div>
            ))
          ) : (
            <div style={itemStyle}>录制进行中时，这里会逐步显示请求索引。</div>
          )}
        </div>
      </div>
    </section>
  );
}
