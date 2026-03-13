# tiangong-core

## 配置（dotenv）

- 将 `env.example` 复制为 `.env`（放在仓库根目录，或你运行 `tiangong -w <workspace>` 的 workspace 目录里）
- 配置项会在启动时自动加载：优先 `workspace/.env`，其次当前目录 `.env`
