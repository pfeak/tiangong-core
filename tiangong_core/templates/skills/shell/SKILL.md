---
name: shell
description: Execute shell commands inside the workspace using the shell.exec skill, with clear safety and timeout constraints.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"💻"}}
---

# Shell Skill (`shell.exec`)

Use this skill when you need to run **short, deterministic commands** in a shell, such as invoking formatters, linters, or project-specific scripts.

## When to use

- Running `pytest`, `ruff`, `black`, or other CLI tools.
- Calling project-specific scripts (for example, `scripts/*.sh`).
- Inspecting git status or simple one-off commands.

## When **not** to use

- Do **not** use shell commands to read or write files when `fs.*` is sufficient (prefer `fs.read`, `fs.write`, `fs.edit`, `fs.list`).
- Avoid long-running tasks, background daemons, or interactive programs.

## shell.exec

```json
{
  "command": "string, required",
  "cwd": "optional working directory, relative or absolute"
}
```

Behavior:

- If `cwd` is omitted, the workspace root is used.
- Execution is bounded by a configured timeout (seconds). If the command exceeds this timeout it fails with a timeout error.
- The result includes:
  - `exit_code`: integer exit code from the command.
  - `stdout`: standard output as a string.
  - `stderr`: standard error as a string.

## Good usage patterns

- Prefer explicit, idempotent commands:

```bash
pytest -q
ruff check .
python -m pip install -r requirements.txt
```

- Always assume the command may fail; check `exit_code` and include useful excerpts from `stdout`/`stderr` in your explanation to the user.
