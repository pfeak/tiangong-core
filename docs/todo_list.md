# Tiangong v0.1 TODO List（干净版）

> 目标：先把 `tiangong-core` 做成可运行的最小闭环内核，再在 `tiangong-research` 落地 3 个场景（测试/优化指定项目/Python 代码）。

---

## 0. 约定与基线（先定不做大改）

- [~] **配置约定**：确定配置文件位置与加载优先级（用户目录 vs workspace），并定义最小 schema（已实现 env + `.env` 加载与最小 dataclass schema：`tiangong_core/config.py`；尚未落地“用户目录 vs workspace”的分层配置文件方案）
- [~] **身份约定**：落地 `agent_id/agent_name/run_id` 的生成与持久化位置（与 `prd.md` 3.9.4 对齐）（已实现 `agent_id` 持久化：`workspace/runtime/agent.json`；`run_id` 每次 `run_once` 生成并贯穿；尚未实现跨 run 的 `run_id` 记录/查询约定）

---

## 1. tiangong-core：内核最小闭环

### 1.1 Session（append-only JSONL）

### 1.3 ContextBuilder（bootstrap + skills + memory + runtime）

### 1.4 Providers（LiteLLM 主实现 + registry）

- [~] **LiteLLMProvider**：model 解析、drop_params、messages sanitize、tool_call_id 规范化（已实现 model normalize、messages sanitize、tool_calls 解析与 tool_call_id 透传：`tiangong_core/providers/litellm_provider.py`；“drop_params”目前为尽量少传参策略，未做可配置的参数剔除表）
- [~] **最小可用 provider 配置**：至少覆盖 1 个标准 provider + 1 个网关（便于真实跑通）（已支持 `openai/*` 与 openai-compatible gateway 的基础 spec；配置目前主要走 env：`TIANGONG_*`）

### 1.5 Tool 系统（registry + 默认工具）

- [ ] **web 工具（可选）**：search/fetch（代理与 key 配置）（未实现）
- [ ] **spawn/cron/mcp 接口预留**：先定义工具 schema 与空实现或 feature flag（未实现）

### 1.6 AgentLoop（核心迭代执行）

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

## 接下来建议优先级（v0.1 → 可跑可迭代）

- [ ] **完善配置与身份约定**：补齐“用户目录 vs workspace”的分层配置文件方案，以及跨 run 的 `run_id` 记录/查询约定，对齐 PRD 3.9.4 的身份设计。
- [ ] **落地 ContextBuilder 与 skills/memory 集成**：按照 PRD 3.4/3.3/3.6，将 bootstrap（AGENTS/SOUL/USER/TOOLS）、skills summary/always skills、memory consolidation 的最小闭环串到 ContextBuilder 中。
- [ ] **补齐 LiteLLMProvider 与 provider 配置**：为不同 provider/gateway 建立可配置的 drop_params 表与最小可用配置（至少 1 个标准 provider + 1 个网关的 out-of-the-box 体验）。
- [ ] **实现 web/spawn/cron/mcp 工具与 PocketFlow glue**：完成 web 工具、spawn/cron/mcp 接口的 schema/空实现，并打通 PocketFlow Flow Runner + 基础节点（`ToolExecNode`/`ChatNode`）与 AgentLoop/Tools/Session。
- [ ] **在 tiangong-research 落地 3 个场景**：为 Test/Optimize/Python 三个 Agent 定义最小可运行的 flow + skills + demo（分别覆盖失败修复闭环、plan-only 优化、Spec→实现→自测链路）。
