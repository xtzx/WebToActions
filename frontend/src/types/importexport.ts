export interface RecordingBundleDownload {
  blob: Blob;
  fileName: string;
}

export interface ImportRecordingBundleResult {
  recordingId: string;
  actionIds: string[];
  executionIds: string[];
  warnings: string[];
}
