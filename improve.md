# 用户体验改进可执行计划

基于 `.kiro/specs/crowd-counting-system/用户体验改进.md` 的“未完成/部分完成”项，整理如下执行计划，按优先级推进。

## 1. 未完成项清单（来源：功能完成情况）

- P0.1 页面布局优化（未开始）
- P0.2 实时数据折线图（未开始）
- P0.3 ROI 形状预设绘制（未开始）
- P0.4 ROI 区域统计修复（待修复）
- P0.5 ROI 区域统计（部分完成）
- P0.5 ROI 预设模板分辨率适配（部分完成）
- P1.1 配置导入导出（未开始）
- P1.4 检测框叠加开关（部分完成）

## 2. 改进计划（按阶段交付）

### 阶段 A：修复 ROI 统计链路（P0.4 + P0.5）

**目标**：ROI 绘制后统计稳定展示，模板在不同分辨率正确适配。  
**工作项**：
- 统一 ROI 坐标系：明确前端发送的坐标格式（像素/归一化），补齐视频帧真实尺寸的传递与换算逻辑。
- ROI 创建/更新后触发后端缓存刷新，确保 `_get_cached_rois` 立即可见。
- WebSocket `region_stats` 推送与 ROI 列表绑定，补齐新增 ROI 的统计字段。
- 完成模板分辨率适配：模板坐标归一化后在前端或后端统一换算。
- 增加最小链路验证：绘制 ROI → 推送统计 → 前端展示闭环验收。

**验收标准**：
- 新建 ROI 在 1 个推送周期内显示统计数据。
- 模板在 3 种分辨率（如 720p/1080p/4K）下与实际区域对齐。

### 阶段 B：核心体验补齐（P0.1 + P0.2 + P0.3）

**目标**：主页面可同时监控视频与数据，实时趋势可视化，ROI 绘制更高效。  
**工作项**：
- 页面分栏布局：加入可拖拽分割条与三种预设布局，布局偏好存储到 localStorage。
- 实时折线图：实现滑动窗口缓存（1/5 分钟可选），支持全局/ROI 维度切换，接入 `region_stats`。
- ROI 形状预设：新增矩形/圆形绘制，形状编辑（移动/缩放/旋转），最终转多边形存储。

**验收标准**：
- 拖拽分割条平滑；刷新后布局保持不变。
- 实时折线图每个推送周期更新，切换维度/ROI 后数据正确。
- 形状绘制与编辑稳定，无明显卡顿或坐标漂移。

### 阶段 C：次要体验补齐（P1.1 + P1.4）

**目标**：配置可迁移，检测框可控，减少遮挡。  
**工作项**：
- 配置导入/导出：提供 JSON/CSV 形式导出入口，导入后校验并提示覆盖策略。
- 检测框叠加开关：增加 UI 开关，状态本地保存，默认与主题一致。

**验收标准**：
- 导出文件可在另一环境导入并生效。
- 检测框开关即时生效，刷新后保持设置。

## 3. 代码层面实现细节（按需求点）

### P0.4 / P0.5 ROI 统计链路与模板适配
- 前端坐标换算：`frontend/src/App.vue` 以 `displayResult.frame_width/height` 与 `videoWidth/videoHeight` 做缩放，`handleRoiCreate`/`handleRoiUpdate` 使用 `scalePoints`，展示层使用 `displayRois`（传给 `ROIDrawer` 与 `RegionDensityDisplay`）。
- 绘制层/显示层：`frontend/src/components/ROIDrawer.vue` 与 `frontend/src/components/RegionDensityDisplay.vue` 只消费“显示坐标”，避免直接用后端原始点位。
- 后端缓存刷新：`backend/app/api/rois.py` 的 create/update/delete/preset 后调用 `_publish_roi_update`；`backend/app/services/render_worker.py` 订阅 `roi:updated` 并 `pop` 缓存，必要时补日志定位未刷新或 TTL 过期问题。
- region_stats 推送：`backend/app/services/render_worker.py:_calculate_region_stats` → `ROICalculator.calculate_region_stat` 组装 `DetectionResult.region_stats`，确保 WebSocket `result` 消息携带最新 ROI 统计。
- 模板适配：`backend/app/api/rois.py:apply_roi_preset` 使用 `latest_result` 的 `frame_width/height` 进行归一化坐标换算；若 `latest_result` 不可用，补齐 fallback（如从 `VideoPlayer` 元数据或默认分辨率）。

### P0.1 页面布局优化
- 主布局：`frontend/src/App.vue` 使用 `splitpanes`（`splitSize` + `LAYOUT_PREF_KEY`）实现左右分栏，`@resized` 写入 localStorage。
- 上下拉伸：新增一层垂直 `Splitpanes`（horizontal）包裹视频区与工具区，增加 `splitHeight` 与对应的本地存储键。
- 样式：`frontend/src/App.vue` 中 `.video-section` / `.data-panel-container` 保证 100% 高度与最小宽度，避免折叠时遮挡。

### P0.2 实时数据折线图
- 新建 `frontend/src/components/RealtimeChart.vue`（复用 `HistoryChart.vue` 的 Canvas 绘制逻辑），或在 `StatsPanel.vue` 内嵌同类绘制函数。
- 数据流：`frontend/src/components/DataTabs.vue` 将 `result` + `selectedRoiId` + `alertEvents` 传入图表组件；在组件内 `watch(() => result?.timestamp)` 追加点位并维护滑动窗口。
- 序列模型：`[{ ts, count, density, alerts }]`，按窗口（60/300s）裁剪；`ROI 模式` 取 `result.region_stats.find(region_id)`，`全局模式` 取 `result.total_count`，密度需与后端 `AREA_NORMALIZATION_FACTOR` 对齐或由后端新增 `global_density` 字段。
- UI 控件：时间窗口、指标选择、ROI/全局切换均用 `ref` 管理，更新后触发重新绘制。

### P0.3 ROI 形状预设绘制
- 形状选择 UI：在 `frontend/src/components/DataTabs.vue` ROI 工具条新增“矩形/圆形/多边形”按钮，通过 props 或事件传给 `ROIDrawer.vue`。
- 矩形：`mousedown` 记录起点，`mousemove` 预览矩形四点，`mouseup` 提交 4 点多边形。
- 圆/椭圆：以中心点 + 半径计算 N 边形（如 32 边）作为多边形坐标存储，保持后端兼容。
- 编辑：复用已有顶点拖拽；如需旋转，追加“旋转手柄 + 角度计算”并转换为点位后提交 `updateROI`。

### P1.1 配置导入导出
- 前端：`frontend/src/components/ConfigPanel.vue` 中 `importConfig` 解析 JSON 后做字段与范围校验，再调用 `updateConfig` 持久化；`exportConfig` 以 `getConfig` 的已保存配置为源。
- 校验逻辑：新增 `frontend/src/utils/config.ts`（或同类）统一验证 `render_fps`、`heatmap_grid_size`、`default_density_thresholds` 的取值范围。
- 可选后端：`backend/app/api/config.py` 可追加 `GET /{stream_id}/export` 与 `POST /{stream_id}/import`，复用 `SystemConfigUpdate` 做服务端校验。

### P1.4 检测框叠加开关
- 入口：`frontend/src/App.vue` 增加 `showDetections` 与 `SHOW_DETECTIONS_KEY` 持久化，工具栏使用 checkbox 控制。
- 展示：`DetectionOverlay` 使用 `v-if="showDetections"` 保护，避免遮挡与多余渲染。

## 4. 依赖与风险提示

- ROI 统计修复依赖前后端对坐标体系的统一定义，需先明确“像素/归一化”基准。
- 实时折线图依赖 WebSocket 推送频率稳定与 `region_stats` 数据完整。
- ROI 形状预设与编辑可能引入复杂交互，需要评估是否引入现成绘制库或自研。

## 5. 建议里程碑（可按周划分）

- M1：阶段 A 完成并上线（ROI 统计闭环稳定）
- M2：阶段 B 完成并上线（布局 + 实时图 + 形状绘制）
- M3：阶段 C 完成并上线（配置迁移 + 检测框开关）
