import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Palette, ChevronLeft, ChevronRight, Bell, Settings } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import { fetchErrorTasks } from '../../lib/api'
import { hasUnreadNotification, onNotificationChange, getNotificationTasks, getNotificationTasksAndClear, onNotificationTasksChange } from '../../lib/notification'
import type { WorkTask } from '../../types/work'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import MessageList from './MessageDropdown'
import SettingsModal from '../settings/SettingsModal'
import logoSvg from '../../assets/logo.svg'

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [showSettings, setShowSettings] = useState(false)
  const [messagesOpen, setMessagesOpen] = useState(false)
  const [hasUnread, setHasUnread] = useState(false)
  const [localTasks, setLocalTasks] = useState<WorkTask[]>(() => getNotificationTasksAndClear())

  const { data: errorTasks } = useQuery({
    queryKey: ['work-tasks', 'error'],
    queryFn: fetchErrorTasks,
    refetchInterval: 15000,
  })

  useEffect(() => {
    return onNotificationChange(() => {
      setHasUnread(hasUnreadNotification())
    })
  }, [])

  useEffect(() => {
    return onNotificationTasksChange(() => {
      setLocalTasks(getNotificationTasks())
    })
  }, [])

  const tasks = useMemo(() => {
    const errors = errorTasks || []
    const taskMap = new Map<string, WorkTask>()
    for (const t of errors) taskMap.set(t.id, t)
    for (const t of localTasks) {
      if (!taskMap.has(t.id)) {
        taskMap.set(t.id, t)
      }
    }
    return Array.from(taskMap.values()).sort((a, b) => {
      const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0
      const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0
      return bTime - aTime
    })
  }, [errorTasks, localTasks])

  useEffect(() => {
    if (messagesOpen) {
      setHasUnread(false)
    }
  }, [messagesOpen])

  const navItems = [
    { label: '工作空间', path: '/', icon: FileText },
    { label: '模板库', path: '/templates', icon: Palette },
  ]

  return (
    <>
      <aside
        className="bg-card border-r border-muted-foreground/20 flex flex-col h-full transition-all duration-300 ease-in-out overflow-hidden"
        style={{ width: collapsed ? '64px' : '208px' }}
      >
        <div className="h-14 flex items-center px-4 border-b border-muted-foreground/20 shrink-0 gap-3">
          <button type="button" onClick={() => navigate('/workspace')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <img src={logoSvg} alt="Chiren" className="w-7 h-7 shrink-0" />
            <span className="text-pink-500 font-bold text-lg whitespace-nowrap transition-opacity duration-300" style={{ opacity: collapsed ? 0 : 1 }}>Chiren</span>
          </button>
        </div>

        <nav className="flex-1 p-3 flex flex-col">
          <ul className="space-y-1">
            {navItems.map(({ label, path, icon: Icon }) => {
              const isActive = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
              return (
                <li key={path}>
                  <button
                    type="button"
                    onClick={() => navigate(path)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      isActive
                        ? 'text-pink-400 bg-accent/20 dark:bg-pink-500/10'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-pink-500' : ''}`} />
                    <span className="text-sm whitespace-nowrap transition-opacity duration-300" style={{ opacity: collapsed ? 0 : 1 }}>{label}</span>
                  </button>
                </li>
              )
            })}
          </ul>

          <div className="mt-auto pt-3 space-y-1">
            <Popover open={messagesOpen} onOpenChange={setMessagesOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <span className="relative shrink-0">
                    <Bell className="w-4 h-4" />
                    {hasUnread && (
                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-pink-500 rounded-full" />
                    )}
                  </span>
                  <span className="text-sm whitespace-nowrap transition-opacity duration-300" style={{ opacity: collapsed ? 0 : 1 }}>通知</span>
                </button>
              </PopoverTrigger>
              <PopoverContent
                side="right"
                align="start"
                sideOffset={12}
                className="w-96 p-0 bg-card rounded-xl border border-muted-foreground/20 shadow-lg"
              >
                <MessageList tasks={tasks} />
              </PopoverContent>
            </Popover>

            <button
              type="button"
              onClick={() => setShowSettings(true)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Settings className="w-4 h-4 shrink-0" />
              <span className="text-sm whitespace-nowrap transition-opacity duration-300" style={{ opacity: collapsed ? 0 : 1 }}>设置</span>
            </button>
          </div>
        </nav>

        <div className="border-t border-muted-foreground/20 p-3">
          <button
            type="button"
            onClick={onToggle}
            className="flex items-center justify-center w-full h-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            {!collapsed && <span className="ml-2 text-sm">折叠侧边栏</span>}
          </button>
        </div>
      </aside>

      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} />
    </>
  )
}
