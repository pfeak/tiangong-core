# tiangong-core PRD（v0.1）

本文档只描述 `tiangong-core` 仓库**已经实现**或**明确在 v0.1 范围内实现**的能力，并以“可验收”的产品需求形式组织；不再包含跨仓分层、外部项目对照或远期设想。

---

## 1. 背景与目标

`tiangong-core` 是一个可复用的智能体内核运行时，提供：

- **CLI 交互入口**：本地对话、单次消息模式、skills 管理命令
- **统一的 Agent 运行闭环**：会话（Session）+ 上下文（Context）+ Provider 调用 + Tool/Skill 执行 + 结果落盘
- **可插拔技能体系**：以“工具定义（function calling tools）+ 执行器（runtime）”的形式向模型暴露能力
- **轻量流程编排（Flow）**：v0.1 提供顺序执行的 FlowRunner 与基础节点

### 1.1 v0.1 产品目标（可衡量）

- **开箱即用**：用户仅需设置 `TIANGONG_API_KEY`（或等价 OpenAI 兼容 key）与 `TIANGONG_MODEL`，即可通过 `tiangong agent` 进行对话。
- **稳定闭环**：支持 tool calling 的多轮迭代，保证消息序列合法（尤其是 tool_calls 与 tool 消息配对），避免常见 400 错误。
- **可追踪可排障**：每轮有 `run_id`，并在会话落盘中记录元信息，便于回放与定位问题。
- **可控安全边界**：工具默认限制在 workspace 内执行（文件系统/命令执行），并提供 CLI sender allowlist。

### 1.2 非目标（v0.1 不做）

- Web 控制台/可视化工作台
- 分布式调度、多租户权限/审计体系
- 图遍历/条件跳转/复杂 DAG 的流程引擎（v0.1 Flow 仅顺序执行）

---

## 2. 用户与使用场景

### 2.1 目标用户

- **本地开发者**：在一个 workspace 里运行智能体，让其调用本地文件/命令完成任务。
- **仓库维护者**：需要一个可测试、可复用的 agent runtime 内核，便于在不同项目复用。

### 2.2 典型场景

- **交互式协作**：`tiangong agent`，模型可调用 `fs`/`shell`/`message` 等工具完成任务。
- **脚本式单次对话**：`tiangong agent -m "..."`，用于自动化或 CI 中的简单调用。
- **skills 管理**：`tiangong skills list/summary/show/install`，查看与安装工作区技能包。

---

## 3. 产品范围与模块（以实际实现为准）

### 3.1 CLI（命令行产品形态）

#### 3.1.1 命令

- **`tiangong agent`**：进入交互式对话
- **`tiangong agent -m/--message`**：单次消息模式
- **`tiangong skills list`**：列出 workspace 与内置 skills（workspace 同名覆盖内置）
- **`tiangong skills summary`**：输出 `<skills>...</skills>` 形态概要 + always skills 正文
- **`tiangong skills show <name>`**：显示单个 skill 的正文（Markdown）
- **`tiangong skills install [names...] [--update]`**：封装 `npx clawhub@latest install/update`

#### 3.1.2 交互与输出

- **Markdown 渲染**：默认开启（可 `--no-markdown` 关闭）
- **进度输出**：当执行工具调用时，通过 “progress 事件”输出 `↳ [tool] <name>` 风格提示
- **历史记录**：CLI 输入历史写入 `<workspace>/runtime/cli_history.txt`

#### 3.1.3 访问控制（CLI sender allowlist）

- **默认**：允许所有 sender（保证开箱即用）
- **可配置**：当 allow_all=false 时，只有 allow_from 中的 sender 或 `*` 被允许

---

### 3.2 配置（env + .env 分层加载）

#### 3.2.1 .env 加载优先级

在不覆盖 OS 显式环境变量的前提下，按以下顺序加载（后加载覆盖先加载）：

- `$TIANGONG_HOME/.env` 或 `~/.tiangong/.env`
- 当前工作目录 `./.env`
- workspace 下的 `<workspace>/.env`（优先级最高）

#### 3.2.2 核心环境变量（v0.1）

- **模型与身份**
  - `TIANGONG_MODEL` / `OPENAI_MODEL`：默认模型（默认值：`openai/gpt-4.1-mini`）
  - `TIANGONG_AGENT_NAME`：agent 逻辑名称（默认：`core-default`）
- **Provider**
  - `TIANGONG_API_KEY` / `OPENAI_API_KEY`
  - `TIANGONG_BASE_URL` / `OPENAI_BASE_URL`
- **运行约束**
  - `TIANGONG_MAX_TOOL_ITER`：最大工具迭代次数（默认：12）
  - `TIANGONG_SHELL_TIMEOUT_S`：shell 工具超时秒数（默认：30）
  - `TIANGONG_RESTRICT_WORKSPACE`：是否限制工具在 workspace 内运行（默认开启；设置为 `0` 关闭）
- **会话键策略**
  - `TIANGONG_SESSION_KEY_SCHEME`：`channel_chat`（默认）或 `agent_chat`

---

### 3.3 Runtime Identity（agent_id / agent_name / run_id）

- **agent_id**：在 workspace 下持久化生成并复用的稳定 ID
- **agent_name**：来自配置（`TIANGONG_AGENT_NAME`）
- **run_id**：每次处理一条 inbound message 生成（或由 channel 传入）

在 v0.1 中，以上字段被注入到：

- **runtime_metadata**：随本轮消息进入上下文（以 `<runtime_metadata>...</runtime_metadata>` 包裹）
- **会话落盘**：在每轮写入 meta 记录，便于回放与排查
- **OutboundMessage.metadata**：用于区分 progress/final/error 等事件

---

### 3.4 Provider（模型接入）

#### 3.4.1 LiteLLMProvider（默认实现）

- **统一入口**：通过 LiteLLM `completion()` 完成 chat + tool calling
- **消息清洗**：仅保留允许字段，避免 provider 拒绝；对 `assistant content=None` 做兼容
- **tool_call_id 规范化**：保证非空、安全字符、长度限制与本次响应内唯一
- **参数剔除（drop_params）**：按 ProviderSpec 默认剔除不兼容字段，并允许使用 `TIANGONG_PROVIDER_DROP_PARAMS_<NAME>` 追加
- **DashScope 扩展**：当 `api_base` 指向 DashScope 时，可通过 env 开启联网搜索与图文混合相关 payload（仅在启用时透传）

#### 3.4.2 ProviderRegistry（模型名归一化与网关识别）

- **normalize_model**：为未带前缀的模型补齐 `openai/` 等前缀（按 spec）
- **find_gateway(api_base, api_key)**：按 key 前缀与 api_base 关键词识别 “openai-compatible-gateway” 等网关形态

---

### 3.5 Skills（技能体系：加载、概要、执行）

#### 3.5.1 Skill 文档格式

- 位置：`<workspace>/skills/<name>/SKILL.md`（workspace skills 优先于内置）
- 文件内容：YAML frontmatter（子集）+ Markdown 正文
- 常驻：frontmatter `always: true` 的 skill 可被识别为 always skills

#### 3.5.2 SkillsLoader（加载与摘要）

- `list_skills()`：列出所有可用 skills（workspace 覆盖内置）
- `build_skills_summary()`：生成 `<skills>...</skills>` 摘要（用于注入上下文，避免 prompt 膨胀）
- `load_skills_for_context(names)`：把指定 skills 的正文拼接为 `## SKILL: ...` 块

#### 3.5.3 SkillsRuntime（可调用能力唯一入口）

- **对模型暴露**：以 function calling tools schema 提供 `get_definitions()`
- **执行**：`execute(name, arguments)` 返回字符串结果，供写入 tool 消息

#### 3.5.4 内置技能适配器（v0.1）

在 `TiangongApp` 中默认注册：

- `fs`（文件系统）
- `shell`（命令执行，支持超时与 workspace 限制）
- `message`（向 bus 投递消息/事件）
- `cron`（进程内后台线程调度触发；v0.1 能力边界以当前实现为准）
- `spawn`（子任务异步投递到本进程队列执行；v0.1 能力边界以当前实现为准）
- `mcp`：仅桥接接口预留；当前版本不注册任何具体 MCP 技能（对模型不可见）

---

### 3.6 Session（会话持久化与 /stop）

- **会话键**：默认 `channel:chat_id`；可切换为 `<agent_id>:<chat_id>`
- **历史读取**：`get_history(..., max_messages=80)`（用于控制上下文长度）
- **落盘**：append-only 写入本轮 turn 记录，并在开头写入 meta（包含 `run_id` 与 runtime metadata）
- **停止**：内置命令 `/stop`，将该 session 标记为 stopped；后续请求直接返回“已停止”

---

### 3.7 AgentLoop（核心执行循环）

#### 3.7.1 消息序列与稳定性约束

- 系统 prompt（如存在）+ 会话历史 + 本轮 user（包含 runtime_metadata 包裹块）
- 当模型返回 tool_calls 且 content 为空时，仍必须持久化该 assistant 消息，确保下一轮历史序列合法

#### 3.7.2 工具迭代与截断

- **最大迭代**：`max_tool_iterations` 控制最多循环次数
- **工具结果截断**：tool 输出按 `tool_result_max_chars` 截断，避免会话与上下文膨胀
- **progress 回调**：每次工具执行前可推送 progress 事件

---

### 3.8 Flow（PocketFlow glue：v0.1 轻量执行器）

- **FlowRunner**：按顺序执行 `FlowNodeSpec` 列表；遇到 `status="error"` 终止后续节点
- **内置节点**：
  - `chat`：占位/透传节点（v0.1 不调用 LLM，仅把输入包装为结果，便于下游组装 Flow）
  - `tool_exec`：工具执行节点

---

## 4. 验收标准（v0.1）

- **CLI 可用性**
  - 执行 `tiangong agent -m "hello"` 可获得输出（final）
  - 交互模式可连续多轮对话，且 progress 行与最终输出分离
- **tool calling 稳定性**
  - 连续 tool 调用不会出现 “tool 消息无对应 tool_calls” 的非法序列
  - 工具输出超长时会被截断并标注 `…[truncated]`
- **配置可控**
  - .env 分层加载生效，且不会覆盖 OS 显式环境变量
  - `TIANGONG_SESSION_KEY_SCHEME=agent_chat` 生效（同一 chat_id 不同 agent_id 不共享历史）
- **安全默认值**
  - 默认启用 workspace 限制（`TIANGONG_RESTRICT_WORKSPACE=1`）
  - CLI allowlist 逻辑正确（allow_all=false 且 allow_from 为空时拒绝）

---

## 5. 里程碑（建议按发布节奏维护）

- **v0.1（当前范围）**：CLI + Provider + Skills + Session + AgentLoop + FlowRunner 最小闭环完成并通过单测
- **v0.2（候选）**：更完善的通道（HTTP/IM）、更丰富的 Flow 图能力、能力开关与策略更细化

---

## 6. 风险与对策（与实现对齐）

- **Provider 兼容性**：通过消息清洗、tool_call_id 规范化、按 provider/gateway 的 drop_params 减少拒参
- **会话历史污染**：强约束持久化顺序，避免非法 tool 序列；对 provider 调用失败返回可操作提示
- **输出膨胀**：统一对工具输出与模型长文本做截断
- **本地执行安全**：默认限制工具在 workspace 内运行；shell 超时；CLI sender allowlist
