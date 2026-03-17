from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tiangong_core.gateway.pidfile import gateway_pid_path, is_pid_running, read_pid, remove_pid, write_pid


def test_pidfile_roundtrip_and_running_detection(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    pidp = gateway_pid_path(ws)

    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1.5)"])
    try:
        write_pid(pidp, p.pid)
        pid = read_pid(pidp)
        assert pid == p.pid
        assert is_pid_running(pid)
    finally:
        p.terminate()
        try:
            p.wait(timeout=2.0)
        except Exception:
            p.kill()
        remove_pid(pidp)

