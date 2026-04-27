"""
event_bus.py — 任务级事件总线

后台线程（Orchestrator）→ 写入 sync Queue
SSE 异步端点              → 从 Queue 读取并推送给浏览器

设计原则：
  - 简单：标准库 queue.Queue，无外部依赖
  - 安全：None 作为 sentinel，表示流结束
  - 防泄漏：close() 后自动清除引用
"""
from __future__ import annotations

import queue
import threading
from typing import Optional

_lock = threading.Lock()
_queues: dict[str, queue.Queue[Optional[dict]]] = {}

QUEUE_MAXSIZE = 1000   # 防止极端情况下内存爆炸


def create(task_id: str) -> queue.Queue[Optional[dict]]:
    """为指定任务创建一个新队列，返回队列引用。"""
    q: queue.Queue[Optional[dict]] = queue.Queue(maxsize=QUEUE_MAXSIZE)
    with _lock:
        _queues[task_id] = q
    return q


def get_queue(task_id: str) -> Optional[queue.Queue[Optional[dict]]]:
    """获取任务队列，不存在返回 None。"""
    return _queues.get(task_id)


def push(task_id: str, event: dict) -> None:
    """向任务队列推送一个事件，队列满时静默丢弃。"""
    q = _queues.get(task_id)
    if q is None:
        return
    try:
        q.put_nowait(event)
    except queue.Full:
        pass


def close(task_id: str) -> None:
    """发送 sentinel（None）并移除队列引用。"""
    with _lock:
        q = _queues.pop(task_id, None)
    if q:
        try:
            q.put_nowait(None)   # sentinel → SSE 端关闭流
        except queue.Full:
            pass
