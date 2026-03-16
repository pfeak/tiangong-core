from __future__ import annotations

from pathlib import Path

from tiangong_core.agent.context import ContextBuilder
from tiangong_core.agent.skills import SkillsLoader


def test_skills_loader_uses_builtin_when_workspace_missing(tmp_path: Path) -> None:
    """
    当 workspace 下不存在 skills 目录时，应自动回退到 builtin skills。
    """
    ws = tmp_path
    loader = SkillsLoader(workspace=ws)
    names = {s.name for s in loader.list_skills()}
    # templates/skills 中至少包含 clawhub，占位作为 builtin 示例。
    assert "clawhub" in names


def test_context_builder_injects_builtin_skills_summary(tmp_path: Path) -> None:
    """
    空 workspace 但存在 builtin skills 时，system prompt 中应包含 skills 概要。
    """
    ws = tmp_path
    ctx = ContextBuilder(workspace=ws)
    parts = ctx.build()
    # skills_summary 非空，且提到 builtin 来源。
    assert "Skills" in parts.skills_summary
    assert "clawhub" in parts.skills_summary
