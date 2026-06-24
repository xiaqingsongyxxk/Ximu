import { useMemo, useState } from 'react';
import { ZoomIn, ZoomOut } from 'lucide-react';
import ResumePreview from '@/components/preview/ResumePreview';
import { useResumeStore } from '@/stores/resume-store';
import type { Resume } from '@/types/resume';

const A4_WIDTH = 794;

interface EditorPreviewPanelProps {
  className?: string;
}

export function EditorPreviewPanel({ className }: EditorPreviewPanelProps = {}) {
  const { currentResume, sections } = useResumeStore();
  const [zoom, setZoom] = useState(80);

  const liveResume = useMemo<Resume | null>(() => {
    if (!currentResume) return null;
    return { ...currentResume, sections } as Resume;
  }, [currentResume, sections]);

  if (!liveResume) return null;

  const scale = zoom / 100;

  return (
    <div className={`flex min-w-0 flex-[6] flex-col border-l border-border bg-background ${className ?? ''}`}>
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-card px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">预览</span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(30, z - 10))}
            disabled={zoom <= 30}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded transition-colors hover:bg-accent disabled:opacity-40"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="w-10 text-center text-xs text-muted-foreground">{zoom}%</span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(150, z + 10))}
            disabled={zoom >= 150}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded transition-colors hover:bg-accent disabled:opacity-40"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="flex justify-center p-4">
          <div
            className="bg-white shadow-md"
            style={{ width: '100%', maxWidth: A4_WIDTH, zoom: scale }}
          >
            <ResumePreview resume={liveResume} />
          </div>
        </div>
      </div>
    </div>
  );
}
