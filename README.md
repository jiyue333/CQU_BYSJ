# CrowdFlow

基于 YOLO 的实时人流密度检测与分析系统，前后端分离：

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：Vue 3 + TypeScript + Vite
- 检测模型：Ultralytics YOLO

## 项目结构

```text
.
├── backend/            # FastAPI 后端
├── frontend/           # Vue 前端
├── docker/             # Dockerfile
├── scripts/            # 开发 / 启动脚本
├── data/               # SQLite 数据与导出结果
├── uploads/            # 上传文件
├── models/             # 额外模型目录
├── logs/               # 日志目录
├── yolo11n.pt          # 默认模型文件
└── docker-compose.yml
```

## 本地开发

日常开发优先使用 `./scripts/dev.sh`。脚本会：

- 自动创建 `backend/.venv`
- 自动安装后端和前端依赖
- 支持分别启动前端、后端或同时启动

### 环境要求

- Python 3.10 及以上，建议 3.11
- Node.js 18 及以上
- npm

### 第一次启动

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 安装依赖：

```bash
./scripts/dev.sh setup
```

3. 启动前后端：

```bash
./scripts/dev.sh
```

启动后默认访问地址：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/api
- Swagger：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 常用命令

```bash
# 启动前后端
./scripts/dev.sh

# 仅启动后端
./scripts/dev.sh backend

# 仅启动前端
./scripts/dev.sh frontend

# 重新安装依赖
./scripts/dev.sh setup
```

### 手动启动

如果你不想使用脚本，也可以分别启动：

```bash
# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install setuptools wheel
python -m pip install --no-build-isolation -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# 前端
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

## Docker 启动

如果你只想快速拉起整套服务，保留 Docker 流程。

### 第一次启动

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 构建并启动：

```bash
docker compose up --build -d
```

也可以通过脚本：

```bash
./scripts/dev.sh docker-up
```

3. 查看服务：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/api
- Swagger：http://localhost:8000/docs

### 停止服务

```bash
docker compose down
```

或：

```bash
./scripts/dev.sh docker-down
```

### 常用 Docker 命令

```bash
# 查看容器状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 查看前端日志
docker compose logs -f frontend
```

## 环境变量

项目根目录的 `.env` 会同时被本地脚本和 Docker Compose 使用。

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEBUG` | 是否开启调试模式 | `true` |
| `HOST` | 后端监听地址 | `0.0.0.0` |
| `PORT` | 本地后端端口 | `8000` |
| `BACKEND_PORT` | Docker 映射到宿主机的后端端口 | `8000` |
| `FRONTEND_PORT` | 本地前端端口 / Docker 前端端口 | `3000` |
| `DATABASE_URL` | 自定义数据库连接串，留空则使用 SQLite | 空 |
| `YOLO_MODEL_PATH` | 自定义模型路径，留空则使用仓库根目录的 `yolo11n.pt` | 空 |
| `YOLO_CONF_THRESHOLD` | YOLO 置信度阈值 | `0.5` |
| `YOLO_DEVICE` | 推理设备：`cpu` / `cuda` / `mps` | `cpu` |
| `ALERT_COOLDOWN_SECONDS` | 同一区域告警冷却时间（秒） | `30` |
| `DENSITY_FACTOR` | 密度计算系数 | `10000` |
| `DENSITY_MAX` | 密度显示上限 | `100` |
| `VITE_API_URL` | 前端构建时使用的后端地址，通常无需设置 | 空 |

## 常见问题

### 1. 后端启动时报模型文件不存在

默认会读取仓库根目录下的 `yolo11n.pt`。如果你使用自定义模型，在 `.env` 中设置 `YOLO_MODEL_PATH=/absolute/path/to/model.pt`。

### 2. 端口被占用

修改 `.env` 中的 `PORT` 或 `FRONTEND_PORT` 后重新启动：

```bash
./scripts/dev.sh
```

### 3. 依赖状态异常

可以删除 `backend/.venv` 和 `frontend/node_modules` 后重新执行：

```bash
./scripts/dev.sh setup
```
