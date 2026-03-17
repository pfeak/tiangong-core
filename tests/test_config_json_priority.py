from __future__ import annotations

import json
from pathlib import Path

from tiangong_core.config import load_config


def test_load_config_json_then_env_overrides(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    # 隔离真实用户目录配置（~/.tiangong/.env），避免污染本测试
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("TIANGONG_HOME", str(home))
    for k in (
        "TIANGONG_MODEL",
        "OPENAI_MODEL",
        "TIANGONG_AGENT_NAME",
        "TIANGONG_API_KEY",
        "OPENAI_API_KEY",
        "TIANGONG_BASE_URL",
        "OPENAI_BASE_URL",
        "TIANGONG_CHANNELS_SLACK_ENABLED",
    ):
        monkeypatch.delenv(k, raising=False)
    (ws / "config.json").write_text(
        json.dumps(
            {
                "agent": {"model": "json-model", "agentName": "json-agent"},
                "provider": {"apiKey": "json-key", "apiBase": "http://json-base"},
                "channels": {"telegram": {"enabled": True, "token": "json-token"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # env overrides json
    monkeypatch.setenv("TIANGONG_MODEL", "env-model")
    monkeypatch.setenv("TIANGONG_API_KEY", "env-key")

    cfg = load_config(ws)
    assert cfg.agent.model == "env-model"
    assert cfg.agent.agent_name == "json-agent"
    assert cfg.provider.api_key == "env-key"
    assert cfg.channels.telegram.enabled is True
    assert cfg.channels.telegram.token == "json-token"

