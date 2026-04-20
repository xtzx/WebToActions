import { useEffect } from 'react';

import type { ReviewJobSnapshot } from '../../types/review';

export function useReviewJobStream(
  recordingId: string | undefined,
  enabled: boolean,
  onMessage: (payload: ReviewJobSnapshot) => void,
  onError?: () => void
) {
  useEffect(() => {
    if (!recordingId || !enabled) {
      return;
    }

    const eventSource = new EventSource(`/api/reviews/${recordingId}/events`);
    eventSource.onmessage = (event) => {
      onMessage(JSON.parse(event.data) as ReviewJobSnapshot);
    };
    eventSource.onerror = () => {
      eventSource.close();
      onError?.();
    };

    return () => {
      eventSource.close();
    };
  }, [enabled, onError, onMessage, recordingId]);
}
