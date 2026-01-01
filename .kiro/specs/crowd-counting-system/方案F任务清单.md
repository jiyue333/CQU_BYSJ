# 方案 F：服务端渲染热力图 - 任务清单

> 基于 `工程1.md` 方案 F 设计，从现有方案 E（前端 Canvas 叠加）**完全切换**为服务端渲染热力图并推流。
> 
> **注意：不保留方案 E，前端 HeatmapOverlay 将被移除。**
>
> **文档版本**：v2（2026-01-01 Codex high 评审后更新）

## 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 同步模式 | **严格对齐** | 方案 F 核心价值是热力图与视频完美对齐；验收口径：推理帧同帧叠加，非推理帧复用缓存 heatmap |
| E/F 切换 | **不保留** | 简化架构，全面切换到方案 F |
| 渲染流命名 | `{stream_id}_heatmap` | 清晰区分原始流与渲染流 |
| 验收指标 | 延迟 1-5s / 渲染 24fps / 推理 8fps | 符合设计文档预期 |
| **拉流技术** | **ffmpeg subprocess** | OpenCV VideoCapture 在容器里对 RTSP/RTMP 支持不稳；ffmpeg 可精确控制编码参数 |
| **容器内 URL** | 从 `ZLM_BASE_URL` 推导 host | 拉流用 `rtsp://zlmediakit:554/live/{stream_id}`，推流用 `rtmp://zlmediakit:1935/live/{stream_id}_heatmap` |
| **状态模型** | 硬映射到现有 StreamStatus | `RENDER_STARTED→running`，`RENDER_STOPPED→stopped`，`RENDER_ERROR→error`，`RENDER_COOLDOWN→cooldown`；注：`cooldown` 已存在于现有枚举 |
| **F-17 删除范围** | 只删 worker/control 链路 | 保留 `inference_service.py`（YOLO 封装）、`heatmap_generator.py`，供 RenderWorker 复用 |

---

## Phase 1: 基础设施与配置（F-01 ~ F-03）

### F-01 方案F改造决策与范围锁定

- **任务描述**：明确同步策略（严格同帧）、渲染流命名规则与验收指标（延迟/帧率/并发）
- **涉及文件**：
  - `.kiro/specs/crowd-counting-system/工程1.md`
  - `backend/app/services/stream_service.py`
  - `frontend/src/App.vue`
- **依赖**：无
- **复杂度**：中
- **风险点**：验收指标不明确导致"能跑但不可用"

### F-02 定义"渲染流"命名与URL生成规则（含容器内地址体系）

- **任务描述**：
  1. 统一 `render_stream_id = {stream_id}_heatmap` 与播放 URL 生成（HLS/FLV/WebRTC）
  2. **区分 external 播放 URL 与 internal 拉/推 URL**：
     - 外部播放：从 `ZLM_EXTERNAL_URL` 生成（供浏览器访问）
     - 容器内拉流：从 `ZLM_BASE_URL` 推导 host，构建 `rtsp://{host}:{ZLM_RTSP_PORT}/live/{stream_id}`
     - 容器内推流：`rtmp://{host}:{ZLM_RTMP_PORT}/live/{stream_id}_heatmap`
  3. 新增 `ZLM_RTMP_PORT` 环境变量（默认 1935），与现有 `ZLM_RTSP_PORT` 保持命名一致
- **涉及文件**：
  - `backend/app/services/gateway_adapter.py`（新增 `build_internal_rtsp_url`、`build_internal_rtmp_url` 方法）
  - `backend/app/core/config.py`（新增 `zlm_rtmp_port`）
  - `backend/app/api/streams.py`
  - `.env.example`
- **依赖**：F-01
- **复杂度**：中
- **风险点**：命名冲突/重复启动；URL 拼装不一致导致前端播放失败；**容器内 localhost 问题**
- **命名规范**：统一使用 `ZLM_RTSP_PORT` + `ZLM_RTMP_PORT`，不引入其他命名

### F-03 渲染配置参数设计（env vs SystemConfig）

- **任务描述**：新增渲染相关配置（推理步长、渲染 fps、overlay alpha、ffmpeg 参数、最大并发渲染数），决定放环境变量还是落库
- **涉及文件**：
  - `backend/app/core/config.py`
  - `backend/app/models/system_config.py`
  - `backend/app/schemas/system_config.py`
  - `.env.example`
- **依赖**：F-01
- **复杂度**：中
- **风险点**：参数散落导致不可运维；落库则需迁移与兼容

---

## Phase 2: 后端核心实现（F-04 ~ F-09）

### F-04 [Backend] 新增 RenderControl（控制面：Redis PubSub）

- **任务描述**：仿照 `InferenceControlService` 新增 `RenderControlService`，定义 `render:control` 指令协议（START/STOP、cmd_id、stream_id 等），支持幂等与过期
- **涉及文件**：
  - 新增 `backend/app/services/render_control.py`
  - 参考 `backend/app/services/inference_control.py`
- **依赖**：F-03
- **复杂度**：中
- **风险点**：幂等处理不当导致重复拉流/推流；指令字段版本演进困难
- **多副本控制语义**：若 render 服务多副本部署，需明确消费策略：
  - 方案 A：每路流绑定到特定副本（stream_id hash 分片）
  - 方案 B：使用 Redis Streams + Consumer Group 替代 PubSub（推荐）
  - 当前 MVP 可先单副本，后续扩展时迁移到 Consumer Group

### F-04.1 [Backend] 拉流解码技术选型与 PoC（新增）

- **任务描述**：验证 ffmpeg subprocess 解码/编码链路可行性
  1. 用 ffmpeg 从 ZLM 拉 RTSP 流，解码输出 raw frames 到 pipe
  2. Python 读取 pipe，叠加简单图形，再通过 ffmpeg 编码推 RTMP 到 ZLM
  3. 验证 24fps 输出与延迟
- **涉及文件**：
  - 新增 `backend/scripts/poc_render_pipeline.py`（PoC 脚本，不进入生产代码）
- **依赖**：F-02（需要容器内 URL 体系）
- **复杂度**：中
- **风险点**：ffmpeg 参数不当导致高延迟/高 CPU；pipe 阻塞导致死锁
- **验收标准**（调整为基线记录模式）：
  - 单路 720p 流，记录 CPU 占用基线（目标 <150% 单核）
  - 端到端延迟目标 <5s（可接受范围 1-5s）
  - 若超标，记录瓶颈点并评估优化方案

### F-05 [Backend] 实现 RenderWorker（拉流→推理→叠加→推流主循环）

- **任务描述**：实现服务端渲染 Worker：
  1. 使用 **ffmpeg subprocess** 从 ZLM 拉原始流（24fps 解码）
  2. 每 N 帧做 YOLO 推理生成 heatmap（复用 `InferenceService`）
  3. 对每帧叠加热力图（复用 `HeatmapGenerator` + `demo_inference.py:draw_heatmap_overlay`）
  4. 通过 ffmpeg 编码推流到 ZLM
- **涉及文件**：
  - 新增 `backend/app/services/render_worker.py`
  - 复用 `backend/app/services/inference_service.py`（YOLO 推理）
  - 复用 `backend/app/services/heatmap_generator.py`
  - 参考 `backend/scripts/demo_inference.py:draw_heatmap_overlay`
- **依赖**：F-02, F-03, F-04, F-04.1
- **复杂度**：**高**
- **风险点**：CPU/内存开销暴增；ffmpeg 子进程阻塞导致事件循环卡死；异常退出后资源未回收

### F-06 [Backend] FFmpeg 推流管道与生命周期管理

- **任务描述**：在 RenderWorker 内用 `ffmpeg pipe:0` 推送 `rtmp://<zlm>/live/{render_stream_id}`，处理 stdin 写入、BrokenPipe、重启、退出清理
- **涉及文件**：
  - `backend/app/services/render_worker.py`
  - 或新增 `backend/app/services/ffmpeg_push.py`
- **依赖**：F-05
- **复杂度**：**高**
- **风险点**：子进程泄漏/僵尸进程；编码参数不当造成高延迟/高码率；不同分辨率/像素格式不匹配

### F-07 [Backend] 严格对齐模式实现（每 N 帧推理）

- **任务描述**：RenderWorker 内每 N 帧推理（如每 3 帧 = 8fps），同帧生成 heatmap 并叠加，其余帧复用缓存的 heatmap
- **涉及文件**：
  - `backend/app/services/render_worker.py`
- **依赖**：F-05
- **复杂度**：中
- **风险点**：严格模式算力不足时需要动态调整 N 值

### F-08 [Backend] 渲染状态上报与健康/重试策略

- **任务描述**：
  1. 建立 `render:status` Redis Stream，上报 RENDER_STARTED/STOPPED/ERROR/HEALTH_UPDATE
  2. 加入退避重试与熔断
  3. **适配 StatusPushService**：修改 `status_push_service.py` 监听 `render:status`（替代 `inference:status`），事件映射：
     - `RENDER_STARTED` → `running`
     - `RENDER_STOPPED` → `stopped`
     - `RENDER_ERROR` → `error`
     - `RENDER_COOLDOWN` → `cooldown`
- **涉及文件**：
  - `backend/app/services/render_worker.py`
  - `backend/app/services/status_push_service.py`（修改 `STATUS_STREAM` 常量，更新 `event_map`）
- **依赖**：F-04, F-05
- **复杂度**：中
- **风险点**：状态洪泛；错误恢复导致重复推流；熔断策略误杀正常流；**StatusPushService 监听源切换**

### F-09 [Backend] StreamService 接入"渲染流"生命周期

- **任务描述**：扩展 `StreamService.start/stop`：
  - start：创建原始流后触发 RenderWorker（替代 InferenceWorker）
  - stop：停止渲染 Worker、强制关闭渲染流、再清理原始流
- **涉及文件**：
  - `backend/app/services/stream_service.py`
  - 新增 `backend/app/services/render_control.py`
- **依赖**：F-02, F-04, F-05, F-06, F-07, F-08
- **复杂度**：**高**
- **风险点**：部分失败回滚复杂；状态机与并发限制需要重新定义

---

## Phase 3: 后端 API 扩展（F-10 ~ F-13）

### F-10 [Backend] API 简化：移除 enable_infer，默认启用渲染

- **任务描述**：移除 `VideoStreamStart` 中的 `enable_infer` 字段，start 时默认启动渲染流
- **涉及文件**：
  - `backend/app/schemas/video_stream.py`
  - `backend/app/api/streams.py`
- **依赖**：F-09
- **复杂度**：低
- **风险点**：向后兼容（老前端可能仍传 enable_infer）

### F-11 [Backend] API 响应：返回渲染流播放地址

- **任务描述**：在 `VideoStreamResponse` 中 `play_url` 直接返回渲染流地址（`{stream_id}_heatmap`）
- **涉及文件**：
  - `backend/app/schemas/video_stream.py`
  - `backend/app/api/streams.py`
- **依赖**：F-02, F-10
- **复杂度**：低
- **风险点**：渲染流未就绪时返回值策略（预测URL vs 轮询确认）

### F-12 [Backend] 结果发布：RenderWorker 写入 Redis

- **任务描述**：RenderWorker 负责写 `result:{stream_id}` 与 **`latest_result:{stream_id}`**（替代 InferenceWorker）
  - **注意**：当前代码 `latest_result:{stream_id}` 无写入方，需在 RenderWorker 中明确实现
- **涉及文件**：
  - `backend/app/services/render_worker.py`
  - `backend/app/api/streams.py`（latest-result 取 Redis key）
- **依赖**：F-07, F-09
- **复杂度**：中
- **风险点**：结果源切换导致前端统计"断档"；**`latest_result` key 未写入导致 API 返回空**

### F-13 [Backend] WebSocket 状态推送适配渲染状态

- **任务描述**：让前端能看到"渲染中/渲染错误/渲染恢复"状态
- **涉及文件**：
  - `backend/app/services/status_push_service.py`
  - `backend/app/api/websockets.py`
- **依赖**：F-08, F-11
- **复杂度**：中
- **风险点**：与现有 inference 事件映射冲突；前端状态机不一致导致 UI 抖动

---

## Phase 4: 前端改造（F-14 ~ F-16）

### F-14 [Frontend] 类型与 API 调用简化

- **任务描述**：更新前端类型定义，移除 `enable_infer` 相关字段，直接使用 `play_url`（已是渲染流）
- **涉及文件**：
  - `frontend/src/types/index.ts`
  - `frontend/src/api/streams.ts`
- **依赖**：F-10, F-11
- **复杂度**：低
- **风险点**：类型不一致造成运行时字段缺失

### F-15 [Frontend] 移除 HeatmapOverlay 组件及相关逻辑

- **任务描述**：
  1. 删除 `HeatmapOverlay.vue` 及其在 `App.vue` 中的引用
  2. **清理 `App.vue` 中相关逻辑**：`showHeatmap`、`heatmapGrid`、`videoAspectRatio` 等耦合代码
  3. 前端不再做热力图叠加
- **涉及文件**：
  - 删除 `frontend/src/components/HeatmapOverlay.vue`
  - `frontend/src/App.vue`（清理 `showHeatmap`、`heatmapGrid`、`videoAspectRatio` 相关代码）
- **依赖**：F-14
- **复杂度**：低
- **风险点**：ROI 相关 Canvas 叠加需确认不受影响（ROI 绘制可能仍需保留）

### F-16 [Frontend] 渲染流延迟体验优化

- **任务描述**：在 UI 明示"预计 1–5 秒延迟"，调整 VideoPlayer 缓冲策略
- **涉及文件**：
  - `frontend/src/components/VideoPlayer.vue`
  - `frontend/src/App.vue`
- **依赖**：F-15
- **复杂度**：低
- **风险点**：直播 seek 可能导致播放异常；不同协议表现差异

---

## Phase 5: 清理旧代码（F-17 ~ F-18）

### F-17 [Backend] 下线 InferenceWorker 链路（保留推理核心库）

- **任务描述**：
  1. **删除**：`inference_control.py`、`inference_worker.py`、`inference_main.py`、`Dockerfile.inference`
  2. **保留**：`inference_service.py`（YOLO 推理封装，供 RenderWorker 复用）、`heatmap_generator.py`
  3. 清理 `stream_service.py` 中对 `InferenceControlService` 的引用
- **涉及文件**：
  - 删除 `backend/app/services/inference_control.py`
  - 删除 `backend/app/services/inference_worker.py`
  - 删除 `backend/inference_main.py`
  - 删除 `backend/Dockerfile.inference`
  - 修改 `backend/app/services/stream_service.py`（移除 `inference_control` 导入和调用）
  - 修改 `backend/app/services/__init__.py`（移除导出）
- **依赖**：F-09, F-12
- **复杂度**：低
- **风险点**：**误删 `inference_service.py` 会导致 RenderWorker 无法推理**

### F-18 [Backend] 清理 getSnap 抽帧相关代码（可选）

- **任务描述**：移除 ZLMediaKit getSnap API 调用相关代码（RenderWorker 直接拉流解码，不再需要 getSnap）
  - **建议保留**：`GatewayAdapter.get_snapshot()` 对排障/未来功能（缩略图、诊断）有价值
- **涉及文件**：
  - `backend/app/services/gateway_adapter.py`（可选删除 `get_snapshot` 方法）
- **依赖**：F-17
- **复杂度**：低
- **风险点**：确认无其他模块依赖 getSnap；**建议标记为可选，不阻塞主链路**

---

## Phase 6: 部署改造（F-19 ~ F-23）

### F-19 [Deploy] 新增 render 服务镜像与入口

- **任务描述**：提供独立渲染服务入口 `backend/render_main.py`，便于水平扩展与隔离 CPU/编码压力
- **涉及文件**：
  - 新增 `backend/render_main.py`
  - 新增 `backend/Dockerfile.render`
- **依赖**：F-05, F-06
- **复杂度**：中
- **风险点**：镜像缺依赖（OpenCV/ffmpeg）；健康检查不可靠导致容器频繁重启
- **镜像依赖清单**（必须包含）：
  - `ffmpeg`（apt install ffmpeg）
  - `libgl1-mesa-glx`（OpenCV 运行依赖）
  - `ultralytics`（YOLO）
  - `opencv-python-headless`（避免 GUI 依赖）

### F-20 [Deploy] docker-compose 增加 render 服务，移除 inference 服务

- **任务描述**：在 `docker-compose.prod.yml` 增加 render 服务，移除 inference 服务
- **涉及文件**：
  - `docker-compose.prod.yml`
  - `docker-compose.yml`
  - `docker-compose.gpu.yml`
- **依赖**：F-19, F-09
- **复杂度**：中
- **风险点**：容器内访问 RTSP/RTMP 地址配置错误；端口/网络不通导致黑屏

### F-21 [Deploy] GPU/硬编优化（可选）

- **任务描述**：为渲染服务增加 GPU 编码路径（NVENC/VAAPI），在 `docker-compose.gpu.yml` 扩展到 render
- **涉及文件**：
  - `docker-compose.gpu.yml`
  - `backend/Dockerfile.render`
- **依赖**：F-20, F-06
- **复杂度**：**高**
- **风险点**：宿主机驱动/容器工具链不一致；ffmpeg 不含 nvenc；性能收益不达预期

### F-22 [Deploy/ZLM] ZLMediaKit 配置调优

- **任务描述**：针对方案 F 做延迟与协议选择调优：保持 HTTP-FLV/WebRTC 优先；必要时下调 `hls.segDur`；生产环境修正 `[rtc].externIP`
- **涉及文件**：
  - `zlm-config/config.ini`
- **依赖**：F-02, F-20
- **复杂度**：中
- **风险点**：WebRTC NAT/公网 IP 配置错误直接不可用；降低 segDur 增加负载

### F-23 [Docs] 文档/脚本更新

- **任务描述**：更新文档，移除方案 E 相关说明，补充方案 F 的部署方式、环境变量、故障排查
- **涉及文件**：
  - `README.md`
  - `backend/README.md`
  - `scripts/deploy.sh`
  - `.env.example`
- **依赖**：F-20, F-22
- **复杂度**：低
- **风险点**：文档与实现偏差导致运维困难

---

## Phase 7: 数据层扩展（F-24 ~ F-25，可选）

### F-24 [DB 可选] SystemConfig 扩展渲染参数持久化

- **任务描述**：若需要"每路流可配置渲染策略"，扩展 SystemConfig（infer_stride、overlay_alpha、render_fps 等）
- **涉及文件**：
  - `backend/app/models/system_config.py`
  - `backend/app/schemas/system_config.py`
  - `backend/app/api/config.py`
  - `backend/alembic/versions/*.py`
- **依赖**：F-03, F-09
- **复杂度**：中-高
- **风险点**：迁移兼容与回滚；配置热更新一致性

### F-25 [Redis] 新增 render streams/key 的保留与清理策略

- **任务描述**：定义 `render:status` 的 maxlen、渲染失败的清理动作、stop 时清除缓存
- **涉及文件**：
  - `backend/app/core/config.py`
  - `backend/app/services/render_worker.py`
- **依赖**：F-08
- **复杂度**：低-中
- **风险点**：Redis 内存被打爆；清理过度导致排障困难

---

## Phase 8: 测试与验收（F-26 ~ F-29）

### F-26 [Test] RenderWorker 纯逻辑单元测试

- **任务描述**：对热力图叠加、色图映射、网格缩放、ffmpeg 参数拼装做可重复单测
- **涉及文件**：
  - 新增 `backend/tests/test_render_worker_unit.py`
  - 复用 `backend/scripts/demo_inference.py` 逻辑作为基准
- **依赖**：F-05, F-06
- **复杂度**：中
- **风险点**：OpenCV 相关测试易脆；需做纯函数化拆分

### F-27 [Test] StreamService/API 测试：渲染流行为覆盖

- **任务描述**：扩展现有流管理测试，验证 start/stop 的控制指令发布、play_url 返回、错误回滚
- **涉及文件**：
  - `backend/tests/test_stream_api_properties.py`
  - `backend/tests/test_integration_e2e.py`
- **依赖**：F-09, F-10, F-11
- **复杂度**：中
- **风险点**：Mock 面扩大；未覆盖部分失败路径

### F-28 [Test] WebSocket 状态推送：渲染状态事件覆盖

- **任务描述**：验证 StatusPushService 能正确转发渲染状态
- **涉及文件**：
  - 新增/扩展 `backend/tests/test_*status*.py`
- **依赖**：F-13
- **复杂度**：中
- **风险点**：异步时序导致 flaky；事件映射规则变化频繁

### F-29 [验收] 端到端验收清单/脚本

- **任务描述**：提供可复现的 E2E 验收步骤：启动一路流→ZLM 出现 `{stream_id}_heatmap`→前端播放渲染流（带热力图）→停止后无残留推流进程
- **涉及文件**：
  - `README.md` 或新增 `scripts/smoke_render.sh`
- **依赖**：F-20, F-23
- **复杂度**：低
- **风险点**：依赖真实媒体环境；不同平台差异

### F-30 [Test] 性能/稳定性验收（新增）

- **任务描述**：
  1. 单路 1080p/720p CPU 占用、内存基线测量
  2. 24h 长时间运行泄漏检测
  3. 并发 2/4 路的降级策略验证（降分辨率/降 fps/增 stride/熔断）
- **涉及文件**：
  - 新增 `backend/tests/test_render_performance.py`（或手动测试脚本）
  - `backend/app/core/config.py`（降级参数）
- **依赖**：F-05, F-06, F-20
- **复杂度**：中
- **风险点**：性能不达标需要返工优化；多路并发时 CPU 打满

---

## 任务依赖图（简化）

```
F-01 ─┬─> F-02 ────────────────────────────> F-11 ─> F-14 ─> F-15 ─> F-16
      │     │
      │     └─> F-04.1 (PoC) ─────────────────────────────────────────────┐
      │                                                                    │
      └─> F-03 ─> F-04 ─> F-05 ─┬─> F-06 ─> F-19 ─> F-20 ─> F-21/F-22/F-23
                          │     │                              │
                          │     └─> F-07 ─> F-09 ─> F-10 ─> F-11
                          │                   │
                          └─> F-08 ──────────┴─> F-12/F-13 ─> F-17 ─> F-18
                                                    │
                                                    └─> F-24/F-25/F-26~F-30
```

**关键路径**：F-01 → F-02 → F-04.1(PoC) → F-05 → F-06 → F-09 → F-20

---

## 建议实施顺序

1. **Week 1**: F-01 ~ F-03 + **F-04.1 (PoC)**（决策与配置 + 技术验证）
2. **Week 2-3**: F-04 ~ F-09（后端核心，最复杂）
3. **Week 4**: F-10 ~ F-13（API 扩展）
4. **Week 5**: F-14 ~ F-18（前端改造 + 旧代码清理）
5. **Week 6**: F-19 ~ F-23（部署）
6. **Week 7-8**: F-24 ~ F-30（可选扩展 + 测试验收 + 性能调优）

预估总工时：**6-8 周**（含 PoC 验证和性能调优缓冲）

---

## 与原方案 E 的主要差异

| 维度 | 方案 E（原） | 方案 F（新） |
|------|-------------|-------------|
| 热力图渲染 | 前端 Canvas 叠加 | 服务端 OpenCV 叠加 |
| 推理服务 | InferenceWorker (getSnap) | RenderWorker (拉流解码) |
| 前端复杂度 | 高（HeatmapOverlay + EMA） | 低（只播放视频） |
| 服务端负载 | 低（1-3fps 推理） | 高（24fps 解码 + 8fps 推理 + 编码） |
| 延迟 | <1s | 1-5s |
| 热力图对齐 | 需要时间同步 | 完美对齐（同帧处理） |
