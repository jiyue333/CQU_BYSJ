/**
 * 告警相关 API 封装
 */

import type {
  AlertEvent,
  AlertEventListResponse,
  AlertRule,
  AlertRuleListResponse
} from '@/types'
import { handleResponse } from './request'

const API_BASE = '/api/alerts'

// ApiRequestError and handleResponse moved to ./request

export async function listAlertRules(streamId?: string): Promise<AlertRuleListResponse> {
  const params = new URLSearchParams()
  if (streamId) params.set('stream_id', streamId)
  const response = await fetch(`${API_BASE}/rules?${params.toString()}`)
  return handleResponse<AlertRuleListResponse>(response)
}

export async function createAlertRule(data: Partial<AlertRule>): Promise<AlertRule> {
  const response = await fetch(`${API_BASE}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<AlertRule>(response)
}

export async function updateAlertRule(ruleId: string, data: Partial<AlertRule>): Promise<AlertRule> {
  const response = await fetch(`${API_BASE}/rules/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return handleResponse<AlertRule>(response)
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/rules/${ruleId}`, { method: 'DELETE' })
  if (!response.ok) {
    await handleResponse(response)
  }
}

export async function listAlertEvents(params: {
  stream_id?: string
  start_ts?: number
  end_ts?: number
  limit?: number
  offset?: number
}): Promise<AlertEventListResponse> {
  const query = new URLSearchParams()
  if (params.stream_id) query.set('stream_id', params.stream_id)
  if (params.start_ts) query.set('start_ts', params.start_ts.toString())
  if (params.end_ts) query.set('end_ts', params.end_ts.toString())
  if (params.limit) query.set('limit', params.limit.toString())
  if (params.offset) query.set('offset', params.offset.toString())
  const response = await fetch(`${API_BASE}/events?${query.toString()}`)
  return handleResponse<AlertEventListResponse>(response)
}

export async function acknowledgeAlert(eventId: string): Promise<AlertEvent> {
  const response = await fetch(`${API_BASE}/events/${eventId}/acknowledge`, {
    method: 'POST'
  })
  return handleResponse<AlertEvent>(response)
}


