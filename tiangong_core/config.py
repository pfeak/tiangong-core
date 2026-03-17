from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tiangong_core.channels.config import (
    ChannelsConfig,
    CLIChannelConfig,
    FeishuChannelConfig,
    QQChannelConfig,
    TelegramChannelConfig,
)


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str | None = None
    api_base: str | None = None
    dashscope_enable_search: bool = False
    dashscope_search_options: dict[str, Any] | None = None
    dashscope_enable_text_image_mixed: bool = False


@dataclass(frozen=True)
class ToolConfig:
    restrict_to_workspace: bool = True
    shell_timeout_s: int = 30


@dataclass(frozen=True)
class AgentConfig:
    agent_name: str = "core-default"
    model: str = "openai/gpt-4.1-mini"
    max_tool_iterations: int = 12
    tool_result_max_chars: int = 20_000
    workspace: Path = Path(".")


@dataclass(frozen=True)
class AppConfig:
    provider: ProviderConfig = ProviderConfig()
    tools: ToolConfig = ToolConfig()
    agent: AgentConfig = AgentConfig()
    channels: ChannelsConfig = ChannelsConfig()


def _load_dotenv(workspace: Path) -> None:
    """
    Load environment variables from .env files if present.

    Priority（后加载的优先级更高，可以覆盖前面的值）：
    - 用户目录配置：$TIANGONG_HOME/.env 或 ~/.tiangong/.env
    - repo/.env（当前工作目录）
    - workspace/.env（当 CLI 传入 --workspace 时）

    Notes:
    - Does NOT override already-set OS env vars.
    """
    try:
        # 使用 dotenv_values 读取后自行合并，才能实现“后加载覆盖前加载”
        # 同时保证不覆盖 OS env（显式环境变量永远优先）。
        from dotenv import dotenv_values
    except Exception:
        return

    os_env_keys = set(os.environ.keys())
    merged: dict[str, str] = {}

    # 1) 用户目录配置：$TIANGONG_HOME/.env 或 ~/.tiangong/.env
    home = Path(os.getenv("TIANGONG_HOME") or Path.home() / ".tiangong")
    home_env = home / ".env"
    if home_env.exists():
        for k, v in dotenv_values(home_env).items():
            if k and v is not None:
                merged[str(k)] = str(v)

    # 2) 当前工作目录 ".env"
    cwd_env = Path(".") / ".env"
    if cwd_env.exists():
        for k, v in dotenv_values(cwd_env).items():
            if k and v is not None:
                merged[str(k)] = str(v)

    # 3) workspace/.env：最贴近工作目录，优先级最高
    ws_env = workspace / ".env"
    if ws_env.exists():
        for k, v in dotenv_values(ws_env).items():
            if k and v is not None:
                merged[str(k)] = str(v)

    # 应用合并结果：不覆盖 OS env
    for k, v in merged.items():
        if k in os_env_keys:
            continue
        os.environ[k] = v


def _load_config_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("config.json must be an object")
    return obj


def _pick_config_json_path(*, workspace: Path, config_path: str | Path | None) -> Path | None:
    if config_path is not None:
        p = Path(config_path).expanduser()
        return p
    p_env = (os.getenv("TIANGONG_CONFIG") or "").strip()
    if p_env:
        return Path(p_env).expanduser()
    ws_cfg = workspace / "config.json"
    if ws_cfg.exists():
        return ws_cfg
    cwd_cfg = Path(".") / "config.json"
    if cwd_cfg.exists():
        return cwd_cfg
    return None


def _d_get(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        if k in cur:
            cur = cur[k]
            continue
        # allow snake_case / camelCase fallback
        alt = None
        if "_" in k:
            parts = k.split("_")
            alt = parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])
        else:
            # crude camel->snake for common fields
            alt = "".join(["_" + c.lower() if c.isupper() else c for c in k]).lstrip("_")
        if alt and alt in cur:
            cur = cur[alt]
            continue
        return None
    return cur


def load_config(workspace: str | Path | None = None, config_path: str | Path | None = None) -> AppConfig:
    defaults = AppConfig()
    ws = Path(workspace) if workspace is not None else Path(".")
    ws = ws.resolve()

    # 1) Load dotenv into env (env has highest priority; .env is treated as env source)
    _load_dotenv(ws)

    # 2) Load config.json (second priority)
    cfg_json_path = _pick_config_json_path(workspace=ws, config_path=config_path)
    j: dict[str, Any] = {}
    if cfg_json_path and cfg_json_path.exists():
        j = _load_config_json(cfg_json_path)

    base_provider = ProviderConfig(
        api_key=_d_get(j, "provider", "api_key") or defaults.provider.api_key,
        api_base=_d_get(j, "provider", "api_base") or defaults.provider.api_base,
        dashscope_enable_search=bool(
            _d_get(j, "provider", "dashscope_enable_search")
            if _d_get(j, "provider", "dashscope_enable_search") is not None
            else defaults.provider.dashscope_enable_search
        ),
        dashscope_search_options=(
            _d_get(j, "provider", "dashscope_search_options")
            if isinstance(_d_get(j, "provider", "dashscope_search_options"), dict)
            else defaults.provider.dashscope_search_options
        ),
        dashscope_enable_text_image_mixed=bool(
            _d_get(j, "provider", "dashscope_enable_text_image_mixed")
            if _d_get(j, "provider", "dashscope_enable_text_image_mixed") is not None
            else defaults.provider.dashscope_enable_text_image_mixed
        ),
    )
    base_tools = ToolConfig(
        restrict_to_workspace=bool(
            _d_get(j, "tools", "restrict_to_workspace")
            if _d_get(j, "tools", "restrict_to_workspace") is not None
            else defaults.tools.restrict_to_workspace
        ),
        shell_timeout_s=int(_d_get(j, "tools", "shell_timeout_s") or defaults.tools.shell_timeout_s),
    )
    base_agent = AgentConfig(
        agent_name=str(_d_get(j, "agent", "agent_name") or defaults.agent.agent_name),
        model=str(_d_get(j, "agent", "model") or defaults.agent.model),
        max_tool_iterations=int(_d_get(j, "agent", "max_tool_iterations") or defaults.agent.max_tool_iterations),
        tool_result_max_chars=int(_d_get(j, "agent", "tool_result_max_chars") or defaults.agent.tool_result_max_chars),
        workspace=ws,
    )

    def _ch_enabled(name: str, default: bool) -> bool:
        v = _d_get(j, "channels", name, "enabled")
        return default if v is None else bool(v)

    base_channels = ChannelsConfig(
        cli=CLIChannelConfig(
            enabled=_ch_enabled("cli", defaults.channels.cli.enabled),
            allow_from=tuple(_d_get(j, "channels", "cli", "allow_from") or _d_get(j, "channels", "cli", "allowFrom") or defaults.channels.cli.allow_from),
            channel_name=str(_d_get(j, "channels", "cli", "channel_name") or _d_get(j, "channels", "cli", "channelName") or defaults.channels.cli.channel_name),
        ),
        telegram=TelegramChannelConfig(
            enabled=_ch_enabled("telegram", defaults.channels.telegram.enabled),
            allow_from=tuple(_d_get(j, "channels", "telegram", "allow_from") or _d_get(j, "channels", "telegram", "allowFrom") or ()),
            token=str(_d_get(j, "channels", "telegram", "token") or ""),
            proxy=_d_get(j, "channels", "telegram", "proxy"),
            reply_to_message=bool(_d_get(j, "channels", "telegram", "reply_to_message") or _d_get(j, "channels", "telegram", "replyToMessage") or False),
        ),
        feishu=FeishuChannelConfig(
            enabled=_ch_enabled("feishu", defaults.channels.feishu.enabled),
            allow_from=tuple(_d_get(j, "channels", "feishu", "allow_from") or _d_get(j, "channels", "feishu", "allowFrom") or ()),
            mode=str(_d_get(j, "channels", "feishu", "mode") or defaults.channels.feishu.mode),
            app_id=str(_d_get(j, "channels", "feishu", "app_id") or _d_get(j, "channels", "feishu", "appId") or ""),
            app_secret=str(_d_get(j, "channels", "feishu", "app_secret") or _d_get(j, "channels", "feishu", "appSecret") or ""),
            encrypt_key=str(_d_get(j, "channels", "feishu", "encrypt_key") or _d_get(j, "channels", "feishu", "encryptKey") or ""),
            verification_token=str(_d_get(j, "channels", "feishu", "verification_token") or _d_get(j, "channels", "feishu", "verificationToken") or ""),
            react_emoji=str(_d_get(j, "channels", "feishu", "react_emoji") or _d_get(j, "channels", "feishu", "reactEmoji") or defaults.channels.feishu.react_emoji),
            reply_in_thread=bool(
                _d_get(j, "channels", "feishu", "reply_in_thread")
                if _d_get(j, "channels", "feishu", "reply_in_thread") is not None
                else (
                    _d_get(j, "channels", "feishu", "replyInThread")
                    if _d_get(j, "channels", "feishu", "replyInThread") is not None
                    else defaults.channels.feishu.reply_in_thread
                )
            ),
            webhook_host=str(_d_get(j, "channels", "feishu", "webhook_host") or _d_get(j, "channels", "feishu", "webhookHost") or defaults.channels.feishu.webhook_host),
            webhook_port=int(_d_get(j, "channels", "feishu", "webhook_port") or _d_get(j, "channels", "feishu", "webhookPort") or defaults.channels.feishu.webhook_port),
            webhook_path=str(_d_get(j, "channels", "feishu", "webhook_path") or _d_get(j, "channels", "feishu", "webhookPath") or defaults.channels.feishu.webhook_path),
        ),
        qq=QQChannelConfig(
            enabled=_ch_enabled("qq", defaults.channels.qq.enabled),
            allow_from=tuple(_d_get(j, "channels", "qq", "allow_from") or _d_get(j, "channels", "qq", "allowFrom") or ()),
            app_id=str(_d_get(j, "channels", "qq", "app_id") or _d_get(j, "channels", "qq", "appId") or ""),
            secret=str(_d_get(j, "channels", "qq", "secret") or ""),
        ),
    )

    base = AppConfig(provider=base_provider, tools=base_tools, agent=base_agent, channels=base_channels)

    # 3) Env overrides (highest priority)
    model = os.getenv("TIANGONG_MODEL") or os.getenv("OPENAI_MODEL") or base.agent.model
    agent_name = os.getenv("TIANGONG_AGENT_NAME") or base.agent.agent_name
    api_key = os.getenv("TIANGONG_API_KEY") or os.getenv("OPENAI_API_KEY") or base.provider.api_key
    api_base = os.getenv("TIANGONG_BASE_URL") or os.getenv("OPENAI_BASE_URL") or base.provider.api_base
    restrict = (os.getenv("TIANGONG_RESTRICT_WORKSPACE", "1") != "0") if os.getenv("TIANGONG_RESTRICT_WORKSPACE") else base.tools.restrict_to_workspace
    timeout_s = int(os.getenv("TIANGONG_SHELL_TIMEOUT_S", str(base.tools.shell_timeout_s)))
    max_iter = int(os.getenv("TIANGONG_MAX_TOOL_ITER", str(base.agent.max_tool_iterations)))

    channels = base.channels

    return AppConfig(
        provider=ProviderConfig(
            api_key=api_key,
            api_base=api_base,
            dashscope_enable_search=base.provider.dashscope_enable_search,
            dashscope_search_options=base.provider.dashscope_search_options,
            dashscope_enable_text_image_mixed=base.provider.dashscope_enable_text_image_mixed,
        ),
        tools=ToolConfig(restrict_to_workspace=restrict, shell_timeout_s=timeout_s),
        agent=AgentConfig(
            agent_name=agent_name,
            model=model,
            max_tool_iterations=max_iter,
            tool_result_max_chars=base.agent.tool_result_max_chars,
            workspace=ws,
        ),
        channels=channels,
    )
