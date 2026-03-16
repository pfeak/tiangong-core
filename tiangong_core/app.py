from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from tiangong_core.agent.context import ContextBuilder
from tiangong_core.agent.loop import AgentLoop
from tiangong_core.bus.events import InboundMessage, OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.config import AppConfig
from tiangong_core.providers.litellm_provider import LiteLLMProvider
from tiangong_core.runtime.identity import load_or_create_identity
from tiangong_core.session.manager import SessionManager
from tiangong_core.skills.runtime import SkillsRuntime
from tiangong_core.cron.service import CronService
from tiangong_core.agent.subagent import SubagentManager
from tiangong_core.skills.adapters.fs import make_fs_skills
from tiangong_core.skills.adapters.message import MessageSkillContext, make_message_skills
from tiangong_core.skills.adapters.shell import make_shell_skills
from tiangong_core.skills.adapters.cron import make_cron_skills
from tiangong_core.skills.adapters.spawn import make_spawn_skills
from tiangong_core.skills.adapters.mcp import make_mcp_skills
from tiangong_core.utils.ids import new_id


class TiangongApp:
    def __init__(self, *, workspace: Path, config: AppConfig) -> None:
        self.workspace = workspace
        self.config = config

        self.bus = MessageBus()
        self.sessions = SessionManager(workspace)
        self.ctx_builder = ContextBuilder(workspace)
        # Background services (no env vars required)
        self.cron = CronService(bus=self.bus)
        self.subagents = SubagentManager(bus=self.bus)

        ident = load_or_create_identity(workspace, config.agent.agent_name)
        self._agent_id = ident.agent_id
        self._agent_name = ident.agent_name

        self.provider = LiteLLMProvider(api_key=config.provider.api_key, api_base=config.provider.api_base)

    def make_session_key(self, *, channel: str, chat_id: str) -> str:
        """
        根据配置生成 session_key，支持按 channel/chat_id 或 agent_id+chat_id 两种方案：
        - 方案 A（默认）：channel/chat_id → "cli:default"
        - 方案 B：agent_id + chat_id → "<agent_id>:<chat_id>"

        通过环境变量 TIANGONG_SESSION_KEY_SCHEME 控制：
        - "agent_chat"：使用 agent_id + chat_id（方案 B）
        - 其他/未设置：使用 channel + chat_id（方案 A）
        """
        scheme = os.getenv("TIANGONG_SESSION_KEY_SCHEME", "channel_chat").strip().lower()
        if scheme == "agent_chat":
            return f"{self._agent_id}:{chat_id}"
        # 默认：按 channel + chat_id
        return f"{channel}:{chat_id}"

    def _build_skills(self, inbound: InboundMessage, runtime_metadata: dict[str, Any]) -> SkillsRuntime:
        rt = SkillsRuntime()
        for s in make_fs_skills(workspace=self.workspace, restrict_to_workspace=self.config.tools.restrict_to_workspace):
            rt.register(s)
        for s in make_shell_skills(
            workspace=self.workspace,
            restrict_to_workspace=self.config.tools.restrict_to_workspace,
            timeout_s=self.config.tools.shell_timeout_s,
        ):
            rt.register(s)
        for s in make_message_skills(
            MessageSkillContext(
                bus=self.bus,
                channel=inbound.channel,
                chat_id=inbound.chat_id,
                session_key=inbound.session_key,
                metadata=runtime_metadata,
            )
        ):
            rt.register(s)
        # 预留 cron/subagent/mcp 三类能力的注入入口，均由各自的 feature flag 控制是否生效。
        for s in make_cron_skills(svc=self.cron):
            rt.register(s)
        for s in make_spawn_skills(mgr=self.subagents):
            rt.register(s)
        for s in make_mcp_skills():
            rt.register(s)
        return rt

    def run_once(self, inbound: InboundMessage) -> None:
        # runtime metadata: app identity + per-run id + inbound extras
        run_id = str((inbound.metadata or {}).get("run_id") or "") or new_id()
        runtime_metadata: dict[str, Any] = {
            "agent_id": self._agent_id,
            "agent_name": self._agent_name,
            "run_id": run_id,
            "channel": inbound.channel,
            "chat_id": inbound.chat_id,
        }
        if inbound.metadata:
            # allow channel to attach additional fields (non-conflicting)
            runtime_metadata.update({k: v for k, v in inbound.metadata.items() if k not in runtime_metadata})

        # If a subagent was cancelled before starting, skip execution.
        if inbound.channel == "subagent":
            try:
                subagent_id = str(inbound.chat_id or "")
                if subagent_id and self.subagents.is_cancelled(subagent_id):
                    self.bus.publish_outbound(
                        OutboundMessage(
                            channel=inbound.channel,
                            chat_id=inbound.chat_id,
                            session_key=inbound.session_key,
                            content="该子任务已取消，未执行。",
                            metadata={**runtime_metadata, "event": "final"},
                        )
                    )
                    return
            except Exception:
                pass

        # built-in command: /stop
        if inbound.content.strip() == "/stop":
            self.sessions.stop(inbound.session_key, metadata=runtime_metadata)
            self.bus.publish_outbound(
                OutboundMessage(
                    channel=inbound.channel,
                    chat_id=inbound.chat_id,
                    session_key=inbound.session_key,
                    content="已停止该会话（/stop）。",
                    metadata={**runtime_metadata, "event": "final"},
                )
            )
            return

        ctx = self.ctx_builder.build()
        skills = self._build_skills(inbound, runtime_metadata)
        loop = AgentLoop(
            provider=self.provider,
            skills=skills,
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
                    metadata={**runtime_metadata, "event": "progress"},
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
                metadata={**runtime_metadata, "event": "final"},
            )
        )

    def serve_forever(self) -> None:
        while True:
            msg = self.bus.consume_inbound(timeout_s=0.5)
            if msg is None:
                continue
            try:
                self.run_once(msg)
            except Exception as e:
                # 避免后台线程静默崩溃导致 channel 永远等不到 outbound
                run_id = ""
                try:
                    run_id = str((msg.metadata or {}).get("run_id") or "")
                except Exception:
                    run_id = ""
                self.bus.publish_outbound(
                    OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        session_key=msg.session_key,
                        content=f"[error] {type(e).__name__}: {e}",
                        metadata={
                            "event": "error",
                            "agent_id": getattr(self, "_agent_id", ""),
                            "agent_name": getattr(self, "_agent_name", ""),
                            "run_id": run_id,
                            "channel": msg.channel,
                            "chat_id": msg.chat_id,
                        },
                    )
                )
