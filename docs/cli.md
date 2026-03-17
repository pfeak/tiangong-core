# CLI 命令清单

CLI 名称：`tiangong`

帮助：`-h` / `--help`

全局选项：

- `--install-completion`：Install completion for the current shell.
- `--show-completion`：Show completion for the current shell, to copy it or customize the installation.

公共选项（所有命令通用）：

- `-w, --workspace <path>`：workspace path (default: .)（默认：`.`）
- `-c, --config <path>`：config json path (default: workspace/config.json)（默认：不传）

## 命令结构

- `tiangong agent`
- `tiangong skills ...`
  - `tiangong skills list`
  - `tiangong skills summary`
  - `tiangong skills show <name>`
  - `tiangong skills install [names...]`
- `tiangong gateway ...`
  - `tiangong gateway start`
  - `tiangong gateway stop`
  - `tiangong gateway status`
  - `tiangong gateway restart`

无参数行为：

- `tiangong agent` / `tiangong skills` / `tiangong gateway` 不带参数时，输出对应层级的帮助信息（等价于加 `-h/--help`）。

## `tiangong agent`

Help：`Chat with Tiangong agent in CLI`

选项：

- `-m, --message <text>`：single message mode（默认：不传=交互模式）
- （同“公共选项”）
- `--chat-id <id>`：chat id (default: default)（默认：`default`）
- `--markdown / --no-markdown`：render assistant output as Markdown（默认：开启）

## `tiangong skills`

Help：`skills management`

### `tiangong skills list`

Help：`List all available skills in the workspace`

选项：

- （同“公共选项”）

### `tiangong skills summary`

Help：`Show a summary of skills and always-on skills`

选项：

- （同“公共选项”）

### `tiangong skills show <name>`

Help：`Show detailed information for a specific skill`

参数：

- `<name>`：skill name（必填）

选项：

- （同“公共选项”）

### `tiangong skills install [names...]`

Help：`Install or update skills using clawhub`

参数：

- `[names...]`：optional skill names to install/update (default: interactive or as defined by clawhub)（默认：不传）

选项：

- （同“公共选项”）
- `--update`：use clawhub update instead of install（默认：关闭）

## `tiangong gateway`

Help：`gateway management`

### `tiangong gateway start`

Help：`Start gateway in background`

选项：

- （同“公共选项”）
- `-v`：在前台运行（等价于旧的 `tiangong gateway run`）

### `tiangong gateway stop`

Help：`Stop gateway`

选项：

- （同“公共选项”）

### `tiangong gateway status`

Help：`Show gateway status`

选项：

- （同“公共选项”）

### `tiangong gateway restart`

Help：`Restart gateway`

选项：

- （同“公共选项”）
- `-v`：在前台运行（重启后阻塞）
- `--timeout-s <seconds>`：等待旧进程退出的超时（秒）（默认：10）
