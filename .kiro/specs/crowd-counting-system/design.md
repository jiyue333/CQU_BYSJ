# 设计文档

## 概述

基于 YOLO 的实时人流计数与密度分析系统。采用**播放帧率与推理频率解耦**的设计：
- 视频播放：前端流畅播放
- 推理频率：后端每秒抽取 1-3 帧进行 YOLO 推理
- 热力图更新：按秒刷新，平滑过渡叠加在原始画面上

**核心设计原则**：所有视频源（本地文件、浏览器摄像头、RTSP 摄像头）统一抽象为 `stream_id`，前端只认 `play_url`，推理只认 `getSnap(stream_id)`。

## 架构

### 整体数据链路

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          浏览器前端 Web (Vue 3)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  视频源选择                                                          │   │
│  │  - 本地视频文件（选择并上传）                                         │   │
│  │  - 浏览器摄像头（授权采集）                                           │   │
│  │  - RTSP 摄像头地址（用户输入）                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ 开始/停止 按钮   │  │ 视频播放器      │  │ 热力图叠加层    │            │
│  │                 │  │ (play_url)      │  │ (Canvas)        │            │
│  └────────┬────────┘  └────────▲────────┘  └────────▲────────┘            │
└───────────┼────────────────────┼────────────────────┼──────────────────────┘
            │(1) REST API        │(4) play_url       │(6) WebSocket 推送
            │ create/start/stop  │                    │ /ws/result/{stream_id}
            ▼                    │                    │
┌───────────────────────────────────────────────────────────────────────────┐
│                    控制面后端 Stream Manager (FastAPI)                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  REST API：流管理（创建/开始/停止/删除）                              │  │
│  │  WebSocket：结果推送（/ws/result/{stream_id}）                        │  │
│  │  编排网关：根据输入源类型执行不同动作                                 │  │
│  │  生命周期管理：维护 stream_id 状态 (starting/running/stopped/error)   │  │
│  │  通知推理：running 时通知推理服务 START，停止时通知 STOP              │  │
│  │  结果推送：消费 Redis Streams，转发到 WebSocket 客户端                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────┬───────────────────────┬─────────────┘
           │(2) 编排网关              │(5) START/STOP         │ 订阅 Redis
           ▼                          ▼                       │ 
           
┌──────────────────────────────────┐  ┌──────────────────────────────┐
│      媒体网关 (开源组件)          │  │      推理服务 Worker          │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────┐  │
│  │ RTSP pull / 文件转流 /     │  │◄─│  │ 循环调 getSnap(stream_id)│  │
│  │ 浏览器摄像头 ingest        │  │(3)│  │ 只保最新，忙就丢        │  │
│  │                            │  │  │  │ YOLO 推理 + 统计        │  │
│  │ 对外：播放接口 + getSnap   │  │  │  │ 结果写入 Redis Streams  │──┘
│  └────────────────────────────┘  │  │  └────────────────────────┘  │
└──────────────────────────────────┘  └──────────────────────────────┘
```

### 三类输入的统一处理

| 输入类型 | 用户操作 | 后端编排 | 网关动作 | 最终产物 |
|---------|---------|---------|---------|---------|
| 本地视频文件 | 选择文件上传 | 存储文件 → 通知网关转流 | 文件转为可播放流 | stream_id + play_url |
| 浏览器摄像头 | 授权摄像头 | 下发发布会话信息 | 接收浏览器 publish | stream_id + play_url |
| RTSP 摄像头 | 输入 RTSP 地址 | 调用网关 API 拉流 | pull RTSP 并转码 | stream_id + play_url |

**统一关键**：所有源最终都在网关里变成同一个抽象 `stream_id`，浏览器播放用它，推理抓 snap 也用它。

## 组件与接口

### 1. Stream Manager（控制面后端）

**职责**：统一入口，编排网关，管理视频流生命周期，推送检测结果

**REST API 接口**：

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/streams` | POST | 创建视频流（返回 stream_id） |
| `/api/streams/{stream_id}/start` | POST | 开始播放 |
| `/api/streams/{stream_id}/stop` | POST | 停止播放 |
| `/api/streams/{stream_id}` | GET | 获取流状态和 play_url |
| `/api/streams/{stream_id}` | DELETE | 删除视频流 |
| `/api/streams` | GET | 获取所有视频流列表 |
| `/api/streams/{stream_id}/latest-result` | GET | 获取最新检测结果（用于 WebSocket 重连恢复） |

**WebSocket 接口**：

| 接口 | 描述 |
|------|------|
| `/ws/result/{stream_id}` | 订阅某路视频的检测结果推送 |
| `/ws/status` | 订阅所有视频流的状态变更 |

**WebSocket 推送服务设计**：

#### 心跳机制

为避免"靠 receive_text 挂起保活"导致的连接超时问题，采用**应用层心跳**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `WS_HEARTBEAT_INTERVAL` | 30 | 心跳间隔（秒） |
| `WS_HEARTBEAT_TIMEOUT` | 10 | 心跳响应超时（秒） |
| `WS_SLOW_CLIENT_THRESHOLD` | 5 | 慢客户端消息积压阈值 |

**心跳协议**：
- 前端每 30 秒发送 `{"type": "ping", "ts": 1234567890}`
- 后端回复 `{"type": "pong", "ts": 1234567890}`
- 超过 40 秒无心跳，后端主动断开连接

```
ResultPushService: Redis Streams → WebSocket 桥接服务（含心跳和慢客户端处理）
├── 数据结构: connections[stream_id] → websockets, last_heartbeat[ws], pending_messages[ws]
├── subscribe_result(ws, stream_id):
│   ├── 接受连接 → 注册到 connections → 通知 lifecycle_manager
│   ├── 循环等待消息（带心跳超时检测）
│   │   ├── 收到 ping → 更新心跳时间 → 回复 pong
│   │   └── 超时 → 断开连接
│   └── finally: 清理连接 → 通知 lifecycle_manager
├── start_redis_listener():
│   ├── 循环阻塞读取 Redis Streams (result:{stream_id})
│   ├── 遍历消息 → 推送给订阅的 WebSocket
│   └── 慢客户端检测: pending >= 阈值 → 丢弃消息
└── recover_from_disconnect(stream_id, last_id):
    └── 从 Redis xrange 恢复遗漏消息（排除已读，限制数量）

WebSocket 端点: /ws/result/{stream_id} → subscribe_result()
```

**数据流**：
```
推理服务 → Redis Streams (result:{stream_id}) → ResultPushService → WebSocket → 前端
```

**创建流请求示例**：
```json
// 本地视频文件
{
  "type": "file",
  "name": "监控视频1",
  "file_id": "uploaded_file_123"
}

// 浏览器摄像头
{
  "type": "webcam",
  "name": "本地摄像头"
}

// RTSP 摄像头
{
  "type": "rtsp",
  "name": "入口摄像头",
  "url": "rtsp://192.168.1.100:554/stream"
}
```

**创建流响应**：
```json
{
  "stream_id": "stream_abc123",
  "status": "starting",
  "play_url": null,
  "publish_info": null  // 仅 webcam 类型返回发布会话信息
}
```

#### publish_info 字段定义（webcam ingest 必需）

当 `type: "webcam"` 时，响应中的 `publish_info` 包含浏览器推流所需的全部信息：

```json
{
  "stream_id": "stream_abc123",
  "status": "starting",
  "play_url": null,
  "publish_info": {
    "whip_url": "https://gateway.example.com/whip/stream_abc123",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_at": 1735689600,
    "ice_servers": [
      {
        "urls": ["stun:stun.example.com:3478"]
      },
      {
        "urls": ["turn:turn.example.com:3478"],
        "username": "user",
        "credential": "pass"
      }
    ]
  }
}
```

**字段说明**：

| 字段 | 类型 | 描述 |
|------|------|------|
| `whip_url` | string | WHIP 推流地址（WebRTC HTTP Ingest Protocol） |
| `token` | string | 短期有效 token（避免公网裸推，有效期 5 分钟） |
| `expires_at` | int | token 过期时间戳（epoch） |
| `ice_servers` | array | STUN/TURN 服务器列表（WebRTC ICE 协商用） |

**前端推流流程**：
```
publishWebcam(publishInfo): 浏览器摄像头 WHIP 推流
├── 创建 RTCPeerConnection (使用 ice_servers)
├── 获取摄像头流 → 添加 track 到 pc
├── 创建 offer → 设置 localDescription
├── POST offer.sdp 到 whip_url (带 token)
└── 收到 answer → 设置 remoteDescription
```

#### 文件转流语义

**核心问题**：文件转流是 VOD 播放还是按实时节奏"像直播一样跑"？

**本期策略**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `realtime` | `true` | 按实时节奏输出（FFmpeg `-re` 模式），getSnap 时间轴与播放同步 |
| `allow_seek` | `false` | 本期不支持 seek，简化推理端 timestamp 语义 |
| `loop` | `true` | 文件播放完毕后循环播放 |

**文件生命周期**：

| 阶段 | 策略 |
|------|------|
| 上传 | 存储到本地磁盘或对象存储（如 MinIO） |
| 保留 | 上传后保留 **7 天**（可配置） |
| 清理 | 定时任务扫描过期文件并删除 |
| 关联 | 文件删除时，关联的 stream 自动进入 ERROR 状态 |

**文件上传配置**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FILE_MAX_SIZE_MB` | 500 | 单文件最大大小（MB） |
| `FILE_RETENTION_DAYS` | 7 | 文件保留天数 |
| `FILE_ALLOWED_EXTENSIONS` | mp4, avi, mkv, mov, webm, flv | 支持的视频格式 |

**支持的视频格式**：

| 格式 | 容器 | 说明 |
|------|------|------|
| MP4 | MPEG-4 Part 14 | 推荐格式，兼容性最好 |
| AVI | Audio Video Interleave | Windows 常用格式 |
| MKV | Matroska | 开源容器，支持多轨道 |
| MOV | QuickTime | Apple 格式 |
| WebM | WebM | Web 优化格式 |
| FLV | Flash Video | 流媒体常用格式 |

```
FileStorageService: 文件存储服务
├── 配置: 存储路径=/data/uploads, 保留天数=7, 最大500MB
├── upload(file) → 生成 uuid → 保存文件 → 返回 file_id
└── cleanup_expired() → 扫描过期文件 → 删除
```

**流状态枚举**：
```python
class StreamStatus(str, Enum):
    STARTING = "starting"    # 正在初始化
    RUNNING = "running"      # 正常运行
    STOPPED = "stopped"      # 已停止
    ERROR = "error"          # 错误
    COOLDOWN = "cooldown"    # 冷却中（重连失败后）
```

### 流生命周期管理

#### start/stop 语义定义

| 操作 | 语义 | 行为 |
|------|------|------|
| **start** | 启动播放 + 推理 | 1. 网关产生可播放流（play_url 可用）<br>2. 默认开启推理（可通过 `enable_infer=false` 关闭）<br>3. 状态变为 RUNNING |
| **stop** | 停止播放 + 推理 | 1. 停止播放流（断开 publish/pull）<br>2. **强制停止推理**（无论 enable_infer 设置）<br>3. 状态变为 STOPPED |

**start 请求参数**：
```json
{
  "enable_infer": true    // 可选，默认 true，是否开启推理
}
```

#### 资源止损机制（无人观看自动停止）

为避免"没人看但推理在空耗"，采用**会话心跳 + TTL**机制：

```
StreamLifecycleManager: 流生命周期管理器（无人观看自动停止）
├── 配置: 心跳间隔=10s, 超时=30s, 自动停止延迟=60s
├── 数据结构: viewer_count[stream_id], last_heartbeat[stream_id]
├── on_viewer_join(stream_id) → 计数+1 → 更新心跳时间
├── on_viewer_leave(stream_id) → 计数-1 → 若为0则启动延迟停止
├── on_heartbeat(stream_id) → 更新心跳时间
└── _delayed_stop(stream_id) → 等待60s → 若仍无观看者则停止流
```

#### 状态转换图

```
                    create
                      │
                      ▼
    ┌─────────────────────────────────┐
    │           STARTING              │
    │  (网关初始化中，play_url 未就绪)  │
    └─────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │ 成功              │ 失败
        ▼                   ▼
┌───────────────┐    ┌───────────────┐
│    RUNNING    │    │     ERROR     │
│ (播放+推理中)  │    │  (初始化失败)  │
└───────┬───────┘    └───────────────┘
        │
        │ stop / 无人观看 / 连续失败
        ▼
┌───────────────┐    ┌───────────────┐
│    STOPPED    │◄───│   COOLDOWN    │
│   (已停止)    │    │ (重连冷却中)   │
└───────────────┘    └───────┬───────┘
                             │ 冷却结束
                             │ 自动重试
                             ▼
                      (回到 STARTING)
```

### 2. Media Gateway（媒体网关）- ZLMediaKit

**本期选型**：ZLMediaKit（详见 `网关选择.md`）

**职责**：视频流接入、转码、分发、截图

**核心能力**：
- RTSP pull：拉取 RTSP 流并转码（`addStreamProxy`）
- 文件转流：将视频文件转为实时流（`addFFmpegSource`）
- WebRTC ingest：接收浏览器摄像头推流（WHIP 协议）
- 播放接口：提供 WebRTC/HLS/FLV 播放
- 截图接口：`getSnap(stream_id)` 返回 JPEG bytes（**开箱即用**）

#### 	 Docker 部署配置

**Docker Compose 配置**：

```yaml
services:
  zlmediakit:
    image: zlmediakit/zlmediakit:master
    container_name: zlmediakit
    restart: unless-stopped
    ports:
      - "1935:1935"      # RTMP
      - "8080:80"        # HTTP API / HTTP-FLV / HLS
      - "8443:443"       # HTTPS
      - "8554:554"       # RTSP
      - "10000:10000"    # RTP TCP
      - "10000:10000/udp" # RTP UDP
      - "8000:8000/udp"  # WebRTC UDP
      - "9000:9000/udp"  # SRT
    volumes:
      - ./zlm-config:/opt/media/conf      # 配置文件
      - ./zlm-logs:/opt/media/log         # 日志
      - ./zlm-media:/opt/media/www        # 媒体文件（HLS 切片等）
      - ./uploads:/data/uploads           # 上传的视频文件
    environment:
      - TZ=Asia/Shanghai
    networks:
      - crowd-counting-net
```

**端口说明**：

| 端口 | 协议 | 用途 |
|------|------|------|
| 1935 | TCP | RTMP 推流/拉流 |
| 8080 (80) | TCP | HTTP API、HTTP-FLV、HLS 播放 |
| 8443 (443) | TCP | HTTPS |
| 8554 (554) | TCP | RTSP 播放 |
| 10000 | TCP/UDP | RTP 收发 |
| 8000 | UDP | WebRTC |
| 9000 | UDP | SRT |

**关键配置项**（config.ini）：

```ini
[api]
# API 密钥，Stream Manager 调用时需要
secret=your_api_secret_here

[general]
# 无人观看自动关闭流（秒），与 Stream Manager 的 AUTO_STOP_DELAY 配合
streamNoneReaderDelayMS=60000

[hls]
# HLS 切片时长（秒）
segDur=2
# HLS 切片数量
segNum=3

[rtsp]
# RTSP 拉流超时（秒）
timeoutSec=10
```

**环境变量配置**：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ZLM_BASE_URL` | `http://zlmediakit:80` | ZLMediaKit HTTP API 地址 |
| `ZLM_SECRET` | - | API 密钥（必须配置） |
| `ZLM_RTSP_PORT` | `554` | RTSP 端口 |
| `ZLM_HTTP_PORT` | `80` | HTTP 端口 |

#### GatewayAdapter 适配层

为了隔离网关差异，Stream Manager 内部定义 **GatewayAdapter** 抽象接口：

```
数据结构:
├── StreamInfo: stream_id, play_url, rtsp_url?, hls_url?
└── PublishInfo: whip_url, token, expires_at, ice_servers (摄像头推流用)

GatewayAdapter: 媒体网关抽象接口
├── create_rtsp_proxy(stream_id, rtsp_url, retry_count, timeout) → StreamInfo
├── create_file_stream(stream_id, file_path, realtime) → StreamInfo
├── create_webcam_ingest(stream_id) → (StreamInfo, PublishInfo)
├── delete_stream(stream_id) → bool
├── get_snapshot(stream_id, timeout, expire) → bytes?
└── get_stream_info(stream_id) → StreamInfo?
```

#### ZLMediaKit 适配实现

```
ZLMediaKitAdapter: ZLMediaKit 适配器实现
├── 配置: base_url, secret
├── create_rtsp_proxy(stream_id, rtsp_url, ...) 
│   └── 调用 addStreamProxy API → 返回 StreamInfo (flv/hls 播放地址)
└── get_snapshot(stream_id, timeout, expire)
    └── 调用 getSnap API → 返回 JPEG bytes
```

**接口（由 Stream Manager 通过 GatewayAdapter 调用）**：

| 抽象接口 | ZLMediaKit 实际 API | 描述 |
|---------|---------------------|------|
| `create_rtsp_proxy()` | `addStreamProxy` | 创建 RTSP 拉流代理 |
| `create_file_stream()` | `addFFmpegSource` | 文件转流（FFmpeg fork） |
| `create_webcam_ingest()` | WebRTC WHIP | 浏览器摄像头推流 |
| `delete_stream()` | `delStreamProxy` / `close_streams` | 删除流 |
| `get_snapshot()` | `getSnap` | 获取快照（JPEG） |
| `get_stream_info()` | `getMediaList` | 获取流信息 |

### 3. Inference Worker（推理服务）

**职责**：接收 START/STOP 指令，按频率抓帧推理

**设计要点**：
- 收到 `START(stream_id, fps)` 后开始循环
- 调用网关 `getSnap(stream_id)` 获取 JPEG bytes
- 只保最新帧，忙就丢（背压策略）
- 推理结果通过 Redis Streams 推送

#### getSnap 超时与退避策略

**关键配置**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SNAP_TIMEOUT_SEC` | 2.0 | HTTP 请求超时（秒） |
| `SNAP_MAX_FAILURES` | 5 | 连续失败阈值，超过后进入 COOLDOWN |
| `SNAP_BACKOFF_BASE` | 1.0 | 退避基数（秒） |
| `SNAP_BACKOFF_MAX` | 30.0 | 最大退避时间（秒） |
| `COOLDOWN_DURATION` | 60 | COOLDOWN 持续时间（秒） |

**退避算法**：指数退避 + 抖动
```python
def calculate_backoff(failure_count: int) -> float:
    """计算退避时间：min(base * 2^n + jitter, max)"""
    backoff = min(
        SNAP_BACKOFF_BASE * (2 ** failure_count) + random.uniform(0, 1),
        SNAP_BACKOFF_MAX
    )
    return backoff
```

```
InferenceWorker: 推理服务（含超时/退避/状态上报）
├── 数据结构: model(YOLO), active_streams, failure_counts, stream_health
├── start_stream(stream_id, fps): 幂等启动推理线程
├── stop_stream(stream_id): 幂等停止
├── _inference_loop(stream_id, fps):
│   ├── 循环: 获取快照 → 推理 → 发布结果
│   ├── 成功: 重置失败计数 → 更新健康状态为 healthy
│   ├── 失败: 计数+1 → ≥3次则 degraded → ≥5次则进入 COOLDOWN
│   └── 频率控制: 考虑退避时间
├── _handle_failure(stream_id, reason): 失败计数 + 健康状态更新
├── _enter_cooldown(stream_id): 通知 Stream Manager → 启动恢复定时器
├── _cooldown_recovery(stream_id): 等待60s → 重置计数 → 重启推理
├── _update_health(stream_id, status): 状态变更时通知 Stream Manager
├── _notify_stream_manager(...): 写入 Redis Streams (inference:status)
└── _infer(stream_id, jpeg_bytes): 解码图像 → YOLO 推理 → 返回 DetectionResult
```

#### 热力图 EMA 算法

**EMA（指数移动平均）公式**：

```
EMA_t = α × value_t + (1 - α) × EMA_{t-1}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `α (alpha)` | 0.3 | 平滑因子，越大越敏感，越小越平滑 |
| `grid_size` | 20 | 热力图网格大小（20×20） |

**实现细节**：

```
HeatmapGenerator: 热力图生成器（含 EMA 平滑）
├── 配置: grid_size=20, alpha=0.3
├── 数据结构: ema_grids[stream_id] → numpy 网格
├── generate(stream_id, detections, frame_width, frame_height):
│   ├── 1. 计算原始热力图: 遍历检测 → 中心点映射到网格 → 累加
│   ├── 2. 归一化: raw_grid / max
│   ├── 3. EMA 平滑: 首帧直接用 / 后续帧 α*raw + (1-α)*ema
│   └── 返回 ema_grid.tolist()
└── reset(stream_id): 清除 EMA 状态
```

#### ROI 密度计算算法

**多边形面积计算（Shoelace 公式）**：

```
Area = 0.5 × |Σ(x_i × y_{i+1} - x_{i+1} × y_i)|
```

**点在多边形内判断（射线法）**：

从点向右发射水平射线，计算与多边形边的交点数。奇数则在内部，偶数则在外部。

```
ROICalculator: ROI 区域计算器
├── polygon_area(points): Shoelace 公式计算多边形面积
│   └── Σ(x_i × y_{i+1} - x_{i+1} × y_i) / 2
├── point_in_polygon(point, polygon): 射线法判断点是否在多边形内
│   └── 从点向右发射射线 → 计算与边交点数 → 奇数在内/偶数在外
└── calculate_region_density(roi, detections, ...):
    ├── 1. 计算区域面积 (polygon_area)
    ├── 2. 统计区域内检测数 (point_in_polygon)
    ├── 3. 计算密度 = count / (area / 5000) → 归一化到 0-1
    └── 4. 根据阈值分类: LOW / MEDIUM / HIGH
```
```

### 4. 前端（Vue 3，略）

前端实现相对简单，主要组件：
- **VideoSourceSelector**：选择视频源类型，调用后端创建流
- **VideoPlayer**：根据 play_url 播放视频（WebRTC > HTTP-FLV > HLS 降级）
- **HeatmapOverlay**：Canvas 叠加热力图
- **WebSocketService**：订阅检测结果，支持断线重连（指数退避）

## 数据模型

### VideoStream（视频流）
```python
class VideoStream(BaseModel):
    stream_id: str                 # 唯一标识
    name: str                      # 显示名称
    type: StreamType               # file/webcam/rtsp
    status: StreamStatus           # starting/running/stopped/error/cooldown
    play_url: Optional[str]        # 播放地址（running 后才有）
    source_url: Optional[str]      # RTSP 地址（仅 rtsp 类型）
    file_id: Optional[str]         # 文件 ID（仅 file 类型）
    created_at: datetime
    updated_at: datetime

class StreamType(str, Enum):
    FILE = "file"
    WEBCAM = "webcam"
    RTSP = "rtsp"

class StreamStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    COOLDOWN = "cooldown"
```

### ROI（感兴趣区域）
```python
class ROI(BaseModel):
    id: str
    stream_id: str
    name: str                  # 如 "前区"、"中区"
    points: List[Point]        # 多边形顶点 [(x1,y1), (x2,y2), ...]
    density_thresholds: DensityThresholds

class Point(BaseModel):
    x: float
    y: float

class DensityThresholds(BaseModel):
    low: float = 0.3           # 低密度阈值
    medium: float = 0.6        # 中密度阈值
    high: float = 0.8          # 高密度阈值
```

### DetectionResult（检测结果）
```python
class DetectionResult(BaseModel):
    stream_id: str
    timestamp: float           # 检测时间戳（epoch）
    total_count: int           # 总人数
    detections: List[Detection]
    heatmap_grid: List[List[float]]  # 热力图网格 (如 20x20)
    region_stats: List[RegionStat]

class Detection(BaseModel):
    x: int
    y: int
    width: int
    height: int
    confidence: float

class RegionStat(BaseModel):
    region_id: str
    region_name: str
    count: int
    density: float
    level: DensityLevel        # LOW/MEDIUM/HIGH

class DensityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

### SystemConfig（系统配置）
```python
class SystemConfig(BaseModel):
    stream_id: str
    confidence_threshold: float = 0.5   # 检测置信度阈值
    inference_fps: int = 2              # 推理频率 1-3
    heatmap_grid_size: int = 20         # 热力图网格大小
    heatmap_decay: float = 0.3          # 热力图衰减因子（EMA alpha）

class GlobalConfig(BaseModel):
    """全局系统配置"""
    max_concurrent_streams: int = 10    # 最大并发流数
    file_max_size_mb: int = 500         # 单文件最大大小（MB）
    file_retention_days: int = 7        # 文件保留天数
    auto_stop_delay: int = 60           # 无观看者自动停止延迟（秒）
    cooldown_duration: int = 60         # COOLDOWN 持续时间（秒）
```

**多流并发限制**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_CONCURRENT_STREAMS` | 10 | 最大同时运行的流数量 |
| `MAX_STREAMS_PER_USER` | 5 | 单用户最大流数量（下一迭代） |

**资源限制策略**：
- 创建流时检查当前运行流数量
- 超过限制时返回 429 Too Many Requests
- 提示用户停止其他流或等待

### HistoryStat（历史统计）
```python
class HistoryStat(BaseModel):
    id: int
    stream_id: str
    timestamp: datetime
    total_count: int
    region_stats: List[RegionStat]
```

## Redis 数据结构

### 视频流状态（由 Stream Manager 维护）
```python
# Key: stream:{stream_id}
# Type: Hash
# TTL: 无（手动管理）
stream:{stream_id} = {
    "status": "running",
    "play_url": "https://gateway/play/stream_abc123",
    "type": "rtsp",
    "created_at": 1234567890,
    "health": "healthy",           # healthy/degraded/cooldown
    "viewer_count": 2,
    "last_heartbeat": 1234567890
}
```

### 最新检测结果（由推理服务写入）
```python
# Key: latest_result:{stream_id}
# Type: String (JSON)
# TTL: 10 秒
latest_result:{stream_id} = {
    "timestamp": 1234567890.123,
    "total_count": 15,
    "heatmap_grid": [[0.1, 0.2, ...], ...],
    "region_stats": [{"region_id": "front", "count": 5, "density": 0.3, "level": "low"}]
}
```

### Redis Streams（检测结果与状态上报）

**为什么选择 Streams 而不是 PubSub**：
- 消息持久化：断连不丢失
- 背压控制：MAXLEN 自动裁剪老数据
- 断点续传：通过 last_id 机制恢复
- 历史回溯：可查询最近 N 条消息

**Streams 配置**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `STREAM_RESULT_MAXLEN` | ~500 | 结果 Stream 最大长度（近似裁剪） |
| `STREAM_STATUS_MAXLEN` | ~1000 | 状态 Stream 最大长度（近似裁剪） |
| `STREAM_READ_BLOCK_MS` | 1000 | 阻塞读取超时（毫秒） |
| `STREAM_READ_COUNT` | 100 | 每次读取最大消息数 |
| `STREAM_RECOVER_COUNT` | 50 | 断点续传最大恢复消息数 |

```python
# 检测结果 Stream
# Key: result:{stream_id}
# MAXLEN: 100（自动背压）
result:{stream_id} = [
    {"id": "1234567890-0", "data": '{"timestamp": 1234567890.123, "total_count": 15, ...}'},
    {"id": "1234567890-1", "data": '{"timestamp": 1234567891.456, "total_count": 16, ...}'},
    ...
]

# 推理状态 Stream
# Key: inference:status
# MAXLEN: 1000
inference:status = [
    {"id": "...", "data": '{"stream_id": "xxx", "event": "HEALTH_UPDATE", ...}'},
    ...
]
```

**写入示例**：
```python
# 推理服务写入检测结果（使用近似裁剪 ~）
redis.xadd(
    f"result:{stream_id}",
    {"data": json.dumps(result)},
    maxlen=STREAM_RESULT_MAXLEN,
    approximate=True  # 近似裁剪，减少 CPU 开销
)

# 推理服务写入状态上报
redis.xadd(
    "inference:status",
    {"data": json.dumps(status)},
    maxlen=STREAM_STATUS_MAXLEN,
    approximate=True
)
```

**消费示例**：
```python
# Stream Manager 消费检测结果
last_ids = {}  # stream_id -> last_message_id
streams_to_read = list(self.connections.keys())  # 快照避免迭代时修改
streams = {f"result:{sid}": last_ids.get(sid, "0") for sid in streams_to_read}
messages = await redis.xread(
    streams,
    block=STREAM_READ_BLOCK_MS,
    count=STREAM_READ_COUNT
)

for stream_key, entries in messages:
    # 安全解析 stream_id（避免 stream_id 包含 : 的问题）
    stream_id = stream_key.decode().removeprefix("result:")
    for msg_id, data in entries:
        last_ids[stream_id] = msg_id
        # 推送到 WebSocket...

# WebSocket 重连后恢复遗漏消息（排除已读消息，限制数量）
messages = await redis.xrange(
    f"result:{stream_id}",
    min=f"({last_id}",  # 使用 ( 前缀排除 last_id 本身
    max="+",
    count=STREAM_RECOVER_COUNT  # 限制恢复数量，避免大量数据
)
```

### PubSub 通道（控制指令）

> 控制指令保留 PubSub，因为是即时指令，不需要持久化。

```python
# 推理服务控制指令
channel: inference:control
```

### 控制指令协议（inference:control）

**消息格式**：
```json
{
  "cmd_id": "cmd_abc123",           // 唯一指令 ID（用于幂等和追踪）
  "stream_id": "stream_xyz",
  "action": "START",                // START / STOP
  "fps": 2,                         // 仅 START 时有效
  "timestamp": 1234567890.123
}
```

**幂等性保证**：

| 场景 | 处理方式 |
|------|----------|
| 重复 START | 检查 `active_streams[stream_id]`，已存在则忽略 |
| 重复 STOP | 设置 `active_streams[stream_id] = False`，多次安全 |
| 过期指令 | 检查 `timestamp`，超过 30 秒的指令忽略 |

```
InferenceControlHandler: 推理控制指令处理器（幂等）
├── 数据结构: processed_cmds (已处理 cmd_id 集合), cmd_ttl=60s
└── handle_command(message):
    ├── 幂等检查: cmd_id 已处理 → 跳过
    ├── 过期检查: timestamp > 30s → 跳过
    ├── 处理: START → start_stream / STOP → stop_stream
    └── 记录 cmd_id → 定期清理
```

### 推理状态上报协议（inference:status）

**消息格式**：
```json
{
  "stream_id": "stream_xyz",
  "event": "HEALTH_UPDATE",         // HEALTH_UPDATE / COOLDOWN / STARTED / STOPPED
  "data": {
    "health": "degraded",           // healthy / degraded / cooldown
    "reason": "consecutive_failures",
    "failure_count": 5,
    "cooldown_until": 1234567890
  },
  "timestamp": 1234567890.123
}
```

**Stream Manager 处理**：
```
handle_inference_status(message): Stream Manager 处理推理状态上报
├── HEALTH_UPDATE → 更新流健康状态
└── COOLDOWN → 更新流状态为 COOLDOWN → 通知前端
```

## 关键设计决策

### 决策1：视频源统一抽象
**选择**：所有视频源统一为 stream_id + play_url + getSnap(stream_id)

**理由**：
- 前端不需要感知不同视频源的差异
- 推理服务不需要关心视频来源
- 便于扩展新的视频源类型

### 决策2：媒体网关选型 - ZLMediaKit
**选择**：本期选定 **ZLMediaKit** 作为媒体网关

**理由**：
- **现成的截图 API**：`getSnap(url, timeout_sec, expire_sec)` 直接返回 JPEG，带超时和缓存
- **动态拉流代理**：`addStreamProxy` 支持重试、超时、按需生成、无人观看自动关闭
- **文件转流**：`addFFmpegSource` 支持任意协议/格式（FFmpeg fork）
- **多协议互转**：RTSP/WebRTC/HLS/HTTP-FLV 等覆盖面广

**备选方案**：
- MediaMTX：部署轻、单可执行文件，但需要自己补截图 API
- SRS：直播/RTC 平台能力强，但 RTSP 接入和截图需要额外旁路

### 决策3：控制面与数据面分离
**选择**：Stream Manager 只做编排，不处理媒体数据

**理由**：
- 职责清晰：控制面管理生命周期，数据面处理媒体
- 便于扩展：可以水平扩展推理服务
- 故障隔离：媒体问题不影响控制面

### 决策4：推理服务主动拉取
**选择**：推理服务主动调用 getSnap(stream_id) 而不是被动接收帧

**理由**：
- 天然背压：推理慢时自动丢帧，不会积压
- 简化架构：不需要帧队列和复杂的同步机制
- 灵活控制：可以动态调整抓帧频率

### 决策5：会话心跳 + TTL 资源止损
**选择**：前端每 30 秒发送心跳，无观看者 60 秒后自动停止流

**理由**：
- 避免"没人看但推理在空耗"的资源浪费
- 简单可靠：不依赖复杂的引用计数
- 容错性好：网络抖动不会立即停流

### 决策6：控制指令幂等性
**选择**：所有控制指令（START/STOP）设计为幂等操作

**理由**：
- 网络重传安全：重复指令不会产生副作用
- 简化错误处理：不需要复杂的状态同步
- 便于调试：可以安全地重放指令

## 错误处理

### 错误分类与处理策略

| 错误类型 | 可恢复性 | 处理策略 |
|----------|----------|----------|
| 网络超时 | 可恢复 | 重试 + 指数退避 |
| 连接断开 | 可恢复 | 自动重连 |
| 鉴权失败 | 不可恢复 | 立即停止，通知用户 |
| URL 错误 | 不可恢复 | 立即停止，通知用户 |
| 资源不存在 | 不可恢复 | 返回 ERROR 状态 |

### 视频源错误（由媒体网关 + Stream Manager 协同处理）

| 错误类型 | 处理策略 | 状态转换 |
|----------|----------|----------|
| RTSP 连接超时 | 网关自动重试（3次），Stream Manager 更新状态 | STARTING → RUNNING 或 ERROR |
| RTSP 断开 | 网关自动重连，连续失败后进入 COOLDOWN | RUNNING → COOLDOWN |
| RTSP 鉴权失败 | 立即停止，不重试 | → ERROR |
| 文件不存在 | 返回 ERROR 状态，通知用户 | → ERROR |
| 摄像头授权失败 | 返回 ERROR 状态，提示用户重新授权 | → ERROR |

### 推理错误（含超时/退避/COOLDOWN）

| 错误类型 | 处理策略 | 状态影响 |
|----------|----------|----------|
| getSnap 超时（单次） | 跳过本次，计入失败计数 | health: healthy → degraded |
| getSnap 连续失败（≥5次） | 进入 COOLDOWN，停止推理 | health: → cooldown |
| 模型推理异常 | 跳过该帧，记录日志 | 不影响 |
| Redis 连接失败 | 重试 3 次，失败后告警 | 不影响流状态 |

**COOLDOWN 恢复流程**：
```
COOLDOWN (60秒) → 自动重试 START → 成功: RUNNING / 失败: 延长 COOLDOWN
```

### 前端错误（略）

前端错误处理：WebSocket 断开自动重连（指数退避），视频播放失败显示错误提示。

## 测试策略

### 正确性属性

*正确性属性是系统在所有有效执行中都应保持为真的特征或行为。属性作为人类可读规范与机器可验证正确性保证之间的桥梁。*

**Property 1: 视频源统一抽象**
*For any* 视频源类型（file/webcam/rtsp），创建成功后都应返回有效的 stream_id
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

**Property 2: 置信度过滤**
*For any* 检测结果集合和置信度阈值，返回的所有检测结果的置信度都应 >= 阈值
**Validates: Requirements 2.4, 8.1**

**Property 3: 密度计算与等级分类**
*For any* ROI 区域和检测结果，密度值应等于区域内人数除以区域面积，且密度等级应根据阈值正确分类
**Validates: Requirements 3.3, 3.4**

**Property 4: ROI 配置持久化**
*For any* ROI 配置，保存后读取应返回等价的配置对象
**Validates: Requirements 3.1**

**Property 5: 热力图生成**
*For any* 检测位置集合，热力图网格中对应位置的值应反映检测密度
**Validates: Requirements 4.1**

**Property 6: 历史数据时间范围查询**
*For any* 时间范围查询，返回的所有数据的时间戳都应在指定范围内
**Validates: Requirements 6.1, 6.2**

**Property 7: 配置范围约束**
*For any* 推理频率配置，值应在 1-3 范围内；配置持久化后重启应保持
**Validates: Requirements 8.3, 8.4**

**Property 8: 流状态一致性**
*For any* stream_id，状态转换应遵循：starting → running/error，running → stopped/error
**Validates: Requirements 9.4**

### 单元测试
- 检测结果解析
- 热力图生成算法
- 区域密度计算
- EMA 平滑算法

### 集成测试
- 视频采集 → Redis → 推理 → 结果推送
- WebSocket 连接与消息推送
- REST API 接口

### 端到端测试
- 完整视频流处理链路
- 多路视频并发
- 断线重连场景

---

## 模型相关（当前迭代跳过）

> **注意**：当前迭代优先跑通工程功能，模型相关难点后续迭代处理。

**当前策略**：
- 使用 YOLOv8n 预训练模型（Ultralytics 官方）
- 检测目标：person 类别
- 置信度阈值：0.5（可配置）

**后续迭代待处理**：
1. 模型选型与结构能力优化
2. 数据集与标注体系建设
3. 训练与鲁棒性优化
4. 推理性能与部署加速

详见 `plan.md` 中的模型难点章节。
