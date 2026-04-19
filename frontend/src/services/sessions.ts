import type {
  BrowserSessionListResponse,
  BrowserSessionSummary
} from '../types/session';

const SESSIONS_ENDPOINT = '/api/sessions';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function fetchSessions(): Promise<BrowserSessionListResponse> {
  const response = await fetch(SESSIONS_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<BrowserSessionListResponse>(response);
}

export async function createSession(): Promise<BrowserSessionSummary> {
  const response = await fetch(SESSIONS_ENDPOINT, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  });
  return parseJson<BrowserSessionSummary>(response);
}
