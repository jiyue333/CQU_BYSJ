/**
 * WebSocket 服务
 * 支持自动重连（指数退避）和断点续传
 * Requirements: 5.3, 9.1, 9.2
 */

import type { DetectionResult, StreamStatusUpdate, WsMessage } from '@/types'

// 重连配置
const RECONNECT_BASE_DELAY = 1000 // 1s
const RECONNECT_MAX_DELAY = 30000 // 30s
const RECONNECT_JITTER = 0.2 // ±20% jitter
const RECONNECT_MAX_ATTEMPTS = 5 // 最大重连次数
const HEARTBEAT_INTERVAL = 30000 // 30s

// Calculate backoff with jitter
function calculateBackoff(attempts: number): number {
  const baseDelay = Math.min(
    RECONNECT_BASE_DELAY * Math.pow(2, attempts),
    RECONNECT_MAX_DELAY
  )
  // Add jitter: ±20%
  const jitter = baseDelay * RECONNECT_JITTER * (Math.random() * 2 - 1)
  return Math.max(RECONNECT_BASE_DELAY, baseDelay + jitter)
}

type ResultCallback = (result: DetectionResult) => void
type StatusCallback = (status: StreamStatusUpdate) => void
type ConnectionCallback = (connected: boolean) => void
type ReconnectCallback = (attempt: number, maxAttempts: number, delay: number) => void
type ErrorCallback = (error: string) => void

/**
 * 检测结果 WebSocket 服务
 */
export class ResultWebSocket {
  private ws: WebSocket | null = null
  private streamId: string
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private lastMsgId: string | null = null
  private isManualClose = false

  private onResult: ResultCallback | null = null
  private onConnection: ConnectionCallback | null = null
  private onReconnect: ReconnectCallback | null = null
  private onError: ErrorCallback | null = null

  constructor(streamId: string) {
    this.streamId = streamId
  }

  /**
   * 连接 WebSocket
   */
  connect(
    onResult: ResultCallback,
    onConnection?: ConnectionCallback,
    onReconnect?: ReconnectCallback,
    onError?: ErrorCallback
  ): void {
    this.onResult = onResult
    this.onConnection = onConnection || null
    this.onReconnect = onReconnect || null
    this.onError = onError || null
    this.isManualClose = false
    this.reconnectAttempts = 0
    this.doConnect()
  }

  private doConnect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/result/${this.streamId}`

    try {
      this.ws = new WebSocket(url)
    } catch (err) {
      console.error('WebSocket creation failed:', err)
      this.onError?.(`WebSocket 创建失败: ${err}`)
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.startHeartbeat()
      this.onConnection?.(true)

      // 断点续传：请求恢复遗漏消息
      if (this.lastMsgId) {
        this.send({ type: 'recover', last_id: this.lastMsgId })
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        this.handleMessage(msg)
      } catch {
        console.error('Failed to parse WebSocket message:', event.data)
      }
    }

    this.ws.onclose = (event) => {
      this.stopHeartbeat()
      this.onConnection?.(false)

      if (!this.isManualClose) {
        // 非正常关闭，记录原因
        if (event.code !== 1000) {
          console.warn(`WebSocket closed abnormally: code=${event.code}, reason=${event.reason}`)
        }
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.onError?.('WebSocket 连接错误')
    }
  }

  private handleMessage(msg: WsMessage): void {
    switch (msg.type) {
      case 'pong':
        // 心跳响应，无需处理
        break

      case 'result':
      case 'recovery':
        if (msg.msg_id) {
          this.lastMsgId = msg.msg_id
        }
        if (msg.data && this.onResult) {
          this.onResult(msg.data as DetectionResult)
        }
        break

      case 'recovery_complete':
        console.log(`Recovery complete: ${msg.count} messages`)
        break
    }
  }

  private send(msg: WsMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping', ts: Date.now() })
    }, HEARTBEAT_INTERVAL)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    // 检查是否超过最大重连次数
    if (this.reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      console.error(`Max reconnection attempts (${RECONNECT_MAX_ATTEMPTS}) reached`)
      this.onError?.(`重连失败：已达到最大重试次数 (${RECONNECT_MAX_ATTEMPTS})`)
      return
    }

    // Check if browser is online
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      console.log('Browser is offline, waiting for online event...')
      const onOnline = () => {
        window.removeEventListener('online', onOnline)
        this.scheduleReconnect()
      }
      window.addEventListener('online', onOnline)
      return
    }

    // Exponential backoff with jitter
    const delay = calculateBackoff(this.reconnectAttempts)

    console.log(`Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts + 1}/${RECONNECT_MAX_ATTEMPTS})`)
    
    // 通知重连状态
    this.onReconnect?.(this.reconnectAttempts + 1, RECONNECT_MAX_ATTEMPTS, delay)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.doConnect()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取当前重连次数
   */
  get currentReconnectAttempts(): number {
    return this.reconnectAttempts
  }
}

/**
 * 状态变更 WebSocket 服务
 */
export class StatusWebSocket {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private isManualClose = false

  private onStatus: StatusCallback | null = null
  private onConnection: ConnectionCallback | null = null
  private onReconnect: ReconnectCallback | null = null
  private onError: ErrorCallback | null = null

  /**
   * 连接 WebSocket
   */
  connect(
    onStatus: StatusCallback,
    onConnection?: ConnectionCallback,
    onReconnect?: ReconnectCallback,
    onError?: ErrorCallback
  ): void {
    this.onStatus = onStatus
    this.onConnection = onConnection || null
    this.onReconnect = onReconnect || null
    this.onError = onError || null
    this.isManualClose = false
    this.reconnectAttempts = 0
    this.doConnect()
  }

  private doConnect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/status`

    try {
      this.ws = new WebSocket(url)
    } catch (err) {
      console.error('WebSocket creation failed:', err)
      this.onError?.(`WebSocket 创建失败: ${err}`)
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.startHeartbeat()
      this.onConnection?.(true)
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        this.handleMessage(msg)
      } catch {
        console.error('Failed to parse WebSocket message:', event.data)
      }
    }

    this.ws.onclose = (event) => {
      this.stopHeartbeat()
      this.onConnection?.(false)

      if (!this.isManualClose) {
        if (event.code !== 1000) {
          console.warn(`WebSocket closed abnormally: code=${event.code}, reason=${event.reason}`)
        }
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.onError?.('WebSocket 连接错误')
    }
  }

  private handleMessage(msg: WsMessage): void {
    switch (msg.type) {
      case 'pong':
        break

      case 'status':
        if (msg.data && this.onStatus) {
          this.onStatus(msg.data as StreamStatusUpdate)
        }
        break
    }
  }

  private send(msg: WsMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping', ts: Date.now() })
    }, HEARTBEAT_INTERVAL)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    // 检查是否超过最大重连次数
    if (this.reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      console.error(`Max reconnection attempts (${RECONNECT_MAX_ATTEMPTS}) reached`)
      this.onError?.(`重连失败：已达到最大重试次数 (${RECONNECT_MAX_ATTEMPTS})`)
      return
    }

    // Check if browser is online
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      console.log('Browser is offline, waiting for online event...')
      const onOnline = () => {
        window.removeEventListener('online', onOnline)
        this.scheduleReconnect()
      }
      window.addEventListener('online', onOnline)
      return
    }

    // Exponential backoff with jitter
    const delay = calculateBackoff(this.reconnectAttempts)

    console.log(`Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts + 1}/${RECONNECT_MAX_ATTEMPTS})`)
    
    // 通知重连状态
    this.onReconnect?.(this.reconnectAttempts + 1, RECONNECT_MAX_ATTEMPTS, delay)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.doConnect()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取当前重连次数
   */
  get currentReconnectAttempts(): number {
    return this.reconnectAttempts
  }
}
