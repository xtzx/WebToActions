export interface HealthResponse {
  status: string;
  stage?: string;
  [key: string]: unknown;
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
      `Health check failed: ${response.status} ${response.statusText}`
    );
  }

  return (await response.json()) as HealthResponse;
}
