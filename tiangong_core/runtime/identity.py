from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tiangong_core.utils.ids import new_id


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    agent_name: str


def load_or_create_identity(workspace: Path, agent_name: str) -> AgentIdentity:
    runtime_dir = workspace / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    p = runtime_dir / "agent.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            agent_id = str(data.get("agent_id") or "").strip()
            if agent_id:
                return AgentIdentity(agent_id=agent_id, agent_name=agent_name)
        except Exception:
            pass

    ident = AgentIdentity(agent_id=new_id(), agent_name=agent_name)
    p.write_text(json.dumps({"agent_id": ident.agent_id}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ident
