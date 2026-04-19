import { cleanup, fireEvent, render, screen } from '@testing-library/react';

const healthPayload = {
  status: 'ok',
  phase: 'stage1',
  appName: 'WebToActions Backend',
  environment: 'development',
  apiPrefix: '/api',
  targetPython: '3.11+',
  runtimePython: '3.11.11',
  dataDir: '.webtoactions',
  browserChannel: 'chromium',
  browserHeadless: false
};

async function renderAppAt(path = '/') {
  window.history.pushState({}, '', path);
  const { default: App } = await import('./App');
  return render(<App />);
}

describe('App', () => {
  beforeEach(() => {
    vi.resetModules();
    window.history.pushState({}, '', '/');
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

  it('navigates to placeholder pages from the primary nav', async () => {
    await renderAppAt();

    fireEvent.click(screen.getByRole('link', { name: '录制中心' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: '录制中心' })
    ).toBeInTheDocument();
    expect(
      screen.getByText('阶段 1 只保留正式导航入口，后续阶段再接入真实能力。')
    ).toBeInTheDocument();
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
        '后端响应正常，status="ok"，phase="stage1"，targetPython="3.11+"。'
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/"phase": "stage1"/)).toBeInTheDocument();
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
});
