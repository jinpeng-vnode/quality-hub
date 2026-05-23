# 项目启动指南（AI 角色必读）

## 基础信息
- 项目名：quality-hub（项目质量管理平台）
- 主分支：dev
- 后端目录：`backend/`
- 前端目录：`frontend/`

## 环境依赖
- Docker：是（推荐使用 docker-compose 一键启动）
- 后端：Python 3.11，包管理器 uv
- 前端：Node 18，包管理器 yarn
- 数据库：SQLite（Docker volume 持久化）

## 一键启动（优先使用）

### Docker 方式
```bash
# 首次启动（复制环境变量文件）
cp .env.example .env

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 非 Docker 方式
```bash
# 后端
cd backend && uv sync && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend && yarn install && yarn dev --host 0.0.0.0 --port 3000
```

## 环境变量
- 配置文件位置：`.env`（从 `.env.example` 复制）
- 必须配置的变量：无（默认值可用于开发）
- 默认值是否可用于开发：是

## 端口分配
| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 8000 | FastAPI |
| 前端 | 3000 | Vite dev server |

## 验证方式
```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端访问
curl http://localhost:3000
```

## 加速源配置
- 后端 uv：清华源（`backend/uv.toml`）
- 前端 yarn：淘宝源（`frontend/.yarnrc`）

## 注意事项
- SQLite 数据库文件存储在 Docker volume `sqlite-data` 中
- 开发模式下源码目录已挂载，修改代码后服务自动重载
- 修改 Dockerfile 或依赖文件后需 `docker-compose up -d --build` 重建镜像
