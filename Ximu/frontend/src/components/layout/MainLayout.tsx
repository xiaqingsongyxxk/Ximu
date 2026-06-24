/**
 * 全局布局组件
 * 
 * 本文件挂载了全局 SSE 管理器 (useGlobalSSE)，该管理器负责：
 *   1. 监听所有 running 状态的 SSE 任务
 *   2. 根据 taskType 自动查找并执行已注册的 handler
 *   3. 派发全局事件 'global-sse-complete' / 'global-sse-error'
 * 
 * ============================================
 * 如何在你的页面/组件中使用？
 * ============================================
 * 
 * 步骤 1: 注册你的 taskType handler（useEffect 中注册，cleanup 中自动注销）
 * 
 *   import { useEffect } from 'react'
 *   import { registerSSEHandler } from '../lib/notification'
 *   import { toast } from 'sonner'
 * 
 *   useEffect(() => {
 *     const cleanup = registerSSEHandler('your_task_type', {
 *       // 任务完成时调用 — 可返回 string / ReactNode 作为 toast.success 内容
 *       onSuccess: (task) => {
 *         toast.success(`「${task.metaInfo?.title || '未命名'}」完成`)
 *         yourRefreshFunction()  // 可选：自定义业务逻辑
 *       },
 *       // 任务失败时调用 — 返回 string 作为 toast.error 内容
 *       onError: () => '任务执行失败',
 *     })
 *     return cleanup  // 组件卸载时自动注销
 *   }, [yourRefreshFunction])
 * 
 * 步骤 2: 在适当时机添加通知任务（状态为 running 时，全局管理器会自动建立 SSE 连接）
 * 
 *   import { addNotificationTask } from '../lib/notification'
 * 
 *   addNotificationTask({
 *     id: taskId,                    // 后端返回的任务 ID
 *     taskType: 'your_task_type',    // 必须与 registerSSEHandler 中的 taskType 一致
 *     status: 'running',
 *     workspaceId: optionalId,
 *     metaInfo: { title: '任务标题' },
 *     errorMessage: null,
 *     createdAt: new Date().toISOString(),
 *     updatedAt: new Date().toISOString(),
 *   })
 * 
 * 补充：Dashboard 会监听 'global-sse-complete' 事件自动刷新工作区列表，
 *       所以即使你的 taskType 没有注册 handler，任务完成后 Dashboard 仍会刷新。
 * 
 * ============================================
 */

import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Toaster } from 'sonner'
import { toast } from 'sonner'
import Sidebar from './Sidebar'
import { useGlobalSSE } from '../../hooks/useGlobalSSE'
import { registerSSEHandler } from '../../lib/notification'

/**
 * 全局 SSE handler 注册 — 在模块加载时执行，保证始终存在。
 * 注意：这里注册的是与页面组件生命周期无关的通用 handler。
 * 页面组件可以在各自的 useEffect 中注册额外的 handler（会被这里的覆盖或共存）。
 */
registerSSEHandler('jd_generate', {
  onSuccess: (task) => {
    toast.success(
      <div className="flex flex-col gap-1">
        <span className="font-medium text-sm">子简历「{task.metaInfo?.title || '未命名'}」生成完成</span>
      </div>,
    )
  },
  onError: () => '子简历生成失败',
})

registerSSEHandler('parse', {
  onSuccess: (task) => {
    toast.success(
      <div className="flex flex-col gap-1">
        <span className="font-medium text-sm">工作空间「{task.metaInfo?.title || '未命名'}」生成完成</span>
      </div>,
    )
  },
  onError: () => '工作空间解析失败',
})

registerSSEHandler('jd_score', {
  onSuccess: (task) => {
    toast.success(
      <div className="flex flex-col gap-1">
        <span className="font-medium text-sm">JD 匹配评分「{task.metaInfo?.title || '未命名'}」完成</span>
      </div>,
    )
  },
  onError: () => 'JD 匹配评分失败',
})

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)

  // 挂载全局 SSE 管理器 — 监听所有 running 状态的 SSE 任务
  // 页面/组件通过 registerSSEHandler() 注册自定义 handler
  useGlobalSSE()

  return (
    <div className="h-screen w-full flex bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(prev => !prev)} />
      <main className="flex-1 min-h-0 p-6">
        <Outlet />
      </main>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            color: 'hsl(var(--card-foreground))',
          },
        }}
      />
    </div>
  )
}
