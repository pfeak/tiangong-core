from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from tiangong_core.skills.runtime import SkillFn


@dataclass(frozen=True)
class CronJobSpec:
    """
    Cron 任务的最小规格描述（接口预留）。

    v0.1 不真正调度执行，只用于校验参数形状与后续兼容。
    """

    cron: str
    payload: Dict[str, Any]
    session_key: str | None = None


def _cron_schedule_executor(args: Dict[str, Any]) -> str:
    spec = CronJobSpec(
        cron=str(args.get("cron", "")),
        payload=dict(args.get("payload") or {}),
        session_key=str(args["session_key"]) if "session_key" in args and args["session_key"] is not None else None,
    )
    return json.dumps(
        {
            "ok": True,
            "message": "cron.schedule 接口已注册，但当前版本仅记录参数，不执行实际调度。",
            "job": {
                "cron": spec.cron,
                "payload": spec.payload,
                "session_key": spec.session_key,
            },
        },
        ensure_ascii=False,
    )


def make_cron_skills() -> List[SkillFn]:
    return [
        SkillFn(
            name="cron.schedule",
            description="创建或更新一个 cron 任务（v0.1 仅记录参数，不实际调度）。",
            parameters={
                "type": "object",
                "properties": {
                    "cron": {"type": "string", "description": "标准 cron 表达式，例如 '*/5 * * * *'。"},
                    "payload": {"type": "object", "description": "触发时传递给 Agent 的 payload，自由键值结构。"},
                    "session_key": {"type": ["string", "null"], "description": "可选：明确指定触发时使用的 session_key。"},
                },
                "required": ["cron", "payload"],
            },
            executor=_cron_schedule_executor,
        ),
    ]


__all__ = ["CronJobSpec", "make_cron_skills"]

