import type { ExecutionListResponse, ExecutionRunDetail } from '../types/execution';

const EXECUTIONS_ENDPOINT = '/api/executions';

async function buildError(response: Response): Promise<Error> {
  const contentType = response.headers?.get?.('content-type') ?? '';

  if (contentType.includes('application/json')) {
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        return new Error(payload.detail);
      }
    } catch {
      // fall through to plain-text handling
    }
  }

  try {
    const message = (await response.text()).trim();
    if (message) {
      return new Error(message);
    }
  } catch {
    // ignore and use status fallback
  }

  return new Error(`请求失败：${response.status} ${response.statusText}`);
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await buildError(response);
  }

  return (await response.json()) as T;
}

export async function fetchExecutions(): Promise<ExecutionListResponse> {
  const response = await fetch(EXECUTIONS_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<ExecutionListResponse>(response);
}

export async function fetchExecutionDetail(
  executionId: string
): Promise<ExecutionRunDetail> {
  const response = await fetch(`${EXECUTIONS_ENDPOINT}/${executionId}`, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<ExecutionRunDetail>(response);
}
