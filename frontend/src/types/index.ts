/**
 * TypeScript 类型定义
 * 与后端 Pydantic schemas 对应
 */

// 视频流类型
export type StreamType = 'file' | 'webcam' | 'rtsp'

// 视频流状态
export type StreamStatus = 'starting' | 'running' | 'stopped' | 'error' | 'cooldown'

// 密度等级
export type DensityLevel = 'low' | 'medium' | 'high'

// ICE 服务器配置
export interface IceServer {
  urls: string[]
  username?: string
  credential?: string
}

// 浏览器摄像头推流信息
export interface PublishInfo {
  whip_url: string
  token: string
  expires_at: number
  ice_servers: IceServer[]
}

// 视频流响应
export interface VideoStream {
  stream_id: string
  name: string
  type: StreamType
  status: StreamStatus
  play_url: string | null
  webrtc_url: string | null
  source_url: string | null
  file_id: string | null
  publish_info: PublishInfo | null
  created_at: string
  updated_at: string
}

// 视频流列表响应
export interface VideoStreamListResponse {
  streams: VideoStream[]
  total: number
}

// 创建视频流请求
export interface VideoStreamCreate {
  name: string
  type: StreamType
  source_url?: string
  file_id?: string
}

// 启动视频流请求
// 方案 F：默认启用渲染，enable_infer 已废弃但保留用于向后兼容
export interface VideoStreamStart {
  /** @deprecated 方案 F 默认启用渲染，此字段已废弃 */
  enable_infer?: boolean
}

// 单个检测结果
export interface Detection {
  x: number
  y: number
  width: number
  height: number
  confidence: number
}

// 区域统计结果
export interface RegionStat {
  region_id: string
  region_name: string
  count: number
  density: number
  level: DensityLevel
}

export interface DensityThresholds {
  low: number
  medium: number
  high: number
}

export interface Point {
  x: number
  y: number
}

export interface StatusMetrics {
  render_fps_actual: number
  infer_fps_actual: number
  last_frame_ts?: number
  latency_ms: number
  health: 'healthy' | 'degraded' | 'cooldown' | 'error'
  state: StreamStatus
}

// 完整检测结果
export interface DetectionResult {
  stream_id: string
  capture_ts?: number
  timestamp: number
  total_count: number
  frame_width: number
  frame_height: number
  detections: Detection[]
  heatmap_grid: number[][]
  region_stats: RegionStat[]
}

// 文件上传响应
export interface FileUploadResponse {
  file_id: string
  filename: string
  size: number
  content_type: string
  created_at: string
  expires_at: string
}

// 文件信息
export interface FileInfo {
  file_id: string
  filename: string
  size: number
  content_type: string
  created_at: string
  expires_at: string
}

// 文件列表响应
export interface FileListResponse {
  files: FileInfo[]
  total: number
}

// WebSocket 消息类型
export interface WsMessage {
  type: 'ping' | 'pong' | 'result' | 'recovery' | 'recovery_complete' | 'recover' | 'status' | 'alert'
  ts?: number
  msg_id?: string
  data?: DetectionResult | StreamStatusUpdate
  last_id?: string
  count?: number
  event?: AlertEvent
}

// 流状态更新
export interface StreamStatusUpdate {
  stream_id: string
  status: StreamStatus
  play_url?: string
  error?: string
  metrics?: StatusMetrics
  event?: string
  timestamp?: number
}

export interface AlertRule {
  id: string
  stream_id: string
  roi_id?: string | null
  threshold_type: 'count' | 'density'
  threshold_value?: number | null
  level: DensityLevel
  min_duration_sec: number
  cooldown_sec: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface AlertEvent {
  id: string
  rule_id?: string | null
  stream_id: string
  roi_id?: string | null
  level: DensityLevel
  start_ts: number
  end_ts?: number | null
  peak_density: number
  count_peak: number
  message?: string | null
  acknowledged: boolean
}

export interface AlertRuleListResponse {
  rules: AlertRule[]
  total: number
}

export interface AlertEventListResponse {
  events: AlertEvent[]
  total: number
}

export interface ROITemplateRegion {
  name: string
  points: Point[]
}

export interface ROITemplate {
  id: string
  name: string
  description: string
  tags: string[]
  regions: ROITemplateRegion[]
}

export interface ROITemplateListResponse {
  templates: ROITemplate[]
  total: number
}

export interface ConfigPreset {
  id: string
  name: string
  render_fps: number
  render_infer_stride: number
  heatmap_decay: number
  render_overlay_alpha: number
}

export interface ConfigPresetListResponse {
  presets: ConfigPreset[]
  total: number
}

// API 错误响应
export interface ApiError {
  detail: string
}

// 系统配置（方案 F：服务端渲染热力图）
export interface SystemConfig {
  id: number
  stream_id: string
  confidence_threshold: number
  heatmap_grid_size: number
  heatmap_decay: number
  default_density_thresholds: DensityThresholds
  // 方案 F 渲染配置
  render_fps: number
  render_infer_stride: number
  render_overlay_alpha: number
  // 已废弃字段（保留向后兼容）
  /** @deprecated 方案 F 使用 render_infer_stride */
  inference_fps?: number
}

// 系统配置更新请求
export interface SystemConfigUpdate {
  confidence_threshold?: number
  heatmap_grid_size?: number
  heatmap_decay?: number
  default_density_thresholds?: DensityThresholds
  // 方案 F 渲染配置
  render_fps?: number
  render_infer_stride?: number
  render_overlay_alpha?: number
}
