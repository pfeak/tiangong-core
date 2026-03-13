from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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

    def load_bootstrap(self) -> str:
        chunks: list[str] = []
        for name in BOOTSTRAP_FILES:
            s = _read_if_exists(self._ws / name)
            if s:
                chunks.append(f"## {name}\n{s}")
        return "\n\n".join(chunks).strip()

    def build_skills_summary(self) -> str:
        skills_dir = self._ws / "skills"
        if not skills_dir.exists():
            return ""
        names = sorted({p.parent.name for p in skills_dir.glob("*/SKILL.md")})
        if not names:
            return ""
        return (
            "## Skills\n"
            "可用技能（按需启用；避免把整份技能全文塞满上下文）：\n"
            + "\n".join(f"- {n}" for n in names)
        )

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
        memory = self.load_memory()

        system_chunks = []
        if bootstrap:
            system_chunks.append(bootstrap)
        if skills:
            system_chunks.append(skills)
        if memory:
            system_chunks.append(memory)

        system = "\n\n".join(system_chunks).strip()
        if not system:
            # 兜底 system prompt：没有 workspace 引导文件时也尽量让 agent 正确使用工具
            system = (
                "你是 Tiangong 助手，运行在一个本地 workspace 中。\n"
                "当用户请求查看/操作文件、执行命令、读取目录内容等需要真实环境信息时，优先使用可用工具获取事实（如 shell.exec、fs.*）。\n"
                "回复应直接给出结果；如果工具执行失败，要把错误原因和可操作的下一步说明清楚。"
            )
        return ContextParts(system=system, skills_summary=skills, memory=memory)
