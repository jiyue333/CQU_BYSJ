/**
 * ROI 管理 API 封装
 * Requirements: 3.1, 3.2, 3.5
 */

import type { ROITemplateListResponse } from '@/types'
import { handleResponse } from './request'

const API_BASE = '/api/streams'
const TEMPLATE_BASE = '/api/rois'

// ROI 相关类型定义
export interface Point {
  x: number
  y: number
}

export interface DensityThresholds {
  low: number
  medium: number
  high: number
}

export interface ROI {
  roi_id: string
  stream_id: string
  name: string
  points: Point[]
  density_thresholds: DensityThresholds
  created_at: string
  updated_at: string
}

export interface ROICreate {
  name: string
  points: Point[]
  density_thresholds?: DensityThresholds
}

export interface ROIUpdate {
  name?: string
  points?: Point[]
  density_thresholds?: DensityThresholds
}

export interface ROIListResponse {
  rois: ROI[]
  total: number
}

// ApiRequestError and handleResponse moved to ./request

/**
 * 创建 ROI
 */
export async function createROI(streamId: string, data: ROICreate): Promise<ROI> {
  const response = await fetch(`${API_BASE}/${streamId}/rois`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<ROI>(response)
}

/**
 * 获取 ROI 列表
 */
export async function listROIs(streamId: string): Promise<ROIListResponse> {
  const response = await fetch(`${API_BASE}/${streamId}/rois`)
  return handleResponse<ROIListResponse>(response)
}

/**
 * 获取 ROI 详情
 */
export async function getROI(streamId: string, roiId: string): Promise<ROI> {
  const response = await fetch(`${API_BASE}/${streamId}/rois/${roiId}`)
  return handleResponse<ROI>(response)
}

/**
 * 更新 ROI
 */
export async function updateROI(
  streamId: string,
  roiId: string,
  data: ROIUpdate
): Promise<ROI> {
  const response = await fetch(`${API_BASE}/${streamId}/rois/${roiId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<ROI>(response)
}

/**
 * 删除 ROI
 */
export async function deleteROI(streamId: string, roiId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${streamId}/rois/${roiId}`, {
    method: 'DELETE'
  })
  return handleResponse<void>(response)
}

/**
 * 获取 ROI 模板列表
 */
export async function listROITemplates(): Promise<ROITemplateListResponse> {
  const response = await fetch(`${TEMPLATE_BASE}/templates`)
  return handleResponse<ROITemplateListResponse>(response)
}

/**
 * 应用 ROI 模板
 */
export async function applyROIPreset(
  streamId: string,
  templateId: string,
  replaceExisting = false
): Promise<ROIListResponse> {
  const response = await fetch(`${API_BASE}/${streamId}/rois/preset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_id: templateId, replace_existing: replaceExisting })
  })
  return handleResponse<ROIListResponse>(response)
}


