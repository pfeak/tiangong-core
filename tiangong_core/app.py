from __future__ import annotations

from pathlib import Path
from typing import Any

from tiangong_core.agent.context import ContextBuilder
from tiangong_core.agent.loop import AgentLoop
from tiangong_core.bus.events import InboundMessage, OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.config import AppConfig
from tiangong_core.providers.litellm_provider import LiteLLMProvider
from tiangong_core.runtime.identity import load_or_create_identity
from tiangong_core.session.manager import SessionManager
from tiangong_core.tools.fs import make_fs_tools
from tiangong_core.tools.message import MessageToolContext, make_message_tools
from tiangong_core.tools.registry import ToolRegistry
from tiangong_core.tools.shell import make_shell_tools
from tiangong_core.utils.ids import new_id


class TiangongApp:
    def __init__(self, *, workspace: Path, config: AppConfig) -> None:
        self.workspace = workspace
        self.config = config

        self.bus = MessageBus()
        self.sessions = SessionManager(workspace)
        self.ctx_builder = ContextBuilder(workspace)

        ident = load_or_create_identity(workspace, config.agent.agent_name)
        self._agent_id = ident.agent_id
        self._agent_name = ident.agent_name

        self.provider = LiteLLMProvider(api_key=config.provider.api_key, api_base=config.provider.api_base)

    def _build_tools(self, inbound: InboundMessage, runtime_metadata: dict[str, Any]) -> ToolRegistry:
        reg = ToolRegistry()
        for t in make_fs_tools(workspace=self.workspace, restrict_to_workspace=self.config.tools.restrict_to_workspace):
            reg.register(t)
        for t in make_shell_tools(
            workspace=self.workspace,
            restrict_to_workspace=self.config.tools.restrict_to_workspace,
            timeout_s=self.config.tools.shell_timeout_s,
        ):
            reg.register(t)
        for t in make_message_tools(
            MessageToolContext(
                bus=self.bus,
                channel=inbound.channel,
                chat_id=inbound.chat_id,
                session_key=inbound.session_key,
                metadata=runtime_metadata,
            )
        ):
            reg.register(t)
        return reg

    def run_once(self, inbound: InboundMessage) -> None:
        run_id = new_id()
        runtime_metadata: dict[str, Any] = {
            "agent_id": self._agent_id,
            "agent_name": self._agent_name,
            "run_id": run_id,
            "channel": inbound.channel,
            "chat_id": inbound.chat_id,
        }

        ctx = self.ctx_builder.build()
        tools = self._build_tools(inbound, runtime_metadata)
        loop = AgentLoop(
            provider=self.provider,
            tools=tools,
            sessions=self.sessions,
            model=self.config.agent.model,
            max_iterations=self.config.agent.max_tool_iterations,
            tool_result_max_chars=self.config.agent.tool_result_max_chars,
        )

        def progress(s: str) -> None:
            self.bus.publish_outbound(
                OutboundMessage(
                    channel=inbound.channel,
                    chat_id=inbound.chat_id,
                    session_key=inbound.session_key,
                    content=s,
                    metadata=runtime_metadata,
                )
            )

        res = loop.process_direct(
            session_key=inbound.session_key,
            system_prompt=ctx.system,
            user_content=inbound.content,
            runtime_metadata=runtime_metadata,
            progress=progress,
        )
        self.bus.publish_outbound(
            OutboundMessage(
                channel=inbound.channel,
                chat_id=inbound.chat_id,
                session_key=inbound.session_key,
                content=res.content,
                metadata=runtime_metadata,
            )
        )

    def serve_forever(self) -> None:
        while True:
            msg = self.bus.consume_inbound(timeout_s=0.5)
            if msg is None:
                continue
            self.run_once(msg)
