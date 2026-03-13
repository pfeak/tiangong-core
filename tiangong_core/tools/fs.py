from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from .registry import Tool


def _resolve(workspace: Path, p: str, restrict: bool) -> Path:
    pp = Path(p)
    if not pp.is_absolute():
        pp = (workspace / pp).resolve()
    else:
        pp = pp.resolve()
    if restrict:
        ws = workspace.resolve()
        if ws not in pp.parents and pp != ws:
            raise PermissionError(f"path_outside_workspace: {pp}")
    return pp


def make_fs_tools(*, workspace: Path, restrict_to_workspace: bool) -> list[Tool]:
    def read(args: dict[str, Any]) -> dict[str, Any]:
        path = _resolve(workspace, str(args.get("path") or ""), restrict_to_workspace)
        text = path.read_text(encoding="utf-8")
        return {"path": str(path), "content": text}

    def write(args: dict[str, Any]) -> dict[str, Any]:
        path = _resolve(workspace, str(args.get("path") or ""), restrict_to_workspace)
        content = str(args.get("content") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "bytes": len(content.encode("utf-8"))}

    def list_dir(args: dict[str, Any]) -> dict[str, Any]:
        path = _resolve(workspace, str(args.get("path") or "."), restrict_to_workspace)
        if not path.exists():
            return {"path": str(path), "entries": []}
        entries = []
        for p in sorted(path.iterdir(), key=lambda x: x.name):
            entries.append({"name": p.name, "is_dir": p.is_dir(), "size": p.stat().st_size})
        return {"path": str(path), "entries": entries}

    def edit(args: dict[str, Any]) -> dict[str, Any]:
        path = _resolve(workspace, str(args.get("path") or ""), restrict_to_workspace)
        old = str(args.get("old") or "")
        new = str(args.get("new") or "")
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise ValueError("old_string_not_found")
        text2 = text.replace(old, new, 1)
        path.write_text(text2, encoding="utf-8")
        diff = "\n".join(
            difflib.unified_diff(text.splitlines(), text2.splitlines(), fromfile="before", tofile="after", lineterm="")
        )
        return {"path": str(path), "diff": diff}

    schema_path = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
    schema_write = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }
    schema_edit = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
        "required": ["path", "old", "new"],
    }

    return [
        Tool(name="fs.read", description="Read a text file", parameters=schema_path, executor=read),
        Tool(name="fs.write", description="Write a text file (overwrite)", parameters=schema_write, executor=write),
        Tool(name="fs.list", description="List directory entries", parameters=schema_path, executor=list_dir),
        Tool(name="fs.edit", description="Replace one occurrence in a file", parameters=schema_edit, executor=edit),
    ]
