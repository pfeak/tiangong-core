from __future__ import annotations

from tiangong_core.skills.runtime import SkillFn


def make_mcp_skills() -> list[SkillFn]:
    """
    MCP bridge 接口预留。

    当前版本始终启用该桥接入口，但尚未注册具体技能集合。
    后续可以在此把 MCP 能力动态注入 SkillsRuntime（参考 PRD 3.2.3）。
    """

    return []


__all__ = ["make_mcp_skills"]
