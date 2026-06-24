import { useState, useEffect } from 'react'
import { X, Loader2, Pencil } from 'lucide-react'

export interface EditSubResumeModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (payload: {
    title: string
    jobTitle: string
    jobDescription: string
  }) => void
  initialData?: {
    title: string
    jobTitle?: string
    jobDescription?: string
  }
}

export default function EditSubResumeModal({ open, onClose, onSubmit, initialData }: EditSubResumeModalProps) {
  const [title, setTitle] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (open && initialData) {
      setTitle(initialData.title || '')
      setJobTitle(initialData.jobTitle || '')
      setJobDescription(initialData.jobDescription || '')
    }
  }, [open, initialData])

  const handleSubmit = async () => {
    if (!jobDescription.trim()) return
    setIsSubmitting(true)
    try {
      await onSubmit({
        title: title.trim() || initialData?.title || '未命名简历',
        jobTitle: jobTitle.trim(),
        jobDescription: jobDescription.trim(),
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetAndClose = () => {
    onClose()
    setTitle('')
    setJobTitle('')
    setJobDescription('')
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        role="button"
        tabIndex={0}
        onClick={resetAndClose}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') resetAndClose() }}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm cursor-pointer"
      />

      <div className="relative w-[640px] bg-card rounded-2xl shadow-2xl shadow-black/20 flex flex-col">
        <div className="flex items-start justify-between px-6 pt-6 pb-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">编辑子简历</h2>
            <p className="text-muted-foreground text-sm mt-1">修改简历名称、岗位信息和 JD 描述</p>
          </div>
          <button
            type="button"
            onClick={resetAndClose}
            className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4 flex-1 flex flex-col overflow-hidden">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="edit-name" className="text-xs text-muted-foreground mb-1.5 block">
                简历名称
              </label>
              <input
                id="edit-name"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如：前端开发工程师-张三"
                className="w-full px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
              />
            </div>
            <div>
              <label htmlFor="edit-job-title" className="text-xs text-muted-foreground mb-1.5 block">
                岗位名称 <span className="text-muted-foreground/60">(选填)</span>
              </label>
              <input
                id="edit-job-title"
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="例如：高级前端开发"
                className="w-full px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
              />
            </div>
          </div>

          <div className="mt-4">
            <label htmlFor="edit-jd" className="text-xs text-muted-foreground mb-1.5 block">
              JD 描述 <span className="text-red-400">*</span>
            </label>
            <textarea
              id="edit-jd"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="粘贴完整的职位描述（JD），AI 将根据此内容为您定制简历..."
              rows={8}
              className="w-full resize-none px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
            />
            <div className="flex justify-between mt-1">
              <span className="text-muted-foreground/60 text-[11px]">请尽量填写完整的岗位要求和职责描述</span>
              <span className={`text-[11px] ${jobDescription.trim() ? 'text-pink-400' : 'text-muted-foreground/60'}`}>
                {jobDescription.length > 0 ? `${jobDescription.length} 字` : '必填'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-foreground/10">
          <button
            type="button"
            onClick={resetAndClose}
            className="cursor-pointer px-5 py-2 rounded-lg border border-foreground/10 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors text-sm font-medium"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!jobDescription.trim() || isSubmitting}
            className="cursor-pointer px-5 py-2 rounded-lg bg-gradient-to-r from-pink-500 to-pink-600 text-primary-foreground hover:from-pink-600 hover:to-pink-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Pencil className="h-4 w-4" />
                保存修改
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
