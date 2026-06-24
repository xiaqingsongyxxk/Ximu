import { useState, useRef, useEffect } from 'react'
import { MoreVertical, Pencil, Trash2 } from 'lucide-react'
import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover'
import ConfirmDialog from '../ui/ConfirmDialog'
import { TemplateThumbnail } from '../template/TemplateThumbnail'

export interface WorkspaceCardProps {
  id: string
  title: string
  domain: string
  subResumeIds: string[]
  lastModified: string
  templateName: string
  isActive?: boolean
  onClick?: () => void
  onDelete?: (id: string) => void
  onRename?: (id: string, newTitle: string) => void
}

interface CoverImageProps {
  templateName: string
}

function CoverImage({ templateName }: CoverImageProps) {
  const isKnownTemplate = [
    'classic', 'professional', 'formal', 'elegant', 'corporate', 'ats', 'executive',
    'consultant', 'minimal', 'modern', 'clean', 'compact', 'swiss', 'nordic', 'gradient',
    'bold', 'two-column', 'sidebar', 'card', 'blocks', 'timeline', 'material', 'creative',
    'artistic', 'neon', 'watercolor', 'mosaic', 'luxe', 'retro', 'magazine', 'ribbon',
    'rose', 'zigzag', 'developer', 'coder', 'designer', 'architect', 'engineer',
    'scientist', 'finance', 'medical', 'metro', 'legal', 'teacher', 'academic', 'startup',
    'japanese', 'euro', 'berlin', 'infographic'
  ].includes(templateName)

  if (isKnownTemplate) {
    return (
      <div className="w-full h-full bg-muted flex items-center justify-center overflow-hidden">
        <TemplateThumbnail
          template={templateName}
          className="w-20 h-28 rounded-sm shadow-lg"
        />
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-muted flex items-center justify-center">
      <div className="w-full h-full opacity-30" style={{
        background: 'linear-gradient(135deg, hsl(var(--muted-foreground) / 0.3) 0%, hsl(var(--accent) / 0.1) 100%)'
      }} />
      <span className="absolute text-muted-foreground text-xs">{templateName}</span>
    </div>
  )
}

export default function WorkspaceCard({
  id,
  title,
  domain,
  subResumeIds,
  lastModified,
  templateName,
  isActive = false,
  onClick,
  onDelete,
  onRename,
}: WorkspaceCardProps) {
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState(title)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const renameInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isRenaming && renameInputRef.current) {
      renameInputRef.current.focus()
      renameInputRef.current.select()
    }
  }, [isRenaming])

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setPopoverOpen(false)
    setConfirmOpen(true)
  }

  const handleConfirmDelete = () => {
    setConfirmOpen(false)
    onDelete?.(id)
  }

  const handleRenameClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setPopoverOpen(false)
    setIsRenaming(true)
    setRenameValue(title)
  }

  const handleRenameConfirm = () => {
    const newTitle = renameValue.trim()
    if (newTitle && newTitle !== title) {
      onRename?.(id, newTitle)
    }
    setIsRenaming(false)
  }

  const handleRenameCancel = () => {
    setIsRenaming(false)
    setRenameValue(title)
  }

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleRenameConfirm()
    if (e.key === 'Escape') handleRenameCancel()
  }

  return (
    <>
      <div
        onClick={onClick}
        className={`relative rounded-2xl bg-card border border-border overflow-hidden group hover:shadow-md hover:shadow-black/10 hover:border-border/80 transition-all duration-200 cursor-pointer w-full h-[280px] flex flex-col ${isActive ? 'ring-2 ring-pink-500/50' : ''}`}
      >
        <div className="pt-4">
          <div className="relative w-full h-[140px] shrink-0">
            <CoverImage templateName={templateName} />
          </div>
        </div>

        <div className="p-4 flex flex-col flex-1 min-h-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {isRenaming ? (
                <input
                  ref={renameInputRef}
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={handleRenameKeyDown}
                  onBlur={handleRenameCancel}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full px-2 py-1 bg-background border border-input rounded-md text-foreground text-sm outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/30"
                />
              ) : (
                <h3 className="text-foreground font-semibold text-base truncate leading-tight">{title}</h3>
              )}
              <p className="text-muted-foreground text-xs truncate mt-0.5">{domain}</p>
            </div>
            <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  onClick={(e) => e.stopPropagation()}
                  className="p-1 rounded-md border border-transparent text-muted-foreground/40 opacity-0 group-hover:opacity-100 hover:text-muted-foreground hover:bg-muted hover:border-border transition-all cursor-pointer shrink-0"
                >
                  <MoreVertical className="w-3.5 h-3.5" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-40 p-1.5 border-border" align="end" sideOffset={4}>
                <div className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={handleRenameClick}
                    className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-foreground hover:bg-muted transition-colors text-left cursor-pointer"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    重命名
                  </button>
                  <div className="h-px bg-border mx-1.5" />
                  <button
                    type="button"
                    onClick={handleDeleteClick}
                    className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-red-500 hover:bg-red-500/10 transition-colors text-left cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    删除
                  </button>
                </div>
              </PopoverContent>
            </Popover>
          </div>

          <div className="flex-1 min-h-[8px]" />

          <div className="flex items-center justify-between pt-2.5 border-t border-foreground/10">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
              <span className="text-muted-foreground text-[11px] font-medium">
                {subResumeIds.length} 个子简历
              </span>
            </div>
            <span className="text-muted-foreground text-[11px]">
              {lastModified}
            </span>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="删除工作空间"
        description={`确定要删除「${title}」吗？此操作将同时删除该工作空间下的所有子简历，且不可撤销。`}
        confirmText="删除"
        cancelText="取消"
        confirmVariant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  )
}
