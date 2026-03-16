from __future__ import annotations

import os
from pathlib import Path

from tiangong_core.config import load_config


def test_load_config_env_priority(tmp_path, monkeypatch) -> None:
    """
    验证“用户目录 vs workspace”的分层 .env 加载优先级：
    - 用户目录：提供默认值
    - repo/.env：可覆盖用户目录
    - workspace/.env：优先级最高
    """

    # 模拟 TIANGONG_HOME
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("TIANGONG_HOME", str(home))

    # 1) 用户目录 .env
    (home / ".env").write_text(
        "\n".join(
            [
                "TIANGONG_MODEL=home-model",
                "TIANGONG_AGENT_NAME=home-agent",
            ]
        ),
        encoding="utf-8",
    )

    # 2) repo/.env（当前工作目录）
    repo_env = tmp_path / ".env"
    repo_env.write_text(
        "\n".join(
            [
                "TIANGONG_MODEL=repo-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    # 3) workspace/.env
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text(
        "\n".join(
            [
                "TIANGONG_MODEL=ws-model",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(ws)

    # workspace/.env 覆盖 repo/.env 与 用户目录
    assert cfg.agent.model == "ws-model"
    # repo/.env 覆盖用户目录（但不影响 agent_name，因为未设置）
    assert cfg.agent.agent_name == "home-agent"
