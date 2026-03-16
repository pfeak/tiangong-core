# Tiangong 双仓分层：内核（tiangong-core）与实践（tiangong-research）PRD/架构设计（v0.1）

> 参考：`taichu` 的 PocketFlow 节点/图执行模式（仅作为编排抽象参考）；`nanobot` 的 providers/bus/channel/session/memory/cron/subagent/loop/skills/cli 等内核构件。

---

## 1. 背景与目标

我们需要一套**可复用的智能体内核平台**（在 `tiangong-core`）和一套**面向实践的个性化 Agent/场景工程**（在 `tiangong-research`）。

- **tiangong-core**：沉淀公共能力（大模型交互与 providers、节点/流程编排、Agent base、网络检索、skills、cli、cron、channel、bus、memory、subagent、loop、context、session 等）。
- **tiangong-research**：沉淀个性化 Agent 与实践场景（第一版暂定：测试、优化指定项目、Python 代码）。

### 1.1 非目标（v0.1 不做）

- 分布式/多机调度、多租户权限/审计全套
- Web 控制台/可视化工作台
- 完整 RAG/向量库平台化（仅预留接口）
- 大规模长时编排平台化（先做可运行的最小闭环）

---

## 2. 总体架构

### 2.1 分层与职责边界

#### 2.1.1 `tiangong-core`（平台内核）

- **运行时核心**：AgentLoop（消息驱动、可迭代 skill-calls（底层为 function calling）、可取消/限迭代）
- **上下文系统**：ContextBuilder（bootstrap + memory + skills + runtime metadata）
- **模型接入**：Providers（LiteLLM 为主，支持直连/本地/网关/OAuth 预留）
- **技能系统**：Skills（fs/shell/web/message/spawn/cron/mcp 等都以 skill 形态动态注入与调度；不再存在独立“工具分层”）
- **会话与记忆**：SessionManager（jsonl append-only）、MemoryStore + Consolidator（写 MEMORY/HISTORY）
- **通道与总线**：Channel + MessageBus（解耦输入输出）
- **定时与后台任务**：CronService、Heartbeat（可选）
- **子智能体**：SubagentManager（spawn/cancel/隔离）
- **流程编排**：PocketFlow 集成（节点/图执行的 glue）

#### 2.1.2 `tiangong-research`（场景工程）

- **只做策略与组合**：自定义 Agent/Flow/Skills（可复用 core 的公共能力）
- **不重复造轮子**：不再实现 provider/bus/session/cli 等内核
- **输出可验证的实践**：场景 demo、评测脚本、最佳实践沉淀

### 2.2 核心消息流（message-driven turn）

1. Channel 接收输入（CLI/IM/HTTP）
2. Channel → Bus 投递 `InboundMessage`（带上 agent 唯一身份信息，见 3.9.4）
3. SessionManager 取回 session 历史（append-only）
4. ContextBuilder 拼装 system prompt + bootstrap + memory + skills + runtime metadata + user 输入
5. AgentLoop 调用 Provider → 得到文本或 skill_calls（底层为 function calling）
6. SkillsRuntime 执行技能 → 写入 skill_result 消息
7. 循环直到 final/stop/max_iterations
8. 保存 turn（截断超大 skill_result、过滤“空 assistant”毒化历史）
9. Bus 下发 `OutboundMessage` → Channel 发送输出

---

## 3. tiangong-core 模块设计

> 说明：以下为模块边界、接口形状、数据结构与扩展点；具体实现细节（依赖、代码组织、测试）留到开发阶段。

### 3.1 Providers（大模型交互与多 Provider）

#### 3.1.1 设计目标

- 统一 chat 接口、tool calling、重试策略、错误短路
- 统一消息字段（sanitize）、tool_call_id 兼容、参数丢弃策略（drop unsupported）
- 统一模型名解析：显式 prefix + registry 驱动的自动路由

#### 3.1.2 核心接口（建议）

- `LLMProvider.chat(messages, skills=None, model=None, generation=None, skill_choice=None, reasoning_effort=None) -> LLMResponse`（协议层仍以 function calling 形状传递）
- `LLMProvider.chat_with_retry(...) -> LLMResponse`
- `LLMResponse`：
  - `content: str | None`
  - `skill_calls: list[SkillCallRequest]`（协议层为 function calling/tool_calls 形状）
  - `finish_reason: str`
  - `usage: dict`
  - `reasoning_content?: str | None`
  - `thinking_blocks?: list[dict] | None`

#### 3.1.3 LiteLLMProvider（主实现）

参考 `nanobot/providers/litellm_provider.py` 的成熟实践：

- **消息 sanitize**：丢弃非标准 key；补齐 assistant content；保留 provider 特定字段（如 anthropic 的 `thinking_blocks`）
- **call_id 规范化**：映射到短的安全 ID 并保持 call 与 assistant（协议字段 `tool_call_id`）的一致
- **drop_params**：避免某些模型拒参（例如推理参数、cache_control 等）
- **模型解析**：配合 Provider Registry 完成 gateway/local/standard provider 的路由策略

#### 3.1.4 Provider Registry（单一事实来源）

参考 `nanobot/providers/registry.py`：

- `ProviderSpec`：name/keywords/env_key/display_name/litellm_prefix/skip_prefixes/env_extras/is_gateway/is_local/detect_by_key_prefix/detect_by_base_keyword/default_api_base/strip_model_prefix/model_overrides/supports_prompt_caching/is_oauth/is_direct…
- `find_by_model(model)`：标准 provider 匹配（按关键字或显式 prefix）
- `find_gateway(provider_name, api_key, api_base)`：网关/本地识别（优先级：provider_name → key prefix → api_base keyword）

### 3.2 Skills（技能：文档化指令包）

参考 `nanobot/skills/README.md` 与 skill-creator 体系。

#### 3.2.1 约定

- workspace：`skills/<skill-name>/SKILL.md`
- 文件结构：YAML frontmatter + Markdown 指令内容
- 支持 always skills（默认常驻）

#### 3.2.2 SkillsLoader（建议）

- `list_skills() -> metadata`
- `get_always_skills() -> list[str]`
- `load_skills_for_context(names) -> str`
- `build_skills_summary() -> str`（只提供概要与可用性，避免 system prompt 膨胀）

#### 3.2.3 SkillsRuntime（skill = 唯一可调用能力入口）

- **统一“可调用能力”来源**：所有可被模型调用的能力都以 skill 形态暴露；不再维护独立的“工具层/注册表”。
- **动态决定可用集合**：像 `nanobot` 的 skills 一样，由“上下文 + 策略 + 安全约束”决定本轮可用 skills（以及其 function calling schema）。
- **能力适配器**（v0.1 形态）：fs/shell/web/message/spawn/cron/mcp 都作为“skills 的适配器/实现”存在，其中：
  - `mcp`：将 MCP 能力以 skill schema 的方式动态注入（至少预留接口）
  - `web`：v0.1 不在 core 内自研实现，仅通过外部 Web 搜索能力集成；推荐直接复用云厂商 Web 搜索能力（例如阿里云百炼 Web 搜索，参考文档：`https://help.aliyun.com/zh/model-studio/web-search#312c12c262fsr`）
- **建议接口形状**：
  - `get_definitions() -> list[dict]`（function calling 形状）
  - `execute(name, arguments) -> str`（结果可直接写入 skill_result）

#### 3.2.4 实现边界（v0.1 建议）

- **core 负责加载与注入**：`tiangong-core` 内实现 `SkillsLoader`（建议位置：`tiangong_core/agent/skills.py`），并在 `ContextBuilder` 中使用“渐进式加载”策略：
  - **默认注入 summary**（仅名称/描述/路径/可用性），避免 system prompt 膨胀
  - **always skills 少量常驻**（满足要求时自动注入）
  - **按需加载全文**：当策略需要时再把某个 `SKILL.md` 的 body 拼入上下文
- **workspace 优先 + builtin 回退**：优先加载 `workspace/skills/` 下的技能；可选提供内置 skills（模板/示例），作为回退与开箱即用能力
- **技能安装/更新不做成 core 硬编码依赖**：
  - 推荐参考 `nanobot`：提供一个 `clawhub` 技能，指导用户通过 `npx clawhub@latest install/update --workdir <workspace>` 将技能下载安装到 `workspace/skills/`
  - `tiangong-core` 可选提供 `tiangong skills ...` 的 CLI wrapper（本质仍是调用外部 CLI），但避免让 core 强依赖 Node.js/`npx`

### 3.4 Context（上下文构建）

参考 `nanobot/agent/context.py`。

#### 3.4.1 Bootstrap 文件

- `AGENTS.md`：行为准则/工作方式
- `SOUL.md`：人格/语气（可选）
- `USER.md`：用户偏好（可选）
- `SKILLS.md`：技能说明（可选）

#### 3.4.2 Runtime metadata 注入策略

- 使用显式标签声明“metadata only, not instructions”
- 与本轮 user 内容合并成单条 user message，避免某些 provider 拒绝连续同 role

#### 3.4.3 多模态（预留）

- 支持 `media: list[path]`（图片转 base64 image_url content block）
- v0.1 可不启用，但接口保持向后兼容

### 3.5 Session（会话）

参考 `nanobot/session/manager.py`。

#### 3.5.1 存储格式

- `sessions/<safe_key>.jsonl`：首行 metadata，其余为消息行
- key：`channel:chat_id`（可扩展 thread/session_key_override）
- append-only：有利于缓存、回放与审计

补充：为支持“同一 chat 下多个不同智能体并行/轮换”，建议在 session 维度引入显式身份：

- **agent_id**：单个智能体的唯一身份 ID（稳定、不随进程重启变化；推荐 UUIDv4 字符串）
- **agent_name**：智能体逻辑名称（例如 `core-default`、`research-test-agent`）
- **run_id**：一次运行/一次任务链路 ID（可选，用于链路追踪；同一次用户请求内保持一致）

推荐 session key 形态（两种择一，v0.1 先实现 A）：

- A（默认，简单）：`session_key = "{channel}:{chat_id}"`，并在 session metadata 中记录 `agent_id/agent_name`（便于审计与迁移）
- B（隔离更强）：`session_key = "{channel}:{chat_id}:{agent_id}"`（同一 chat 不同 agent 自动隔离历史）

#### 3.5.2 读取策略

- `get_history(max_messages)`：只返回未 consolidated 段；从 user turn 对齐，避免孤儿 skill_result

#### 3.5.3 保存策略

- 截断超大 skill_result（避免上下文爆炸与文件膨胀）
- 过滤“空 assistant 且无 skill_calls”的消息（避免毒化上下文）
- 错误响应（finish_reason=error）不落盘或以安全方式落盘（避免 400 loop）

### 3.6 Memory（长期记忆与压缩）

参考 `nanobot.agent.memory` 的 consolidation 思路（此处只定义边界）。

#### 3.6.1 目标

- 将长对话压缩到可控窗口
- 重要事实写入 `memory/MEMORY.md`，过程摘要写入 `memory/HISTORY.md`
- 不修改 session.messages（保持可追溯与缓存友好）

#### 3.6.2 触发条件（建议）

- token 超阈值触发
- 回合数触发
- cron 定时触发
- 手动命令触发

### 3.7 Cron（定时任务）

参考 `nanobot` 的 cron service + agent callback 模式。

#### 3.7.1 目标

- 允许 agent 通过工具创建/管理定时任务
- 触发时走同样的 agent loop（`process_direct`）
- 支持投递到指定 channel/chat（可配置 deliver）

#### 3.7.2 安全策略

- cron 执行上下文中限制再创建 cron（避免递归调度/爆炸）

### 3.8 Subagent（子智能体）

参考 `nanobot.agent.subagent.SubagentManager` 的思路。

#### 3.8.1 目标

- 将长任务/探索任务/专门能力下放到子 agent
- 支持取消、并发、结果汇总
- 子 agent 工具集可受限（只读/只 web/只 fs）

补充：子智能体必须具备可追踪身份与父子关系：

- `parent_agent_id`：发起该 subagent 的父智能体 ID
- `subagent_id`：子智能体唯一身份 ID（UUIDv4）
- `subtask_id/run_id`：用于把一次子任务的输出与主任务链路关联（可选）

### 3.9 Bus + Channels（通道与消息总线）

参考 `nanobot/bus/queue.py` 与 `nanobot/channels/base.py`。

#### 3.9.1 MessageBus（建议）

- `publish_inbound/consume_inbound/publish_outbound/consume_outbound`
- 作为 channel 与 agent 的解耦层

#### 3.9.2 Channel 接口（建议）

- `start/stop/send`
- `is_allowed(sender_id)`：allowlist（空 = deny all；含 `*` = allow all）
- `_handle_message(...)`：统一封装 inbound message，支持 media/metadata/session_key_override

#### 3.9.4 智能体唯一身份 ID（必须）

单个智能体未来需要唯一身份 ID（用于：会话隔离、审计、并行、子智能体溯源、跨通道路由、Cron 触发归属）。

**定义**

- **agent_id**：稳定唯一 ID（UUIDv4 字符串），由 Agent 实例在首次启动/创建时生成并持久化（建议写入 workspace 的 `runtime/agent.json` 或用户配置目录；实现时再定位置）
- **agent_name**：逻辑名称（可配置，方便人读）
- **run_id**：每次“处理一条 inbound message”的链路 ID（UUIDv4），贯穿 provider 调用、工具执行、session 写入与 outbound 发送

**放置位置（v0.1 约定）**

- `InboundMessage.metadata`：写入 `agent_id/agent_name/run_id`
- `OutboundMessage.metadata`：原样透传上述字段（便于 channel 侧日志与回放）
- `Session.metadata`：保存该 session 最近一次写入的 `agent_id/agent_name`（若采用方案 B 则无需）
- `CronJob.payload`：保存触发时应使用的 `agent_id/agent_name`（或 session_key），保证定时任务“归属明确”

**与 session_key 的关系**

- 如果选择 3.5.1 的方案 A：同一 chat 内多 agent 共享历史，需要在 ContextBuilder 中显式注入 `agent_name` 并在 session 中记录；适合早期快速迭代。
- 如果选择方案 B：session_key 包含 agent_id，天然隔离；更适合并行多 agent 与避免历史互相污染。

#### 3.9.3 v0.1 通道范围建议

- 必须：CLI
- 可选：HTTP（供内部调用/测试）
- IM（Telegram/Slack/…）后置到 v0.2

### 3.10 Loop（核心执行循环）

参考 `nanobot/agent/loop.py` 的能力集合：

- max_iterations 保护
- skill_result 截断
- progress 回调（将“过程/工具提示”作为 OutboundMessage 流式发送）
- /stop、/restart（CLI 环境可先不做 restart，保留 stop）
- `process_direct`：CLI/cron 直接调用，不必走 channel/bus

### 3.11 PocketFlow（节点/流程编排：节点管理）

参考 `taichu` 的 `pocketflow.Node`（例如 taichu 的 ExecNode 思路）并与 core 的 Provider/SkillsRuntime/Session/Context 打通。

#### 3.11.1 两层抽象

- **AgentLoop**：面向消息 turn 的通用执行器（工具闭环）
- **Flow/Graph（PocketFlow）**：面向任务结构化拆分（Planner/Executor/Verifier/Reporter…）

#### 3.11.2 Node 约定（建议）

- `prep(shared) -> input`
- `exec(input) -> NodeResult(status, data)`
- `post(shared, prep_res, exec_res) -> next_status`

#### 3.11.3 core 提供的基础节点（建议 v0.1）

- `SkillExecNode`：技能调用闭环节点（等价于 taichu 的 ExecNode 思路，但使用 core 的统一组件）
- `ChatNode`：纯对话节点（无工具/或只少量工具）
- `ReportNode`（可选）：结构化输出与落盘

---

## 4. tiangong-research（个性化 Agent 与实践场景 v0.1）

### 4.1 原则

- 只写“场景策略/组合”，不复制 core 的基础设施
- 使用 core 的 public API：providers/skills/session/context/loop/flow

### 4.2 第一版场景（暂定）

#### 4.2.1 测试（Test Agent）

- 输入：目标项目路径、测试命令、失败日志
- 输出：最小修复方案、补充用例、验证结果摘要
- flow（示意）：`AnalyzeFail -> ProposeFix -> ApplyFix -> RunTests -> Summarize`

#### 4.2.2 优化指定项目（Optimize Agent）

- 输入：repo、优化目标（性能/可维护/依赖/结构）、约束（只改某目录/不改行为）
- 输出：分步骤改动计划与最小变更清单（v0.1 可先做 plan-only）
- flow（示意）：`RepoScan -> HotspotHypothesis -> Plan -> ExecuteSmallRefactors -> Verify`

#### 4.2.3 Python 代码（Python Agent）

- 输入：规格/签名/期望行为
- 输出：实现 + 边界用例 + 自测
- flow（示意）：`Spec -> Implement -> SelfTest(pytest) -> PackageResult`

---

## 5. 配置与运行形态（建议）

### 5.1 配置（建议沿用 nanobot 的 schema 思路）

建议统一配置文件（路径最终在实现时确定）：

- `providers.*`：api_key / api_base / extra_headers
- `agents.defaults`：model/temperature/max_tokens/reasoning_effort/context_window_tokens/max_tool_iterations/workspace
- `skills.exec`：timeout/path_append/restrict_to_workspace
- `skills.web`：search api_key / proxy
- `channels.*`：enabled/allow_from/凭证
- `gateway`：port/cron/heartbeat（可选）

v0.1 实现中的实际约定（env + .env 分层）：

- **环境变量优先级**：显式 OS env 始终最高优先级。
- **.env 分层加载**（后加载的优先级更高，可以覆盖前面的值）：
  - 用户目录：`$TIANGONG_HOME/.env` 或 `~/.tiangong/.env`
  - repo 根目录：`./.env`
  - workspace：`<workspace>/.env`（例如 CLI 传入 `--workspace` 时）
- **核心 env 键位**：
  - `TIANGONG_MODEL`：默认模型（例如 `gpt-4.1-mini`，会通过 Provider Registry 归一化为 `openai/gpt-4.1-mini`）
  - `TIANGONG_AGENT_NAME`：agent 逻辑名称（写入 `runtime/agent.json` 与 runtime metadata）
  - `TIANGONG_API_KEY` / `OPENAI_API_KEY`：标准 provider/gateway API key
  - `TIANGONG_BASE_URL` / `OPENAI_BASE_URL`：标准 provider/gateway API base
  - `TIANGONG_MAX_TOOL_ITER`：最大工具迭代次数
  - `TIANGONG_SHELL_TIMEOUT_S`：shell 工具超时时间（秒）
  - `TIANGONG_RESTRICT_WORKSPACE`：是否限制工具在 workspace 内运行（默认开启）

Provider Registry + LiteLLMProvider 的最小可用配置（out-of-the-box）：

- **标准 provider（OpenAI 系）**：
  - `AgentConfig.model` 默认为 `openai/gpt-4.1-mini`
  - 对未带前缀的 model（如 `gpt-4.1-mini`）自动归一化为 `openai/gpt-4.1-mini`
  - `ProviderSpec(name="openai", drop_params=("reasoning_effort", "extra_headers", "cache_control"))`
- **OpenAI-compatible 网关**：
  - 通过 `ProviderSpec(name="openai-compatible-gateway", is_gateway=True, detect_by_key_prefix=("sk-",), api_base_keywords=("openai", "v1"))` 识别
  - 允许通过 `TIANGONG_API_KEY` + `TIANGONG_BASE_URL` 指向自建/第三方网关
  - 默认也会剔除 `reasoning_effort`/`extra_headers`/`cache_control` 等高风险参数，避免网关侧拒参

此外，可通过环境变量 `TIANGONG_PROVIDER_DROP_PARAMS_<PROVIDER_NAME>`（例如 `TIANGONG_PROVIDER_DROP_PARAMS_OPENAI="reasoning_effort,cache_control"`）为指定 provider/gateway 追加自定义的 drop_params。

### 5.2 运行模式（建议）

- CLI 单次：`tiangong agent -m "..."`
- CLI 交互：`tiangong agent`
- Gateway：`tiangong gateway`（v0.1 可后置，仅保留 CLI + cron）

---

## 6. 关键设计决策与理由

- **Bus 解耦**：channel 与 agent 解耦，便于扩展与并发取消（参考 nanobot）
- **Session append-only + consolidation**：可追溯 + 控制上下文窗口（参考 nanobot）
- **Provider registry 驱动**：减少 provider 特判，便于扩展网关/本地/直连（参考 nanobot）
- **PocketFlow 编排层**：复杂任务结构化、可复用、可测试（参考 taichu）
- **Skills 文档化**：能力扩展更像 SOP，可被摘要并融入 prompt（参考 nanobot）

---

## 7. v0.1 最小闭环建议（设计层面）

### 7.1 tiangong-core 必须具备

- Providers：LiteLLMProvider + registry（至少覆盖常用 provider/gateway）
- Skills：fs + shell +（可选 web）+ message（CLI 可退化；其余能力如 cron/spawn/mcp 以 skill 形态预留/注入）
- Session：jsonl 持久化（append-only）
- Context：bootstrap + memory + skills summary + runtime metadata
- Loop：skill-calls 迭代、max_iterations、skill_result 截断
- PocketFlow glue：可运行的基础节点与 flow runner
- CLI：agent（单次/交互）

### 7.2 建议预留但可后置

- Cron：jobs 存储 + 触发走 `process_direct`
- Subagent：spawn/cancel 接口（先空实现或禁用）
- Channels：IM/HTTP（后置）

---

## 8. 建议的包结构（草案）

### 8.1 tiangong-core

- `tiangong_core/providers/`：`base.py`, `litellm_provider.py`, `registry.py`, `custom.py`, `azure.py`…
- `tiangong_core/skills/`：`runtime.py`, `adapters/`（fs/shell/web/message/cron/spawn/mcp…）
- `tiangong_core/agent/`：`loop.py`, `context.py`, `memory.py`, `skills.py`, `subagent.py`
- `tiangong_core/session/`：`manager.py`
- `tiangong_core/bus/`：`events.py`, `queue.py`
- `tiangong_core/channels/`：`base.py`, `cli.py`, `manager.py`, `registry.py`
- `tiangong_core/cron/`：`service.py`, `types.py`
- `tiangong_core/flow/`：`nodes/`, `runner.py`, `schemas.py`
- `tiangong_core/cli/`：`commands.py`
- `tiangong_core/templates/`：bootstrap 文件与内置 skills

### 8.2 tiangong-research

- `tiangong_research/agents/`：`test_agent.py`, `optimize_repo_agent.py`, `python_agent.py`
- `tiangong_research/flows/`：PocketFlow graphs
- `tiangong_research/skills/`：场景技能包
- `tiangong_research/eval/`：评测与对比脚本（可选）

---

## 9. 风险与对策（提前规避）

- **Provider 兼容性问题**（字段/参数/协议 call_id）：sanitize + id 规范化 + drop_params（参考 nanobot）
- **上下文毒化导致循环报错**：不持久化错误响应；过滤空 assistant（参考 nanobot）
- **技能输出过大**：统一截断 +（后续可）落盘引用
- **安全边界**：默认 restrict_to_workspace；shell 超时；allowlist 默认 deny
