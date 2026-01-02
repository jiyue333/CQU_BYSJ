/**
 * 配置管理 API 封装
 * Requirements: 8.1, 8.2, 8.3, 8.4
 */

import type { SystemConfig, SystemConfigUpdate, ConfigPresetListResponse } from '@/types'
import { handleResponse } from './request'

const API_BASE = '/api/config'

// ApiRequestError and handleResponse moved to ./request

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

/**
 * 获取配置预设
 */
export async function getConfigPresets(): Promise<ConfigPresetListResponse> {
  const response = await fetch(`${API_BASE}/presets`)
  return handleResponse<ConfigPresetListResponse>(response)
}


