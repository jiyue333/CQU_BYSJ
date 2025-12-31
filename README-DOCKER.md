# Docker 开发环境使用指南

本文档说明如何使用 Docker Compose 启动人流计数系统的开发环境。

## 目录结构

```
.
├── docker-compose.yml          # Docker Compose 配置文件
├── .env.example                # 环境变量模板
├── .env                        # 环境变量配置（需手动创建）
├── zlm-config/                 # ZLMediaKit 配置目录
│   └── config.ini              # ZLMediaKit 配置文件
├── zlm-logs/                   # ZLMediaKit 日志目录（自动创建）
├── zlm-media/                  # ZLMediaKit 媒体文件目录（自动创建）
└── uploads/                    # 上传视频文件目录（自动创建）
```

## 快速开始

### 1. 环境准备

确保已安装：
- Docker 20.10+
- Docker Compose 2.0+

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，修改以下关键配置：
# - POSTGRES_PASSWORD: PostgreSQL 密码
# - ZLM_SECRET: ZLMediaKit API 密钥（必须修改）
```

### 3. 同步 ZLMediaKit 密钥

**重要**：`.env` 文件中的 `ZLM_SECRET` 必须与 `zlm-config/config.ini` 中的 `[api] secret` 保持一致。

```bash
# 编辑 zlm-config/config.ini
# 找到 [api] 部分，修改 secret 值与 .env 中的 ZLM_SECRET 一致
```

### 4. 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f zlmediakit
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 5. 验证服务

#### PostgreSQL
```bash
# 测试连接
docker-compose exec postgres psql -U crowd_user -d crowd_counting -c "SELECT 1"

# 进入 PostgreSQL 命令行
docker-compose exec postgres psql -U crowd_user -d crowd_counting
```

#### Redis
```bash
# 测试连接
docker-compose exec redis redis-cli ping

# 进入 Redis 命令行
docker-compose exec redis redis-cli
```

#### ZLMediaKit
```bash
# 测试 API（替换 <ZLM_SECRET> 为实际密钥）
curl "http://localhost:8080/index/api/getServerConfig?secret=<ZLM_SECRET>"

# 查看 ZLMediaKit 日志
tail -f zlm-logs/zlm.log
```

**注意**：ZLMediaKit 服务没有配置健康检查，因为：
- 健康检查依赖的工具（curl/wget）在镜像中可能不存在
- 开发环境更关注服务是否可启动和可调试
- 可以通过 API 测试和日志查看来验证服务状态

### 6. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用，会删除数据库数据）
docker-compose down -v
```

## 服务端口

| 服务 | 端口 | 协议 | 用途 |
|------|------|------|------|
| PostgreSQL | 5432 | TCP | 数据库连接 |
| Redis | 6379 | TCP | 缓存与消息队列 |
| ZLMediaKit | 1935 | TCP | RTMP 推流/拉流 |
| ZLMediaKit | 8080 | TCP | HTTP API / HTTP-FLV / HLS |
| ZLMediaKit | 8443 | TCP | HTTPS |
| ZLMediaKit | 8554 | TCP | RTSP 播放 |
| ZLMediaKit | 10000 | TCP/UDP | RTP 收发 |
| ZLMediaKit | 8000 | UDP | WebRTC |
| ZLMediaKit | 9000 | UDP | SRT |

## 后端服务连接配置

### 配置文件说明

本项目有两个环境变量文件：
1. **根目录 `.env`**：用于 Docker Compose 服务配置（PostgreSQL、Redis、ZLMediaKit）
2. **`backend/.env`**：用于后端应用配置

**重要**：两个文件中的数据库和 Redis 配置必须保持一致！

### 宿主机开发模式（推荐）

后端服务在宿主机运行，连接 Docker 容器中的基础设施。

在 `.env` 文件中使用：
```bash
DATABASE_URL=postgresql+asyncpg://crowd_user:crowd_pass_dev@localhost:5432/crowd_counting
REDIS_URL=redis://localhost:6379/0
ZLM_BASE_URL=http://localhost:8080
```

### 容器化部署模式

后端服务也在 Docker 中运行，使用服务名连接。

在 `.env` 文件中使用：
```bash
DATABASE_URL=postgresql+asyncpg://crowd_user:crowd_pass_dev@postgres:5432/crowd_counting
REDIS_URL=redis://redis:6379/0
ZLM_BASE_URL=http://zlmediakit:80
```

## 数据持久化

### 命名卷（自动管理）
- `postgres-data`: PostgreSQL 数据
- `redis-data`: Redis 数据

### 绑定挂载（本地目录）
- `zlm-config/`: ZLMediaKit 配置文件
- `zlm-logs/`: ZLMediaKit 日志文件
- `zlm-media/`: ZLMediaKit 媒体文件（HLS 切片等）
- `uploads/`: 上传的视频文件

**注意**：删除容器不会删除命名卷中的数据，除非使用 `docker-compose down -v`。

## 日志管理

### 查看实时日志
```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f zlmediakit
docker-compose logs -f postgres
docker-compose logs -f redis
```

### ZLMediaKit 日志文件
```bash
# 查看日志文件
tail -f zlm-logs/zlm.log

# 清理日志（如果文件过大）
> zlm-logs/zlm.log
```

**重要提醒**：
- ZLMediaKit 日志会持续增长，长期运行可能占用大量磁盘空间
- 建议定期清理日志文件，或配置日志轮转
- 可以使用 `du -sh zlm-logs/` 查看日志目录大小

## 配置修改

### 修改 ZLMediaKit 配置
1. 编辑 `zlm-config/config.ini`
2. 重启 ZLMediaKit 服务：
   ```bash
   docker-compose restart zlmediakit
   ```

### 修改环境变量
1. 编辑 `.env` 文件
2. 重启相关服务：
   ```bash
   docker-compose up -d
   ```

## 常见问题

### 端口冲突

如果本地已有服务占用端口（如 PostgreSQL 5432、Redis 6379），可以修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "15432:5432"  # 将宿主机端口改为 15432
```

然后相应修改 `.env` 中的连接地址。

### 权限问题

如果遇到目录权限问题，可以手动创建目录并设置权限：

```bash
mkdir -p zlm-config zlm-logs zlm-media uploads
chmod 755 zlm-config zlm-logs zlm-media uploads
```

### ZLMediaKit 配置未生效

确保 `zlm-config/config.ini` 中的 `[api] secret` 与 `.env` 中的 `ZLM_SECRET` 一致，然后重启服务：

```bash
docker-compose restart zlmediakit
```

### 数据库连接失败

检查 PostgreSQL 是否已启动并健康：

```bash
docker-compose ps postgres
docker-compose logs postgres
```

等待健康检查通过后再连接。

## 资源限制（可选）

如果需要限制容器资源使用，可以在 `docker-compose.yml` 中添加：

```yaml
services:
  postgres:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 生产环境注意事项

**警告**：此配置仅用于开发环境，生产环境需要额外考虑：

1. **安全性**：
   - 修改所有默认密码和密钥
   - 关闭不必要的端口暴露（使用 `expose` 而非 `ports`）
   - 启用 TLS/SSL
   - 配置防火墙规则

2. **稳定性**：
   - 固定镜像版本（避免使用 `latest` 或 `master`）
   - 配置资源限制
   - 配置重启策略
   - 配置健康检查

3. **可观测性**：
   - 集成日志收集系统（如 ELK、Loki）
   - 配置监控和告警（如 Prometheus、Grafana）
   - 配置链路追踪

4. **数据安全**：
   - 配置数据库备份策略
   - 使用外部存储卷
   - 配置数据加密

## 测试清单

启动服务后，建议执行以下测试：

### 基础连接测试
- [ ] PostgreSQL 连接测试：`docker-compose exec postgres psql -U crowd_user -d crowd_counting -c "SELECT 1"`
- [ ] Redis 连接测试：`docker-compose exec redis redis-cli ping`
- [ ] ZLMediaKit API 测试（使用正确的 secret）：`curl "http://localhost:8080/index/api/getServerConfig?secret=<ZLM_SECRET>"`

### 鉴权测试（失败用例）
- [ ] ZLMediaKit API 鉴权测试（使用错误的 secret 应失败）：
  ```bash
  curl "http://localhost:8080/index/api/getServerConfig?secret=wrong_secret"
  # 应返回鉴权失败错误
  ```

### 配置同步测试
- [ ] 修改 zlm-config/config.ini 中的 secret，不重启容器，验证 API 仍使用旧值
- [ ] 重启容器后验证新配置生效：`docker-compose restart zlmediakit`

### 数据持久化测试（回归点）
- [ ] 在 PostgreSQL 中创建测试数据：
  ```bash
  docker-compose exec postgres psql -U crowd_user -d crowd_counting -c "CREATE TABLE test (id INT);"
  ```
- [ ] 重启容器：`docker-compose restart postgres`
- [ ] 验证数据仍存在：
  ```bash
  docker-compose exec postgres psql -U crowd_user -d crowd_counting -c "\dt"
  ```

### 日志和目录测试
- [ ] 检查 zlm-logs 目录是否生成日志文件
- [ ] 检查 zlm-media 目录是否可写入

### 端口占用测试（失败用例）
- [ ] 模拟端口占用：
  ```bash
  # 先启动一个占用 8080 端口的服务
  python3 -m http.server 8080
  # 然后尝试启动 Docker Compose，应报错
  docker-compose up -d
  ```

### 连接配置切换测试（回归点）
- [ ] 测试宿主机模式连接（DATABASE_URL=postgresql+asyncpg://...@localhost:5432/...）
- [ ] 测试容器化模式连接（DATABASE_URL=postgresql+asyncpg://...@postgres:5432/...）

### ZLMediaKit 功能测试
- [ ] 验证 streamNoneReaderDelayMS=60000 配置：
  ```bash
  # 查看配置
  curl "http://localhost:8080/index/api/getServerConfig?secret=<ZLM_SECRET>" | grep streamNoneReaderDelayMS
  ```

## 参考资料

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [ZLMediaKit 文档](https://github.com/ZLMediaKit/ZLMediaKit/wiki)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Redis 文档](https://redis.io/documentation)
