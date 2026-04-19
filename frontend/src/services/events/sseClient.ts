import type { RecordingStreamSnapshot } from '../../types/recording';

export interface StreamSubscription {
  close: () => void;
}

export function subscribeToRecordingStream(
  recordingId: string,
  onMessage: (payload: RecordingStreamSnapshot) => void
): StreamSubscription {
  const eventSource = new EventSource(`/api/recordings/${recordingId}/events`);
  eventSource.onmessage = (event) => {
    onMessage(JSON.parse(event.data) as RecordingStreamSnapshot);
  };
  return {
    close: () => eventSource.close()
  };
}
