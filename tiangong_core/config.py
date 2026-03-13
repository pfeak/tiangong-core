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

    Priority:
    - workspace/.env (when CLI passes --workspace)
    - repo/.env (when running from project root)

    Notes:
    - Does NOT override already-set OS env vars.
    """
    try:
        # `dotenv` (and `python-dotenv`) both expose `load_dotenv` in most setups.
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    ws_env = workspace / ".env"
    if ws_env.exists():
        load_dotenv(dotenv_path=ws_env, override=False)

    # fallback: current working directory ".env"
    cwd_env = Path(".") / ".env"
    if cwd_env.exists():
        load_dotenv(dotenv_path=cwd_env, override=False)


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
