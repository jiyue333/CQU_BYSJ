# 人流计数与密度分析系统

基于 YOLOv8 的实时人流计数与密度分析系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端浏览器                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  HTTP API │   │ WebSocket │   │ 视频流播放 │
            │  :8000    │   │  :8000    │   │   :8080   │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
┌───────────────────┼───────────────┼───────────────┼───────────────────┐
│                   ▼               ▼               ▼                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Backend API (FastAPI)                        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                   │                                    │
│                    ┌──────────────┼──────────────┐                    │
│                    ▼              ▼              ▼                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                   Redis (PubSub + Streams)                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                   │                                    │
│                                   ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                 Inference Service (YOLO Worker)                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│         ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│         │ PostgreSQL │    │ ZLMediaKit │    │  Uploads   │            │
│         │   :5432    │    │   :8080    │    │  Volume    │            │
│         └────────────┘    └────────────┘    └────────────┘            │
└───────────────────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 克隆项目
git clone <repository-url>
cd crowd-counting

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，确保 ZLM_SECRET 与 zlm-config/config.ini 一致

# 3. 启动服务
chmod +x scripts/deploy.sh
./scripts/deploy.sh prod      # 生产模式
./scripts/deploy.sh dev       # 开发模式（仅基础设施）
./scripts/deploy.sh stop      # 停止服务
```

## 端口说明

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|---------|-----------|------|
| frontend | 80 | 3000 | Vue 前端 |
| backend | 8000 | 8000 | FastAPI API + WebSocket |
| inference | - | - | YOLO 推理（无外部端口，通过 Redis 通信） |
| postgres | 5432 | 5432 | PostgreSQL 数据库 |
| redis | 6379 | 6379 | Redis 消息队列 |
| zlmediakit | 80 | 8080 | HTTP API / HTTP-FLV / HLS |
| zlmediakit | 1935 | 1935 | RTMP |
| zlmediakit | 554 | 8554 | RTSP |
| zlmediakit | 10000 | 10000 | RTP (TCP/UDP) |
| zlmediakit | 8000/udp | 8000/udp | WebRTC |

## 挂载卷说明

| 挂载路径 | 容器路径 | 说明 |
|---------|---------|------|
| `./uploads` | `/data/uploads` | 上传的视频文件（backend + zlmediakit 共享） |
| `./zlm-config` | `/opt/media/conf` | ZLMediaKit 配置文件 |
| `./zlm-logs` | `/opt/media/log` | ZLMediaKit 日志 |
| `./zlm-media` | `/opt/media/www` | HLS 切片等媒体文件 |
| `postgres-data` | `/var/lib/postgresql/data` | PostgreSQL 数据（Docker Volume） |
| `redis-data` | `/data` | Redis 持久化数据（Docker Volume） |

## 配置文件

| 文件 | 说明 |
|------|------|
| `.env` | 环境变量（从 `.env.example` 复制） |
| `zlm-config/config.ini` | ZLMediaKit 配置（`[api] secret` 需与 `.env` 中 `ZLM_SECRET` 一致） |

## 扩展

```bash
# 水平扩展推理服务
docker-compose -f docker-compose.prod.yml up -d --scale inference=3

# GPU 加速（需要 NVIDIA Container Toolkit）
docker-compose -f docker-compose.prod.yml -f docker-compose.gpu.yml up -d
```

## 访问地址

- 前端界面: http://localhost:3000
- API 文档: http://localhost:8000/docs
- ZLMediaKit: http://localhost:8080
