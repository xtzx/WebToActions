import { useEffect, useMemo, useState, type ChangeEvent, type CSSProperties } from 'react';

import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { exportRecordingBundle, importRecordingBundle } from '../../services/importexport';
import { fetchRecordings } from '../../services/recordings';
import type { ImportRecordingBundleResult } from '../../types/importexport';
import type { RecordingSummary } from '../../types/recording';

const containerStyle: CSSProperties = {
  width: '100%',
  maxWidth: '1120px',
  display: 'grid',
  gap: '24px'
};

const panelGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
  gap: '20px'
};

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '20px',
  padding: '28px',
  boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)',
  display: 'grid',
  gap: '18px',
  alignContent: 'start'
};

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  width: 'fit-content',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#eef2ff',
  color: '#3745a5',
  fontWeight: 700
};

const labelStyle: CSSProperties = {
  display: 'grid',
  gap: '8px',
  color: '#344054',
  fontWeight: 600
};

const inputStyle: CSSProperties = {
  width: '100%',
  borderRadius: '12px',
  border: '1px solid #cbd5e1',
  padding: '12px 14px',
  fontSize: '14px'
};

const buttonStyle: CSSProperties = {
  border: 0,
  borderRadius: '12px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontWeight: 700,
  cursor: 'pointer'
};

const noteStyle: CSSProperties = {
  margin: 0,
  padding: '14px 16px',
  borderRadius: '14px',
  background: '#f5f7fb',
  color: '#344054'
};

const successStyle: CSSProperties = {
  margin: 0,
  padding: '14px 16px',
  borderRadius: '14px',
  background: '#ecfdf3',
  color: '#067647'
};

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gap: '10px',
  padding: '18px',
  borderRadius: '16px',
  background: '#f8fbff',
  border: '1px solid #d8e0ee'
};

function triggerBrowserDownload(blob: Blob, fileName: string) {
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(downloadUrl);
}

export function ImportExportPage() {
  const [recordings, setRecordings] = useState<RecordingSummary[]>([]);
  const [selectedRecordingId, setSelectedRecordingId] = useState('');
  const [bundleFile, setBundleFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exportSuccessMessage, setExportSuccessMessage] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportRecordingBundleResult | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetchRecordings();
        if (cancelled) {
          return;
        }
        setRecordings(response.items);
        setSelectedRecordingId((current) => current || response.items[0]?.id || '');
        setErrorMessage(null);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '录制列表加载失败。');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedRecording = useMemo(
    () => recordings.find((item) => item.id === selectedRecordingId) ?? null,
    [recordings, selectedRecordingId]
  );

  async function handleExport() {
    if (!selectedRecordingId) {
      setErrorMessage('请先选择一条录制。');
      return;
    }

    setExporting(true);
    setErrorMessage(null);
    setImportResult(null);
    try {
      const result = await exportRecordingBundle(selectedRecordingId);
      triggerBrowserDownload(result.blob, result.fileName);
      setExportSuccessMessage('导出完成，浏览器已开始下载资料包。');
    } catch (error) {
      setExportSuccessMessage(null);
      setErrorMessage(error instanceof Error ? error.message : '录制资料包导出失败。');
    } finally {
      setExporting(false);
    }
  }

  function handleBundleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setBundleFile(event.target.files?.[0] ?? null);
  }

  async function handleImport() {
    if (!bundleFile) {
      setErrorMessage('请先选择一个资料包文件。');
      return;
    }

    setImporting(true);
    setErrorMessage(null);
    setExportSuccessMessage(null);
    try {
      const result = await importRecordingBundle(bundleFile);
      setImportResult(result);
      const refreshed = await fetchRecordings();
      setRecordings(refreshed.items);
      setSelectedRecordingId((current) => current || refreshed.items[0]?.id || '');
    } catch (error) {
      setImportResult(null);
      setErrorMessage(error instanceof Error ? error.message : '资料包导入失败。');
    } finally {
      setImporting(false);
    }
  }

  return (
    <section style={containerStyle}>
      <div style={panelStyle}>
        <span style={badgeStyle}>Stage 6 Recording Bundle</span>
        <h1 style={{ margin: 0 }}>导入导出</h1>
        <p style={{ margin: 0, color: '#475467' }}>
          导出单条录制链路资料包，或将资料包导入当前工作区，恢复录制、审核、动作宏与执行记录。
        </p>
      </div>

      {loading ? <p style={noteStyle}>正在加载录制列表...</p> : null}
      {errorMessage ? <ErrorState message={errorMessage} title="导入导出操作失败" /> : null}
      {exportSuccessMessage ? <p style={successStyle}>{exportSuccessMessage}</p> : null}
      {importResult ? (
        <div style={panelStyle}>
          <p style={successStyle}>已导入录制 {importResult.recordingId}。</p>
          <p style={{ margin: 0, color: '#475467' }}>
            关联动作宏 {importResult.actionIds.length} 个，执行记录 {importResult.executionIds.length} 条。
          </p>
          {importResult.warnings.map((warning) => (
            <p key={warning} style={noteStyle}>
              导入警告：{warning}
            </p>
          ))}
        </div>
      ) : null}

      {!loading ? (
        <div style={panelGridStyle}>
          <div style={panelStyle}>
            <h2 style={{ margin: 0 }}>导出录制资料包</h2>
            <label style={labelStyle}>
              选择录制
              <select
                aria-label="选择录制"
                value={selectedRecordingId}
                onChange={(event) => setSelectedRecordingId(event.target.value)}
                style={inputStyle}
              >
                {recordings.length === 0 ? <option value="">当前没有可导出的录制</option> : null}
                {recordings.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            {selectedRecording ? (
              <div style={detailGridStyle}>
                <strong>{selectedRecording.name}</strong>
                <span>录制 ID：{selectedRecording.id}</span>
                <span>状态：{selectedRecording.status}</span>
                <span>请求数：{selectedRecording.requestCount}</span>
                <span>页面阶段：{selectedRecording.pageStageCount}</span>
                <span>文件传输：{selectedRecording.fileTransferCount}</span>
              </div>
            ) : (
              <EmptyState message="当前还没有可导出的录制，请先完成一条录制链路。" />
            )}

            <button
              type="button"
              onClick={() => void handleExport()}
              disabled={!selectedRecording || exporting}
              style={{
                ...buttonStyle,
                opacity: !selectedRecording || exporting ? 0.72 : 1,
                cursor: !selectedRecording || exporting ? 'not-allowed' : 'pointer'
              }}
            >
              {exporting ? '正在导出...' : '导出资料包'}
            </button>
          </div>

          <div style={panelStyle}>
            <h2 style={{ margin: 0 }}>导入资料包</h2>
            <label htmlFor="bundle-file-input" style={labelStyle}>
              选择资料包
            </label>
            <input
              id="bundle-file-input"
              aria-label="选择资料包"
              type="file"
              accept=".zip,application/zip"
              onChange={handleBundleFileChange}
              style={inputStyle}
            />
            <p style={noteStyle}>
              当前只支持 `RECORDING` 单条链路资料包。导入后浏览器登录态不会自动恢复，需要重新登录。
            </p>
            <button
              type="button"
              onClick={() => void handleImport()}
              disabled={!bundleFile || importing}
              style={{
                ...buttonStyle,
                background: '#0f766e',
                opacity: !bundleFile || importing ? 0.72 : 1,
                cursor: !bundleFile || importing ? 'not-allowed' : 'pointer'
              }}
            >
              {importing ? '正在导入...' : '导入资料包'}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
