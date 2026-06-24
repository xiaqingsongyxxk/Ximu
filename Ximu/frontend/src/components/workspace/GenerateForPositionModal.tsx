import { useState } from 'react'
import { X, Check, Loader2, Sparkles, FileText } from 'lucide-react'
import { TemplateThumbnail } from '../template/TemplateThumbnail'
import { templateLabelsMap, TEMPLATE_ORDER } from '../../lib/template-labels'

export interface GenerateForPositionModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (payload: {
    template: string
    name: string
    jobTitle: string
    jdDescription: string
  }) => void
  onCreateDirect: (payload: {
    template: string
    name: string
    jobTitle: string
    jdDescription: string
  }) => void
}

export default function GenerateForPositionModal({ open, onClose, onSubmit, onCreateDirect }: GenerateForPositionModalProps) {
  const [selectedTemplate, setSelectedTemplate] = useState(TEMPLATE_ORDER[0])
  const [name, setName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jdDescription, setJdDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCreatingDirect, setIsCreatingDirect] = useState(false)

  const handleCreateDirect = async () => {
    setIsCreatingDirect(true)
    try {
      await onCreateDirect({
        template: selectedTemplate,
        name,
        jobTitle,
        jdDescription,
      })
    } finally {
      setIsCreatingDirect(false)
    }
  }

  const handleSubmit = async () => {
    if (!jdDescription.trim()) return
    setIsSubmitting(true)
    try {
      await onSubmit({
        template: selectedTemplate,
        name,
        jobTitle,
        jdDescription,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetAndClose = () => {
    onClose()
    setName('')
    setJobTitle('')
    setJdDescription('')
    setSelectedTemplate(TEMPLATE_ORDER[0])
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

      <div className="relative w-[896px] h-[768px] bg-card rounded-2xl shadow-2xl shadow-black/20 flex flex-col">
        <div className="flex items-start justify-between px-6 pt-6 pb-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">针对新职位生成</h2>
            <p className="text-muted-foreground text-sm mt-1">填写岗位要求，AI 将为您生成定制简历</p>
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
              <label htmlFor="gen-name" className="text-xs text-muted-foreground mb-1.5 block">
                简历名称 <span className="text-muted-foreground/60">(选填)</span>
              </label>
              <input
                id="gen-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：前端开发工程师-张三"
                className="w-full px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
              />
            </div>
            <div>
              <label htmlFor="gen-job-title" className="text-xs text-muted-foreground mb-1.5 block">
                岗位名称 <span className="text-muted-foreground/60">(选填)</span>
              </label>
              <input
                id="gen-job-title"
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="例如：高级前端开发"
                className="w-full px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
              />
            </div>
          </div>

          <div className="mt-4">
            <label htmlFor="gen-jd" className="text-xs text-muted-foreground mb-1.5 block">
              JD 描述 <span className="text-red-400">*</span>
            </label>
            <textarea
              id="gen-jd"
              value={jdDescription}
              onChange={(e) => setJdDescription(e.target.value)}
              placeholder="粘贴完整的职位描述（JD），AI 将根据此内容为您定制简历..."
              rows={6}
              className="w-full resize-none px-4 py-2.5 bg-background border border-foreground/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
            />
            <div className="flex justify-between mt-1">
              <span className="text-muted-foreground/60 text-[11px]">请尽量填写完整的岗位要求和职责描述</span>
              <span className={`text-[11px] ${jdDescription.trim() ? 'text-pink-400' : 'text-muted-foreground/60'}`}>
                {jdDescription.length > 0 ? `${jdDescription.length} 字` : '必填'}
              </span>
            </div>
          </div>

          <div className="mt-4 flex flex-col flex-1 min-h-0">
            <p className="mb-3 text-sm font-medium text-muted-foreground shrink-0">
              选择模板 <span className="text-red-400">*</span>
            </p>
            <div className="flex-1 overflow-y-auto pr-1 min-h-0">
              <div className="grid grid-cols-5 gap-3">
                {TEMPLATE_ORDER.map((tpl) => {
                  const isSelected = selectedTemplate === tpl
                  return (
                    <button
                      key={tpl}
                      type="button"
                      className={`relative cursor-pointer overflow-hidden rounded-xl border-2 transition-all duration-200 ${
                        isSelected
                          ? 'border-pink-500 shadow-md shadow-pink-500/10'
                          : 'border-foreground/10 hover:border-foreground/30'
                      }`}
                      onClick={() => setSelectedTemplate(tpl)}
                    >
                      <div className="relative bg-muted p-2">
                        <TemplateThumbnail
                          template={tpl}
                          className="mx-auto h-[100px] w-[71px] shadow-sm ring-1 ring-foreground/10"
                        />
                        {isSelected && (
                          <div className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-pink-500 text-primary-foreground shadow-sm">
                            <Check className="h-3 w-3" strokeWidth={3} />
                          </div>
                        )}
                      </div>
                      <div className={`px-2 py-1.5 text-center text-xs font-medium transition-colors ${
                        isSelected
                          ? 'bg-pink-500/10 text-pink-400'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}>
                        {templateLabelsMap[tpl]}
                      </div>
                    </button>
                  )
                })}
              </div>
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
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCreateDirect}
              disabled={!jdDescription.trim() || isCreatingDirect}
              className="cursor-pointer px-4 py-2 rounded-lg border border-foreground/10 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {isCreatingDirect ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  创建中...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4" />
                  直接创建
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!jdDescription.trim() || isSubmitting}
              className="cursor-pointer px-5 py-2 rounded-lg bg-gradient-to-r from-pink-500 to-pink-600 text-primary-foreground hover:from-pink-600 hover:to-pink-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  AI 生成
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
