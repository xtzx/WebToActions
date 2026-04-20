import type {
  ImportRecordingBundleResult,
  RecordingBundleDownload
} from '../types/importexport';

const IMPORTEXPORT_ENDPOINT = '/api/importexport';

async function buildError(response: Response): Promise<Error> {
  const contentType = response.headers?.get?.('content-type') ?? '';

  if (contentType.includes('application/json')) {
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        return new Error(payload.detail);
      }
    } catch {
      // fall through to plain-text handling
    }
  }

  try {
    const message = (await response.text()).trim();
    if (message) {
      return new Error(message);
    }
  } catch {
    // ignore and use status fallback
  }

  return new Error(`请求失败：${response.status} ${response.statusText}`);
}

function parseDownloadFileName(response: Response, recordingId: string): string {
  const contentDisposition = response.headers?.get?.('content-disposition') ?? '';
  const match = /filename="?([^"]+)"?/.exec(contentDisposition);
  return match?.[1] ?? `${recordingId}-bundle.zip`;
}

export async function exportRecordingBundle(
  recordingId: string
): Promise<RecordingBundleDownload> {
  const response = await fetch(`${IMPORTEXPORT_ENDPOINT}/recordings/${recordingId}/bundle`, {
    method: 'GET',
    headers: {
      Accept: 'application/zip'
    }
  });

  if (!response.ok) {
    throw await buildError(response);
  }

  return {
    blob: await response.blob(),
    fileName: parseDownloadFileName(response, recordingId)
  };
}

export async function importRecordingBundle(
  bundleFile: File
): Promise<ImportRecordingBundleResult> {
  const formData = new FormData();
  formData.append('file', bundleFile);

  const response = await fetch(`${IMPORTEXPORT_ENDPOINT}/recordings/import`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw await buildError(response);
  }

  return (await response.json()) as ImportRecordingBundleResult;
}
