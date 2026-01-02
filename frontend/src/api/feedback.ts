/**
 * 反馈 API 封装
 */

// import type { ApiError } from '@/types'
import { handleResponse } from './request'

const API_BASE = '/api/feedback'

// ApiRequestError and handleResponse moved to ./request

export async function submitFeedback(data: {
  stream_id: string
  message?: string
  payload?: Record<string, unknown>
}): Promise<void> {
  const response = await fetch(`${API_BASE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  await handleResponse(response)
}


