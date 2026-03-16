from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str | None = None
    api_base: str | None = None


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
        from dotenv import dotenv_values  # type: ignore
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


def load_config(workspace: str | Path | None = None) -> AppConfig:
    defaults = AppConfig()
    ws = Path(workspace) if workspace is not None else Path(".")
    _load_dotenv(ws)
    model = os.getenv("TIANGONG_MODEL") or os.getenv("OPENAI_MODEL") or defaults.agent.model
    agent_name = os.getenv("TIANGONG_AGENT_NAME") or defaults.agent.agent_name
    api_key = os.getenv("TIANGONG_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("TIANGONG_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    restrict = (os.getenv("TIANGONG_RESTRICT_WORKSPACE", "1") != "0")
    timeout_s = int(os.getenv("TIANGONG_SHELL_TIMEOUT_S", str(defaults.tools.shell_timeout_s)))
    max_iter = int(os.getenv("TIANGONG_MAX_TOOL_ITER", str(defaults.agent.max_tool_iterations)))

    return AppConfig(
        provider=ProviderConfig(api_key=api_key, api_base=api_base),
        tools=ToolConfig(restrict_to_workspace=restrict, shell_timeout_s=timeout_s),
        agent=AgentConfig(
            agent_name=agent_name,
            model=model,
            max_tool_iterations=max_iter,
            tool_result_max_chars=defaults.agent.tool_result_max_chars,
            workspace=ws.resolve(),
        ),
    )
