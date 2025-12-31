/**
 * 历史数据 API
 * 
 * Requirements: 6.2, 6.3, 6.4
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// 聚合粒度
export type AggregationGranularity = 'minute' | 'hour' | 'day'

// 密度等级
export type DensityLevel = 'low' | 'medium' | 'high'

// 区域统计
export interface RegionStat {
  region_id: string
  region_name: string
  count: number
  density: number
  level: DensityLevel
}

// 历史统计响应
export interface HistoryStatResponse {
  id: number
  stream_id: string
  timestamp: string
  total_count: number
  region_stats: RegionStat[]
}

// 历史列表响应
export interface HistoryListResponse {
  stats: HistoryStatResponse[]
  total: number
  has_more: boolean
}

// 聚合统计
export interface AggregatedStat {
  timestamp: string
  avg_count: number
  max_count: number
  min_count: number
  sample_count: number
}

// 聚合历史响应
export interface AggregatedHistoryResponse {
  stream_id: string
  granularity: AggregationGranularity
  start_time: string
  end_time: string
  data: AggregatedStat[]
}

// 查询参数
export interface HistoryQueryParams {
  start_time?: string
  end_time?: string
  limit?: number
  offset?: number
}

// 聚合查询参数
export interface AggregatedQueryParams {
  granularity?: AggregationGranularity
  start_time?: string
  end_time?: string
}

/**
 * 查询历史数据
 */
export async function getHistory(
  streamId: string,
  params: HistoryQueryParams = {}
): Promise<HistoryListResponse> {
  const searchParams = new URLSearchParams()
  
  if (params.start_time) {
    searchParams.set('start_time', params.start_time)
  }
  if (params.end_time) {
    searchParams.set('end_time', params.end_time)
  }
  if (params.limit !== undefined) {
    searchParams.set('limit', params.limit.toString())
  }
  if (params.offset !== undefined) {
    searchParams.set('offset', params.offset.toString())
  }
  
  const url = `${API_BASE}/api/streams/${streamId}/history?${searchParams.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch history')
  }
  
  return response.json()
}

/**
 * 查询聚合历史数据
 */
export async function getAggregatedHistory(
  streamId: string,
  params: AggregatedQueryParams = {}
): Promise<AggregatedHistoryResponse> {
  const searchParams = new URLSearchParams()
  
  if (params.granularity) {
    searchParams.set('granularity', params.granularity)
  }
  if (params.start_time) {
    searchParams.set('start_time', params.start_time)
  }
  if (params.end_time) {
    searchParams.set('end_time', params.end_time)
  }
  
  const url = `${API_BASE}/api/streams/${streamId}/history/aggregated?${searchParams.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch aggregated history')
  }
  
  return response.json()
}

/**
 * 导出历史数据
 */
export async function exportHistory(
  streamId: string,
  format: 'csv' | 'excel' = 'csv',
  params: { start_time?: string; end_time?: string } = {}
): Promise<Blob> {
  const searchParams = new URLSearchParams()
  searchParams.set('format', format)
  
  if (params.start_time) {
    searchParams.set('start_time', params.start_time)
  }
  if (params.end_time) {
    searchParams.set('end_time', params.end_time)
  }
  
  const url = `${API_BASE}/api/streams/${streamId}/history/export?${searchParams.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to export history')
  }
  
  return response.blob()
}

/**
 * 下载导出文件
 */
export async function downloadHistory(
  streamId: string,
  format: 'csv' | 'excel' = 'csv',
  params: { start_time?: string; end_time?: string } = {}
): Promise<void> {
  const blob = await exportHistory(streamId, format, params)
  
  // 创建下载链接
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `history_${streamId}_${new Date().toISOString().slice(0, 10)}.${format === 'excel' ? 'xlsx' : 'csv'}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
