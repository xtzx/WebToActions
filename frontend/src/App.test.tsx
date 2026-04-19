import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { act } from 'react';

const healthPayload = {
  status: 'ok',
  phase: 'stage4',
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
        '后端响应正常，status="ok"，phase="stage4"，targetPython="3.11+"。'
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/"phase": "stage4"/)).toBeInTheDocument();
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
    expect(MockEventSource.instances[0]?.url).toBe('/api/reviews/recording-1/events');

    await act(async () => {
      MockEventSource.instances[0]?.emit({
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
});
