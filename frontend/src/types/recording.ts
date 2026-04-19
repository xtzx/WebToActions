export interface RecordingSummary {
  id: string;
  name: string;
  startUrl: string;
  browserSessionId: string;
  status: string;
  createdAt: string;
  startedAt: string | null;
  endedAt: string | null;
  currentUrl: string;
  requestCount: number;
  pageStageCount: number;
  fileTransferCount: number;
  sessionSnapshotCount: number;
  failedRequestCount: number;
}

export interface RecordingListResponse {
  items: RecordingSummary[];
}

export interface RecordingPageStage {
  id: string;
  url: string;
  name: string;
  startedAt: string;
  endedAt: string | null;
  relatedRequestIds: string[];
  waitPoints: string[];
  observableState: Record<string, string>;
}

export interface RecordingRequestHeader {
  name: string;
  value: string;
}

export interface RecordingRequestRecord {
  id: string;
  requestMethod: string;
  requestUrl: string;
  requestedAt: string;
  requestHeaders: RecordingRequestHeader[];
  requestBodyBlobKey: string | null;
  responseStatus: number | null;
  responseHeaders: RecordingRequestHeader[];
  responseBodyBlobKey: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  pageStageId: string | null;
  failureReason: string | null;
}

export interface SessionSnapshotRecord {
  id: string;
  browserSessionId: string;
  capturedAt: string;
  pageStageId: string | null;
  requestId: string | null;
  cookieSummary: Record<string, string>;
  storageSummary: Record<string, Record<string, string>>;
}

export interface FileTransferRecord {
  id: string;
  direction: string;
  fileName: string;
  occurredAt: string;
  relatedRequestId: string | null;
  sourcePathSummary: string | null;
  targetPathSummary: string | null;
  notes: string | null;
}

export interface RecordingDetail extends RecordingSummary {
  pageStages: RecordingPageStage[];
  requests: RecordingRequestRecord[];
  sessionSnapshots: SessionSnapshotRecord[];
  fileTransfers: FileTransferRecord[];
}

export interface RecordingStreamSnapshot {
  recordingId: string;
  status: string;
  currentUrl: string;
  requestCount: number;
  pageStageCount: number;
  fileTransferCount: number;
  updatedAt: string;
}

export interface CreateRecordingPayload {
  name: string;
  startUrl: string;
  browserSessionId?: string;
}
