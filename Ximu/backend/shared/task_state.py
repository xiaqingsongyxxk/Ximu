"""通用任务状态管理模块。

本模块提供后台异步任务的状态管理功能：
1. 任务状态的内存存储
2. 任务事件的SSE推送
3. 任务的创建、更新、清理

使用内存存储（字典），任务状态在应用重启后会丢失。
"""  # 模块文档字符串

import asyncio  # 导入异步IO模块
import json  # 导入JSON模块
from collections.abc import AsyncIterator, Awaitable, Callable  # 导入异步相关类型
from typing import Any  # 导入Any类型

from shared.types.task import TaskStatus, TaskType  # 导入任务状态和类型枚举

# 内存中的任务存储：task_id -> 任务数据字典
tasks: dict[str, dict[str, Any]] = {}

# 内存中的事件队列：task_id -> asyncio.Queue
task_events: dict[str, asyncio.Queue] = {}


class TaskEventHub:
    """通用任务事件中心，支持SSE流式推送。

    管理任务的生命周期：创建 → 更新状态 → 推送事件 → 清理。
    """

    def __init__(self) -> None:
        self._tasks = tasks  # 引用内存任务字典
        self._events = task_events  # 引用内存事件队列字典

    def create(
        self,
        task_id: str,
        task_type: TaskType,
        initial_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建新任务。

        Args:
            task_id: 任务ID。
            task_type: 任务类型。
            initial_data: 初始数据（可选）。

        Returns:
            任务数据字典。
        """
        task_data = {
            "task_id": task_id,
            "task_type": task_type.value,
            "status": TaskStatus.PENDING,  # 初始状态：待处理
            "result": None,  # 初始结果：None
            "error": None,  # 初始错误：None
        }
        if initial_data:
            task_data.update(initial_data)
        self._tasks[task_id] = task_data  # 存入内存
        self._events[task_id] = asyncio.Queue()  # 创建事件队列
        return self._tasks[task_id]

    async def emit(self, task_id: str, event: str, data: Any) -> None:
        """发射任务事件。

        Args:
            task_id: 任务ID。
            event: 事件类型（status/result/error）。
            data: 事件数据。
        """
        if task_id in self._tasks:
            if event == "status":
                self._tasks[task_id]["status"] = data  # 更新状态
            elif event == "result":
                self._tasks[task_id]["result"] = data  # 更新结果
            elif event == "error":
                self._tasks[task_id]["error"] = data  # 更新错误

        if task_id in self._events:
            await self._events[task_id].put(  # 将事件放入队列
                {
                    "event": event,
                    "data": json.dumps(
                        {
                            "content": data,
                            "type": self._tasks[task_id]["task_type"],
                        },
                        ensure_ascii=False,
                    ),
                }
            )

    async def subscribe(self, task_id: str) -> AsyncIterator[dict[str, Any]]:
        """订阅任务事件流。

        Args:
            task_id: 任务ID。

        Yields:
            事件字典。
        """
        queue = self._events.get(task_id)
# self._events.get(task_id) 拿到的是队列这个容器（整个信箱），而 queue.get() 拿到的是容器里的内容（信箱里的信）。容器可以立即拿到，但信需要等别人放进去才能取到。这就是 asyncio.Queue 的生产者-消费者模型——.get() 在队列空时会await直到有 .put() 发生。        
        if not queue:
            return
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60)  # 等待事件，超时60秒
# 对，asyncio.Queue 就是干这个的。
# # 协程A（subscribe）                    # 协程B（emit/后台任务）
#                                           await queue.put({"event": "result", "data": "..."})
# await queue.get()  ← 一直挂在这
#                       ↓
#                   put 发生的那一瞬间，get 被唤醒
#                   event = {"event": "result", "data": "..."}  ← 拿到了
# put 放进去的一瞬间，等在 get 上的协程立刻被唤醒，直接拿到那个元素。
# 不轮询、不延迟、不反复检查。这就是 asyncio.Queue 的核心机制——内部用 asyncio.Event / asyncio.Condition 实现，put 时通知所有在 get 上等待的协程。
# 整个过程就是：
# 1. get 发现队列空 → 挂起
# 2. put 塞入元素 → 通知
# 3. get 被唤醒 → 取出元素 → 继续执行
# 一步接一步，零延迟。
                yield event
                if event["event"] in ("result", "error"):  # 结束事件
                    break
            except TimeoutError:
                yield {"event": "heartbeat", "data": ""}  # 发送心跳
            except asyncio.CancelledError:
                raise

    async def cleanup(
        self,
        task_id: str,
        cleanup_fn: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """清理任务（延迟120秒）。

        Args:
            task_id: 任务ID。
            cleanup_fn: 自定义清理函数（可选）。
        """
        await asyncio.sleep(120)  # 等待120秒（让客户端接收完成事件）
        if cleanup_fn:
            await cleanup_fn()
        if task_id in self._tasks:
            del self._tasks[task_id]  # 删除任务数据
        if task_id in self._events:
            del self._events[task_id]  # 删除事件队列


# 全局任务事件中心实例
hub = TaskEventHub()
# ---
# 实际流程
# 模块加载时
# # app.py 启动
# import shared.task_state  # ← 触发模块加载
# # 此时自动执行：
# hub = TaskEventHub()  # 创建全局实例，存储在内存中
# 运行时
# # router.py 中使用
# from shared.task_state import hub  # ← 导入的是同一个 hub
# @router.post("/parse")
# async def parse():
#     hub.create(task_id="123")  # ← 操作全局实例
# ---
# 内存中的状态
# 内存 (进程生命周期内)
# ┌─────────────────────────────────────┐
# │ shared/task_state.py               │
# │                                     │
# │ tasks = {                          │
# │   "task_1": {status: "running"},   │
# │   "task_2": {status: "completed"} │
# │ }                                  │
# │                                     │
# │ hub ─────────────────────────┐      │
# │   └──────────────────────────┘      │
# │        (都指向同一个实例)            │
# └─────────────────────────────────────┘
# 所有请求共享同一个 hub → 共享同一个 tasks 字典
# ---
# 作用
# 1. 跨请求共享数据
# # 请求 A: 创建任务
# hub.create("task_1", "parse", {...})
# # 请求 B: 查询任务（能查到！）
# task = hub.get("task_1")
# 2. 统一管理
# # 不用传参数
# hub = TaskEventHub()  # 一个实例
# # 任何地方导入都是同一个
# from module_a import hub
# from module_b import hub  # ← 同一个！
# 3. 状态一致性
# 请求 A: hub.emit("task_1", "status", "running")
# 请求 B: hub.get("task_1")["status"]  # → "running"
# ---

def create_task(
    task_id: str,
    task_type: TaskType,
    initial_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """创建新任务。"""
    return hub.create(task_id, task_type, initial_data)


async def update_task_status(task_id: str, status: TaskStatus) -> None:
    """更新任务状态。"""
    await hub.emit(task_id, "status", status.value)


async def update_task_result(task_id: str, result: dict) -> None:
    """更新任务结果。"""
    await hub.emit(task_id, "status", TaskStatus.SUCCESS.value)
    await hub.emit(task_id, "result", json.dumps(result, ensure_ascii=False))


async def update_task_error(task_id: str, error: str) -> None:
    """更新任务错误。"""
    await hub.emit(task_id, "status", TaskStatus.ERROR.value)
    await hub.emit(task_id, "error", error)


async def cleanup_task(
    task_id: str,
    cleanup_fn: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """清理任务。"""
    await hub.cleanup(task_id, cleanup_fn)
