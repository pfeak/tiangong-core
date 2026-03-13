# tiangong-core

## 安装（统一使用 uv tool）

推荐把 `tiangong` 当作一个工具安装到全局工具环境里，这样可以直接运行 `tiangong ...`。

在仓库根目录执行：

```bash
# 开发/本地修改：可编辑安装（推荐）
uv tool install -e .

# 升级（强制重装）
uv tool install -e . --force

# 验证
tiangong --help
tiangong skills --help
```

如果出现 `command not found: tiangong`，通常是 `uv` 的工具 bin 目录未加入 `PATH`。
你可以先用以下命令找到工具路径并加入到 shell 配置中：

```bash
uv tool dir
uv tool list
```

## 配置（dotenv）

- 将 `env.example` 复制为 `.env`（放在仓库根目录，或你运行 `tiangong -w <workspace>` 的 workspace 目录里）
- 配置项会在启动时自动加载：优先 `workspace/.env`，其次当前目录 `.env`
