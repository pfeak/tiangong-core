from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SubagentHandle:
    """
    代表一次子智能体运行的“句柄”。

    v0.1 仅作为占位符存在，后续可以挂接真正的子进程/子会话实现。
    """

    subagent_id: str
    parent_agent_id: str
    subtask_id: str | None = None


class SubagentManager:
    """
    子智能体管理器（接口预留版）。

    设计目标参考 PRD 3.8：
    - 将长任务/探索任务/专门能力下放到子 agent
    - 支持取消、并发、结果汇总
    - 子 agent 工具集可受限（只读/只 web/只 fs）

    v0.1 中我们仅提供最小可用的接口形状，具体调度/隔离策略后续迭代补充。
    """

    def __init__(self) -> None:
        # 目前仅在内存中保存占位信息，避免 API 形状日后难以兼容。
        self._running: dict[str, SubagentHandle] = {}

    def spawn(
        self,
        *,
        parent_agent_id: str,
        name: str,
        payload: Dict[str, Any] | None = None,
        subtask_id: str | None = None,
    ) -> SubagentHandle:
        """
        启动一个子智能体。

        v0.1 中不会真正执行子任务，仅返回一个 SubagentHandle 占位，
        以便后续在工具层面或 Cron 中挂接真实实现。
        """
        # 延迟导入，避免 utils.ids 在早期导入阶段产生循环依赖。
        from tiangong_core.utils.ids import new_id

        subagent_id = new_id()
        handle = SubagentHandle(subagent_id=subagent_id, parent_agent_id=parent_agent_id, subtask_id=subtask_id)
        self._running[subagent_id] = handle
        # payload 当前仅用于未来扩展，不做持久化。
        _ = payload
        return handle

    def cancel(self, subagent_id: str) -> bool:
        """
        取消一个子智能体。

        v0.1 中仅从内存表中移除记录，不做真正的进程/任务取消。
        返回值表示是否存在对应 subagent 记录。
        """
        return self._running.pop(subagent_id, None) is not None

    def list_running(self) -> list[SubagentHandle]:
        """
        返回当前仍被认为“运行中”的子智能体列表。

        仅用于调试与占位，后续可挂接真实的状态刷新逻辑。
        """
        return list(self._running.values())
