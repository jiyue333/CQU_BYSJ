## 当前服务与职责（方案 F）

### 1) 前端 Web（浏览器）

- 选择输入源：本地视频文件、浏览器摄像头、RTSP 地址
- 发起开始/停止/删除
- 播放渲染流（WebRTC 优先，HTTP-FLV/HLS 兜底）
- 展示实时统计（总人数、状态）

### 2) 控制面后端（Stream Manager）

- 统一入口：创建/启动/停止/删除流
- 编排 ZLMediaKit：
  - RTSP：调用 ZLM 代理拉流
  - 文件：调用 ZLM ffmpeg 转流
  - 摄像头：生成 WebRTC ingest 会话
- 默认启动渲染服务：通过 Redis PubSub 向 `render:control` 发布 START/STOP
- play_url/webrtc_url 返回渲染流 `{stream_id}_heatmap`
- 监听 Redis Streams，推送结果与状态到 WebSocket

### 3) 渲染服务（RenderWorker）

- 订阅 `render:control`，启动/停止渲染循环
- ffmpeg 拉取原始 RTSP → YOLO 推理 → 热力图叠加 → ffmpeg 推 RTMP
- 结果写入 `result:{stream_id}` 与 `latest_result:{stream_id}`
- 状态写入 `inference:status`（供 StatusPushService 复用）

### 4) 媒体网关（ZLMediaKit）

- 接入原始视频流
- 对外提供 WebRTC/HTTP-FLV/HLS 播放
- 接收渲染服务推回的 RTMP 流，形成 `{stream_id}_heatmap`

### 5) Redis / PostgreSQL

- Redis: render control / results / status
- PostgreSQL: stream/config/history 数据存储

---

## 数据链路（简化版）

```
前端 create/start
  → 后端 Stream Manager
    → ZLM 生成原始流
    → 发布 render:control START
      → RenderWorker 拉 RTSP + 推 RTMP
        → ZLM 生成渲染流 {stream_id}_heatmap
前端播放渲染流
后端通过 Redis Streams 推送结果/状态
```

## 关键约定

- 渲染流命名：`{stream_id}_heatmap`
- 外部播放地址由 `ZLM_EXTERNAL_URL` 生成
- 容器内拉/推流使用 `ZLM_BASE_URL` 推导 host，并补充 `vhost=__defaultVhost__`
