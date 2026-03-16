from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        skills = self.build_skills_summary()
        always_skills = self.load_always_skills()
        memory = self.load_memory()

        base = (
            "你是 Tiangong 助手，运行在一个本地 workspace 中。\n"
            "当用户请求查看/操作文件、执行命令、读取目录内容等需要真实环境信息时，优先使用可用工具获取事实（如 shell.exec、fs.*）。\n"
            "回复应直接给出结果；如果工具执行失败，要把错误原因和可操作的下一步说明清楚。"
        )

        system_chunks = [base]
        if bootstrap:
            system_chunks.append(bootstrap)
        if skills:
            system_chunks.append(skills)
        if always_skills:
            system_chunks.append(always_skills)
        if memory:
            system_chunks.append(memory)

        system = "\n\n".join(system_chunks).strip()
        return ContextParts(system=system, skills_summary=skills, memory=memory)
