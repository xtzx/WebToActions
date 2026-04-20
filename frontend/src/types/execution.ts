export interface ExecutionStepOutcome {
  stepId: string;
  requestId: string | null;
  requestBodyPreview: string | null;
  responseStatus: number | null;
}

export interface ExecutionDiagnostics {
  currentStepId?: string;
  currentStepTitle?: string;
  currentUrl?: string;
  failedStepId?: string;
  failedStepTitle?: string;
  finalUrl?: string;
  stepOutcomes?: ExecutionStepOutcome[];
  [key: string]: unknown;
}

export interface ExecutionRunDetail {
  id: string;
  actionKind: string;
  actionId: string;
  actionVersion: number;
  browserSessionId: string;
  parametersSnapshot: Record<string, unknown>;
  status: string;
  createdAt: string;
  startedAt: string | null;
  endedAt: string | null;
  stepLogs: string[];
  failureReason: string | null;
  diagnostics: ExecutionDiagnostics;
}

export interface ExecutionListResponse {
  items: ExecutionRunDetail[];
}

export interface ExecutionStreamSnapshot {
  executionId: string;
  status: string;
  currentStepId: string | null;
  currentStepTitle: string | null;
  currentUrl: string | null;
  logCount: number;
  failureReason: string | null;
  updatedAt: string;
}
