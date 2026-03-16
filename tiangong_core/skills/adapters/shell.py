from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from tiangong_core.skills.adapters.fs import _resolve
from tiangong_core.skills.runtime import SkillFn


def make_shell_skills(*, workspace: Path, restrict_to_workspace: bool, timeout_s: int) -> list[SkillFn]:
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
    return [SkillFn(name="shell.exec", description="Execute a shell command", parameters=schema, executor=exec_cmd)]


__all__ = ["make_shell_skills"]

