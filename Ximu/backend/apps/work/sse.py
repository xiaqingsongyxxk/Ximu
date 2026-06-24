"""SSE（Server-Sent Events）事件生成器模块。

本模块提供SSE事件流的生成逻辑。
SSE是一种服务器向客户端推送实时数据的技术，
前端通过EventSource API连接，可以实时收到任务状态更新。
"""  # 模块文档字符串

from shared.task_state import (
    hub,  # 从shared/task_state.py导入任务状态中心（EventHub实例）
)

# hub 是一个事件总线，支持subscribe（订阅）和publish（发布）
# 后台任务通过hub.publish()发布状态变化
# 前端通过hub.subscribe()订阅状态变化


async def sse_event_generator(  # 定义SSE事件生成器异步函数
    task_id: str,  # 参数：要监听的任务ID
):  # 异步生成器
    """生成SSE事件流。

    订阅指定任务的实时状态变化，通过异步生成器yield事件。
    前端通过EventSource连接此生成器，实时接收任务状态更新。

    事件类型：
    - status: 任务状态变化（pending/running/success/error）
    - result: 任务完成后的结果数据
    - error: 任务执行过程中的错误信息
    - heartbeat: 保持连接的心跳（每60秒一次）

    Args:
        task_id: 要监听的任务ID。

    Yields:
        包含事件类型和数据的字典。
    """  # 文档字符串
    async for event in hub.subscribe(task_id):  # 异步迭代：订阅指定任务的事件流
        # hub.subscribe(task_id) 返回一个异步迭代器
        # 每当有新事件时，迭代器会yield该事件
        # 如果没有新事件，会等待（不消耗CPU）
        yield event  # 将事件yield出去，发送给SSE客户端
        # FastAPI的EventSourceResponse会将yield的数据格式化为SSE格式
        # 格式如：data: {"type": "status", "data": "running"}\n\n
