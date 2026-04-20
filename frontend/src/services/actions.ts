import type {
  ActionDetail,
  ActionListResponse,
  CreateActionMacroPayload,
  StartActionExecutionPayload
} from '../types/action';
import type { ExecutionRunDetail } from '../types/execution';

const ACTIONS_ENDPOINT = '/api/actions';

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

export async function fetchActions(): Promise<ActionListResponse> {
  const response = await fetch(ACTIONS_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<ActionListResponse>(response);
}

export async function fetchActionDetail(actionId: string): Promise<ActionDetail> {
  const response = await fetch(`${ACTIONS_ENDPOINT}/${actionId}`, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<ActionDetail>(response);
}

export async function createActionMacro(
  payload: CreateActionMacroPayload
): Promise<ActionDetail> {
  const response = await fetch(ACTIONS_ENDPOINT, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return parseJson<ActionDetail>(response);
}

export async function startActionExecution(
  actionId: string,
  payload: StartActionExecutionPayload
): Promise<ExecutionRunDetail> {
  const response = await fetch(`${ACTIONS_ENDPOINT}/${actionId}/executions`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return parseJson<ExecutionRunDetail>(response);
}
