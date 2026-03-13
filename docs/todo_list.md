# Tiangong v0.1 TODO List（干净版）

> 目标：先把 `tiangong-core` 做成可运行的最小闭环内核，再在 `tiangong-research` 落地 3 个场景（测试/优化指定项目/Python 代码）。

---

## 0. 约定与基线（先定不做大改）

- [~] **配置约定**：确定配置文件位置与加载优先级（用户目录 vs workspace），并定义最小 schema（已实现 env + `.env` 加载与最小 dataclass schema：`tiangong_core/config.py`；尚未落地“用户目录 vs workspace”的分层配置文件方案）
- [~] **身份约定**：落地 `agent_id/agent_name/run_id` 的生成与持久化位置（与 `prd.md` 3.9.4 对齐）（已实现 `agent_id` 持久化：`workspace/runtime/agent.json`；`run_id` 每次 `run_once` 生成并贯穿；尚未实现跨 run 的 `run_id` 记录/查询约定）

---

## 1. tiangong-core：内核最小闭环

### 1.1 Bus + Events + Channels（CLI 优先）

- [~] **定义事件模型**：`InboundMessage/OutboundMessage`（字段包含 `metadata.agent_id/agent_name/run_id`）（已定义事件模型：`tiangong_core/bus/events.py`；runtime 元数据在 `TiangongApp.run_once()` 侧注入到 outbound 的 `metadata`，inbound 侧仍是空 metadata）
- [~] **通道权限**：allowlist 的默认策略与 CLI 兼容（CLI 可默认允许）（CLIConfig 里已有 `allow_all=True`，但尚未实现真正的 allowlist 校验/拦截）

### 1.2 Session（append-only JSONL）

- [~] **Session/SessionManager**：jsonl 存取、缓存、`get_history()` 对齐 user turn（已实现 append-only JSONL + `get_history()` 对齐 user turn：`tiangong_core/session/manager.py`；尚未实现缓存层）
- [~] **session_key 方案**：v0.1 实现 PRD 方案 A（metadata 记录 agent_id），并预留切到方案 B 的开关（当前 `session_key` 由 channel 拼接：`cli:{chat_id}`；agent_id/run_id 作为 runtime_metadata 注入到 user turn 内容与 outbound metadata；尚未实现可切换方案/明确 PRD A/B 开关）

### 1.3 ContextBuilder（bootstrap + skills + memory + runtime）

- [ ] **SkillsLoader**：实现 `list_skills()/get_always_skills()/load_skills_for_context()/build_skills_summary()`（对齐 `prd.md` 3.3.2），并支持 workspace skills 优先 + builtin skills 回退
- [ ] **Skills 获取与管理（可选）**：提供 `clawhub` 技能（或 CLI wrapper）以安装/更新 skills 到 `workspace/skills/`，但 core 不强依赖 Node（参考 `nanobot` 的“clawhub skill + npx”方式）

### 1.4 Providers（LiteLLM 主实现 + registry）

- [~] **Provider registry**：ProviderSpec + find_by_model/find_gateway（网关/本地/直连识别）（已实现 ProviderSpec + `find_by_model()` + `normalize_model()`：`tiangong_core/providers/registry.py`；尚未实现 `find_gateway()`/按 api_base+key 前缀的完整识别链路）
- [~] **LiteLLMProvider**：model 解析、drop_params、messages sanitize、tool_call_id 规范化（已实现 model normalize、messages sanitize、tool_calls 解析与 tool_call_id 透传：`tiangong_core/providers/litellm_provider.py`；“drop_params”目前为尽量少传参策略，未做可配置的参数剔除表）
- [~] **最小可用 provider 配置**：至少覆盖 1 个标准 provider + 1 个网关（便于真实跑通）（已支持 `openai/*` 与 openai-compatible gateway 的基础 spec；配置目前主要走 env：`TIANGONG_*`）

### 1.5 Tool 系统（registry + 默认工具）

- [ ] **web 工具（可选）**：search/fetch（代理与 key 配置）（未实现）
- [ ] **spawn/cron/mcp 接口预留**：先定义工具 schema 与空实现或 feature flag（未实现）

### 1.6 AgentLoop（核心迭代执行）

- [~] **run_id 链路贯穿**：provider 调用、工具执行、session 写入、outbound 发送都带 run_id（已在 runtime_metadata/outbound metadata/session records 里携带；provider 调用本身未显式记录 run_id 到 provider 层日志/trace）

### 1.7 PocketFlow glue（节点/图执行）

- [ ] **Flow Runner**：统一执行 pocketflow graph，并与 AgentLoop/Tools/Session 打通
- [ ] **基础节点**：`ToolExecNode`（工具闭环）、`ChatNode`（可选）
- [ ] **节点注册机制**：允许 research 仓注册自定义节点/flow

---

## 2. tiangong-research：场景落地（第一版）

### 2.1 场景 A：测试（Test Agent）

- [ ] **flow 定义**：AnalyzeFail → ProposeFix → ApplyFix → RunTests → Summarize
- [ ] **skills**：pytest/日志解读/最小修复策略
- [ ] **demo**：对一个示例项目跑通“失败→修复→通过”的闭环

### 2.2 场景 B：优化指定项目（Optimize Agent）

- [ ] **flow 定义**：RepoScan → HotspotHypothesis → Plan → ExecuteSmallRefactors → Verify
- [ ] **约束支持**：只改指定目录/不改行为（plan-only 模式优先）
- [ ] **输出模板**：分步骤计划 + 风险点 + 回滚策略

### 2.3 场景 C：Python 代码（Python Agent）

- [ ] **flow 定义**：Spec → Implement → SelfTest(pytest) → PackageResult
- [ ] **skills**：编码规范/边界用例/复杂度控制

---

## 3. 质量与可维护性（最低要求）

- [ ] **日志与可观测性**：关键路径打点（provider 调用、工具执行、session 落盘），日志包含 agent_id/run_id（目前仅有 LiteLLM 日志降噪；尚未系统化打点/结构化日志）
- [ ] **最小测试集**：覆盖 provider registry、session 对齐、tool_result 截断、tool_call_id 规范化（未实现）
