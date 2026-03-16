from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform

from tiangong_core.agent.skills import SkillsLoader


BOOTSTRAP_FILES = ("AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md")


def _read_if_exists(p: Path) -> str:
    try:
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    return ""


@dataclass(frozen=True)
class ContextParts:
    system: str
    skills_summary: str
    memory: str


class ContextBuilder:
    def __init__(self, workspace: Path) -> None:
        self._ws = workspace
        self._skills = SkillsLoader(workspace=workspace)

    def load_bootstrap(self) -> str:
        chunks: list[str] = []
        for name in BOOTSTRAP_FILES:
            s = _read_if_exists(self._ws / name)
            if s:
                chunks.append(f"## {name}\n{s}")
        return "\n\n".join(chunks).strip()

    def build_skills_summary(self) -> str:
        return self._skills.build_skills_summary()

    def load_always_skills(self) -> str:
        names = self._skills.get_always_skills()
        if not names:
            return ""
        return self._skills.load_skills_for_context(names)

    def load_memory(self) -> str:
        mem_dir = self._ws / "memory"
        mem = _read_if_exists(mem_dir / "MEMORY.md")
        hist = _read_if_exists(mem_dir / "HISTORY.md")
        chunks = []
        if mem:
            chunks.append(f"## MEMORY.md\n{mem}")
        if hist:
            chunks.append(f"## HISTORY.md\n{hist}")
        return "\n\n".join(chunks).strip()

    def build(self) -> ContextParts:
        bootstrap = self.load_bootstrap()
        skills_xml = self.build_skills_summary()
        # 对外暴露的 skills_summary 需要有可读标题，便于测试与下游展示；
        # 但 system prompt 中仍复用 skills_xml，保持稳定结构。
        skills_summary = f"Skills\n\n{skills_xml}".strip() if skills_xml else ""
        always_skills = self.load_always_skills()
        memory = self.load_memory()

        # 身份与运行环境（参考 nanobot，但保持 Tiangong 语境）
        ws = str(self._ws.expanduser().resolve())
        sys_name = platform.system()
        runtime = f"{'macOS' if sys_name == 'Darwin' else sys_name} {platform.machine()}, Python {platform.python_version()}"

        base = (
            "# Tiangong 助手\n\n"
            "你是 Tiangong Core 提供的本地智能体助手。\n\n"
            "## Runtime\n"
            f"{runtime}\n\n"
            "## Workspace\n"
            f"- workspace: {ws}\n"
            f"- skills: {ws}/skills/{{skill-name}}/SKILL.md\n"
            f"- memory: {ws}/memory/MEMORY.md 与 {ws}/memory/HISTORY.md\n\n"
            "## 使用约定\n"
            "- 当需要读取/修改文件或执行命令时，优先使用可用的 fs.* / shell.exec 等技能获取真实环境信息。\n"
            "- 如需使用某个技能包，请先用 fs.read 读取对应的 SKILL.md，按其中说明操作；仅在确有必要时才把大段说明注入后续上下文。\n"
        )

        system_chunks = [base]
        if bootstrap:
            system_chunks.append(bootstrap)
        if memory:
            system_chunks.append(memory)
        if always_skills:
            system_chunks.append(f"# Active Skills\n\n{always_skills}")
        if skills_xml:
            system_chunks.append(
                "# Skills\n\n"
                "The following skills extend your capabilities. To use a skill, read its SKILL.md file using the fs.read skill.\n"
                "Skills with available=\"false\" would require extra dependencies before use.\n\n"
                f"{skills_xml}"
            )

        system = "\n\n---\n\n".join(chunks for chunks in system_chunks if chunks).strip()
        return ContextParts(system=system, skills_summary=skills_summary, memory=memory)
