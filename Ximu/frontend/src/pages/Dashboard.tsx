import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, X } from 'lucide-react'
import { toast } from 'sonner'
import WorkspaceCard from '../components/workspace/WorkspaceCard'
import CreateWorkspaceModal from '../components/workspace/CreateWorkspaceModal'
import { fetchWorkspaces, createWorkspace, deleteWorkspace, updateResume } from '../lib/api'
import type { Workspace } from '../types/workspace'

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  const hhmm = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })

  if (diffSec < 60) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffHour < 24) return `${diffHour} 小时前`
  if (diffDay === 1) return `昨天 ${hhmm}`
  if (diffDay === 2) return `前天 ${hhmm}`

  const mmdd = date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }).replace(/\//g, '-')
  return `${mmdd} ${hhmm}`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null)

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchQuery(value)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setDebouncedQuery(value), 300)
  }, [])

  const refreshWorkspaces = useCallback(() => {
    fetchWorkspaces().then((data) => {
      setWorkspaces(data)
    })
  }, [])

  useEffect(() => {
    fetchWorkspaces().then((data) => {
      setWorkspaces(data)
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    const handler = () => { refreshWorkspaces() }
    window.addEventListener('global-sse-complete', handler)
    return () => { window.removeEventListener('global-sse-complete', handler) }
  }, [refreshWorkspaces])

  const filteredWorkspaces = useMemo(() => {
    if (!debouncedQuery.trim()) return workspaces
    const q = debouncedQuery.toLowerCase().trim()
    return workspaces.filter(ws => ws.title.toLowerCase().includes(q))
  }, [workspaces, debouncedQuery])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  if (loading) {
    return <div className="text-muted-foreground">加载中...</div>
  }

  return (
    <div className="flex flex-col h-[calc(100vh-73px-64px)]">
      <div className="flex items-center justify-between mb-8 shrink-0">
        <div>
          <div className="text-pink-500 text-xs font-medium tracking-widest mb-2">MANAGEMENT</div>
          <h1 className="text-4xl font-bold text-foreground mb-2">工作空间管理</h1>
          <p className="text-muted-foreground text-sm">
            管理您的职业身份。Chiren 为不同岗位精准定制简历，帮助您在每个领域都展现出最佳状态。
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" className="flex items-center gap-2 bg-card rounded-lg px-3 py-2 border border-muted-foreground/20 w-64">
            <Search className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              type="text"
              placeholder="搜索工作空间..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="bg-transparent text-foreground text-sm outline-none placeholder:text-muted-foreground min-w-0 flex-1"
            />
            {searchQuery && (
              <button type="button" onClick={() => { setSearchQuery(''); setDebouncedQuery(''); }} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </button>
          <button
            type="button"
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-pink-500 text-primary-foreground hover:bg-pink-600 transition-colors text-sm font-medium"
            onClick={() => setCreateModalOpen(true)}
          >
            <Plus className="w-4 h-4" />
            新建工作空间
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 flex justify-center">
        <div className="grid grid-cols-5 gap-5 pb-4 max-w-[1500px] w-full px-4">
          {filteredWorkspaces.map((ws) => (
            <WorkspaceCard
              key={ws.id}
              id={ws.id}
              title={ws.title}
              domain={`${ws.template} 模板`}
              subResumeIds={ws.subResumeIds}
              lastModified={formatRelativeTime(ws.updatedAt)}
              templateName={ws.template}
              isActive={ws.isDefault}
              onClick={() => navigate(`/workspace/${ws.id}`)}
              onDelete={async (id) => {
                try {
                  await deleteWorkspace(id)
                  toast.success('工作空间已删除')
                  refreshWorkspaces()
                } catch (err: any) {
                  toast.error(err.message || '删除失败')
                }
              }}
              onRename={async (id, newTitle) => {
                try {
                  await updateResume({ id, title: newTitle })
                  toast.success('重命名成功')
                  refreshWorkspaces()
                } catch (err: any) {
                  toast.error(err.message || '重命名失败')
                }
              }}
            />
          ))}
        </div>
      </div>

      <CreateWorkspaceModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onRefreshWs={refreshWorkspaces}
        onCreate={async (template, name) => {
          const newWs = await createWorkspace(template, name || undefined)
          setWorkspaces((prev) => [...prev, newWs])
          setCreateModalOpen(false)
        }}
      />
    </div>
  )
}
