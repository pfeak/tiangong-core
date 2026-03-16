from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SessionPaths:
    root: Path

    def file_for(self, session_key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in session_key)[:200]
        return self.root / f"{safe}.jsonl"

    def stop_file_for(self, session_key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in session_key)[:200]
        return self.root / f"{safe}.stop.json"


def _is_user_turn_start(msg: dict[str, Any]) -> bool:
    return msg.get("role") == "user"


class SessionManager:
    def __init__(self, workspace: Path) -> None:
        self._paths = SessionPaths(root=(workspace / "sessions"))
        self._paths.root.mkdir(parents=True, exist_ok=True)
        # 简单进程内缓存：append-only JSONL，缓存最近一次 load 结果，避免每轮全量读文件。
        # key: session_key -> list[dict]
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._log = logging.getLogger("tiangong.session")

    def load(self, session_key: str) -> list[dict[str, Any]]:
        if session_key in self._cache:
            return list(self._cache[session_key])
        p = self._paths.file_for(session_key)
        if not p.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        # 仅在正常解析完成后写入缓存，避免污染缓存。
        self._cache[session_key] = list(out)
        return out

    def is_stopped(self, session_key: str) -> bool:
        p = self._paths.stop_file_for(session_key)
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return bool(data.get("stopped"))
        except Exception:
            return True

    def stop(self, session_key: str, *, metadata: dict[str, Any] | None = None) -> None:
        p = self._paths.stop_file_for(session_key)
        payload: dict[str, Any] = {"stopped": True}
        if metadata:
            payload["metadata"] = metadata
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # 停止会话不会清理历史，但可以在此打日志方便排查。
        try:
            self._log.info(
                "session_stopped",
                extra={"session_key": session_key, "metadata": metadata or {}},
            )
        except Exception:
            pass

    def append(self, session_key: str, records: Iterable[dict[str, Any]]) -> None:
        p = self._paths.file_for(session_key)
        # 先写盘，再更新缓存，确保异常不会破坏缓存与文件的一致性。
        with p.open("a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        # 更新进程内缓存（append-only）
        if session_key in self._cache:
            buf = self._cache[session_key]
        else:
            buf = []
        for r in records:
            if isinstance(r, dict):
                buf.append(r)
        self._cache[session_key] = buf
        # 结构化日志：便于按 agent_id/run_id/session_key 排查
        try:
            for r in records:
                meta = r.get("metadata") if isinstance(r, dict) else None
                self._log.info(
                    "session_append",
                    extra={
                        "session_key": session_key,
                        "role": r.get("role") if isinstance(r, dict) else None,
                        "agent_id": (meta or {}).get("agent_id") if isinstance(meta, dict) else None,
                        "run_id": (meta or {}).get("run_id") if isinstance(meta, dict) else None,
                    },
                )
        except Exception:
            # 日志不可影响主流程
            pass

    def append_meta(self, session_key: str, meta: dict[str, Any]) -> None:
        """
        Append a non-message meta record for this run/turn.
        Note: get_history() will ignore it because it doesn't have role=...
        """
        self.append(session_key, [{"type": "meta", **meta}])

    def get_history(self, session_key: str, max_messages: int = 50) -> list[dict[str, Any]]:
        rows = self.load(session_key)
        if not rows:
            return []

        # jsonl: 首行可为 metadata，其余为 messages；这里允许混写，按 role 过滤。
        msgs = [r for r in rows if isinstance(r, dict) and r.get("role") in ("system", "user", "assistant", "tool")]
        if not msgs:
            return []

        tail = msgs[-max_messages:]

        # 避免以 tool/tool_result 开头导致“孤儿 tool_result”
        first_user_idx = next((i for i, m in enumerate(tail) if _is_user_turn_start(m)), None)
        if first_user_idx is None:
            return []
        tail = tail[first_user_idx:]

        # 避免尾部出现 assistant 为空且无 tool_calls 的“毒化”
        if tail and tail[-1].get("role") == "assistant":
            content = tail[-1].get("content")
            tool_calls = tail[-1].get("tool_calls")
            if (content is None or content == "") and not tool_calls:
                tail = tail[:-1]

        return tail
