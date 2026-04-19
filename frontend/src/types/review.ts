export interface ReviewRequestSummary {
  id: string;
  requestMethod: string;
  requestUrl: string;
  responseStatus: number | null;
  pageStageId: string | null;
}

export interface ReviewPageStageSummary {
  id: string;
  name: string;
  url: string;
  relatedRequestIds: string[];
}

export interface ParameterSuggestion {
  name: string;
  source: string;
  exampleValue: string | null;
  reason: string | null;
}

export interface ActionFragmentSuggestion {
  id: string;
  title: string;
  stageId: string;
  requestIds: string[];
  notes: string | null;
}

export interface MetadataDraftDetail {
  id: string;
  version: number;
  previousVersion: number | null;
  recordingId: string;
  candidateRequestIds: string[];
  parameterSuggestions: ParameterSuggestion[];
  actionFragmentSuggestions: ActionFragmentSuggestion[];
  analysisNotes: string | null;
  generatedAt: string;
}

export interface ReviewedMetadataDetail {
  id: string;
  version: number;
  previousVersion: number | null;
  recordingId: string;
  reviewer: string;
  sourceDraftId: string;
  sourceDraftVersion: number;
  keyRequestIds: string[];
  noiseRequestIds: string[];
  fieldDescriptions: Record<string, string>;
  parameterSourceMap: Record<string, string>;
  actionStageIds: string[];
  riskFlags: string[];
  reviewedAt?: string;
}

export interface ReviewContext {
  recordingId: string;
  analysisStatus: string;
  latestDraft: MetadataDraftDetail | null;
  latestReviewedMetadata: ReviewedMetadataDetail | null;
  reviewHistory: ReviewedMetadataDetail[];
  requests: ReviewRequestSummary[];
  pageStages: ReviewPageStageSummary[];
}

export interface ReviewJobSnapshot {
  recordingId: string;
  status: string;
  latestDraftVersion: number | null;
  error: string | null;
  updatedAt: string;
}

export interface SaveReviewedMetadataPayload {
  reviewer: string;
  sourceDraftId: string;
  sourceDraftVersion: number;
  keyRequestIds: string[];
  noiseRequestIds: string[];
  fieldDescriptions: Record<string, string>;
  parameterSourceMap: Record<string, string>;
  actionStageIds: string[];
  riskFlags: string[];
}
