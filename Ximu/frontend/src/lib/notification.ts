import type { WorkTask } from '../types/work'

const NOTIFICATION_KEY = 'notification_unread_flag'
const NOTIFICATION_TASKS_KEY = 'notification_tasks'

export function hasUnreadNotification(): boolean {
  return localStorage.getItem(NOTIFICATION_KEY) === 'true'
}

export function markUnread(): void {
  localStorage.setItem(NOTIFICATION_KEY, 'true')
  window.dispatchEvent(new Event('notification-unread-change'))
  window.dispatchEvent(new Event('notification-tasks-change'))
}

export function markAllRead(): void {
  localStorage.setItem(NOTIFICATION_KEY, 'false')
  window.dispatchEvent(new Event('notification-unread-change'))
}

export function onNotificationChange(cb: () => void): () => void {
  window.addEventListener('notification-unread-change', cb)
  return () => window.removeEventListener('notification-unread-change', cb)
}

function parseStoredTasks(): WorkTask[] {
  try {
    const stored = localStorage.getItem(NOTIFICATION_TASKS_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function storeTasks(tasks: WorkTask[]): void {
  localStorage.setItem(NOTIFICATION_TASKS_KEY, JSON.stringify(tasks))
}

export function getNotificationTasks(): WorkTask[] {
  return parseStoredTasks()
}

export function getNotificationTasksAndClear(): WorkTask[] {
  const tasks = parseStoredTasks()
  storeTasks([])
  return tasks
}

export function addNotificationTask(task: WorkTask): void {
  const tasks = parseStoredTasks()
  const exists = tasks.some(t => t.id === task.id)
  if (!exists) {
    tasks.push(task)
  }
  storeTasks(tasks)
  window.dispatchEvent(new Event('notification-tasks-change'))
}

export function updateNotificationTask(id: string, updates: Partial<WorkTask>): void {
  const tasks = parseStoredTasks()
  const idx = tasks.findIndex(t => t.id === id)
  if (idx !== -1) {
    tasks[idx] = { ...tasks[idx], ...updates }
    storeTasks(tasks)
  }
  window.dispatchEvent(new Event('notification-tasks-change'))
}

export function onNotificationTasksChange(cb: () => void): () => void {
  window.addEventListener('notification-tasks-change', cb)
  return () => window.removeEventListener('notification-tasks-change', cb)
}

// ============================================
// 全局 SSE Handler 注册表
// ============================================
//
// 用途：允许任意组件/页面按 taskType 注册自定义的 toast 和回调逻辑。
// 全局 SSE 管理器（useGlobalSSE）会根据 taskType 自动查找并执行对应 handler。
//
// 使用方式：
//
//   import { registerSSEHandler } from '../lib/notification'
//
//   // 在组件中注册（useEffect 中注册，cleanup 中注销）
//   useEffect(() => {
//     const unregister = registerSSEHandler('my_task_type', {
//       // onSuccess: 任务完成时调用。返回 string | ReactNode 作为 toast.success 内容
//       onSuccess: (task) => {
//         toast.success(`工作空间「${task.metaInfo?.title || '未命名'}」解析完成`)
//         // 可选：执行自定义业务逻辑，如刷新数据
//         refreshData()
//       },
//       // onError: 任务失败时调用。返回 string 作为 toast.error 内容
//       onError: (task) => '工作空间解析失败',
//     })
//     return unregister
//   }, [])
//
//   // 同一 taskType 只能注册一个 handler。后注册会覆盖先注册的。
//   // unregister() 函数可在组件卸载时调用以注销注册。
//
// 全局注册位置（推荐）：
//   在 MainLayout.tsx 的 useGlobalSSE() 调用后，统一注册各页使用的 handler。
//   这样即使组件重新 mount，handler 也不会丢失。
//

export interface SSEHandlerConfig {
  /**
   * 任务成功时回调。
   * @returns string | React.ReactNode — 作为 toast.success 的内容
   */
  onSuccess?: (task: WorkTask) => React.ReactNode | string | void
  /**
   * 任务失败时回调。
   * @returns string — 作为 toast.error 的内容
   */
  onError?: (task: WorkTask) => string | void
  /**
   * 任务状态变化时回调（可选）。
   * 在 'status' 事件（包含 error 状态）触发时调用。
   */
  onStatus?: (task: WorkTask) => void
}

/** 全局 SSE Handler 注册表 — key = taskType */
const sseHandlers = new Map<string, SSEHandlerConfig>()

/**
 * 注册 SSE Handler。
 * @param taskType - 任务类型标识符（如 'ai_resume', 'parse' 等）
 * @param config - Handler 配置（onSuccess / onError / onStatus）
 * @returns cleanup function，调用后注销该 taskType 的注册
 *
 * 示例:
 *   const cleanup = registerSSEHandler('parse', {
 *     onSuccess: (task) => { toast.success(`「${task.metaInfo?.title}」完成`); refreshWorkspaces() },
 *     onError: () => '解析失败',
 *   })
 *   // 组件卸载时: cleanup()
 */
export function registerSSEHandler(taskType: string, config: SSEHandlerConfig): () => void {
  sseHandlers.set(taskType, config)
  return () => {
    sseHandlers.delete(taskType)
  }
}

/**
 * 获取指定 taskType 的已注册 Handler。
 * @param taskType - 任务类型标识符
 * @returns Handler 配置，如果未注册则返回 undefined
 */
export function getRegisteredHandler(taskType: string): SSEHandlerConfig | undefined {
  return sseHandlers.get(taskType)
}

/**
 * 获取所有已注册的 Handler。供全局 SSE 管理器内部使用。
 */
export function getAllRegisteredHandlers(): ReadonlyMap<string, SSEHandlerConfig> {
  return sseHandlers
}
