import type {
  CreateRecordingPayload,
  RecordingDetail,
  RecordingListResponse,
  RecordingSummary
} from '../types/recording';

const RECORDINGS_ENDPOINT = '/api/recordings';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function fetchRecordings(): Promise<RecordingListResponse> {
  const response = await fetch(RECORDINGS_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<RecordingListResponse>(response);
}

export async function startRecording(
  payload: CreateRecordingPayload
): Promise<RecordingSummary> {
  const response = await fetch(RECORDINGS_ENDPOINT, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return parseJson<RecordingSummary>(response);
}

export async function fetchRecordingDetail(
  recordingId: string
): Promise<RecordingDetail> {
  const response = await fetch(`${RECORDINGS_ENDPOINT}/${recordingId}`, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<RecordingDetail>(response);
}

export async function stopRecording(recordingId: string): Promise<RecordingDetail> {
  const response = await fetch(`${RECORDINGS_ENDPOINT}/${recordingId}/stop`, {
    method: 'POST',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<RecordingDetail>(response);
}
