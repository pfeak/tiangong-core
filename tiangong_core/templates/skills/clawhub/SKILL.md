---
name: clawhub
description: Search and install agent skills from ClawHub, the public skill registry.
homepage: https://clawhub.ai
metadata: {"tiangong":{"emoji":"🦞"}}
---

# ClawHub

当你需要安装或更新 skills（技能包）到当前工作区时，优先采用“workspace 本地技能目录”方案：

- 目标目录：`<workspace>/skills/`
- 约定结构：`skills/<skill-name>/SKILL.md`

如果系统已安装 Node.js（含 `npx`），可使用 clawhub。

```bash
npx --yes clawhub@latest install <slug> --workdir "<workspace>"
```

或更新：

```bash
npx --yes clawhub@latest update --all --workdir "<workspace>"
```

列出已安装：

```bash
npx --yes clawhub@latest list --workdir "<workspace>"
```

说明：

- `--workdir "<workspace>"` 很重要，否则会安装到当前目录。
- 需要 Node.js（`npx`）。
- 安装/更新完成后，建议开启新会话以确保技能被发现与加载。
