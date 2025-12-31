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
export interface VideoStreamStart {
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

// 完整检测结果
export interface DetectionResult {
  stream_id: string
  timestamp: number
  total_count: number
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
  type: 'ping' | 'pong' | 'result' | 'recovery' | 'recovery_complete' | 'recover' | 'status'
  ts?: number
  msg_id?: string
  data?: DetectionResult | StreamStatusUpdate
  last_id?: string
  count?: number
}

// 流状态更新
export interface StreamStatusUpdate {
  stream_id: string
  status: StreamStatus
  play_url?: string
  error?: string
}

// API 错误响应
export interface ApiError {
  detail: string
}
