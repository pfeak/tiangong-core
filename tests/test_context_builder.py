from __future__ import annotations

from pathlib import Path

from tiangong_core.agent.context import ContextBuilder, ContextParts


def test_context_builder_aggregates_bootstrap_skills_and_memory(tmp_path: Path) -> None:
    ws = tmp_path

    # bootstrap files
    (ws / "AGENTS.md").write_text("agent-rules", encoding="utf-8")
    (ws / "USER.md").write_text("user-pref", encoding="utf-8")

    # memory files
    mem_dir = ws / "memory"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("important facts", encoding="utf-8")
    (mem_dir / "HISTORY.md").write_text("conversation summary", encoding="utf-8")

    # skills: create a minimal always-on skill and a normal skill
    skills_root = ws / "skills"
    (skills_root / "always-skill").mkdir(parents=True)
    (skills_root / "always-skill" / "SKILL.md").write_text(
        """---
title: always
description: always on skill
always: true
---
ALWAYS BODY
""",
        encoding="utf-8",
    )
    (skills_root / "other-skill").mkdir(parents=True)
    (skills_root / "other-skill" / "SKILL.md").write_text(
        """---
title: other
description: other skill
---
OTHER BODY
""",
        encoding="utf-8",
    )

    ctx = ContextBuilder(workspace=ws)
    parts: ContextParts = ctx.build()

    # system prompt 应包含 bootstrap + skills summary + always skills + memory 片段
    assert "AGENTS.md" in parts.system
    assert "USER.md" in parts.system
    assert "Skills" in parts.system
    assert "always-skill" in parts.system
    assert "ALWAYS BODY" in parts.system
    assert "MEMORY.md" in parts.system
    assert "HISTORY.md" in parts.system

    # skills_summary/memory 字段也应单独暴露
    assert "Skills" in parts.skills_summary
    assert "important facts" in parts.memory
    assert "conversation summary" in parts.memory


def test_context_builder_fallback_system_prompt_when_empty(tmp_path: Path) -> None:
    ws = tmp_path
    ctx = ContextBuilder(workspace=ws)
    parts = ctx.build()

    # workspace 为空时仍应提供基础 system prompt（即使存在 builtin skills summary 也应有该前缀）
    assert isinstance(parts.system, str)
    assert parts.system != ""
    assert "Tiangong 助手" in parts.system
