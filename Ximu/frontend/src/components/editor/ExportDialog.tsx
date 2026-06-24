import { useCallback, useEffect, useState } from 'react';
import { X, Loader2, AlertCircle, FileDown, Globe, AlignLeft, Braces, Download } from 'lucide-react';
import { useResumeStore } from '@/stores/resume-store';
import { exportJson, exportTxt, exportPdf } from '@/lib/api';
import { extractPreviewHtml, downloadHtml, downloadBlob } from '@/lib/export-utils';

interface ExportDialogProps {
  resumeId: string;
  resumeTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type ExportStatus = 'idle' | 'exporting' | 'done' | 'error';

const FORMAT_OPTIONS = [
  { key: 'pdf', label: 'PDF', description: '可打印文档', icon: FileDown },
  { key: 'html', label: 'HTML', description: '网页格式', icon: Globe },
  { key: 'txt', label: '纯文本', description: '简单文本文件', icon: AlignLeft },
  { key: 'json', label: 'JSON', description: '结构化数据', icon: Braces },
] as const;

export function ExportDialog({
  resumeId,
  resumeTitle,
  open,
  onOpenChange,
}: ExportDialogProps) {
  const [status, setStatus] = useState<ExportStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'done') {
      const timer = setTimeout(() => {
        setStatus('idle');
        setSelectedFormat(null);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  const handleExport = useCallback(async () => {
    if (!selectedFormat) return;

    setStatus('exporting');
    setErrorMessage('');

    try {
      await useResumeStore.getState().save();

      const safeTitle = resumeTitle || 'resume';
      const filename = `${safeTitle}-${Date.now()}`;

      switch (selectedFormat) {
        case 'json': {
          const blob = await exportJson(resumeId);
          downloadBlob(blob, `${filename}.json`);
          break;
        }
        case 'txt': {
          const blob = await exportTxt(resumeId);
          downloadBlob(blob, `${filename}.txt`);
          break;
        }
        case 'html': {
          const html = extractPreviewHtml();
          if (!html) {
            throw new Error('无法提取简历预览内容，请确认预览区域已加载');
          }
          downloadHtml(html, `${filename}.html`);
          break;
        }
        case 'pdf': {
          const html = extractPreviewHtml();
          if (!html) {
            throw new Error('无法提取简历预览内容，请确认预览区域已加载');
          }
          const blob = await exportPdf(html);
          downloadBlob(blob, `${filename}.pdf`);
          break;
        }
        default:
          throw new Error(`不支持的格式: ${selectedFormat}`);
      }

      setStatus('done');
    } catch (err: unknown) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : '导出失败，请重试');
    }
  }, [resumeId, resumeTitle, selectedFormat]);

  const handleClose = useCallback(() => {
    setStatus('idle');
    setErrorMessage('');
    setSelectedFormat(null);
    onOpenChange(false);
  }, [onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="flex w-[480px] max-h-[85vh] flex-col rounded-xl bg-card border-border shadow-2xl">
        <div className="flex items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-pink-500/10">
              <Download className="h-4 w-4 text-pink-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">
                导出简历
              </h2>
              <p className="text-xs text-muted-foreground">
                选择导出格式下载简历
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 pb-6">
          {status === 'idle' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                {FORMAT_OPTIONS.map(({ key, label, description, icon: Icon }) => {
                  const isSelected = selectedFormat === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedFormat(key)}
                      className={`flex flex-col items-center gap-2 rounded-xl border p-5 transition-all ${
                        isSelected
                          ? 'border-pink-500/40 bg-pink-500/10'
                          : 'border-border bg-muted hover:border-muted-foreground/50'
                      }`}
                    >
                      <Icon
                        className={`h-7 w-7 ${
                          isSelected ? 'text-pink-400' : 'text-muted-foreground'
                        }`}
                      />
                      <span
                        className={`text-sm font-medium ${
                          isSelected ? 'text-pink-400' : 'text-foreground'
                        }`}
                      >
                        {label}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {description}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-lg bg-secondary px-5 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={!selectedFormat}
                  className="rounded-lg bg-pink-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-pink-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  导出
                </button>
              </div>
            </>
          )}

          {status === 'exporting' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8">
              <Loader2 className="h-8 w-8 animate-spin text-pink-500" />
              <p className="text-sm text-muted-foreground">
                正在生成{selectedFormat ? ` ${FORMAT_OPTIONS.find(f => f.key === selectedFormat)?.label}` : ''}...
              </p>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 py-8">
              <AlertCircle className="h-10 w-10 text-red-500" />
              <p className="text-sm text-red-400">
                {errorMessage}
              </p>
              <button
                type="button"
                onClick={() => {
                  setStatus('idle');
                  setErrorMessage('');
                }}
                className="rounded-lg bg-pink-500 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-pink-600"
              >
                重试
              </button>
            </div>
          )}

          {status === 'done' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
                <svg
                  className="h-6 w-6 text-green-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm font-medium text-green-400">
                导出成功
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}