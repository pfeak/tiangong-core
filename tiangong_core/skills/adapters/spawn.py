from __future__ import annotations

import json
from typing import Any

from tiangong_core.agent.subagent import SubagentManager
from tiangong_core.skills.runtime import SkillFn


def make_spawn_skills(*, mgr: SubagentManager) -> list[SkillFn]:
    def spawn(args: dict[str, Any]) -> str:
        handle = mgr.spawn(
            parent_agent_id=str(args.get("parent_agent_id") or ""),
            name=str(args.get("name") or ""),
            payload=args.get("payload") or {},
            subtask_id=str(args.get("subtask_id")) if args.get("subtask_id") is not None else None,
        )
        return json.dumps(
            {
                "ok": True,
                "message": "spawn.subagent 已创建子任务并投递到队列（异步执行）。",
                "handle": {
                    "subagent_id": handle.subagent_id,
                    "parent_agent_id": handle.parent_agent_id,
                    "subtask_id": handle.subtask_id,
                },
            },
            ensure_ascii=False,
        )

    return [
        SkillFn(
            name="spawn.subagent",
            description="启动一个子智能体以处理长任务（v0.1：异步投递到本进程队列执行）。",
            parameters={
                "type": "object",
                "properties": {
                    "parent_agent_id": {"type": "string", "description": "父智能体的唯一 ID。"},
                    "name": {"type": "string", "description": "子智能体逻辑名称或用途说明。"},
                    "payload": {"type": "object", "description": "可选：子任务输入 payload，自由结构。"},
                    "subtask_id": {"type": ["string", "null"], "description": "可选：用于串联一次子任务链路的 ID。"},
                },
                "required": ["parent_agent_id", "name"],
            },
            executor=spawn,
        ),
        SkillFn(
            name="spawn.cancel",
            description="取消一个子智能体（v0.1：未开始则跳过；已开始可能无法中断）。",
            parameters={
                "type": "object",
                "properties": {"subagent_id": {"type": "string", "description": "需要取消的子智能体 ID。"}},
                "required": ["subagent_id"],
            },
            executor=lambda args: json.dumps(
                {
                    "ok": True,
                    "result": {"cancelled": mgr.cancel(str(args.get("subagent_id") or ""))},
                },
                ensure_ascii=False,
            ),
        ),
    ]


__all__ = ["make_spawn_skills"]
