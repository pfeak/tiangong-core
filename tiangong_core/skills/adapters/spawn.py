from __future__ import annotations

import json
from typing import Any, Dict, List

from tiangong_core.agent.subagent import SubagentManager
from tiangong_core.skills.runtime import SkillFn


def _spawn_executor(args: Dict[str, Any]) -> str:
    mgr = SubagentManager()
    handle = mgr.spawn(
        parent_agent_id=str(args.get("parent_agent_id") or ""),
        name=str(args.get("name") or ""),
        payload=args.get("payload") or {},
        subtask_id=str(args.get("subtask_id")) if args.get("subtask_id") is not None else None,
    )
    return json.dumps(
        {
            "ok": True,
            "message": "spawn.subagent 接口已注册，但当前版本仅返回占位句柄，不执行真实子任务。",
            "handle": {
                "subagent_id": handle.subagent_id,
                "parent_agent_id": handle.parent_agent_id,
                "subtask_id": handle.subtask_id,
            },
        },
        ensure_ascii=False,
    )


def _cancel_executor(args: Dict[str, Any]) -> str:
    subagent_id = str(args.get("subagent_id") or "")
    return json.dumps(
        {
            "ok": True,
            "message": "spawn.cancel 接口为占位实现，当前版本不会真正取消任务。",
            "subagent_id": subagent_id,
        },
        ensure_ascii=False,
    )


def make_spawn_skills() -> List[SkillFn]:
    return [
        SkillFn(
            name="spawn.subagent",
            description="启动一个子智能体以处理长任务（v0.1 仅返回占位句柄，不执行真实子任务）。",
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
            executor=_spawn_executor,
        ),
        SkillFn(
            name="spawn.cancel",
            description="取消一个子智能体（v0.1 为占位实现，不真正取消任务）。",
            parameters={
                "type": "object",
                "properties": {"subagent_id": {"type": "string", "description": "需要取消的子智能体 ID。"}},
                "required": ["subagent_id"],
            },
            executor=_cancel_executor,
        ),
    ]


__all__ = ["make_spawn_skills"]

