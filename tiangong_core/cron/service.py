from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tiangong_core.bus.events import InboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.utils.ids import new_id


@dataclass(frozen=True)
class CronJob:
    job_id: str
    cron: str
    payload: dict[str, Any]
    session_key: str | None = None
    created_at: float = 0.0


def _parse_field(field: str, *, min_v: int, max_v: int) -> set[int]:
    """
    Very small cron parser for v0.1:
    - "*" means all values
    - "*/n" means step
    - "n" means a single integer
    Anything else raises ValueError.
    """
    s = (field or "").strip()
    if s == "*":
        return set(range(min_v, max_v + 1))
    if s.startswith("*/"):
        step = int(s[2:])
        if step <= 0:
            raise ValueError("invalid_cron_step")
        return set(range(min_v, max_v + 1, step))
    v = int(s)
    if v < min_v or v > max_v:
        raise ValueError("invalid_cron_value")
    return {v}


def _cron_matches(cron_expr: str, dt: datetime) -> bool:
    parts = (cron_expr or "").strip().split()
    if len(parts) != 5:
        raise ValueError("invalid_cron_expression")
    minute_s, hour_s, dom_s, month_s, dow_s = parts
    minutes = _parse_field(minute_s, min_v=0, max_v=59)
    hours = _parse_field(hour_s, min_v=0, max_v=23)
    dom = _parse_field(dom_s, min_v=1, max_v=31)
    month = _parse_field(month_s, min_v=1, max_v=12)
    dow = _parse_field(dow_s, min_v=0, max_v=6)  # 0=Mon .. 6=Sun (Python weekday)
    return (
        dt.minute in minutes
        and dt.hour in hours
        and dt.day in dom
        and dt.month in month
        and dt.weekday() in dow
    )


class CronService:
    """
    Minimal in-process cron scheduler for v0.1.

    - Runs a background thread (daemon).
    - Checks jobs every second, but only fires at most once per minute per job.
    - When a job fires, it publishes an InboundMessage to the same MessageBus,
      so the existing Agent loop will pick it up.
    """

    def __init__(self, *, bus: MessageBus) -> None:
        self._bus = bus
        self._lock = threading.Lock()
        self._jobs: dict[str, CronJob] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_fire_key: dict[str, str] = {}  # job_id -> "YYYYmmddHHMM"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="tiangong-cron", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def upsert(self, *, cron: str, payload: dict[str, Any], session_key: str | None = None) -> CronJob:
        job_id = new_id()
        job = CronJob(
            job_id=job_id,
            cron=str(cron or ""),
            payload=dict(payload or {}),
            session_key=str(session_key) if session_key is not None else None,
            created_at=time.time(),
        )
        # Validate cron expression early.
        _ = _cron_matches(job.cron, datetime.now())
        with self._lock:
            self._jobs[job_id] = job
        self.start()
        return job

    def list_jobs(self) -> list[CronJob]:
        with self._lock:
            return list(self._jobs.values())

    def _run(self) -> None:
        while not self._stop.is_set():
            now = datetime.now()
            minute_key = now.strftime("%Y%m%d%H%M")
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                try:
                    if not _cron_matches(job.cron, now):
                        continue
                except Exception:
                    continue
                last = self._last_fire_key.get(job.job_id)
                if last == minute_key:
                    continue
                self._last_fire_key[job.job_id] = minute_key

                msg = InboundMessage(
                    channel="cron",
                    chat_id=job.job_id,
                    content=json.dumps({"event": "cron", "job_id": job.job_id, "payload": job.payload}, ensure_ascii=False),
                    session_key=job.session_key or f"cron:{job.job_id}",
                    metadata={"event": "cron", "job_id": job.job_id, "payload": job.payload},
                )
                self._bus.publish_inbound(msg)
            time.sleep(1.0)


__all__ = ["CronJob", "CronService"]
