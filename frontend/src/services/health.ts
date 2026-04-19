export interface HealthResponse {
  status: string;
  phase: string;
  appName: string;
  environment: string;
  apiPrefix: string;
  targetPython: string;
  runtimePython: string;
  dataDir: string;
  browserChannel: string;
  browserHeadless: boolean;
}

const HEALTH_ENDPOINT = '/api/health';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(HEALTH_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(
      `健康检查失败：${response.status} ${response.statusText}`
    );
  }

  return (await response.json()) as HealthResponse;
}
