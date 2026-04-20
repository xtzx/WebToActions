import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type CSSProperties
} from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ParameterSuggestionPanel } from '../../features/review/ParameterSuggestionPanel';
import { RequestReviewPanel } from '../../features/review/RequestReviewPanel';
import { useReviewJobStream } from '../../features/review/useReviewJobStream';
import { createActionMacro } from '../../services/actions';
import { fetchReviewContext, saveReviewedMetadata } from '../../services/reviews';
import type { ReviewContext, ReviewedMetadataDetail } from '../../types/review';

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

const summaryStyle: CSSProperties = {
  display: 'grid',
  gap: '12px'
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  gap: '12px',
  flexWrap: 'wrap',
  marginTop: '12px'
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

const inputStyle: CSSProperties = {
  borderRadius: '10px',
  border: '1px solid #cbd5e1',
  padding: '10px 12px'
};

const stageListStyle: CSSProperties = {
  display: 'grid',
  gap: '10px',
  marginTop: '16px'
};

const stageItemStyle: CSSProperties = {
  display: 'grid',
  gap: '6px',
  padding: '14px 16px',
  borderRadius: '14px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

type RequestLabel = 'ignored' | 'key' | 'noise';

export function ReviewPage() {
  const { recordingId } = useParams();
  const navigate = useNavigate();
  const [context, setContext] = useState<ReviewContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatingAction, setGeneratingAction] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState('');
  const [requestLabels, setRequestLabels] = useState<Record<string, RequestLabel>>({});
  const [fieldDescriptions, setFieldDescriptions] = useState<Record<string, string>>({});
  const [parameterSourceMap, setParameterSourceMap] = useState<Record<string, string>>({});
  const [selectedActionStageIds, setSelectedActionStageIds] = useState<string[]>([]);
  const [riskFlagsText, setRiskFlagsText] = useState('');

  const loadContext = useCallback(async () => {
    if (!recordingId) {
      return;
    }

    try {
      const response = await fetchReviewContext(recordingId);
      setContext(response);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '审核上下文加载失败。');
    } finally {
      setLoading(false);
    }
  }, [recordingId]);

  useEffect(() => {
    void loadContext();
  }, [loadContext]);

  useEffect(() => {
    if (!context) {
      return;
    }

    setReviewer(context.latestReviewedMetadata?.reviewer ?? '');
    setRequestLabels(buildRequestLabels(context));
    setFieldDescriptions(buildFieldDescriptions(context));
    setParameterSourceMap(buildParameterSourceMap(context));
    setSelectedActionStageIds(buildSelectedActionStageIds(context));
    setRiskFlagsText((context.latestReviewedMetadata?.riskFlags ?? []).join(', '));
  }, [context]);

  useReviewJobStream(
    recordingId,
    Boolean(
      context &&
        !context.latestDraft &&
        (context.analysisStatus === 'queued' || context.analysisStatus === 'running')
    ),
    (snapshot) => {
      setContext((previous) =>
        previous
          ? {
              ...previous,
              analysisStatus: snapshot.status
            }
          : previous
      );
      if (snapshot.status === 'completed') {
        void loadContext();
      }
      if (snapshot.error) {
        setErrorMessage(snapshot.error);
      }
    },
    () => {
      setErrorMessage('审核状态流已中断，正在重新获取最新状态。');
      void loadContext();
    }
  );

  const draft = context?.latestDraft;
  const latestReviewedMetadata = context?.latestReviewedMetadata;
  const analysisFailed = context?.analysisStatus === 'failed';
  const analysisInProgress = context
    ? (context.analysisStatus === 'queued' ||
        context.analysisStatus === 'running' ||
        (!draft && !analysisFailed && context.analysisStatus !== 'completed'))
    : false;
  const keyRequestCount = useMemo(
    () => Object.values(requestLabels).filter((value) => value === 'key').length,
    [requestLabels]
  );
  const hasUnsavedChanges = useMemo(() => {
    if (!latestReviewedMetadata) {
      return false;
    }

    return (
      reviewer.trim() !== latestReviewedMetadata.reviewer.trim() ||
      !haveSameStringItems(
        collectRequestIds(requestLabels, 'key'),
        latestReviewedMetadata.keyRequestIds
      ) ||
      !haveSameStringItems(
        collectRequestIds(requestLabels, 'noise'),
        latestReviewedMetadata.noiseRequestIds
      ) ||
      !haveSameStringRecord(fieldDescriptions, latestReviewedMetadata.fieldDescriptions) ||
      !haveSameStringRecord(parameterSourceMap, latestReviewedMetadata.parameterSourceMap) ||
      !haveSameStringItems(selectedActionStageIds, latestReviewedMetadata.actionStageIds) ||
      !haveSameStringItems(parseRiskFlags(riskFlagsText), latestReviewedMetadata.riskFlags)
    );
  }, [
    fieldDescriptions,
    latestReviewedMetadata,
    parameterSourceMap,
    requestLabels,
    reviewer,
    riskFlagsText,
    selectedActionStageIds
  ]);

  async function handleSave() {
    if (!recordingId || !draft) {
      return;
    }

    setSaving(true);
    try {
      const reviewed = await saveReviewedMetadata(recordingId, {
        reviewer,
        sourceDraftId: draft.id,
        sourceDraftVersion: draft.version,
        keyRequestIds: collectRequestIds(requestLabels, 'key'),
        noiseRequestIds: collectRequestIds(requestLabels, 'noise'),
        fieldDescriptions,
        parameterSourceMap,
        actionStageIds: selectedActionStageIds,
        riskFlags: parseRiskFlags(riskFlagsText)
      });
      setContext((previous) =>
        previous
          ? {
              ...previous,
              latestReviewedMetadata: reviewed,
              reviewHistory: mergeReviewHistory(previous.reviewHistory, reviewed)
            }
          : previous
      );
      setSaveMessage(`已保存审核版本 v${reviewed.version}`);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '保存审核结果失败。');
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateActionMacro() {
    if (!recordingId || !latestReviewedMetadata) {
      return;
    }

    setGeneratingAction(true);
    try {
      const action = await createActionMacro({ recordingId });
      setErrorMessage(null);
      navigate(`/actions/${action.id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '动作宏生成失败。');
    } finally {
      setGeneratingAction(false);
    }
  }

  if (loading) {
    return <section style={panelStyle}>正在加载审核详情...</section>;
  }

  if (!recordingId) {
    return <section style={panelStyle}>未找到审核上下文。</section>;
  }

  if (!context) {
    return (
      <section style={panelStyle}>
        {errorMessage ?? '未找到审核上下文。'}
      </section>
    );
  }

  return (
    <section style={containerStyle}>
      <section style={panelStyle}>
        <div style={summaryStyle}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              width: 'fit-content',
              padding: '6px 12px',
              borderRadius: '999px',
              background: '#eef2ff',
              color: '#3745a5',
              fontWeight: 700
            }}
          >
            Stage 4 Metadata Review MVP
          </span>
          <h1 style={{ marginBottom: 0 }}>元数据审核</h1>
          <p style={{ margin: 0, color: '#475467' }}>
            录制 {recordingId} 的分析状态：{context.analysisStatus}
          </p>
          {draft?.analysisNotes ? (
            <p style={{ margin: 0, color: '#475467' }}>{draft.analysisNotes}</p>
          ) : null}
          <p style={{ margin: 0, color: '#475467' }}>当前已标记关键请求 {keyRequestCount} 个。</p>
        </div>

        <div style={actionRowStyle}>
          <Link to={`/recordings/${recordingId}`} style={secondaryLinkStyle}>
            返回录制详情
          </Link>
        </div>

        {analysisInProgress ? (
          <p style={{ color: '#344054', marginTop: '16px' }}>
            正在分析录制证据，页面会在建议生成后自动刷新。
          </p>
        ) : null}
        {analysisFailed ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>
            分析任务已失败，请检查错误信息后重试。
          </p>
        ) : null}
        {saveMessage ? (
          <p style={{ color: '#027a48', marginTop: '16px' }}>{saveMessage}</p>
        ) : null}
        {errorMessage ? (
          <p style={{ color: '#b42318', marginTop: '16px' }}>{errorMessage}</p>
        ) : null}
      </section>

      {draft ? (
        <>
          <RequestReviewPanel
            requests={context.requests}
            requestLabels={requestLabels}
            onLabelChange={(requestId, next) =>
              setRequestLabels((previous) => ({ ...previous, [requestId]: next }))
            }
          />

          <ParameterSuggestionPanel
            suggestions={draft.parameterSuggestions}
            fieldDescriptions={fieldDescriptions}
            parameterSourceMap={parameterSourceMap}
            onFieldDescriptionChange={(name, value) =>
              setFieldDescriptions((previous) => ({ ...previous, [name]: value }))
            }
            onParameterSourceChange={(name, value) =>
              setParameterSourceMap((previous) => ({ ...previous, [name]: value }))
            }
          />

          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>动作片段与保存</h2>
            <div style={{ display: 'grid', gap: '12px', maxWidth: '480px' }}>
              <label htmlFor="reviewer-input">审核人</label>
              <input
                id="reviewer-input"
                aria-label="审核人"
                style={inputStyle}
                value={reviewer}
                onChange={(event) => setReviewer(event.target.value)}
              />
              <label htmlFor="risk-flags-input">风险标记</label>
              <input
                id="risk-flags-input"
                style={inputStyle}
                value={riskFlagsText}
                onChange={(event) => setRiskFlagsText(event.target.value)}
                placeholder="用逗号分隔，例如：需要人工校验, 涉及审批"
              />
            </div>

            <div style={stageListStyle}>
              {draft.actionFragmentSuggestions.map((item) => {
                const checked = selectedActionStageIds.includes(item.stageId);
                return (
                  <label key={item.id} style={stageItemStyle}>
                    <span>{item.title}</span>
                    <span style={{ color: '#475467' }}>{item.notes}</span>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) =>
                        setSelectedActionStageIds((previous) =>
                          event.target.checked
                            ? Array.from(new Set([...previous, item.stageId]))
                            : previous.filter((stageId) => stageId !== item.stageId)
                        )
                      }
                    />
                  </label>
                );
              })}
            </div>

            <div style={actionRowStyle}>
              <button
                type="button"
                style={{
                  ...primaryButtonStyle,
                  opacity: saving ? 0.72 : 1,
                  cursor: saving ? 'progress' : 'pointer'
                }}
                disabled={saving || reviewer.trim().length === 0}
                onClick={() => void handleSave()}
              >
                {saving ? '保存中...' : '保存审核结果'}
              </button>
              {latestReviewedMetadata ? (
                <button
                  type="button"
                  style={{
                    ...primaryButtonStyle,
                    background: '#0f766e',
                    opacity: generatingAction || saving || hasUnsavedChanges ? 0.72 : 1,
                    cursor:
                      generatingAction || saving || hasUnsavedChanges
                        ? 'not-allowed'
                        : 'pointer'
                  }}
                  disabled={generatingAction || saving || hasUnsavedChanges}
                  onClick={() => void handleGenerateActionMacro()}
                >
                  {generatingAction ? '生成中...' : '生成动作宏'}
                </button>
              ) : null}
            </div>

            {latestReviewedMetadata ? (
              <>
                <p style={{ color: '#475467', marginTop: '16px' }}>
                  最近一次保存：v{latestReviewedMetadata.version}，审核人 {latestReviewedMetadata.reviewer}
                </p>
                {hasUnsavedChanges ? (
                  <p style={{ color: '#b54708', marginTop: '8px' }}>
                    请先保存当前审核修改，再生成动作宏。
                  </p>
                ) : null}
                <p style={{ color: '#475467', marginTop: '8px' }}>
                  审核结果已可用于生成动作宏，并继续进入执行、导入导出与回归验证链路。
                </p>
              </>
            ) : null}
          </section>
        </>
      ) : null}
    </section>
  );
}

function buildRequestLabels(context: ReviewContext): Record<string, RequestLabel> {
  const labels: Record<string, RequestLabel> = Object.fromEntries(
    context.requests.map((item) => [item.id, 'ignored' as const])
  );
  const reviewed = context.latestReviewedMetadata;
  if (reviewed) {
    for (const requestId of reviewed.keyRequestIds) {
      labels[requestId] = 'key';
    }
    for (const requestId of reviewed.noiseRequestIds) {
      labels[requestId] = 'noise';
    }
    return labels;
  }

  for (const requestId of context.latestDraft?.candidateRequestIds ?? []) {
    labels[requestId] = 'key';
  }
  return labels;
}

function buildFieldDescriptions(context: ReviewContext): Record<string, string> {
  if (context.latestReviewedMetadata) {
    return { ...context.latestReviewedMetadata.fieldDescriptions };
  }

  return Object.fromEntries(
    (context.latestDraft?.parameterSuggestions ?? []).map((item) => [item.name, ''])
  );
}

function buildParameterSourceMap(context: ReviewContext): Record<string, string> {
  if (context.latestReviewedMetadata) {
    return { ...context.latestReviewedMetadata.parameterSourceMap };
  }

  return Object.fromEntries(
    (context.latestDraft?.parameterSuggestions ?? []).map((item) => [
      item.name,
      item.source
    ])
  );
}

function buildSelectedActionStageIds(context: ReviewContext): string[] {
  const validStageIds = new Set(context.pageStages.map((item) => item.id));
  if (context.latestReviewedMetadata) {
    return context.latestReviewedMetadata.actionStageIds.filter((stageId) =>
      validStageIds.has(stageId)
    );
  }
  return (context.latestDraft?.actionFragmentSuggestions ?? [])
    .map((item) => item.stageId)
    .filter((stageId) => validStageIds.has(stageId));
}

function collectRequestIds(
  labels: Record<string, RequestLabel>,
  target: RequestLabel
): string[] {
  return Object.entries(labels)
    .filter(([, value]) => value === target)
    .map(([requestId]) => requestId);
}

function mergeReviewHistory(
  history: ReviewedMetadataDetail[],
  latest: ReviewedMetadataDetail
): ReviewedMetadataDetail[] {
  return [
    latest,
    ...history.filter(
      (item) => !(item.id === latest.id && item.version === latest.version)
    )
  ];
}

function haveSameStringItems(left: string[], right: string[]): boolean {
  const normalizedLeft = [...left].sort();
  const normalizedRight = [...right].sort();
  return JSON.stringify(normalizedLeft) === JSON.stringify(normalizedRight);
}

function haveSameStringRecord(
  left: Record<string, string>,
  right: Record<string, string>
): boolean {
  const normalizedLeft = Object.fromEntries(
    Object.entries(left).sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
  );
  const normalizedRight = Object.fromEntries(
    Object.entries(right).sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
  );
  return JSON.stringify(normalizedLeft) === JSON.stringify(normalizedRight);
}

function parseRiskFlags(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}
