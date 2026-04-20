import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';

const healthPayload = {
  status: 'ok',
  phase: 'stage7',
  appName: 'WebToActions Backend',
  environment: 'development',
  apiPrefix: '/api',
  targetPython: '3.11+',
  runtimePython: '3.11.11',
  dataDir: '.webtoactions',
  browserChannel: 'chromium',
  browserHeadless: false
};

const recordingsPayload = {
  items: [
    {
      id: 'recording-1',
      name: '提交报销单',
      startUrl: 'https://example.com/expense/new',
      browserSessionId: 'session-1',
      status: 'pending_review',
      createdAt: '2026-04-19T16:00:00+00:00',
      startedAt: '2026-04-19T16:00:05+00:00',
      endedAt: '2026-04-19T16:02:05+00:00',
      currentUrl: 'https://example.com/expense/confirm',
      requestCount: 4,
      pageStageCount: 2,
      fileTransferCount: 1,
      sessionSnapshotCount: 1,
      failedRequestCount: 0
    }
  ]
};

const sessionsPayload = {
  items: [
    {
      id: 'session-1',
      profileId: 'profile-session-1',
      status: 'available',
      loginSiteSummaries: ['example.com'],
      createdAt: '2026-04-19T15:00:00+00:00',
      lastActivityAt: '2026-04-19T16:02:05+00:00'
    }
  ]
};

const sessionsWithImportedSessionFirstPayload = {
  items: [
    {
      id: 'session-imported',
      profileId: 'profile-session-imported',
      status: 'relogin_required',
      loginSiteSummaries: [],
      createdAt: '2026-04-19T14:50:00+00:00',
      lastActivityAt: '2026-04-19T15:50:00+00:00'
    },
    ...sessionsPayload.items
  ]
};

const recordingDetailPayload = {
  ...recordingsPayload.items[0],
  pageStages: [
    {
      id: 'stage-1',
      url: 'https://example.com/expense/new',
      name: '报销创建页',
      startedAt: '2026-04-19T16:00:05+00:00',
      endedAt: '2026-04-19T16:01:00+00:00',
      relatedRequestIds: ['req-1'],
      waitPoints: [],
      observableState: {}
    }
  ],
  requests: [
    {
      id: 'req-1',
      requestMethod: 'POST',
      requestUrl: 'https://example.com/api/expenses',
      requestedAt: '2026-04-19T16:00:10+00:00',
      requestHeaders: [{ name: 'content-type', value: 'application/json' }],
      requestBodyBlobKey: 'evidence/rec_recording-1/requests/req-1/request-body.bin',
      responseStatus: 200,
      responseHeaders: [{ name: 'content-type', value: 'application/json' }],
      responseBodyBlobKey: 'evidence/rec_recording-1/responses/req-1/response-body.bin',
      finishedAt: '2026-04-19T16:00:11+00:00',
      durationMs: 1000,
      pageStageId: 'stage-1',
      failureReason: null
    }
  ],
  sessionSnapshots: [
    {
      id: 'snapshot-1',
      browserSessionId: 'session-1',
      capturedAt: '2026-04-19T16:02:05+00:00',
      pageStageId: 'stage-1',
      requestId: null,
      cookieSummary: { count: '1', domains: 'example.com' },
      storageSummary: { capture: { blobKey: 'evidence/rec_recording-1/session_state/snapshot-1.json' } }
    }
  ],
  fileTransfers: [
    {
      id: 'download-1',
      direction: 'download',
      fileName: 'receipt.pdf',
      occurredAt: '2026-04-19T16:01:30+00:00',
      relatedRequestId: 'req-1',
      sourcePathSummary: null,
      targetPathSummary: null,
      notes: null
    }
  ]
};

const reviewContextReady = {
  recordingId: 'recording-1',
  analysisStatus: 'completed',
  latestDraft: {
    id: 'draft-recording-1',
    version: 1,
    previousVersion: null,
    recordingId: 'recording-1',
    candidateRequestIds: ['req-1'],
    parameterSuggestions: [
      {
        name: 'amount',
        source: 'request.body.amount',
        exampleValue: '108',
        reason: '检测到请求体中的候选参数字段。'
      },
      {
        name: 'currency',
        source: 'request.body.currency',
        exampleValue: 'CNY',
        reason: '检测到请求体中的候选参数字段。'
      }
    ],
    actionFragmentSuggestions: [
      {
        id: 'fragment-1',
        title: '报销创建页',
        stageId: 'stage-1',
        requestIds: ['req-1'],
        notes: '页面阶段报销创建页覆盖 1 个候选请求。'
      }
    ],
    analysisNotes:
      '阶段 4 MVP 使用确定性规则生成 metadata draft，候选请求 1 个，参数建议 2 个，动作片段 1 个。',
    generatedAt: '2026-04-19T16:05:00+00:00'
  },
  latestReviewedMetadata: null,
  reviewHistory: [],
  requests: [
    {
      id: 'req-1',
      requestMethod: 'POST',
      requestUrl: 'https://example.com/api/expenses',
      responseStatus: 200,
      pageStageId: 'stage-1'
    }
  ],
  pageStages: [
    {
      id: 'stage-1',
      name: '报销创建页',
      url: 'https://example.com/expense/new',
      relatedRequestIds: ['req-1']
    },
    {
      id: 'stage-2',
      name: '报销确认页',
      url: 'https://example.com/expense/confirm',
      relatedRequestIds: []
    }
  ]
};

const reviewContextRunning = {
  ...reviewContextReady,
  analysisStatus: 'running',
  latestDraft: null
};

const savedReviewedMetadata = {
  id: 'review-recording-1',
  version: 1,
  previousVersion: null,
  recordingId: 'recording-1',
  reviewer: 'alice',
  sourceDraftId: 'draft-recording-1',
  sourceDraftVersion: 1,
  keyRequestIds: ['req-1'],
  noiseRequestIds: [],
  fieldDescriptions: {
    amount: '报销金额',
    currency: '币种'
  },
  parameterSourceMap: {
    amount: 'request.body.amount',
    currency: 'request.body.currency'
  },
  actionStageIds: ['stage-1'],
  riskFlags: []
};

const reviewContextReviewed = {
  ...reviewContextReady,
  latestReviewedMetadata: savedReviewedMetadata,
  reviewHistory: [savedReviewedMetadata]
};

const actionDetailPayload = {
  id: 'macro-recording-1',
  version: 1,
  previousVersion: null,
  recordingId: 'recording-1',
  name: '提交报销单 执行宏',
  description: '基于已审核录制自动生成的请求回放宏。',
  stepCount: 1,
  parameterCount: 2,
  createdAt: '2026-04-19T16:10:00+00:00',
  sourceReviewedMetadataId: 'review-recording-1',
  sourceReviewedMetadataVersion: 1,
  steps: [
    {
      id: 'step-1',
      stepKind: 'request_replay',
      title: 'POST https://example.com/api/expenses',
      requestId: 'req-1',
      requestMethod: 'POST',
      requestUrl: 'https://example.com/api/expenses',
      pageStageId: 'stage-1',
      navigateUrl: 'https://example.com/expense/new'
    }
  ],
  requiredPageStageIds: ['stage-1'],
  parameterDefinitions: [
    {
      id: 'macro-recording-1-v1-param-1',
      actionId: 'macro-recording-1',
      ownerKind: 'action_macro',
      name: 'amount',
      parameterKind: 'integer',
      required: true,
      defaultValue: null,
      injectionTarget: 'request.body.amount',
      description: '报销金额'
    },
    {
      id: 'macro-recording-1-v1-param-2',
      actionId: 'macro-recording-1',
      ownerKind: 'action_macro',
      name: 'currency',
      parameterKind: 'string',
      required: true,
      defaultValue: null,
      injectionTarget: 'request.body.currency',
      description: '币种'
    }
  ],
  sessionRequirements: ['example.com']
};

const actionListPayload = {
  items: [
    {
      id: 'macro-recording-1',
      version: 1,
      previousVersion: null,
      recordingId: 'recording-1',
      name: '提交报销单 执行宏',
      description: '基于已审核录制自动生成的请求回放宏。',
      stepCount: 1,
      parameterCount: 2,
      createdAt: '2026-04-19T16:10:00+00:00'
    }
  ]
};

const importRecordingResultPayload = {
  recordingId: 'recording-1',
  actionIds: ['macro-recording-1'],
  executionIds: ['run-1'],
  warnings: ['浏览器 profile 与活跃登录态不会随资料包导出；导入后的会话仅保留历史上下文，如需继续执行请准备新的可用会话。']
};

const executionRunRunningPayload = {
  id: 'run-1',
  actionKind: 'action_macro',
  actionId: 'macro-recording-1',
  actionVersion: 1,
  browserSessionId: 'session-1',
  parametersSnapshot: {
    amount: 208,
    currency: 'USD'
  },
  status: 'running',
  createdAt: '2026-04-19T16:11:00+00:00',
  startedAt: '2026-04-19T16:11:01+00:00',
  endedAt: null,
  stepLogs: ['开始执行 POST https://example.com/api/expenses'],
  failureReason: null,
  diagnostics: {
    currentStepId: 'step-1',
    currentStepTitle: 'POST https://example.com/api/expenses',
    currentUrl: 'https://example.com/expense/new'
  }
};

const executionRunSucceededPayload = {
  ...executionRunRunningPayload,
  status: 'succeeded',
  endedAt: '2026-04-19T16:11:05+00:00',
  stepLogs: [
    '开始执行 POST https://example.com/api/expenses',
    '完成执行 POST https://example.com/api/expenses'
  ],
  diagnostics: {
    finalUrl: 'https://example.com/expense/confirm',
    stepOutcomes: [
      {
        stepId: 'step-1',
        requestId: 'req-1',
        requestBodyPreview: '{"amount":208,"currency":"USD"}',
        responseStatus: 200
      }
    ]
  }
};

const executionRunFailedPayload = {
  ...executionRunRunningPayload,
  status: 'failed',
  endedAt: '2026-04-19T16:11:05+00:00',
  stepLogs: [
    '开始执行 POST https://example.com/api/expenses',
    '步骤失败：POST https://example.com/api/expenses'
  ],
  failureReason: '步骤失败：POST https://example.com/api/expenses',
  diagnostics: {
    failedStepId: 'step-1',
    failedStepTitle: 'POST https://example.com/api/expenses',
    currentUrl: 'https://example.com/expense/new'
  }
};

async function renderAppAt(path = '/') {
  window.history.pushState({}, '', path);
  const { default: App } = await import('./App');
  return render(<App />);
}

class MockEventSource {
  static instances: MockEventSource[] = [];

  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  close = vi.fn();

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }

  emit(payload: unknown) {
    this.onmessage?.(
      {
        data: JSON.stringify(payload)
      } as MessageEvent<string>
    );
  }

  emitError() {
    this.onerror?.(new Event('error'));
  }
}

function getLatestMockEventSourceInstance() {
  const lastIndex = MockEventSource.instances.length - 1;
  return lastIndex >= 0 ? MockEventSource.instances[lastIndex] : undefined;
}

describe('App', () => {
  beforeEach(() => {
    vi.resetModules();
    window.history.pushState({}, '', '/');
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource as unknown as typeof EventSource);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders the stage 1 app shell entry points', async () => {
    await renderAppAt();

    expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '首页' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '录制中心' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: 'WebToActions 管理台' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '检查后端健康状态' })
    ).toBeInTheDocument();
  });

  it('loads recordings and sessions from the stage 3 backend contracts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url === '/api/recordings') {
          return {
            ok: true,
            json: async () => recordingsPayload
          } as Response;
        }

        if (url === '/api/sessions') {
          return {
            ok: true,
            json: async () => sessionsPayload
          } as Response;
        }

        throw new Error(`Unexpected fetch url: ${url}`);
      })
    );

    await renderAppAt('/recordings');

    expect(await screen.findByText('提交报销单')).toBeInTheDocument();
    expect(screen.getByText('录制状态：pending_review')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: '会话管理' }));

    expect(await screen.findByText('session-1')).toBeInTheDocument();
    expect(screen.getByText('已登录站点：example.com')).toBeInTheDocument();
  });

  it('renders the formal health contract when backend check succeeds', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => healthPayload
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt();
    fireEvent.click(screen.getByRole('button', { name: '检查后端健康状态' }));

    expect(
      await screen.findByText(
        '后端响应正常，status="ok"，phase="stage7"，targetPython="3.11+"。'
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/"phase": "stage7"/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/health',
      expect.objectContaining({
        cache: 'no-store',
        headers: { Accept: 'application/json' }
      })
    );
  });

  it('shows an error state when backend health check fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })
    );

    await renderAppAt();
    fireEvent.click(screen.getByRole('button', { name: '检查后端健康状态' }));

    expect(await screen.findByText('后端健康检查失败。')).toBeInTheDocument();
    expect(
      screen.getByText('健康检查失败：500 Internal Server Error')
    ).toBeInTheDocument();
    expect(screen.getByText('健康检查 JSON 输出会显示在这里。')).toBeInTheDocument();
  });

  it('starts a recording, opens the detail stream and can stop recording', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsPayload
        } as Response;
      }

      if (url === '/api/recordings' && method === 'POST') {
        return {
          ok: true,
          json: async () => ({
            id: 'recording-1',
            name: '提交报销单',
            startUrl: 'https://example.com/expense/new',
            browserSessionId: 'session-1',
            status: 'recording',
            createdAt: '2026-04-19T16:00:00+00:00',
            startedAt: '2026-04-19T16:00:05+00:00',
            endedAt: null,
            currentUrl: 'https://example.com/expense/new',
            requestCount: 1,
            pageStageCount: 1,
            fileTransferCount: 0,
            sessionSnapshotCount: 0,
            failedRequestCount: 0
          })
        } as Response;
      }

      if (url === '/api/recordings/recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => ({
            ...recordingDetailPayload,
            status: 'recording',
            endedAt: null,
            fileTransfers: [],
            fileTransferCount: 0,
            sessionSnapshots: [],
            sessionSnapshotCount: 0
          })
        } as Response;
      }

      if (url === '/api/recordings/recording-1/stop' && method === 'POST') {
        return {
          ok: true,
          json: async () => recordingDetailPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/recordings/new');

    fireEvent.change(screen.getByLabelText('录制名称'), {
      target: { value: '提交报销单' }
    });
    fireEvent.change(screen.getByLabelText('起始 URL'), {
      target: { value: 'https://example.com/expense/new' }
    });
    fireEvent.change(screen.getByLabelText('浏览器会话'), {
      target: { value: 'session-1' }
    });

    fireEvent.click(screen.getByRole('button', { name: '开始录制' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: '提交报销单' })
    ).toBeInTheDocument();
    expect(MockEventSource.instances[0]?.url).toBe('/api/recordings/recording-1/events');

    MockEventSource.instances[0]?.emit({
      recordingId: 'recording-1',
      status: 'recording',
      currentUrl: 'https://example.com/expense/confirm',
      requestCount: 3,
      pageStageCount: 2,
      fileTransferCount: 1,
      updatedAt: '2026-04-19T16:01:00+00:00'
    });

    expect(await screen.findByText('当前页面：https://example.com/expense/confirm')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '结束录制' }));

    expect(await screen.findByText('录制状态：pending_review')).toBeInTheDocument();
    expect(screen.getByText('请求数：4')).toBeInTheDocument();
  });

  it('refreshes recording detail content when the live stream reports new evidence', async () => {
    let detailGetCount = 0;
    const updatedDetailPayload = {
      ...recordingDetailPayload,
      status: 'recording',
      endedAt: null,
      requestCount: 2,
      pageStageCount: 2,
      fileTransferCount: 1,
      pageStages: [
        ...recordingDetailPayload.pageStages,
        {
          id: 'stage-2',
          url: 'https://example.com/expense/confirm',
          name: '报销确认页',
          startedAt: '2026-04-19T16:01:00+00:00',
          endedAt: null,
          relatedRequestIds: ['req-2'],
          waitPoints: [],
          observableState: {}
        }
      ],
      requests: [
        ...recordingDetailPayload.requests,
        {
          id: 'req-2',
          requestMethod: 'POST',
          requestUrl: 'https://example.com/api/expenses/confirm',
          requestedAt: '2026-04-19T16:01:05+00:00',
          requestHeaders: [{ name: 'content-type', value: 'application/json' }],
          requestBodyBlobKey: null,
          responseStatus: 200,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }],
          responseBodyBlobKey: null,
          finishedAt: '2026-04-19T16:01:06+00:00',
          durationMs: 1000,
          pageStageId: 'stage-2',
          failureReason: null
        }
      ],
      fileTransfers: []
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/recordings/recording-1' && method === 'GET') {
        detailGetCount += 1;
        return {
          ok: true,
          json: async () =>
            detailGetCount === 1
              ? {
                  ...recordingDetailPayload,
                  status: 'recording',
                  endedAt: null,
                  fileTransfers: [],
                  fileTransferCount: 0,
                  sessionSnapshots: [],
                  sessionSnapshotCount: 0
                }
              : updatedDetailPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/recordings/recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '提交报销单' })
    ).toBeInTheDocument();

    await act(async () => {
      MockEventSource.instances[0]?.emit({
        recordingId: 'recording-1',
        status: 'recording',
        currentUrl: 'https://example.com/expense/confirm',
        requestCount: 2,
        pageStageCount: 2,
        fileTransferCount: 1,
        updatedAt: '2026-04-19T16:01:30+00:00'
      });
    });

    expect(await screen.findByText('报销确认页')).toBeInTheDocument();
    expect(
      await screen.findByText('POST https://example.com/api/expenses/confirm')
    ).toBeInTheDocument();
  });

  it('enters review from recording detail, waits for analysis stream, and saves review result', async () => {
    let reviewGetCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/recordings/recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => recordingDetailPayload
        } as Response;
      }

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        reviewGetCount += 1;
        return {
          ok: true,
          json: async () =>
            reviewGetCount === 1 ? reviewContextRunning : reviewContextReady
        } as Response;
      }

      if (
        url === '/api/reviews/recording-1/reviewed-metadata' &&
        method === 'POST'
      ) {
        return {
          ok: true,
          json: async () => savedReviewedMetadata
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/recordings/recording-1');

    const enterReviewLink = await screen.findByRole('link', { name: '进入审核' });
    fireEvent.click(enterReviewLink);

    expect(
      await screen.findByRole('heading', { level: 1, name: '元数据审核' })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(getLatestMockEventSourceInstance()?.url).toBe('/api/reviews/recording-1/events');
    });

    await act(async () => {
      getLatestMockEventSourceInstance()?.emit({
        recordingId: 'recording-1',
        status: 'completed',
        latestDraftVersion: 1,
        error: null,
        updatedAt: '2026-04-19T16:05:00+00:00'
      });
    });

    expect(await screen.findByText('amount')).toBeInTheDocument();
    expect(screen.getByDisplayValue('request.body.amount')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('审核人'), {
      target: { value: 'alice' }
    });
    fireEvent.change(screen.getByLabelText('字段说明 amount'), {
      target: { value: '报销金额' }
    });
    fireEvent.change(screen.getByLabelText('字段说明 currency'), {
      target: { value: '币种' }
    });

    fireEvent.click(screen.getByRole('button', { name: '保存审核结果' }));

    expect(await screen.findByText('已保存审核版本 v1')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/reviews/recording-1/reviewed-metadata',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        }),
        body: expect.stringContaining('"reviewer":"alice"')
      })
    );
  });

  it('shows a failed review analysis state without keeping the loading hint', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => reviewContextRunning
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/review/recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '元数据审核' })
    ).toBeInTheDocument();

    await act(async () => {
      MockEventSource.instances[0]?.emit({
        recordingId: 'recording-1',
        status: 'failed',
        latestDraftVersion: null,
        error: '分析任务失败。',
        updatedAt: '2026-04-19T16:05:30+00:00'
      });
    });

    expect(await screen.findByText('分析任务失败。')).toBeInTheDocument();
    expect(screen.queryByText('正在分析录制证据，页面会在建议生成后自动刷新。')).not.toBeInTheDocument();
  });

  it('shows the real review loading error when initial context fetch fails', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        return {
          ok: false,
          status: 409,
          statusText: 'Conflict'
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/review/recording-1');

    expect(await screen.findByText('请求失败：409 Conflict')).toBeInTheDocument();
    expect(screen.queryByText('未找到审核上下文。')).not.toBeInTheDocument();
  });

  it('falls back to reloading review context when the review stream disconnects', async () => {
    let reviewGetCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        reviewGetCount += 1;
        return {
          ok: true,
          json: async () =>
            reviewGetCount === 1 ? reviewContextRunning : reviewContextReady
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/review/recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '元数据审核' })
    ).toBeInTheDocument();
    expect(MockEventSource.instances[0]?.url).toBe('/api/reviews/recording-1/events');

    await act(async () => {
      MockEventSource.instances[0]?.emitError();
    });

    expect(await screen.findByText('amount')).toBeInTheDocument();
    expect(screen.queryByText('正在分析录制证据，页面会在建议生成后自动刷新。')).not.toBeInTheDocument();
    expect(reviewGetCount).toBe(2);
  });

  it('loads the stage 5 action library and execution center lists', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/actions' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionListPayload
        } as Response;
      }

      if (url === '/api/executions' && method === 'GET') {
        return {
          ok: true,
          json: async () => ({ items: [executionRunSucceededPayload] })
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/actions');

    expect(
      await screen.findByRole('heading', { level: 1, name: '动作库' })
    ).toBeInTheDocument();
    expect(screen.getByText('提交报销单 执行宏')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看动作详情' })).toHaveAttribute(
      'href',
      '/actions/macro-recording-1'
    );

    fireEvent.click(screen.getByRole('link', { name: '执行中心' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: '执行中心' })
    ).toBeInTheDocument();
    expect(screen.getByText('run-1')).toBeInTheDocument();
    expect(screen.getByText('执行状态：succeeded')).toBeInTheDocument();
  });

  it('generates an action macro from reviewed metadata and opens the action detail page', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => reviewContextReviewed
        } as Response;
      }

      if (url === '/api/actions' && method === 'POST') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/actions/macro-recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/review/recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '元数据审核' })
    ).toBeInTheDocument();

    const generateButton = screen.getByRole('button', { name: '生成动作宏' });
    await waitFor(() => {
      expect(generateButton).not.toBeDisabled();
    });
    fireEvent.click(generateButton);

    expect(
      await screen.findByRole('heading', { level: 1, name: '动作详情' })
    ).toBeInTheDocument();
    expect(screen.getByText('提交报销单 执行宏')).toBeInTheDocument();
    expect(screen.getByDisplayValue('request.body.amount')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始执行' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/actions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify({ recordingId: 'recording-1' })
      })
    );
  });

  it('prefers an available browser session over imported relogin_required sessions', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/actions/macro-recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsWithImportedSessionFirstPayload
        } as Response;
      }

      if (url === '/api/actions/macro-recording-1/executions' && method === 'POST') {
        expect(JSON.parse(String(init?.body ?? '{}')).browserSessionId).toBe('session-1');
        return {
          ok: true,
          json: async () => executionRunRunningPayload
        } as Response;
      }

      if (url === '/api/executions/run-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => executionRunRunningPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/actions/macro-recording-1');

    const sessionSelect = (await screen.findByLabelText('浏览器会话')) as HTMLSelectElement;
    expect(sessionSelect.value).toBe('session-1');
    expect(
      (
        screen.getByRole('option', {
          name: 'session-imported (relogin_required)'
        }) as HTMLOptionElement
      ).disabled
    ).toBe(true);

    fireEvent.change(sessionSelect, {
      target: { value: 'session-1' }
    });
    fireEvent.change(screen.getByLabelText('参数 amount'), {
      target: { value: '208' }
    });
    fireEvent.change(screen.getByLabelText('参数 currency'), {
      target: { value: 'USD' }
    });

    fireEvent.click(screen.getByRole('button', { name: '开始执行' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: '执行详情' })
    ).toBeInTheDocument();
  });

  it('starts an execution from action detail and updates execution detail from the stage 5 stream', async () => {
    let executionDetailRequestCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/actions/macro-recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsPayload
        } as Response;
      }

      if (url === '/api/actions/macro-recording-1/executions' && method === 'POST') {
        return {
          ok: true,
          json: async () => executionRunRunningPayload
        } as Response;
      }

      if (url === '/api/executions/run-1' && method === 'GET') {
        executionDetailRequestCount += 1;
        return {
          ok: true,
          json: async () =>
            executionDetailRequestCount === 1
              ? executionRunRunningPayload
              : executionRunSucceededPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/actions/macro-recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '动作详情' })
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('浏览器会话'), {
      target: { value: 'session-1' }
    });
    fireEvent.change(screen.getByLabelText('参数 amount'), {
      target: { value: '208' }
    });
    fireEvent.change(screen.getByLabelText('参数 currency'), {
      target: { value: 'USD' }
    });

    fireEvent.click(screen.getByRole('button', { name: '开始执行' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: '执行详情' })
    ).toBeInTheDocument();
    expect(await screen.findByText('执行状态：running')).toBeInTheDocument();

    await waitFor(() => {
      expect(getLatestMockEventSourceInstance()?.url).toBe('/api/executions/run-1/events');
    });

    await act(async () => {
      getLatestMockEventSourceInstance()?.emit({
        executionId: 'run-1',
        status: 'succeeded',
        currentStepId: 'step-1',
        currentStepTitle: 'POST https://example.com/api/expenses',
        currentUrl: 'https://example.com/expense/confirm',
        logCount: 2,
        failureReason: null,
        updatedAt: '2026-04-19T16:11:05+00:00'
      });
    });

    expect(await screen.findByText('执行状态：succeeded')).toBeInTheDocument();
    expect(screen.getByText('完成执行 POST https://example.com/api/expenses')).toBeInTheDocument();
    expect(screen.getByText('最终页面：https://example.com/expense/confirm')).toBeInTheDocument();
  });

  it('shows backend execution start detail instead of a generic http error', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/actions/macro-recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsPayload
        } as Response;
      }

      if (url === '/api/actions/macro-recording-1/executions' && method === 'POST') {
        return {
          ok: false,
          status: 400,
          statusText: 'Bad Request',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            detail: 'Browser session must be available before starting execution.'
          })
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/actions/macro-recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '动作详情' })
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('浏览器会话'), {
      target: { value: 'session-1' }
    });
    fireEvent.change(screen.getByLabelText('参数 amount'), {
      target: { value: '208' }
    });
    fireEvent.change(screen.getByLabelText('参数 currency'), {
      target: { value: 'USD' }
    });

    fireEvent.click(screen.getByRole('button', { name: '开始执行' }));

    expect(
      await screen.findByText('Browser session must be available before starting execution.')
    ).toBeInTheDocument();
  });

  it('prevents starting an execution when a required parameter is blank', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/actions/macro-recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => actionDetailPayload
        } as Response;
      }

      if (url === '/api/sessions' && method === 'GET') {
        return {
          ok: true,
          json: async () => sessionsPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/actions/macro-recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '动作详情' })
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('浏览器会话'), {
      target: { value: 'session-1' }
    });
    fireEvent.change(screen.getByLabelText('参数 amount'), {
      target: { value: '   ' }
    });
    fireEvent.change(screen.getByLabelText('参数 currency'), {
      target: { value: 'USD' }
    });

    fireEvent.click(screen.getByRole('button', { name: '开始执行' }));

    expect(await screen.findByText('参数 amount 不能为空。')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/actions/macro-recording-1/executions',
      expect.anything()
    );
  });

  it('requires saving review changes before generating an action macro', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/reviews/recording-1' && method === 'GET') {
        return {
          ok: true,
          json: async () => reviewContextReviewed
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/review/recording-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '元数据审核' })
    ).toBeInTheDocument();

    const generateButton = screen.getByRole('button', { name: '生成动作宏' });
    await waitFor(() => {
      expect(generateButton).not.toBeDisabled();
    });

    fireEvent.change(screen.getByLabelText('字段说明 amount'), {
      target: { value: '报销金额（已修改）' }
    });

    expect(generateButton).toBeDisabled();
    expect(screen.getByText('请先保存当前审核修改，再生成动作宏。')).toBeInTheDocument();
  });

  it('re-subscribes to the execution stream when the stream disconnects and reload fails', async () => {
    let executionDetailRequestCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/executions/run-1' && method === 'GET') {
        executionDetailRequestCount += 1;
        if (executionDetailRequestCount === 1) {
          return {
            ok: true,
            json: async () => executionRunRunningPayload
          } as Response;
        }

        return {
          ok: false,
          status: 503,
          statusText: 'Service Unavailable'
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/execution/run-1');

    expect(
      await screen.findByRole('heading', { level: 1, name: '执行详情' })
    ).toBeInTheDocument();
    expect(getLatestMockEventSourceInstance()?.url).toBe('/api/executions/run-1/events');

    vi.useFakeTimers();
    try {
      await act(async () => {
        getLatestMockEventSourceInstance()?.emitError();
      });

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      expect(MockEventSource.instances).toHaveLength(2);
      expect(getLatestMockEventSourceInstance()?.url).toBe('/api/executions/run-1/events');
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows backend execution detail errors instead of a generic http message', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/executions/run-missing' && method === 'GET') {
        return {
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            detail: 'Execution run run-missing not found.'
          })
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/execution/run-missing');

    expect(
      await screen.findByText('Execution run run-missing not found.')
    ).toBeInTheDocument();
  });

  it('exports the selected recording bundle from the importexport page', async () => {
    const createObjectUrlMock = vi.fn(() => 'blob:recording-bundle');
    const revokeObjectUrlMock = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    class MockUrl extends URL {
      static createObjectURL = createObjectUrlMock;
      static revokeObjectURL = revokeObjectUrlMock;
    }
    vi.stubGlobal('URL', MockUrl);

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/recordings' && method === 'GET') {
        return {
          ok: true,
          json: async () => recordingsPayload
        } as Response;
      }

      if (url === '/api/importexport/recordings/recording-1/bundle' && method === 'GET') {
        return {
          ok: true,
          blob: async () => new Blob(['bundle'], { type: 'application/zip' })
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/importexport');

    expect(
      await screen.findByRole('heading', { level: 1, name: '导入导出' })
    ).toBeInTheDocument();
    expect(screen.getAllByText('提交报销单').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '导出资料包' }));

    expect(await screen.findByText('导出完成，浏览器已开始下载资料包。')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/importexport/recordings/recording-1/bundle',
      expect.objectContaining({
        method: 'GET'
      })
    );
    expect(createObjectUrlMock).toHaveBeenCalled();
    expect(revokeObjectUrlMock).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  });

  it('imports a recording bundle and shows the backend warnings', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (url === '/api/recordings' && method === 'GET') {
        return {
          ok: true,
          json: async () => recordingsPayload
        } as Response;
      }

      if (url === '/api/importexport/recordings/import' && method === 'POST') {
        return {
          ok: true,
          json: async () => importRecordingResultPayload
        } as Response;
      }

      throw new Error(`Unexpected fetch ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await renderAppAt('/importexport');

    expect(
      await screen.findByRole('heading', { level: 1, name: '导入导出' })
    ).toBeInTheDocument();

    const bundleFile = new File(['bundle'], 'recording-bundle.zip', {
      type: 'application/zip'
    });
    fireEvent.change(screen.getByLabelText('选择资料包'), {
      target: { files: [bundleFile] }
    });

    fireEvent.click(screen.getByRole('button', { name: '导入资料包' }));

    expect(await screen.findByText('已导入录制 recording-1。')).toBeInTheDocument();
    expect(
      screen.getByText(
        '导入警告：浏览器 profile 与活跃登录态不会随资料包导出；导入后的会话仅保留历史上下文，如需继续执行请准备新的可用会话。'
      )
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/importexport/recordings/import',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData)
      })
    );
  });
});
