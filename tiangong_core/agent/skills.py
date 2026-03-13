from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    description: str
    always: bool
    tags: tuple[str, ...]
    source: str  # "workspace" | "builtin"
    path: str  # filesystem path (workspace) or resource path (builtin)
    body: str


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """
    Parse a minimal YAML-frontmatter subset:
    - only supports `key: value`, `key: true/false`, `key: [a, b]`, and
      list blocks:
        key:
          - a
          - b
    Any parse failure falls back to empty metadata.
    """
    s = (text or "").lstrip("\ufeff")
    if not s.startswith("---"):
        return {}, text.strip()

    lines = s.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    meta_lines: list[str] = []
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            i += 1
            break
        meta_lines.append(lines[i])
        i += 1

    body = "\n".join(lines[i:]).strip()
    meta = _parse_frontmatter_lines(meta_lines)
    return meta, body


def _parse_frontmatter_lines(lines: list[str]) -> dict[str, object]:
    out: dict[str, object] = {}
    key: str | None = None
    block_items: list[str] | None = None

    def flush_block() -> None:
        nonlocal key, block_items
        if key is not None and block_items is not None:
            out[key] = [x for x in block_items if x]
        key = None
        block_items = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.lstrip().startswith("- ") and key is not None and block_items is not None:
            block_items.append(line.lstrip()[2:].strip())
            continue

        # new key
        flush_block()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue

        if v == "":
            key = k
            block_items = []
            continue

        out[k] = _parse_scalar_or_inline_list(v)

    flush_block()
    return out


def _parse_scalar_or_inline_list(v: str) -> object:
    vv = v.strip()
    if vv.lower() in ("true", "false"):
        return vv.lower() == "true"
    if vv.startswith("[") and vv.endswith("]"):
        inner = vv[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip("'").strip('"') for x in inner.split(",") if x.strip()]
    # strip quotes if present
    if (vv.startswith('"') and vv.endswith('"')) or (vv.startswith("'") and vv.endswith("'")):
        return vv[1:-1]
    return vv


def _as_str(meta: dict[str, object], key: str, default: str = "") -> str:
    v = meta.get(key)
    if isinstance(v, str):
        return v.strip()
    return default


def _as_bool(meta: dict[str, object], key: str, default: bool = False) -> bool:
    v = meta.get(key)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower().strip() in ("true", "1", "yes", "y", "on"):
            return True
        if v.lower().strip() in ("false", "0", "no", "n", "off"):
            return False
    return default


def _as_tags(meta: dict[str, object], key: str = "tags") -> tuple[str, ...]:
    v = meta.get(key)
    if isinstance(v, list):
        return tuple(str(x).strip() for x in v if str(x).strip())
    if isinstance(v, str) and v.strip():
        # allow comma-separated
        return tuple(x.strip() for x in v.split(",") if x.strip())
    return ()


class SkillsLoader:
    """
    Skills: documented instruction packs stored as Markdown (SKILL.md).

    Priority: workspace skills override builtin skills by name.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        skills_dir_name: str = "skills",
        builtin_pkg: str = "tiangong_core.templates.skills",
    ) -> None:
        self._ws = workspace
        self._skills_dir = (workspace / skills_dir_name).resolve()
        self._builtin_pkg = builtin_pkg

    def list_skills(self) -> list[Skill]:
        by_name: dict[str, Skill] = {}
        for s in self._iter_builtin_skills():
            by_name[s.name] = s
        for s in self._iter_workspace_skills():
            by_name[s.name] = s
        return sorted(by_name.values(), key=lambda x: x.name)

    def get_always_skills(self) -> list[str]:
        names = [s.name for s in self.list_skills() if s.always]
        return sorted(set(names))

    def load_skills_for_context(self, names: Iterable[str]) -> str:
        want = {n.strip() for n in names if n and n.strip()}
        if not want:
            return ""
        skills = {s.name: s for s in self.list_skills()}
        chunks: list[str] = []
        for name in sorted(want):
            s = skills.get(name)
            if not s or not s.body:
                continue
            title = s.title or s.name
            header = f"## SKILL: {title}\n"
            if s.description:
                header += f"{s.description}\n"
            header += f"(source={s.source}, name={s.name})\n"
            chunks.append(header + "\n" + s.body.strip())
        return "\n\n".join(chunks).strip()

    def build_skills_summary(self) -> str:
        skills = self.list_skills()
        if not skills:
            return ""
        lines: list[str] = [
            "## Skills",
            "可用技能（默认仅注入概要；always skills 会自动常驻；如需全文可按需加载）：",
        ]
        for s in skills:
            title = s.title or s.name
            always = " (always)" if s.always else ""
            desc = f" — {s.description}" if s.description else ""
            lines.append(f"- {s.name}: {title}{always}{desc} [{s.source}]")
        return "\n".join(lines).strip()

    def _iter_workspace_skills(self) -> Iterable[Skill]:
        root = self._skills_dir
        if not root.exists() or not root.is_dir():
            return []
        out: list[Skill] = []
        for p in sorted(root.glob("*/SKILL.md")):
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            name = p.parent.name
            meta, body = _split_frontmatter(text)
            out.append(
                Skill(
                    name=name,
                    title=_as_str(meta, "title", default=name),
                    description=_as_str(meta, "description", default=""),
                    always=_as_bool(meta, "always", default=False),
                    tags=_as_tags(meta, "tags"),
                    source="workspace",
                    path=str(p),
                    body=body,
                )
            )
        return out

    def _iter_builtin_skills(self) -> Iterable[Skill]:
        try:
            pkg_root = resources.files(self._builtin_pkg)
        except Exception:
            return []

        out: list[Skill] = []
        try:
            for p in sorted(pkg_root.glob("*/SKILL.md")):
                try:
                    text = p.read_text(encoding="utf-8")
                except Exception:
                    continue
                # resource path: <skill-name>/SKILL.md
                name = getattr(getattr(p, "parent", None), "name", "") or str(p).split("/")[-2]
                meta, body = _split_frontmatter(text)
                out.append(
                    Skill(
                        name=name,
                        title=_as_str(meta, "title", default=name),
                        description=_as_str(meta, "description", default=""),
                        always=_as_bool(meta, "always", default=False),
                        tags=_as_tags(meta, "tags"),
                        source="builtin",
                        path=f"{self._builtin_pkg}:{name}/SKILL.md",
                        body=body,
                    )
                )
        except Exception:
            return out
        return out
