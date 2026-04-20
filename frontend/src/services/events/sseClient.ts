import type { RecordingStreamSnapshot } from '../../types/recording';
import type { ExecutionStreamSnapshot } from '../../types/execution';

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

export function subscribeToExecutionStream(
  executionId: string,
  onMessage: (payload: ExecutionStreamSnapshot) => void,
  onError?: () => void
): StreamSubscription {
  const eventSource = new EventSource(`/api/executions/${executionId}/events`);
  eventSource.onmessage = (event) => {
    onMessage(JSON.parse(event.data) as ExecutionStreamSnapshot);
  };
  eventSource.onerror = () => {
    eventSource.close();
    onError?.();
  };
  return {
    close: () => eventSource.close()
  };
}
