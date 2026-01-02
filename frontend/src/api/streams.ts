/**
 * 流管理 API 封装
 * Requirements: 1.5, 1.6
 */

import type {
  VideoStream,
  VideoStreamListResponse,
  VideoStreamCreate,
  VideoStreamStart,
  DetectionResult
} from '@/types'
import { handleResponse } from './request'

const API_BASE = '/api/streams'

// ApiRequestError and handleResponse moved to ./request

/**
 * 创建视频流
 */
export async function createStream(data: VideoStreamCreate): Promise<VideoStream> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<VideoStream>(response)
}

/**
 * 获取所有视频流列表
 */
export async function listStreams(): Promise<VideoStreamListResponse> {
  const response = await fetch(API_BASE)
  return handleResponse<VideoStreamListResponse>(response)
}

/**
 * 获取视频流详情
 */
export async function getStream(streamId: string): Promise<VideoStream> {
  const response = await fetch(`${API_BASE}/${streamId}`)
  return handleResponse<VideoStream>(response)
}

/**
 * 获取最新检测结果
 */
export async function getLatestResult(streamId: string): Promise<DetectionResult | null> {
  const response = await fetch(`${API_BASE}/${streamId}/latest-result`)
  return handleResponse<DetectionResult | null>(response)
}

/**
 * 启动视频流
 * 
 * 方案 F：默认启用服务端热力图渲染
 * - play_url 返回渲染流地址（{stream_id}_heatmap）
 * - options.enable_infer 已废弃，保留用于向后兼容
 */
export async function startStream(
  streamId: string,
  options?: VideoStreamStart
): Promise<VideoStream> {
  const response = await fetch(`${API_BASE}/${streamId}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: options ? JSON.stringify(options) : undefined
  })
  return handleResponse<VideoStream>(response)
}

/**
 * 停止视频流
 */
export async function stopStream(streamId: string): Promise<VideoStream> {
  const response = await fetch(`${API_BASE}/${streamId}/stop`, {
    method: 'POST'
  })
  return handleResponse<VideoStream>(response)
}

/**
 * 删除视频流
 */
export async function deleteStream(streamId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${streamId}`, {
    method: 'DELETE'
  })
  return handleResponse<void>(response)
}


