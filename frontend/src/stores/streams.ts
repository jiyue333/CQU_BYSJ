/**
 * Pinia Store - 流状态管理
 * 包含错误通知和重连状态管理
 * Requirements: 5.3, 9.1, 9.2, 9.4
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  VideoStream,
  VideoStreamCreate,
  VideoStreamStart,
  DetectionResult,
  StreamStatusUpdate
} from '@/types'
import * as api from '@/api'
import { ResultWebSocket, StatusWebSocket } from '@/services/websocket'

// 通知类型
export interface Notification {
  id: number
  type: 'error' | 'warning' | 'success' | 'info'
  message: string
  duration?: number
}

// 重连状态
export interface ReconnectionState {
  streamId: string
  isReconnecting: boolean
  attemptCount: number
  maxAttempts: number
  lastError?: string
}

let notificationId = 0

export const useStreamsStore = defineStore('streams', () => {
  // 状态
  const streams = ref<Map<string, VideoStream>>(new Map())
  const detectionResults = ref<Map<string, DetectionResult>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 通知状态
  const notifications = ref<Notification[]>([])

  // 重连状态
  const reconnectionStates = ref<Map<string, ReconnectionState>>(new Map())

  // WebSocket 连接
  const resultSockets = ref<Map<string, ResultWebSocket>>(new Map())
  const statusSocket = ref<StatusWebSocket | null>(null)
  const wsConnected = ref(false)

  // 计算属性
  const streamList = computed(() => Array.from(streams.value.values()))
  const runningStreams = computed(() =>
    streamList.value.filter((s) => s.status === 'running')
  )

  // 添加通知
  function addNotification(
    type: Notification['type'],
    message: string,
    duration?: number
  ): number {
    const id = ++notificationId
    notifications.value.push({ id, type, message, duration })
    return id
  }

  // 移除通知
  function removeNotification(id: number): void {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  // 显示错误通知
  function showError(message: string, duration?: number): number {
    return addNotification('error', message, duration)
  }

  // 显示警告通知
  function showWarning(message: string, duration?: number): number {
    return addNotification('warning', message, duration)
  }

  // 显示成功通知
  function showSuccess(message: string, duration?: number): number {
    return addNotification('success', message, duration)
  }

  // 显示信息通知
  function showInfo(message: string, duration?: number): number {
    return addNotification('info', message, duration)
  }

  // 更新重连状态
  function updateReconnectionState(
    streamId: string,
    state: Partial<ReconnectionState>
  ): void {
    const current = reconnectionStates.value.get(streamId) || {
      streamId,
      isReconnecting: false,
      attemptCount: 0,
      maxAttempts: 5
    }
    reconnectionStates.value.set(streamId, { ...current, ...state })
  }

  // 清除重连状态
  function clearReconnectionState(streamId: string): void {
    reconnectionStates.value.delete(streamId)
  }

  // 获取流列表
  async function fetchStreams(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const response = await api.listStreams()
      streams.value.clear()
      for (const stream of response.streams) {
        streams.value.set(stream.stream_id, stream)
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch streams'
      error.value = message
      showError(`获取流列表失败: ${message}`)
      throw e
    } finally {
      loading.value = false
    }
  }

  // 创建流
  async function createStream(data: VideoStreamCreate): Promise<VideoStream> {
    loading.value = true
    error.value = null
    try {
      const stream = await api.createStream(data)
      streams.value.set(stream.stream_id, stream)
      showSuccess(`视频流 "${stream.name}" 创建成功`)
      return stream
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to create stream'
      error.value = message
      showError(`创建流失败: ${message}`)
      throw e
    } finally {
      loading.value = false
    }
  }

  // 启动流
  async function startStream(
    streamId: string,
    options?: VideoStreamStart
  ): Promise<VideoStream> {
    error.value = null
    clearReconnectionState(streamId)
    try {
      const stream = await api.startStream(streamId, options)
      streams.value.set(stream.stream_id, stream)
      showSuccess(`视频流已启动`)
      return stream
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to start stream'
      error.value = message
      showError(`启动流失败: ${message}`)
      throw e
    }
  }

  // 停止流
  async function stopStream(streamId: string): Promise<VideoStream> {
    error.value = null
    clearReconnectionState(streamId)
    try {
      const stream = await api.stopStream(streamId)
      streams.value.set(stream.stream_id, stream)
      // 断开该流的 WebSocket
      unsubscribeResult(streamId)
      showInfo(`视频流已停止`)
      return stream
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to stop stream'
      error.value = message
      showError(`停止流失败: ${message}`)
      throw e
    }
  }

  // 删除流
  async function deleteStream(streamId: string): Promise<void> {
    error.value = null
    clearReconnectionState(streamId)
    try {
      await api.deleteStream(streamId)
      streams.value.delete(streamId)
      detectionResults.value.delete(streamId)
      unsubscribeResult(streamId)
      showSuccess(`视频流已删除`)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to delete stream'
      error.value = message
      showError(`删除流失败: ${message}`)
      throw e
    }
  }

  // 订阅检测结果
  function subscribeResult(streamId: string): void {
    if (resultSockets.value.has(streamId)) {
      return
    }

    const ws = new ResultWebSocket(streamId)
    ws.connect(
      (result) => {
        detectionResults.value.set(streamId, result)
      },
      (connected) => {
        console.log(`Result WebSocket ${streamId}: ${connected ? 'connected' : 'disconnected'}`)
        if (!connected) {
          // WebSocket 断开时更新重连状态
          const current = reconnectionStates.value.get(streamId)
          if (current) {
            updateReconnectionState(streamId, {
              isReconnecting: true,
              attemptCount: (current.attemptCount || 0) + 1
            })
          }
        } else {
          // 连接成功时清除重连状态
          clearReconnectionState(streamId)
        }
      }
    )
    resultSockets.value.set(streamId, ws)
  }

  // 取消订阅检测结果
  function unsubscribeResult(streamId: string): void {
    const ws = resultSockets.value.get(streamId)
    if (ws) {
      ws.disconnect()
      resultSockets.value.delete(streamId)
    }
    clearReconnectionState(streamId)
  }

  // 订阅状态变更
  function subscribeStatus(): void {
    if (statusSocket.value) {
      return
    }

    const ws = new StatusWebSocket()
    ws.connect(
      (status: StreamStatusUpdate) => {
        const stream = streams.value.get(status.stream_id)
        if (stream) {
          const oldStatus = stream.status
          streams.value.set(status.stream_id, {
            ...stream,
            status: status.status,
            play_url: status.play_url ?? stream.play_url
          })

          // 状态变更通知
          if (oldStatus !== status.status) {
            if (status.status === 'error') {
              showError(`视频流 "${stream.name}" 发生错误: ${status.error || '未知错误'}`)
            } else if (status.status === 'cooldown') {
              showWarning(`视频流 "${stream.name}" 进入冷却状态，将在 60 秒后自动重试`)
            } else if (status.status === 'running' && oldStatus === 'cooldown') {
              showSuccess(`视频流 "${stream.name}" 已恢复运行`)
            }
          }
        }
      },
      (connected) => {
        wsConnected.value = connected
        console.log(`Status WebSocket: ${connected ? 'connected' : 'disconnected'}`)
        if (!connected) {
          showWarning('WebSocket 连接已断开，正在重连...')
        } else {
          // 连接恢复时刷新流列表
          fetchStreams().catch(() => {})
        }
      }
    )
    statusSocket.value = ws
  }

  // 取消订阅状态变更
  function unsubscribeStatus(): void {
    if (statusSocket.value) {
      statusSocket.value.disconnect()
      statusSocket.value = null
    }
  }

  // 获取流的检测结果
  function getDetectionResult(streamId: string): DetectionResult | undefined {
    return detectionResults.value.get(streamId)
  }

  // 获取流的重连状态
  function getReconnectionState(streamId: string): ReconnectionState | undefined {
    return reconnectionStates.value.get(streamId)
  }

  // 清理所有连接
  function cleanup(): void {
    for (const ws of resultSockets.value.values()) {
      ws.disconnect()
    }
    resultSockets.value.clear()
    unsubscribeStatus()
    reconnectionStates.value.clear()
    notifications.value = []
  }

  return {
    // 状态
    streams,
    detectionResults,
    loading,
    error,
    wsConnected,
    notifications,
    reconnectionStates,

    // 计算属性
    streamList,
    runningStreams,

    // 通知方法
    addNotification,
    removeNotification,
    showError,
    showWarning,
    showSuccess,
    showInfo,

    // 重连状态方法
    updateReconnectionState,
    clearReconnectionState,
    getReconnectionState,

    // 流管理方法
    fetchStreams,
    createStream,
    startStream,
    stopStream,
    deleteStream,
    subscribeResult,
    unsubscribeResult,
    subscribeStatus,
    unsubscribeStatus,
    getDetectionResult,
    cleanup
  }
})
