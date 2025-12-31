/**
 * Pinia Store - 流状态管理
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

export const useStreamsStore = defineStore('streams', () => {
  // 状态
  const streams = ref<Map<string, VideoStream>>(new Map())
  const detectionResults = ref<Map<string, DetectionResult>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // WebSocket 连接
  const resultSockets = ref<Map<string, ResultWebSocket>>(new Map())
  const statusSocket = ref<StatusWebSocket | null>(null)
  const wsConnected = ref(false)

  // 计算属性
  const streamList = computed(() => Array.from(streams.value.values()))
  const runningStreams = computed(() =>
    streamList.value.filter((s) => s.status === 'running')
  )

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
      error.value = e instanceof Error ? e.message : 'Failed to fetch streams'
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
      return stream
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create stream'
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
    try {
      const stream = await api.startStream(streamId, options)
      streams.value.set(stream.stream_id, stream)
      return stream
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start stream'
      throw e
    }
  }

  // 停止流
  async function stopStream(streamId: string): Promise<VideoStream> {
    error.value = null
    try {
      const stream = await api.stopStream(streamId)
      streams.value.set(stream.stream_id, stream)
      // 断开该流的 WebSocket
      unsubscribeResult(streamId)
      return stream
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to stop stream'
      throw e
    }
  }

  // 删除流
  async function deleteStream(streamId: string): Promise<void> {
    error.value = null
    try {
      await api.deleteStream(streamId)
      streams.value.delete(streamId)
      detectionResults.value.delete(streamId)
      unsubscribeResult(streamId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete stream'
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
          streams.value.set(status.stream_id, {
            ...stream,
            status: status.status,
            play_url: status.play_url ?? stream.play_url
          })
        }
      },
      (connected) => {
        wsConnected.value = connected
        console.log(`Status WebSocket: ${connected ? 'connected' : 'disconnected'}`)
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

  // 清理所有连接
  function cleanup(): void {
    for (const ws of resultSockets.value.values()) {
      ws.disconnect()
    }
    resultSockets.value.clear()
    unsubscribeStatus()
  }

  return {
    // 状态
    streams,
    detectionResults,
    loading,
    error,
    wsConnected,

    // 计算属性
    streamList,
    runningStreams,

    // 方法
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
