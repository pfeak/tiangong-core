from __future__ import annotations

import os
import signal
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PidStatus:
    pid: int | None
    running: bool


def gateway_runtime_dir(workspace: Path) -> Path:
    p = (workspace / "runtime").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def gateway_pid_path(workspace: Path) -> Path:
    return gateway_runtime_dir(workspace) / "gateway.pid"


def gateway_log_path(workspace: Path) -> Path:
    return gateway_runtime_dir(workspace) / "gateway.log"


def read_pid(path: Path) -> int | None:
    try:
        s = path.read_text(encoding="utf-8").strip()
        return int(s) if s else None
    except Exception:
        return None


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def status(workspace: Path) -> PidStatus:
    pid = read_pid(gateway_pid_path(workspace))
    if not pid:
        return PidStatus(pid=None, running=False)
    return PidStatus(pid=pid, running=is_pid_running(pid))


def write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(pid)), encoding="utf-8")


def remove_pid(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def stop_pid(pid: int, *, sig: int = signal.SIGTERM) -> None:
    os.kill(pid, sig)

