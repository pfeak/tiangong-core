from __future__ import annotations

import json

from tiangong_core.agent.subagent import SubagentManager
from tiangong_core.bus.queue import MessageBus
from tiangong_core.cron.service import CronService
from tiangong_core.skills.adapters.cron import make_cron_skills
from tiangong_core.skills.adapters.mcp import make_mcp_skills
from tiangong_core.skills.adapters.spawn import make_spawn_skills


def test_cron_skills_always_enabled() -> None:
    bus = MessageBus()
    svc = CronService(bus=bus)
    skills = make_cron_skills(svc=svc)
    assert skills
    names = {s.name for s in skills}
    assert "cron.schedule" in names

    cron_skill = next(s for s in skills if s.name == "cron.schedule")
    out = cron_skill.executor({"cron": "*/5 * * * *", "payload": {"x": 1}})
    data = json.loads(out)
    assert data["ok"] is True
    assert "cron.schedule 已创建任务" in data["message"]
    assert data["job"]["cron"] == "*/5 * * * *"


def test_spawn_skills_always_enabled() -> None:
    bus = MessageBus()
    mgr = SubagentManager(bus=bus)
    skills = make_spawn_skills(mgr=mgr)
    assert skills
    names = {s.name for s in skills}
    assert {"spawn.subagent", "spawn.cancel"}.issubset(names)

    spawn_skill = next(s for s in skills if s.name == "spawn.subagent")
    out = spawn_skill.executor({"parent_agent_id": "p1", "name": "child"})
    data = json.loads(out)
    assert data["ok"] is True
    assert "异步执行" in data["message"]
    assert data["handle"]["parent_agent_id"] == "p1"


def test_mcp_skills_bridge_is_noop_but_enabled() -> None:
    skills = make_mcp_skills()
    # 当前实现始终启用 bridge，但尚未注册具体技能。
    assert skills == []
