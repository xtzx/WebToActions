import type {
  ReviewContext,
  ReviewedMetadataDetail,
  SaveReviewedMetadataPayload
} from '../types/review';

const REVIEWS_ENDPOINT = '/api/reviews';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function fetchReviewContext(recordingId: string): Promise<ReviewContext> {
  const response = await fetch(`${REVIEWS_ENDPOINT}/${recordingId}`, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });
  return parseJson<ReviewContext>(response);
}

export async function saveReviewedMetadata(
  recordingId: string,
  payload: SaveReviewedMetadataPayload
): Promise<ReviewedMetadataDetail> {
  const response = await fetch(`${REVIEWS_ENDPOINT}/${recordingId}/reviewed-metadata`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return parseJson<ReviewedMetadataDetail>(response);
}
