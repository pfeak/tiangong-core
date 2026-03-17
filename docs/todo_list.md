# Tiangong TODO（与 `tiangong-core` 现状对齐）

> 目标：维护一个“**能验收**、**可对照代码/测试**”的清单：把**尚未完成**的能力拆成可执行 TODO。
>
> 范围：仅 `tiangong-core` 仓。研究场景/实验请在 `tiangong-research` 另行维护。

---

## 1. 近期必须补齐（按可验收任务拆分）

### 1.1 Gateway（进程级工程化）

- [ ] **优雅退出与资源回收**：SIGINT/SIGTERM 时显式 stop（如 `ChannelManager.stop()`、后台服务 stop/flush），避免线程泄露与脏退出
- [ ] **前台/后台一致行为**：`gateway start/stop/status/restart` 的行为、退出码、日志路径对齐（包含 pidfile/lock 可靠性）
- [ ] **统一日志与可观测性**：至少把 `print(...)` 收敛到 logger（stdout/stderr 分流、结构化字段：run_id/channel/chat_id）

### 1.2 Channels（可靠性与一致性）

- [ ] **发送失败语义统一**：不同 channel 的 `send()` 返回值与错误字段对齐；失败时 outbound 回传/告警策略明确
- [ ] **重试/退避与限流**：对外部 webhook/API 增加指数退避（可配置）与速率限制，避免短期风暴
- [ ] **Inbound 支持清晰化**：哪些 channel 支持 inbound（消息进入 bus），哪些仅 outbound；在文档/配置中明确

### 1.3 配置与安全（可开箱、可部署）

- [ ] **示例配置与 env 对齐**：确保 `config.example.json` + README 的配置段落与实际 `AppConfig` 字段一致
- [ ] **allowlist/安全边界**：CLI 允许的命令/路径、webhook 签名校验、token/secret 读取策略明确并有测试

---

## 2. 明确后置（不阻塞最小闭环，但要保留形状）

- [ ] **Cron（可运行实现）**：从“注册点/空实现”推进到可配置的定时触发（持久化、幂等、可停用）
- [ ] **Subagent（隔离与取消）**：并发限制、资源隔离、取消语义与结果回传协议
- [ ] **MCP（动态工具注入）**：server discovery、权限与沙箱策略、工具 schema 映射与错误处理

---

## 3. 建议执行顺序（只按 core 仓）

- [ ] **先补齐 Gateway 的优雅退出与日志**（对稳定性提升最大）
- [ ] **再把 Channels 的失败语义/重试/限流做成可配置**（避免线上抖动）
- [ ] **最后推进 cron/subagent/mcp 从“形状”到“可运行”**
