# CrowdFlow - 人流密度分析系统

基于 YOLO 的实时人流密度检测与分析系统。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **前端**: Vue 3 + TypeScript + Vite
- **AI**: YOLOv8 (Ultralytics)

## 项目结构

```
CrowdFlow/
├── backend/          # FastAPI 后端
├── frontend/         # Vue 前端
├── docker/           # Dockerfile
├── scripts/          # 启动脚本
├── data/             # SQLite 数据库
├── uploads/          # 上传的视频文件
├── models/           # YOLO 模型文件
├── logs/             # 日志文件
└── docker-compose.yml
```

---

## 快速开始（Docker）

### 1. 配置环境变量

```bash
cp .env.example .env
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 访问服务

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 4. 停止服务

```bash
docker-compose down
```

---

## 开发模式

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 启动（热重载）
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 启动（热重载）
pnpm dev
```

### 使用脚本

```bash
# 启动全部
./scripts/dev.sh

# 仅后端
./scripts/dev.sh backend

# 仅前端
./scripts/dev.sh frontend
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PYTHON_ENV` | Python 环境类型 | `conda` |
| `CONDA_ENV_NAME` | conda 环境名称 | `crowdflow` |
| `DEBUG` | 调试模式 | `true` |
| `PORT` | 后端端口 | `8000` |
| `BACKEND_PORT` | Docker 后端映射端口 | `8000` |
| `FRONTEND_PORT` | Docker 前端映射端口 | `3000` |
| `YOLO_MODEL_PATH` | YOLO 模型路径 | `yolov8n.pt` |
| `YOLO_DEVICE` | 推理设备 (cpu/cuda/mps) | `cpu` |
| `ALERT_TOTAL_WARNING` | 总人数警告阈值 | `50` |
| `ALERT_TOTAL_CRITICAL` | 总人数严重阈值 | `100` |

> **Python 环境说明**：`PYTHON_ENV=conda` 使用 conda 环境，`PYTHON_ENV=venv` 使用 venv

---

## API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
