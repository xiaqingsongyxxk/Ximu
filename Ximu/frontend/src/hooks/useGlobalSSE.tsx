/**
 * 全局 SSE 通知管理器
 *
 * ============================================
 * 这是唯一的全局 SSE 连接管理器，挂载在 MainLayout 中。
 * 它负责：
 *   1. 监听localStorage 中的所有 running 状态任务（通过 notification.ts）
 *   2. 为每个任务建立 EventSource SSE 连接
 *   3. 根据任务的 taskType，查找已注册的 SSE Handler 并执行对应回调
 *
 * ============================================
 * 如何注册新的任务类型？
 *
 * 1. 在需要使用该任务类型的页面/组件中，调用 registerSSEHandler():
 *
 *    import { registerSSEHandler } from '../lib/notification'
 *
 *    useEffect(() => {
 *      const cleanup = registerSSEHandler('my_task_type', {
 *        onSuccess: (task) => {
 *          toast.success(`「${task.metaInfo?.title || '未命名'}」完成`)
 *          refreshData()  // 可选：自定义业务逻辑
 *        },
 *        onError: () => '任务失败',
 *      })
 *      return cleanup
 *    }, [])
 *
 * 2. 当你通过 addNotificationTask() 添加一个 taskType 为 'my_task_type' 的任务时，
 *    全局 SSE 管理器会自动建立连接，并在任务完成/失败时调用你注册的 handler。
 *
 * ============================================
 * 工作原理：
 *
 *   添加任务 → addNotificationTask({ id, taskType: 'xxx', status: 'running', ... })
 *       ↓
 *   onNotificationTasksChange → syncTasks → connectTask()
 *       ↓
 *   建立 EventSource → 监听 result/status/error 事件
 *       ↓
 *   事件触发 → getRegisteredHandler(taskType) → onSuccess/onError
 *       ↓
 *   dispatch CustomEvent('global-sse-complete') — 供非 React 组件监听
 *
 * ============================================
 */

import { useEffect, useRef } from 'react'
import { toast } from 'sonner'
import type { WorkTask } from '../types/work'
import {
  getNotificationTasks,
  updateNotificationTask,
  markUnread,
  onNotificationTasksChange,
  getRegisteredHandler,
} from '../lib/notification'

/** 全局任务完成/失败事件（供 Dashboard 等页面监听） */
const GLOBAL_SSE_COMPLETE = 'global-sse-complete'
const GLOBAL_SSE_ERROR = 'global-sse-error'

export function useGlobalSSE() {
  const sourcesRef = useRef<Map<string, EventSource>>(new Map())

  useEffect(() => {
    const connectTask = (task: WorkTask) => {
      // 去重：已连接的任务跳过
      if (sourcesRef.current.has(task.id)) return
      // 状态过滤：只连接 running 状态的任务
      if (task.status !== 'running') return
      // Handler 过滤：只连接有注册 handler 的 taskType
      if (!getRegisteredHandler(task.taskType)) return

      const eventSource = new EventSource(`http://localhost:8000/work/stream/${task.id}`)

      eventSource.addEventListener('status', (e: MessageEvent) => {
        const payload = JSON.parse(e.data)
        if (payload.content === 'error') {
          updateNotificationTask(task.id, { status: 'error' })
          markUnread()
          eventSource.close()
          sourcesRef.current.delete(task.id)

          window.dispatchEvent(new CustomEvent(GLOBAL_SSE_ERROR, {
            detail: { taskId: task.id, taskType: task.taskType },
          }))

          // 调用注册的 error handler
          const handler = getRegisteredHandler(task.taskType)
          if (handler?.onError) {
            const errorMsg = handler.onError(task)
            if (errorMsg) toast.error(errorMsg)
          }

          // onStatus 回调
          if (handler?.onStatus) {
            handler.onStatus(task)
          }
        }
        markUnread()
      })

      eventSource.addEventListener('result', (e: MessageEvent) => {
        const payload = JSON.parse(e.data)
        updateNotificationTask(task.id, { status: 'success' })
        eventSource.close()
        sourcesRef.current.delete(task.id)

        // dispatch 全局事件（包含 taskType，方便页面按需监听）
        window.dispatchEvent(new CustomEvent(GLOBAL_SSE_COMPLETE, {
          detail: { taskId: task.id, workspaceId: task.workspaceId, taskType: payload.type || task.taskType },
        }))

        // 调用注册的 success handler
        const handler = getRegisteredHandler(task.taskType)
        if (handler?.onSuccess) {
          const content = handler.onSuccess(task)
          if (content) toast.success(content as any)
        }
      })

      eventSource.addEventListener('error', () => {
        eventSource.close()
        sourcesRef.current.delete(task.id)
      })

      sourcesRef.current.set(task.id, eventSource)
    }

    const syncTasks = () => {
      const tasks = getNotificationTasks()
      for (const task of tasks) {
        connectTask(task)
      }
    }

    syncTasks()
    const cleanup = onNotificationTasksChange(syncTasks)
    return () => {
      cleanup()
      for (const [, source] of sourcesRef.current) {
        source.close()
      }
      sourcesRef.current.clear()
    }
  }, [])
}
