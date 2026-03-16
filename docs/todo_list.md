# Tiangong v0.1 TODO List（与仓库现状对齐）

> 目标：以 `tiangong-core` 为主完成“可运行最小闭环”（PRD 7.1），并把未实现的预留能力（PRD 7.2）拆成可验收任务。
>
> 说明：本清单只覆盖 `tiangong-core` 仓；`tiangong-research` 的 3 个场景落地请在对应仓单独维护。

---

## 0. 约定与基线（PRD 5.1 / 3.9.4）

- [ ] **文档化约定**：在 `docs/prd.md` 的“实际约定”段落旁补充“当前实现路径/环境变量清单”（只写 core 仓的事实）

---

## 1. tiangong-core：最小闭环（PRD 7.1 必须具备）

### 1.1 Providers（PRD 3.1）

- [ ] **tool_call_id 规范化**：如果 provider 返回空/重复/超长 id，需生成稳定安全 id 并保证 tool 消息一致（PRD 3.1.3；目前实现主要是“透传/容错解析”）
- [ ] **错误短路策略**：对 400（非法消息序列）等可判定错误，避免写入“毒化”历史并给出可操作提示（PRD 9；当前已做部分过滤，但缺少系统化策略与测试）

### 1.2 Tools（PRD 3.2）

- [ ] **web 工具（可选但建议做）**：`web.search/web.fetch`（含代理与 key 配置，PRD 3.2.3）
- [ ] **工具命名兼容层（可选）**：支持别名映射（PRD 3.2.4），至少在 ToolRegistry 层预留 alias 表

### 1.3 Session（PRD 3.5）

- [ ] **测试补齐**：覆盖 session 对齐（tool 开头/尾部空 assistant）与 stop 行为（目前缺 session 测试）

### 1.4 Context（PRD 3.4 / 3.3）

- [ ] **builtin skills 回退（可选）**：当 workspace 无 skills 时，从 `tiangong_core/templates/` 提供最小示例（PRD 3.3.3 建议）

### 1.5 Loop（PRD 3.10）

- [ ] **测试补齐**：mock provider 返回 tool_calls，验证“assistant(tool_calls) 必落盘”与 tool_result 截断（目前缺 loop 测试）

### 1.6 Bus + Channels + CLI（PRD 3.9 / 7.1）

- [ ] **最小 e2e 测试（可选但建议）**：用 dummy provider 跑通一轮 turn（inbound→loop→outbound），确保开箱即用不回归

---

## 2. PRD 7.2：建议预留但可后置（本仓当前未实现）

- [ ] **Cron（接口预留）**：定义 tool schema + 空实现/feature flag（PRD 3.7）
- [ ] **Subagent（接口预留）**：spawn/cancel 的最小形状 + 隔离策略占位（PRD 3.8）
- [ ] **MCP 工具桥（接口预留）**：把 MCP tool 动态注册进 ToolRegistry（PRD 3.2.3）
- [ ] **PocketFlow glue**：Flow Runner + 基础节点（`ToolExecNode`/`ChatNode`）+ research 节点注册机制（PRD 3.11）

---

## 3. 建议执行顺序（只按 core 仓）

- [ ] **补齐测试**：Session + Loop 的关键回归点（“tool_calls assistant 必落盘”“tool_result 截断”“stop/对齐策略”）
- [ ] **补齐 Provider 的 tool_call_id 规范化与错误短路**（把 PRD 3.1.3/9 变成可测的行为）
- [ ] **实现 web 工具**（search/fetch）并接入 CLI 最小演示
- [ ] **再做 PocketFlow glue / cron / spawn / mcp 的接口预留**
