from __future__ import annotations

import json
from pathlib import Path

from tiangong_core.config import load_config


def test_dashscope_options_loaded_from_config_json(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    # 隔离真实用户目录配置与 OS env，避免覆盖 config.json
    # （dotenv 不会覆盖已存在的 OS env）
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("TIANGONG_HOME", str(home))
    for k in (
        "TIANGONG_API_KEY",
        "OPENAI_API_KEY",
        "TIANGONG_BASE_URL",
        "OPENAI_BASE_URL",
        "TIANGONG_DASHSCOPE_ENABLE_SEARCH",
        "TIANGONG_DASHSCOPE_SEARCH_OPTIONS",
        "TIANGONG_DASHSCOPE_ENABLE_TEXT_IMAGE_MIXED",
    ):
        monkeypatch.delenv(k, raising=False)
    (ws / "config.json").write_text(
        json.dumps(
            {
                "provider": {
                    "apiKey": "k",
                    "apiBase": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "dashscopeEnableSearch": True,
                    "dashscopeSearchOptions": {"search_strategy": "max"},
                    "dashscopeEnableTextImageMixed": True,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cfg = load_config(ws)
    assert cfg.provider.dashscope_enable_search is True
    assert cfg.provider.dashscope_enable_text_image_mixed is True
    assert cfg.provider.dashscope_search_options == {"search_strategy": "max"}

