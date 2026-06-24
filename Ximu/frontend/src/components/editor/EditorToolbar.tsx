import {
  ArrowLeft,
  Download,
  Settings,
  Palette,
  Save,
  FileSearch,
  Languages,
  FileText,
  SpellCheck,
} from 'lucide-react'
import { useResumeStore } from '@/stores/resume-store';

interface EditorToolbarProps {
  title?: string
  onBack?: () => void
  onCoverLetterOpen?: () => void
  onThemeToggle?: () => void
  onSettings?: () => void
  onExport?: () => void
  themeActive?: boolean
}

/**
 * Editor toolbar with action buttons.
 * Migrated from JadeAI editor. Button handlers are TODO placeholders.
 */
export default function EditorToolbar({ title = '未命名简历', onBack, onCoverLetterOpen, onThemeToggle, onSettings, onExport, themeActive }: EditorToolbarProps) {
  const { isSaving, isDirty } = useResumeStore();

  const saveLabel = isSaving ? '保存中...' : isDirty ? '未保存' : '已保存';

  return (
    <div className="flex h-12 items-center justify-between border-b border-border bg-muted px-3">
      <div className="flex items-center gap-2">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
        )}

        <div className="h-6 w-px bg-muted-foreground/20"></div>

        <span className="max-w-48 truncate text-sm font-medium text-foreground">
          {title}
        </span>

        <span className="text-xs text-muted-foreground">{saveLabel}</span>

        {false && (
          <button
            type="button"
            // TODO: wire to save handler
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-pink-400 transition-colors hover:bg-pink-500/10 hover:text-pink-300"
          >
            <Save className="h-3.5 w-3.5" />
            保存
          </button>
        )}
      </div>

      <div className="flex items-center gap-1">
        <div className="h-6 w-px bg-muted-foreground/20"></div>

        <button
          type="button"
          title="导出"
          onClick={onExport}
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Download className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">导出</span>
        </button>

        <div className="h-6 w-px bg-muted-foreground/20"></div>

        <button
          type="button"
          title="JD 匹配分析"
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <FileSearch className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">JD 分析</span>
        </button>

        <button
          type="button"
          title="翻译"
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Languages className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">翻译</span>
        </button>

        <button
          type="button"
          title="求职信"
          onClick={onCoverLetterOpen}
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <FileText className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">求职信</span>
        </button>

        <button
          type="button"
          title="语法检查"
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <SpellCheck className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">语法</span>
        </button>

        <div className="h-6 w-px bg-muted-foreground/20"></div>

        <button
          type="button"
          title="主题"
          onClick={onThemeToggle}
          className={`flex items-center gap-1 rounded-md p-1.5 transition-colors ${themeActive ? 'bg-pink-500/30 text-pink-400' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}
        >
          <Palette className="h-4 w-4" />
          <span className="ml-1 hidden text-xs sm:inline">主题</span>
        </button>

        <div className="h-6 w-px bg-muted-foreground/20"></div>

        <button
          type="button"
          title="设置"
          onClick={onSettings}
          className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
