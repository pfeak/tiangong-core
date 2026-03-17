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

## 开发环境（Python 版本）

本项目使用 `.python-version` 提供给 `pyenv`/编辑器识别的推荐版本（当前为 `3.10.16`）。

- 如果你的环境里没有该精确补丁版本，也可以使用 **Python 3.10.x**（例如 `3.10.14`）运行与测试。
- 若你使用 `pyenv` 并遇到 “version is not installed”，请安装对应版本或临时指定已安装版本运行测试。

## 配置（dotenv）

默认使用 `config.json`（推荐），环境变量优先级最高。

- 将 `config.example.json` 复制为 `config.json`（放在仓库根目录，或你运行 `tiangong -w <workspace>` 的 workspace 目录里）
- 启动时默认读取：`<workspace>/config.json`（不存在则尝试当前目录 `./config.json`）
- 可用 `tiangong agent -c /path/to/config.json` 显式指定配置文件
- 若你仍使用 `.env`，项目会继续加载（并作为环境变量覆盖 `config.json`），但推荐迁移到 `config.json`

## Channels（发送沟通消息）

tiangong-core 仅保留 `cli/telegram/feishu/qq` 四种 channel；配置统一在 `config.json` 的 `channels.*` 下完成（字段风格参考 nanobot：`token/appId/appSecret/secret/allowFrom`）。

### Telegram

- `channels.telegram.enabled`
- `channels.telegram.token`
- `channels.telegram.allowFrom`
- inbound：使用 Bot API `getUpdates` long polling（无需额外服务）

### Feishu/Lark

- `channels.feishu.enabled`
- `channels.feishu.appId`
- `channels.feishu.appSecret`
- `channels.feishu.allowFrom`
- inbound webhook：
  - `channels.feishu.webhookHost`
  - `channels.feishu.webhookPort`
  - `channels.feishu.webhookPath`

### QQ

- `channels.qq.enabled`
- `channels.qq.appId`
- `channels.qq.secret`
- `channels.qq.allowFrom`

### CLI

- `channels.cli.enabled`
- `channels.cli.allowFrom`（默认 `["*"]` 放通本地 CLI sender）
