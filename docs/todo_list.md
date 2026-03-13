# Tiangong v0.1 TODO List（干净版）

> 目标：先把 `tiangong-core` 做成可运行的最小闭环内核，再在 `tiangong-research` 落地 3 个场景（测试/优化指定项目/Python 代码）。

---

## 0. 约定与基线（先定不做大改）

- [ ] **代码组织**：确定 Python 包名/目录（建议 `tiangong_core/`），并固定 public API 边界
- [ ] **配置约定**：确定配置文件位置与加载优先级（用户目录 vs workspace），并定义最小 schema
- [ ] **身份约定**：落地 `agent_id/agent_name/run_id` 的生成与持久化位置（与 `prd.md` 3.9.4 对齐）

---

## 1. tiangong-core：内核最小闭环

### 1.1 Bus + Events + Channels（CLI 优先）

- [ ] **定义事件模型**：`InboundMessage/OutboundMessage`（字段包含 `metadata.agent_id/agent_name/run_id`）
- [ ] **实现 MessageBus**：inbound/outbound 队列 + publish/consume
- [ ] **实现 CLI Channel**：输入转 InboundMessage，输出消费 OutboundMessage
- [ ] **通道权限**：allowlist 的默认策略与 CLI 兼容（CLI 可默认允许）

### 1.2 Session（append-only JSONL）

- [ ] **Session/SessionManager**：jsonl 存取、缓存、`get_history()` 对齐 user turn
- [ ] **保存策略**：tool_result 截断 + 过滤空 assistant + 错误响应落盘策略
- [ ] **session_key 方案**：v0.1 实现 PRD 方案 A（metadata 记录 agent_id），并预留切到方案 B 的开关

### 1.3 ContextBuilder（bootstrap + skills + memory + runtime）

- [ ] **Bootstrap 文件加载**：`AGENTS.md/SOUL.md/USER.md/TOOLS.md`（workspace 优先）
- [ ] **Runtime metadata 注入**：合并到单条 user message（避免 provider 拒绝连续 role）
- [ ] **Skills summary 注入**：system prompt 中给出 skills 列表与“如何启用”的指引

### 1.4 Providers（LiteLLM 主实现 + registry）

- [ ] **Provider base 接口**：`chat/chat_with_retry` + `LLMResponse/ToolCallRequest`
- [ ] **Provider registry**：ProviderSpec + find_by_model/find_gateway（网关/本地/直连识别）
- [ ] **LiteLLMProvider**：model 解析、drop_params、messages sanitize、tool_call_id 规范化
- [ ] **最小可用 provider 配置**：至少覆盖 1 个标准 provider + 1 个网关（便于真实跑通）

### 1.5 Tool 系统（registry + 默认工具）

- [ ] **ToolRegistry**：注册/definitions/execute + 统一结果序列化
- [ ] **fs 工具**：read/write/edit/list（支持 restrict_to_workspace）
- [ ] **shell 工具**：exec（timeout、工作目录、restrict_to_workspace）
- [ ] **web 工具（可选）**：search/fetch（代理与 key 配置）
- [ ] **message 工具**：向 bus/outbound 发送消息（CLI 退化可用）
- [ ] **spawn/cron/mcp 接口预留**：先定义工具 schema 与空实现或 feature flag

### 1.6 AgentLoop（核心迭代执行）

- [ ] **迭代循环**：max_iterations、工具调用闭环、progress 回调
- [ ] **run_id 链路贯穿**：provider 调用、工具执行、session 写入、outbound 发送都带 run_id
- [ ] **/stop（可选）**：最小实现“取消本 session 活跃任务”
- [ ] **process_direct**：供 CLI 单次与 cron 触发复用

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

- [ ] **日志与可观测性**：关键路径打点（provider 调用、工具执行、session 落盘），日志包含 agent_id/run_id
- [ ] **最小测试集**：覆盖 provider registry、session 对齐、tool_result 截断、tool_call_id 规范化
- [ ] **安全默认值**：restrict_to_workspace 默认开启（可配置关闭），shell 超时默认值明确
