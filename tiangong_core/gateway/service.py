from __future__ import annotations

import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

from tiangong_core.app import TiangongApp
from tiangong_core.config import AppConfig


@dataclass(frozen=True)
class GatewayInfo:
    workspace: Path
    config_path: Path | None


def run_gateway(*, workspace: Path, config: AppConfig, config_path: Path | None = None) -> None:
    """
    Run Tiangong gateway in foreground:
    - starts TiangongApp
    - starts agent serve_forever loop in a background thread
    - channels inbound components are started by ChannelManager (app init)
    """
    ws = workspace.resolve()
    core = TiangongApp(workspace=ws, config=config)

    t = threading.Thread(target=core.serve_forever, daemon=True)
    t.start()

    stopping = threading.Event()

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        stopping.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)

    # Keep process alive; channels run in background threads.
    while not stopping.is_set():
        time.sleep(0.5)

