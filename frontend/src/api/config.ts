/**
 * 配置管理 API 封装
 * Requirements: 8.1, 8.2, 8.3, 8.4
 */

import type { SystemConfig, SystemConfigUpdate, ApiError } from '@/types'

const API_BASE = '/api/config'

class ApiRequestError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiRequestError'
    this.status = status
    this.detail = detail
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const error: ApiError = await response.json()
      detail = error.detail || detail
    } catch {
      // ignore JSON parse error
    }
    throw new ApiRequestError(response.status, detail)
  }

  return response.json()
}

/**
 * 获取流配置
 */
export async function getConfig(streamId: string): Promise<SystemConfig> {
  const response = await fetch(`${API_BASE}/${streamId}`)
  return handleResponse<SystemConfig>(response)
}

/**
 * 更新流配置
 */
export async function updateConfig(
  streamId: string,
  data: SystemConfigUpdate
): Promise<SystemConfig> {
  const response = await fetch(`${API_BASE}/${streamId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<SystemConfig>(response)
}

export { ApiRequestError }
