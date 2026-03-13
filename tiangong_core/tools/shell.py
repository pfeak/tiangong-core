from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .fs import _resolve
from .registry import Tool


def make_shell_tools(*, workspace: Path, restrict_to_workspace: bool, timeout_s: int) -> list[Tool]:
    def exec_cmd(args: dict[str, Any]) -> dict[str, Any]:
        cmd = str(args.get("command") or "")
        cwd_raw = args.get("cwd")
        cwd = _resolve(workspace, str(cwd_raw), restrict_to_workspace) if cwd_raw else workspace
        if not cmd.strip():
            raise ValueError("empty_command")
        cp = subprocess.run(
            cmd,
            cwd=str(cwd),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_s if timeout_s > 0 else None,
        )
        return {"exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}

    schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}},
        "required": ["command"],
    }
    return [Tool(name="shell.exec", description="Execute a shell command", parameters=schema, executor=exec_cmd)]
