from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from tiangong_core.cron.service import CronService
from tiangong_core.skills.runtime import SkillFn


@dataclass(frozen=True)
class CronJobSpec:
    """
    Cron 任务的最小规格描述（接口预留）。

    v0.1 不真正调度执行，只用于校验参数形状与后续兼容。
    """

    cron: str
    payload: dict[str, Any]
    session_key: str | None = None


def make_cron_skills(*, svc: CronService) -> list[SkillFn]:
    def schedule(args: dict[str, Any]) -> str:
        spec = CronJobSpec(
            cron=str(args.get("cron", "")),
            payload=dict(args.get("payload") or {}),
            session_key=str(args["session_key"]) if "session_key" in args and args["session_key"] is not None else None,
        )
        job = svc.upsert(cron=spec.cron, payload=spec.payload, session_key=spec.session_key)
        return json.dumps(
            {
                "ok": True,
                "message": "cron.schedule 已创建任务；由本进程后台调度线程触发执行。",
                "job": {
                    "job_id": job.job_id,
                    "cron": job.cron,
                    "payload": job.payload,
                    "session_key": job.session_key,
                },
            },
            ensure_ascii=False,
        )

    return [
        SkillFn(
            name="cron.schedule",
            description="创建一个 cron 任务（v0.1：进程内后台线程调度触发）。",
            parameters={
                "type": "object",
                "properties": {
                    "cron": {"type": "string", "description": "标准 cron 表达式，例如 '*/5 * * * *'。"},
                    "payload": {"type": "object", "description": "触发时传递给 Agent 的 payload，自由键值结构。"},
                    "session_key": {"type": ["string", "null"], "description": "可选：明确指定触发时使用的 session_key。"},
                },
                "required": ["cron", "payload"],
            },
            executor=schedule,
        ),
    ]


__all__ = ["CronJobSpec", "make_cron_skills"]
