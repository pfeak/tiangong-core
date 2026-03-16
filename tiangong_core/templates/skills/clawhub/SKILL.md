---
title: "Clawhub 安装/更新技能包"
description: "指导把技能安装到 workspace/skills/，core 不强依赖 Node，但可通过 npx 运行。"
always: false
tags:
  - skills
  - setup
---

当你需要安装或更新 skills（技能包）到当前工作区时，优先采用“workspace 本地技能目录”方案：

- 目标目录：`<workspace>/skills/`
- 约定结构：`skills/<skill-name>/SKILL.md`

如果系统已安装 Node.js（含 `npx`），可使用 clawhub：

```bash
npx clawhub@latest install --workdir "<workspace>" 
```

或更新：

```bash
npx clawhub@latest update --workdir "<workspace>"
```

每次下载先登录：

```bash
clawhub login --token <token>
```

安装完成后，你可以通过 `tiangong skills list` 查看已发现的技能。
