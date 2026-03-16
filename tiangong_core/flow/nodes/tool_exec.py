from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.flow.nodes import BaseNode
from tiangong_core.flow.schemas import NodeResult
from tiangong_core.skills.runtime import SkillsRuntime


@dataclass
class ToolExecNode(BaseNode):
    """
    工具执行节点（占位版）。

    典型用法：在 shared 中放入 SkillsRuntime 和技能调用参数，节点负责执行并把结果写回 shared。
    这样 tiangong-research 可以在不直接依赖 AgentLoop 的情况下，搭建 PocketFlow 风格的
    “tools-only” 小流程。
    """

    tools_key: str = "skills"
    call_key: str = "tool_call"
    result_key: str = "tool_result"

    def prep(self, shared: dict[str, Any]) -> dict[str, Any]:
        return {
            "skills": shared.get(self.tools_key),
            "call": shared.get(self.call_key),
        }

    def exec(self, input_data: dict[str, Any]) -> NodeResult:
        skills = input_data.get("skills")
        call = input_data.get("call") or {}
        if not isinstance(skills, SkillsRuntime):
            return NodeResult(status="error", message="ToolExecNode 需要 shared['skills'] 为 SkillsRuntime 实例。")
        name = str(call.get("name") or "")
        if not name:
            return NodeResult(status="error", message="ToolExecNode 需要 call.name。")
        args = call.get("arguments") or {}
        if not isinstance(args, dict):
            return NodeResult(status="error", message="ToolExecNode 需要 call.arguments 为对象。")
        out = skills.execute(name, args)
        return NodeResult(status="ok", data={"name": name, "output": out})

    def post(self, shared: dict[str, Any], prep_res: dict[str, Any], exec_res: NodeResult) -> str:
        shared[self.result_key] = exec_res.data
        return exec_res.status


__all__ = ["ToolExecNode"]
