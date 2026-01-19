## 主要功能

- **多格式输入**：支持视频文件上传和摄像头实时传入
- **实时人数统计**：基于 YOLO 检测，实时显示画面中的总人数
- **区域密度分析**：用户可自定义划分区域（如前/中/后区），分别统计各区域人数与密度
- **密度热力图**：以热力图形式可视化人流密度分布，直观展示拥挤区域
- **高密度预警**：当区域密度超过设定阈值时，自动触发预警提示
- **历史数据查询**：记录历史人流数据，支持按时间段查询与趋势分析
- **数据导出**：支持将统计数据导出为 CSV/Excel 格式

---

## 接口设计

### 通用约定

- **基础路径**：`/api`
- **WebSocket 路径**：`/api/ws`
- **数据格式**：JSON（文件上传为 `multipart/form-data`）
- **字段命名**：`snake_case`
- **统一响应格式**：
  ```json
  {
    "code": 0,
    "data": { ... },
    "msg": "success"
  }
  ```
  - `code`: 0 成功，非 0 失败
  - `data`: 业务数据
  - `msg`: 提示信息

---

### 1. 数据源管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sources/upload` | 上传视频文件 |
| POST | `/api/sources/stream` | 接入摄像头/推流 |
| GET | `/api/sources` | 获取数据源列表 |
| DELETE | `/api/sources/:id` | 删除数据源 |

#### POST /api/sources/upload
上传视频文件

- **请求**：`multipart/form-data`
  - `file`: 视频文件
- **响应**：
  ```json
  { "source_id": "uuid", "name": "video.mp4", "source_type": "file" }
  ```

#### POST /api/sources/stream
接入摄像头/推流地址

- **请求**：
  ```json
  { "url": "rtsp://...", "name": "摄像头1" }
  ```
- **响应**：
  ```json
  { "source_id": "uuid", "name": "摄像头1", "source_type": "stream" }
  ```

#### GET /api/sources
获取数据源列表

- **响应**：
  ```json
  {
    "sources": [
      { "source_id": "uuid", "name": "video.mp4", "source_type": "file", "status": "ready", "created_at": "2025-01-19T10:00:00Z" }
    ]
  }
  ```

---

### 2. 分析控制

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analysis/start` | 开始分析 |
| POST | `/api/analysis/stop` | 停止分析 |
| GET | `/api/analysis/status` | 查询分析状态 |

#### POST /api/analysis/start
开始分析

- **请求**：
  ```json
  {
    "source_id": "uuid",
    "regions": [
      { "name": "前区", "points": [[0,0], [100,0], [100,100], [0,100]], "color": "#FF5733" }
    ],
    "threshold": {
      "total_warning": 50,
      "total_critical": 100,
      "default_region_warning": 20,
      "default_region_critical": 50
    }
  }
  ```
- **响应**：
  ```json
  { "source_id": "uuid", "status": "running" }
  ```

#### POST /api/analysis/stop
停止分析

- **请求**：
  ```json
  { "source_id": "uuid" }
  ```
- **响应**：
  ```json
  { "ok": true }
  ```

#### GET /api/analysis/status?source_id=...
查询分析状态

- **响应**：
  ```json
  {
    "source_id": "uuid",
    "status": "running",
    "start_time": "2025-01-19T10:00:00Z",
    "progress": 0.5
  }
  ```

---

### 3. 实时推送（WebSocket）

| 路径 | 说明 |
|------|------|
| `/api/ws/realtime?source_id=...` | 实时推理数据推送 |
| `/api/ws/alerts?source_id=...` | 预警消息推送 |

#### WS /api/ws/realtime
实时推理数据推送（视频帧已叠加热力图）

- **消息格式**：
  ```json
  {
    "ts": "2025-01-19T10:00:00.123Z",
    "frame": "base64...",
    "total_count": 150,
    "total_density": 0.005,
    "regions": [
      { "name": "前区", "count": 50, "density": 0.008 },
      { "name": "中区", "count": 60, "density": 0.006 },
      { "name": "后区", "count": 40, "density": 0.004 }
    ],
    "crowd_index": 0.75,
    "entry_speed": 12
  }
  ```

#### WS /api/ws/alerts
预警消息推送

- **消息格式**：
  ```json
  {
    "alert_id": "uuid",
    "alert_type": "region_count",
    "level": "critical",
    "region_name": "前区",
    "current_value": 65,
    "threshold": 50,
    "timestamp": "2025-01-19T10:00:00Z",
    "message": "前区人数超过阈值"
  }
  ```

---

### 4. 预警配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/alerts/threshold` | 获取当前阈值配置 |
| POST | `/api/alerts/threshold` | 更新阈值配置 |

#### GET /api/alerts/threshold?source_id=...
获取当前阈值配置

- **响应**：
  ```json
  {
    "total_warning_threshold": 50,
    "total_critical_threshold": 100,
    "default_region_warning": 20,
    "default_region_critical": 50,
    "region_thresholds": {
      "前区": { "warning": 20, "critical": 40 }
    },
    "cooldown_seconds": 30
  }
  ```

#### POST /api/alerts/threshold
更新阈值配置

- **请求**：
  ```json
  {
    "source_id": "uuid",
    "total_warning_threshold": 60,
    "total_critical_threshold": 120,
    "region_thresholds": {
      "前区": { "warning": 25, "critical": 50 }
    }
  }
  ```
- **响应**：
  ```json
  { "ok": true }
  ```

---

### 5. 区域配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/regions` | 获取区域列表 |
| POST | `/api/regions` | 创建区域 |
| PUT | `/api/regions/:id` | 更新区域 |
| DELETE | `/api/regions/:id` | 删除区域 |

#### GET /api/regions?source_id=...
获取区域列表

- **响应**：
  ```json
  {
    "regions": [
      { "region_id": "uuid", "name": "前区", "points": [[0,0], [100,0], [100,100], [0,100]], "color": "#FF5733" }
    ]
  }
  ```

#### POST /api/regions
创建区域

- **请求**：
  ```json
  {
    "source_id": "uuid",
    "name": "前区",
    "points": [[0,0], [100,0], [100,100], [0,100]],
    "color": "#FF5733"
  }
  ```
- **响应**：
  ```json
  { "region_id": "uuid", "name": "前区" }
  ```

---

### 6. 历史与导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history` | 历史趋势查询 |
| GET | `/api/export` | 导出统计数据 |
| POST | `/api/clip/export` | 导出视频片段 |
| POST | `/api/frame/snapshot` | 截图保存 |

#### GET /api/history?source_id=...&from=...&to=...&interval=...
历史趋势查询

- **参数**：
  - `source_id`: 数据源 ID
  - `from`: 开始时间（ISO 8601）
  - `to`: 结束时间（ISO 8601）
  - `interval`: 聚合间隔（1m / 5m / 1h）
- **响应**：
  ```json
  {
    "series": [
      { "time": "2025-01-19T10:00:00Z", "total_count": 120, "total_density": 0.005 },
      { "time": "2025-01-19T10:01:00Z", "total_count": 135, "total_density": 0.006 }
    ]
  }
  ```

#### GET /api/export?source_id=...&from=...&to=...&format=csv|xlsx
导出统计数据

- **响应**：
  ```json
  { "url": "/downloads/export_20250119.csv" }
  ```

#### POST /api/clip/export
导出视频片段

- **请求**：
  ```json
  {
    "source_id": "uuid",
    "from": "2025-01-19T10:00:00Z",
    "to": "2025-01-19T10:05:00Z"
  }
  ```
- **响应**：
  ```json
  { "url": "/downloads/clip_20250119.mp4" }
  ```

#### POST /api/frame/snapshot
截图保存

- **请求**：
  ```json
  { "source_id": "uuid" }
  ```
- **响应**：
  ```json
  { "url": "/downloads/snapshot_20250119.jpg" }
  ```

---

### 7. 系统状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 获取系统运行状态 |

#### GET /api/status
获取系统运行状态

- **响应**：
  ```json
  {
    "status": "running",
    "uptime": 3600,
    "active_sources": 1,
    "gpu_usage": 0.45,
    "cpu_usage": 0.30
  }
  ```

---

## 数据库设计

