export type ApiEnvelope<T> = {
  code: number;
  data: T;
  msg: string;
};

export type SourceType = "file" | "stream";
export type AnalysisStatusValue = "ready" | "running" | "stopped" | "error";
export type HistoryMetricKey =
  | "total_count_avg"
  | "total_count_max"
  | "total_count_min"
  | "total_density_avg";

export interface VideoSource {
  source_id: string;
  name: string;
  source_type: SourceType;
  status: string;
  file_path?: string | null;
  stream_url?: string | null;
  video_width?: number | null;
  video_height?: number | null;
  video_fps?: number | null;
  total_frames?: number | null;
  created_at: string;
}

export interface SourceListResponse {
  sources: VideoSource[];
}

export interface SystemStatus {
  status: string;
  uptime: number;
  active_sources: number;
  gpu_usage?: number | null;
  memory_usage?: number | null;
}

export interface AnalysisStatus {
  source_id: string;
  status: AnalysisStatusValue;
  start_time?: string | null;
}

export interface Region {
  region_id: string;
  source_id: string;
  name: string;
  points: number[][];
  color: string;
  count_warning?: number | null;
  count_critical?: number | null;
  density_warning?: number | null;
  density_critical?: number | null;
}

export interface RegionListResponse {
  regions: Region[];
}

export interface RegionThreshold {
  name: string;
  warning: number;
  critical: number;
}

export interface AlertThresholdConfig {
  total_warning_threshold: number;
  total_critical_threshold: number;
  default_region_warning: number;
  default_region_critical: number;
  region_thresholds: Record<string, RegionThreshold>;
  cooldown_seconds: number;
}

export interface AlertRecentItem {
  alert_id: string;
  alert_type: string;
  level: "warning" | "critical" | string;
  region_id?: string | null;
  region_name?: string | null;
  current_value: number;
  threshold: number;
  timestamp: string;
  message?: string | null;
}

export interface AlertRecentResponse {
  items: AlertRecentItem[];
}

export interface RegionHistoryStats {
  total_count_avg: number;
  total_count_max: number;
  total_count_min: number;
  total_density_avg: number;
}

export interface HistorySeriesItem {
  time: string;
  total_count_avg: number;
  total_count_max: number;
  total_count_min: number;
  total_density_avg: number;
  regions: Record<string, RegionHistoryStats>;
}

export interface HistoryResponse {
  series: HistorySeriesItem[];
}

export interface RegionRealtimeStats {
  total_count_avg: number;
  total_count_max: number;
  total_count_min: number;
  total_density_avg: number;
}

export interface RealtimeFrame {
  ts: string;
  frame: string;
  total_count: number;
  total_density: number;
  regions: Record<string, RegionRealtimeStats>;
  entry_speed: number;
}

export interface AlertSocketMessage {
  alert_id: string;
  alert_type: string;
  level: "warning" | "critical" | string;
  region_id?: string | null;
  region_name?: string | null;
  current_value: number;
  threshold: number;
  timestamp: string;
  message: string;
}

export type SocketEnvelope =
  | { type: "frame"; data: RealtimeFrame }
  | { type: "alert"; data: AlertSocketMessage };
