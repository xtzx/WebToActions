export interface ActionSummary {
  id: string;
  version: number;
  previousVersion: number | null;
  recordingId: string;
  name: string;
  description: string | null;
  stepCount: number;
  parameterCount: number;
  createdAt: string;
}

export interface ActionMacroStep {
  id: string;
  stepKind: string;
  title: string;
  requestId: string;
  requestMethod: string;
  requestUrl: string;
  pageStageId: string | null;
  navigateUrl: string | null;
}

export interface ActionParameterDefinition {
  id: string;
  actionId: string;
  ownerKind: string;
  name: string;
  parameterKind: string;
  required: boolean;
  defaultValue: string | number | boolean | null;
  injectionTarget: string;
  description: string | null;
}

export interface ActionDetail extends ActionSummary {
  sourceReviewedMetadataId: string;
  sourceReviewedMetadataVersion: number;
  steps: ActionMacroStep[];
  requiredPageStageIds: string[];
  parameterDefinitions: ActionParameterDefinition[];
  sessionRequirements: string[];
}

export interface ActionListResponse {
  items: ActionSummary[];
}

export interface CreateActionMacroPayload {
  recordingId: string;
  name?: string;
  description?: string;
}

export interface StartActionExecutionPayload {
  browserSessionId: string;
  parameters: Record<string, unknown>;
}
