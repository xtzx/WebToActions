import { useEffect } from 'react';

import type { ReviewJobSnapshot } from '../../types/review';

export function useReviewJobStream(
  recordingId: string | undefined,
  enabled: boolean,
  onMessage: (payload: ReviewJobSnapshot) => void
) {
  useEffect(() => {
    if (!recordingId || !enabled) {
      return;
    }

    const eventSource = new EventSource(`/api/reviews/${recordingId}/events`);
    eventSource.onmessage = (event) => {
      onMessage(JSON.parse(event.data) as ReviewJobSnapshot);
    };

    return () => {
      eventSource.close();
    };
  }, [enabled, onMessage, recordingId]);
}
