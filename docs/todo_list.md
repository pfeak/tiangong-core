# Tiangong v0.1 TODO List（与仓库现状对齐）

> 目标：以 `tiangong-core` 为主完成“可运行最小闭环”（PRD 7.1），并把未实现的预留能力（PRD 7.2）拆成可验收任务。
>
> 说明：本清单只覆盖 `tiangong-core` 仓；`tiangong-research` 的 3 个场景落地请在对应仓单独维护。

---

## 0. 约定与基线（PRD 5.1 / 3.9.4）

- [x] **文档化约定**：`docs/prd.md` 中已补充 v0.1 实际约定与环境变量清单，对应当前 `config.load_config` / `env.example`

---

## 1. tiangong-core：最小闭环（PRD 7.1 必须具备）

### 1.2 SkillsRuntime（PRD 3.2）

### 1.3 Session（PRD 3.5）

- [x] **测试补齐**：`SessionManager.get_history` 的对齐与尾部处理已由 `test_session_manager_history*.py` 覆盖

### 1.4 Context（PRD 3.4 / 3.3）

- [x] **builtin skills 回退（可选）**：当 workspace 无 skills 时，从 `tiangong_core/templates/` 提供最小示例（PRD 3.3.3 建议）

### 1.5 Loop（PRD 3.10）

- [x] **测试补齐**：`AgentLoop` 的 skill_result 截断与带 skill_calls 的 assistant 持久化逻辑已由 `test_agent_loop_tool_truncation_and_sequence.py` 覆盖

### 1.6 Bus + Channels + CLI（PRD 3.9 / 7.1）

- [x] **最小 e2e 测试（可选但建议）**：用 dummy provider 跑通一轮 turn（inbound→loop→outbound），确保开箱即用不回归

---

## 2. PRD 7.2：建议预留但可后置（本仓当前未实现）

- [x] **Cron（接口预留）**：定义 skill schema + 空实现/feature flag（PRD 3.7）
- [x] **Subagent（接口预留）**：spawn/cancel 的最小形状 + 隔离策略占位（PRD 3.8）
- [x] **MCP 桥（接口预留）**：把 MCP 能力动态注入 SkillsRuntime（PRD 3.2.3）
- [x] **PocketFlow glue**：Flow Runner + 基础节点（`SkillExecNode`/`ChatNode`）+ research 节点注册机制（PRD 3.11）

---

## 3. 建议执行顺序（只按 core 仓）

- [x] **再做 PocketFlow glue / cron / spawn / mcp 的接口预留**
