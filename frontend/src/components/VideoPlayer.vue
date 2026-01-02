<script setup lang="ts">
/**
 * 视频播放器组件
 * 协议优先级：WebRTC → HTTP-FLV → HLS
 * 包含连接状态和处理状态指示
 * Requirements: 1.1, 1.2, 1.3, 9.2, 9.4
 */

import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import flvjs from 'flv.js'
import Hls from 'hls.js'

const props = defineProps<{
  playUrl: string | null
  webrtcUrl?: string | null
  streamId: string
  status?: string
  playbackDelaySec?: number
  preferredProtocol?: 'auto' | 'webrtc' | 'flv' | 'hls'
}>()

const emit = defineEmits<{
  playing: []
  error: [message: string]
  protocolChange: [protocol: string]
}>()

// 播放器状态
type Protocol = 'webrtc' | 'flv' | 'hls' | 'none'
const currentProtocol = ref<Protocol>('none')
const isPlaying = ref(false)
const errorMessage = ref('')
const videoRef = ref<HTMLVideoElement | null>(null)
const isBuffering = ref(false)
const latencyMs = ref<number | null>(null)
const webrtcStats = ref({
  jitter: 0,
  framesDropped: 0,
  framesPerSecond: 0
})

// 播放器实例
let flvPlayer: flvjs.Player | null = null
let hlsPlayer: Hls | null = null
let rtcConnection: RTCPeerConnection | null = null
let delayTimer: ReturnType<typeof setInterval> | null = null
let latencyTimer: ReturnType<typeof setInterval> | null = null
let webrtcStatsTimer: ReturnType<typeof setInterval> | null = null

const DELAY_CHECK_INTERVAL_MS = 200
const MIN_DELAY_MARGIN_SEC = 0.15

// Playback token to prevent race conditions
let playbackToken = 0

// 检测 URL 类型
function detectUrlType(url: string): 'flv' | 'hls' | 'unknown' {
  const lowerUrl = url.toLowerCase()
  if (lowerUrl.includes('.flv') || lowerUrl.includes('/live/')) {
    return 'flv'
  }
  if (lowerUrl.includes('.m3u8') || lowerUrl.includes('/hls/')) {
    return 'hls'
  }
  return 'unknown'
}

// 从 playUrl 推断 WebRTC URL
function inferWebRTCUrl(playUrl: string): string | null {
  try {
    const url = new URL(playUrl)
    // 从 HLS URL 提取 app 和 stream
    // 格式: http://host/live/streamId/hls.m3u8
    const pathParts = url.pathname.split('/').filter(Boolean)
    if (pathParts.length >= 2) {
      const app = pathParts[0] // 'live'
      const stream = pathParts[1] // streamId
      return `${url.origin}/index/api/webrtc?app=${app}&stream=${stream}&type=play`
    }
  } catch {
    // ignore
  }
  return null
}

// 解析播放地址，获取各协议 URL
const urls = computed(() => {
  if (!props.playUrl) return null

  const urlType = detectUrlType(props.playUrl)
  
  // Parse URL properly to handle query strings
  let baseUrl: string
  let queryString = ''
  
  const queryIndex = props.playUrl.indexOf('?')
  if (queryIndex !== -1) {
    baseUrl = props.playUrl.substring(0, queryIndex)
    queryString = props.playUrl.substring(queryIndex)
  } else {
    baseUrl = props.playUrl
  }
  
  // Remove /hls.m3u8 or extension if present
  if (baseUrl.endsWith('/hls.m3u8')) {
    baseUrl = baseUrl.slice(0, -9) // Remove '/hls.m3u8'
  } else {
    const extMatch = baseUrl.match(/\.(flv|m3u8)$/i)
    if (extMatch) {
      baseUrl = baseUrl.substring(0, baseUrl.length - extMatch[0].length)
    }
  }

  // WebRTC URL: 优先使用 props，否则从 playUrl 推断
  const webrtcUrl = props.webrtcUrl || inferWebRTCUrl(props.playUrl)

  return {
    flv: baseUrl + '.flv' + queryString,
    hls: baseUrl + '/hls.m3u8' + queryString,
    webrtc: webrtcUrl,
    detectedType: urlType
  }
})

// 清理播放器
function cleanup() {
  // Increment token to invalidate pending callbacks
  playbackToken++
  
  if (flvPlayer) {
    try {
      flvPlayer.pause()
      flvPlayer.unload()
      flvPlayer.detachMediaElement()
      flvPlayer.destroy()
    } catch {
      // Ignore cleanup errors
    }
    flvPlayer = null
  }

  if (hlsPlayer) {
    try {
      hlsPlayer.destroy()
    } catch {
      // Ignore cleanup errors
    }
    hlsPlayer = null
  }

  if (rtcConnection) {
    rtcConnection.close()
    rtcConnection = null
  }
  
  if (delayTimer) {
    clearInterval(delayTimer)
    delayTimer = null
  }

  stopLatencyMonitor()

  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.src = ''
  }

  isPlaying.value = false
  isBuffering.value = false
  currentProtocol.value = 'none'
}

// 监听视频缓冲状态
function setupBufferingListeners() {
  if (!videoRef.value) return
  
  videoRef.value.addEventListener('waiting', () => {
    isBuffering.value = true
  })
  
  videoRef.value.addEventListener('playing', () => {
    isBuffering.value = false
  })
  
  videoRef.value.addEventListener('canplay', () => {
    isBuffering.value = false
  })
}

function getBufferedEnd(video: HTMLVideoElement): number {
  const buffered = video.buffered
  if (!buffered || buffered.length === 0) return 0
  return buffered.end(buffered.length - 1)
}

function startDelayControl(video: HTMLVideoElement, delaySec: number) {
  if (delayTimer) {
    clearInterval(delayTimer)
    delayTimer = null
  }
  
  if (!delaySec || delaySec <= 0) return
  
  const margin = Math.max(MIN_DELAY_MARGIN_SEC, Math.min(delaySec * 0.25, 0.4))
  
  delayTimer = setInterval(() => {
    if (video.readyState < 2) return
    const bufferedEnd = getBufferedEnd(video)
    if (!Number.isFinite(bufferedEnd) || bufferedEnd <= 0) return
    
    const latency = bufferedEnd - video.currentTime
    if (!Number.isFinite(latency)) return
    
    if (latency < delaySec - margin) {
      if (!video.paused) {
        video.pause()
      }
      return
    }
    
    if (latency > delaySec + margin * 2) {
      const target = bufferedEnd - delaySec
      if (target > 0 && Math.abs(video.currentTime - target) > margin) {
        try {
          video.currentTime = target
        } catch {
          // Ignore seek errors
        }
      }
    }
    
    if (video.paused) {
      video.play().catch(() => {})
    }
  }, DELAY_CHECK_INTERVAL_MS)
}

function stopLatencyMonitor() {
  if (latencyTimer) {
    clearInterval(latencyTimer)
    latencyTimer = null
  }
  if (webrtcStatsTimer) {
    clearInterval(webrtcStatsTimer)
    webrtcStatsTimer = null
  }
  latencyMs.value = null
  webrtcStats.value = { jitter: 0, framesDropped: 0, framesPerSecond: 0 }
}

function startLatencyMonitor() {
  stopLatencyMonitor()

  if (!videoRef.value) return

  latencyTimer = setInterval(() => {
    if (!videoRef.value) return
    if (currentProtocol.value === 'flv' || currentProtocol.value === 'hls') {
      const bufferedEnd = getBufferedEnd(videoRef.value)
      const latency = bufferedEnd - videoRef.value.currentTime
      if (Number.isFinite(latency) && latency >= 0) {
        latencyMs.value = Math.round(latency * 1000)
      }
    }
  }, 500)

  if (currentProtocol.value === 'webrtc' && rtcConnection) {
    webrtcStatsTimer = setInterval(async () => {
      if (!rtcConnection) return
      try {
        const stats = await rtcConnection.getStats()
        stats.forEach((report) => {
          const mediaType = report.kind || report.mediaType
          if (report.type === 'inbound-rtp' && mediaType === 'video') {
            webrtcStats.value = {
              jitter: report.jitter || 0,
              framesDropped: report.framesDropped || 0,
              framesPerSecond: report.framesPerSecond || 0
            }
          }
        })
      } catch {
        // ignore getStats errors
      }
    }, 1000)
  }
}

// 尝试 WebRTC 播放 (WHEP 协议)
async function tryWebRTC(token: number): Promise<boolean> {
  if (!urls.value?.webrtc || !videoRef.value) {
    console.log('WebRTC: No URL or video element')
    return false
  }

  // Check if this attempt is still valid
  if (token !== playbackToken) {
    return false
  }

  console.log('Trying WebRTC:', urls.value.webrtc)

  return new Promise((resolve) => {
    let resolved = false
    let gotTrack = false
    
    const doResolve = (result: boolean) => {
      if (resolved) return
      resolved = true
      clearTimeout(timeoutId)
      resolve(result)
    }

    const timeoutId = setTimeout(() => {
      // 如果已经收到 track，再等一会儿
      if (gotTrack && !resolved) {
        console.log('WebRTC: Got track but still waiting, extending timeout...')
        setTimeout(() => {
          if (!resolved) {
            console.log('WebRTC: Extended timeout reached')
            if (rtcConnection) {
              rtcConnection.close()
              rtcConnection = null
            }
            doResolve(false)
          }
        }, 5000)
        return
      }
      
      console.log('WebRTC: Timeout (no track received)')
      if (rtcConnection) {
        rtcConnection.close()
        rtcConnection = null
      }
      doResolve(false)
    }, 8000)

    try {
      // 创建 RTCPeerConnection
      rtcConnection = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      })

      // 监听远程流
      rtcConnection.ontrack = (event) => {
        console.log('WebRTC: Got remote track', event.track.kind)
        gotTrack = true
        
        if (token !== playbackToken) {
          doResolve(false)
          return
        }
        
        if (event.streams && event.streams[0] && videoRef.value) {
          videoRef.value.srcObject = event.streams[0]
          
          // 等待视频可以播放
          const video = videoRef.value
          
          const tryPlay = () => {
            if (resolved || token !== playbackToken) return
            
            video.play().then(() => {
              if (token === playbackToken && !resolved) {
                console.log('WebRTC: Playing successfully')
                currentProtocol.value = 'webrtc'
                isPlaying.value = true
                emit('playing')
                emit('protocolChange', 'WebRTC')
                startLatencyMonitor()
                doResolve(true)
              }
            }).catch((err) => {
              // 如果是 AbortError，可能是还没准备好，稍后重试
              if (err.name === 'AbortError' && !resolved) {
                console.log('WebRTC: Play aborted, will retry on canplay')
              } else {
                console.error('WebRTC: Play failed', err)
                doResolve(false)
              }
            })
          }
          
          // 监听 canplay 事件
          video.addEventListener('canplay', tryPlay, { once: true })
          
          // 也立即尝试播放
          tryPlay()
        }
      }

      rtcConnection.oniceconnectionstatechange = () => {
        console.log('WebRTC ICE state:', rtcConnection?.iceConnectionState)
        if (rtcConnection?.iceConnectionState === 'connected') {
          console.log('WebRTC: ICE connected')
        }
        if (rtcConnection?.iceConnectionState === 'failed') {
          console.log('WebRTC: ICE failed')
          doResolve(false)
        }
      }

      // 添加 transceiver 以接收视频和音频
      rtcConnection.addTransceiver('video', { direction: 'recvonly' })
      rtcConnection.addTransceiver('audio', { direction: 'recvonly' })

      // 创建 offer
      rtcConnection.createOffer().then((offer) => {
        return rtcConnection!.setLocalDescription(offer)
      }).then(() => {
        // 等待 ICE gathering 完成或超时
        return new Promise<void>((iceResolve) => {
          if (rtcConnection!.iceGatheringState === 'complete') {
            iceResolve()
          } else {
            const checkState = () => {
              if (rtcConnection?.iceGatheringState === 'complete') {
                rtcConnection.removeEventListener('icegatheringstatechange', checkState)
                iceResolve()
              }
            }
            rtcConnection!.addEventListener('icegatheringstatechange', checkState)
            // 最多等待 2 秒
            setTimeout(iceResolve, 2000)
          }
        })
      }).then(() => {
        // 发送 offer 到 ZLMediaKit WebRTC API
        const sdp = rtcConnection!.localDescription!.sdp
        return fetch(urls.value!.webrtc!, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: sdp
        })
      }).then(async (response) => {
        if (!response.ok) {
          // 尝试读取 JSON 错误
          const text = await response.text()
          console.error('WebRTC: Server error', response.status, text)
          throw new Error(`Server error: ${response.status}`)
        }
        const contentType = response.headers.get('content-type') || ''
        if (contentType.includes('application/sdp')) {
          return response.text()
        } else {
          // ZLMediaKit 可能返回 JSON
          const json = await response.json()
          if (json.code === 0 && json.sdp) {
            return json.sdp
          }
          throw new Error(json.msg || 'Invalid response')
        }
      }).then((answerSdp) => {
        console.log('WebRTC: Got answer SDP')
        return rtcConnection!.setRemoteDescription({
          type: 'answer',
          sdp: answerSdp
        })
      }).catch((err) => {
        console.error('WebRTC: Setup failed', err)
        doResolve(false)
      })
    } catch (err) {
      console.error('WebRTC: Init error', err)
      doResolve(false)
    }
  })
}

// 尝试 HTTP-FLV 播放
async function tryFlv(token: number): Promise<boolean> {
  if (!flvjs.isSupported() || !urls.value?.flv || !videoRef.value) {
    return false
  }

  return new Promise((resolve) => {
    // Check if this attempt is still valid
    if (token !== playbackToken) {
      resolve(false)
      return
    }
    
    try {
      flvPlayer = flvjs.createPlayer({
        type: 'flv',
        url: urls.value!.flv,
        isLive: true
      }, {
        enableWorker: true,
        enableStashBuffer: false,
        stashInitialSize: 128
      })

      flvPlayer.attachMediaElement(videoRef.value!)

      flvPlayer.on(flvjs.Events.ERROR, (errorType, errorDetail) => {
        console.error('FLV error:', errorType, errorDetail)
        if (token === playbackToken) {
          resolve(false)
        }
      })

      flvPlayer.load()
      flvPlayer.play()

      // 等待一段时间检查是否成功
      setTimeout(() => {
        // Check token before updating state
        if (token !== playbackToken) {
          resolve(false)
          return
        }
        
        if (videoRef.value && !videoRef.value.paused && videoRef.value.readyState >= 2) {
          currentProtocol.value = 'flv'
          isPlaying.value = true
          emit('playing')
          emit('protocolChange', 'HTTP-FLV')
          startLatencyMonitor()
          resolve(true)
        } else {
          resolve(false)
        }
      }, 3000)
    } catch (err) {
      console.error('FLV init error:', err)
      resolve(false)
    }
  })
}

// 尝试 HLS 播放
async function tryHls(token: number): Promise<boolean> {
  if (!urls.value?.hls || !videoRef.value) {
    return false
  }

  // Check if this attempt is still valid
  if (token !== playbackToken) {
    return false
  }

  // 原生 HLS 支持（Safari）
  if (videoRef.value.canPlayType('application/vnd.apple.mpegurl')) {
    return new Promise((resolve) => {
      if (token !== playbackToken) {
        resolve(false)
        return
      }
      
      const video = videoRef.value!
      video.src = urls.value!.hls
      
      const onLoaded = () => {
        if (token !== playbackToken) {
          resolve(false)
          return
        }
        video.play()
        currentProtocol.value = 'hls'
        isPlaying.value = true
        emit('playing')
        emit('protocolChange', 'HLS (Native)')
        startLatencyMonitor()
        resolve(true)
      }
      
      const onError = () => {
        resolve(false)
      }
      
      video.addEventListener('loadedmetadata', onLoaded, { once: true })
      video.addEventListener('error', onError, { once: true })

      setTimeout(() => {
        video.removeEventListener('loadedmetadata', onLoaded)
        video.removeEventListener('error', onError)
        resolve(false)
      }, 5000)
    })
  }

  // hls.js 支持
  if (!Hls.isSupported()) {
    return false
  }

  return new Promise((resolve) => {
    if (token !== playbackToken) {
      resolve(false)
      return
    }
    
    try {
      hlsPlayer = new Hls({
        enableWorker: true,
        lowLatencyMode: true
      })

      hlsPlayer.loadSource(urls.value!.hls)
      hlsPlayer.attachMedia(videoRef.value!)

      hlsPlayer.on(Hls.Events.MANIFEST_PARSED, () => {
        if (token !== playbackToken) {
          resolve(false)
          return
        }
        videoRef.value!.play()
        currentProtocol.value = 'hls'
        isPlaying.value = true
        emit('playing')
        emit('protocolChange', 'HLS')
        startLatencyMonitor()
        resolve(true)
      })

      hlsPlayer.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          console.error('HLS fatal error:', data)
          resolve(false)
        }
      })

      setTimeout(() => resolve(false), 5000)
    } catch (err) {
      console.error('HLS init error:', err)
      resolve(false)
    }
  })
}

// 自动协议降级播放
async function startPlayback() {
  if (!props.playUrl) {
    errorMessage.value = '无播放地址'
    return
  }

  cleanup()
  errorMessage.value = ''
  
  // Get current token for this playback attempt
  const token = playbackToken

  const preference = props.preferredProtocol ?? 'auto'
  const baseOrder: Protocol[] = ['webrtc', 'flv', 'hls']
  const order = preference === 'auto'
    ? baseOrder
    : [preference as Protocol, ...baseOrder.filter((p) => p !== preference)]

  const skipWebRTCForDelay = preference === 'auto' && (props.playbackDelaySec ?? 0) > 0

  for (const protocol of order) {
    if (protocol === 'webrtc') {
      if (!urls.value?.webrtc || skipWebRTCForDelay) {
        continue
      }
      console.log('Trying WebRTC...')
      if (await tryWebRTC(token)) {
        return
      }
      if (rtcConnection) {
        rtcConnection.close()
        rtcConnection = null
      }
    }

    if (protocol === 'flv') {
      console.log('Trying HTTP-FLV...')
      if (await tryFlv(token)) {
        if (videoRef.value) {
          startDelayControl(videoRef.value, props.playbackDelaySec ?? 0)
        }
        return
      }
      if (flvPlayer) {
        flvPlayer.destroy()
        flvPlayer = null
      }
    }

    if (protocol === 'hls') {
      console.log('Trying HLS...')
      if (await tryHls(token)) {
        if (videoRef.value) {
          startDelayControl(videoRef.value, props.playbackDelaySec ?? 0)
        }
        return
      }
    }
  }

  // Check if this attempt is still valid before showing error
  if (token !== playbackToken) {
    return
  }

  // 所有协议都失败
  errorMessage.value = '无法播放视频，请检查视频源'
  emit('error', errorMessage.value)
}

// 监听 playUrl 变化
watch(
  () => props.playUrl,
  (newUrl) => {
    if (newUrl) {
      startPlayback()
    } else {
      cleanup()
    }
  }
)

watch(
  () => props.preferredProtocol,
  () => {
    if (props.playUrl) {
      startPlayback()
    }
  }
)

// 组件挂载时开始播放
onMounted(() => {
  setupBufferingListeners()
  if (props.playUrl) {
    startPlayback()
  }
})

// 组件卸载时清理
onUnmounted(() => {
  cleanup()
})

// 暴露方法
defineExpose({
  videoElement: videoRef,
  currentProtocol,
  isPlaying,
  isBuffering
})
</script>

<template>
  <div class="video-player">
    <video
      ref="videoRef"
      class="video-element"
      autoplay
      muted
      playsinline
    ></video>

    <!-- 协议指示器 -->
    <div v-if="currentProtocol !== 'none'" class="protocol-badge">
      {{ currentProtocol.toUpperCase() }}
      <!-- 方案 F：服务端渲染流预计有 1-5 秒延迟 -->
      <span class="delay-hint">~1-5s</span>
    </div>

    <!-- 延迟/质量指标 -->
    <div v-if="latencyMs !== null" class="latency-badge">
      延迟 {{ latencyMs }} ms
    </div>
    <div v-if="currentProtocol === 'webrtc'" class="webrtc-metrics">
      <span>FPS {{ webrtcStats.framesPerSecond }}</span>
      <span>抖动 {{ webrtcStats.jitter.toFixed(2) }}</span>
      <span>丢帧 {{ webrtcStats.framesDropped }}</span>
    </div>

    <!-- 状态指示器 -->
    <div v-if="status" class="status-badge" :class="status">
      {{ status === 'running' ? '运行中' : status === 'starting' ? '启动中' : status === 'cooldown' ? '冷却中' : status === 'error' ? '错误' : '已停止' }}
    </div>

    <!-- 缓冲指示器 -->
    <div v-if="isBuffering && isPlaying" class="buffering-indicator">
      <div class="buffering-spinner"></div>
      <span>缓冲中...</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="playUrl && !isPlaying && !errorMessage" class="loading-overlay">
      <div class="spinner"></div>
      <span>连接中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-if="errorMessage" class="error-overlay">
      <span class="error-icon">⚠️</span>
      <span>{{ errorMessage }}</span>
      <button class="retry-btn" @click="startPlayback">重试</button>
    </div>

    <!-- 无播放地址 -->
    <div v-if="!playUrl" class="no-source-overlay">
      <span>等待视频源...</span>
    </div>
  </div>
</template>

<style scoped>
.video-player {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.protocol-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.delay-hint {
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 400;
}

.latency-badge {
  position: absolute;
  top: 8px;
  right: 110px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  color: var(--color-warning);
  font-size: 11px;
  border-radius: 4px;
}

.webrtc-metrics {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  color: var(--color-success);
  font-size: 10px;
  border-radius: 4px;
}

.status-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
}

.status-badge.running {
  color: var(--color-success);
}

.status-badge.starting {
  color: var(--color-warning);
}

.status-badge.cooldown {
  color: var(--color-info);
}

.status-badge.error {
  color: var(--color-danger);
}

.status-badge.stopped {
  color: var(--color-text-muted);
}

.buffering-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 8px;
  color: #fff;
  font-size: 12px;
}

.buffering-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-overlay,
.error-overlay,
.no-source-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-icon {
  font-size: 32px;
}

.error-overlay {
  color: #ff6b6b;
}

.retry-btn {
  margin-top: 8px;
  padding: 8px 16px;
  background: var(--color-primary);
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--color-primary-strong);
}

.no-source-overlay {
  color: var(--color-text-muted);
}
</style>
