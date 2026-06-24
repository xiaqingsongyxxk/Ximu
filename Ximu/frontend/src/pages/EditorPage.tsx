import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useEditorStore } from '@/stores/editor-store';
import { useResumeStore } from '@/stores/resume-store';
import { useEditor } from '@/hooks/use-editor';
import EditorToolbar from '@/components/editor/EditorToolbar';
import { EditorSidebar } from '@/components/editor/EditorSidebar';
import { EditorCanvas } from '@/components/editor/EditorCanvas';
import { ThemeEditor } from '@/components/editor/ThemeEditor';
import { EditorPreviewPanel } from '@/components/editor/EditorPreviewPanel';
import { CoverLetterDialog } from '@/components/editor/CoverLetterDialog';
import { ExportDialog } from '@/components/editor/ExportDialog';
import { DraggableAIChatButton, AIChatProvider } from '@/components/editor/DraggableAIChatButton';
import SettingsModal from '@/components/settings/SettingsModal';
import { Inbox, FileX } from 'lucide-react';
import { mockResume } from '@/data/mockResume';
import { fetchWorkspaces, fetchResumeDetail } from '@/lib/api';

export default function EditorPage() {
  const { id, resumeId } = useParams<{ id: string; resumeId?: string }>();
  const effectiveResumeId = resumeId || id;
  const navigate = useNavigate();
  const { showThemeEditor, toggleThemeEditor } = useEditorStore();
  const { updateSection, addSection, removeSection, reorderSections, loadResume } = useEditor(effectiveResumeId || 'mock-1');
  const { sections, setResume, currentResume } = useResumeStore();
  const [loading, setLoading] = useState(true);
  const [coverLetterOpen, setCoverLetterOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [workspaceNotFound, setWorkspaceNotFound] = useState(false);
  const [resumeNotFound, setResumeNotFound] = useState(false);

  useEffect(() => {
    if (!effectiveResumeId) return;

    // 校验 workspace (id) 和子简历 (resumeId) 是否存在
    Promise.all([
      id ? fetchWorkspaces().catch(() => null) : Promise.resolve(null),
      fetchResumeDetail(effectiveResumeId).catch(() => null),
    ])
      .then(([workspaces, resumeData]) => {
        if (id) {
          const ws = workspaces?.find((w) => w.id === id);
          if (!ws) {
            setWorkspaceNotFound(true);
            return;
          }
        }
        if (resumeId && !resumeData) {
          setResumeNotFound(true);
          return;
        }
        return loadResume();
      })
      .finally(() => {
        if (!workspaceNotFound && !resumeNotFound) {
          if (!useResumeStore.getState().currentResume) {
            setResume(mockResume);
          }
        }
        setLoading(false);
      });
  }, [effectiveResumeId, id, resumeId, loadResume, setResume, workspaceNotFound, resumeNotFound]);

  if (workspaceNotFound) {
    return (
      <div className="flex h-screen items-center justify-center bg-muted">
        <div className="flex flex-col items-center justify-center text-gray-400 gap-4">
          <Inbox className="w-16 h-16 text-gray-400/40" strokeWidth={1.5} />
          <div className="text-center">
            <p className="text-lg text-gray-300 mb-1">工作空间不存在</p>
            <p className="text-sm text-gray-500">访问的工作空间可能已被删除或不存在</p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/workspace')}
            className="mt-2 px-4 py-2 rounded-lg bg-pink-500/20 text-pink-400 hover:bg-pink-500/30 transition-colors text-sm"
          >
            返回工作空间列表
          </button>
        </div>
      </div>
    );
  }

  if (resumeNotFound) {
    return (
      <div className="flex h-screen items-center justify-center bg-muted">
        <div className="flex flex-col items-center justify-center text-gray-400 gap-4">
          <FileX className="w-16 h-16 text-gray-400/40" strokeWidth={1.5} />
          <div className="text-center">
            <p className="text-lg text-gray-300 mb-1">子简历不存在</p>
            <p className="text-sm text-gray-500">访问的子简历可能已被删除或不存在</p>
          </div>
          <button
            type="button"
            onClick={() => id ? navigate(`/workspace/${id}`) : navigate('/workspace')}
            className="mt-2 px-4 py-2 rounded-lg bg-pink-500/20 text-pink-400 hover:bg-pink-500/30 transition-colors text-sm"
          >
            返回工作空间详情
          </button>
        </div>
      </div>
    );
  }

  if (loading || !currentResume) {
    return (
      <div className="flex h-screen items-center justify-center bg-muted">
        <div className="space-y-4 text-zinc-500">加载中...</div>
      </div>
    );
  }

  const backUrl = id ? `/workspace/${id}` : '/';

  return (
    <div className="flex h-screen flex-col bg-muted">
      <EditorToolbar
        title={currentResume.title}
        onBack={() => navigate(backUrl)}
        onCoverLetterOpen={() => setCoverLetterOpen(true)}
        onExport={() => setExportOpen(true)}
        onThemeToggle={toggleThemeEditor}
        onSettings={() => setShowSettings(true)}
        themeActive={showThemeEditor}
      />
      <AIChatProvider>
        <div className="flex flex-1 overflow-hidden">
          <EditorSidebar
            sections={sections}
            onAddSection={addSection}
            onReorderSections={reorderSections}
          />
          <EditorCanvas
            sections={sections}
            onUpdateSection={updateSection}
            onRemoveSection={removeSection}
            onReorderSections={reorderSections}
            className="flex-[4]"
          />
          {showThemeEditor && <ThemeEditor />}
          <EditorPreviewPanel />
        </div>
        <DraggableAIChatButton />
      </AIChatProvider>
      <ExportDialog
        resumeId={currentResume.id}
        resumeTitle={currentResume.title}
        open={exportOpen}
        onOpenChange={setExportOpen}
      />
      <CoverLetterDialog
        resumeId={currentResume.id}
        open={coverLetterOpen}
        onOpenChange={setCoverLetterOpen}
      />
      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}
