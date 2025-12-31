<script setup lang="ts">
/**
 * 视频播放器组件
 * 协议优先级：WebRTC → HTTP-FLV → HLS
 * Requirements: 1.1, 1.2, 1.3
 */

import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import flvjs from 'flv.js'
import Hls from 'hls.js'

const props = defineProps<{
  playUrl: string | null
  streamId: string
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

// 播放器实例
let flvPlayer: flvjs.Player | null = null
let hlsPlayer: Hls | null = null
let rtcConnection: RTCPeerConnection | null = null

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
  
  // Remove extension if present
  const extMatch = baseUrl.match(/\.(flv|m3u8)$/i)
  if (extMatch) {
    baseUrl = baseUrl.substring(0, baseUrl.length - extMatch[0].length)
  }

  return {
    flv: baseUrl + '.flv' + queryString,
    hls: baseUrl + '.m3u8' + queryString,
    detectedType: urlType,
    webrtc: null
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

  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.src = ''
  }

  isPlaying.value = false
  currentProtocol.value = 'none'
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

  // Determine protocol order based on detected URL type
  const detectedType = urls.value?.detectedType
  
  if (detectedType === 'hls') {
    // If URL is HLS, try HLS first
    console.log('Detected HLS URL, trying HLS first...')
    if (await tryHls(token)) {
      return
    }
    
    // Fallback to FLV
    if (hlsPlayer) {
      hlsPlayer.destroy()
      hlsPlayer = null
    }
    
    console.log('Trying HTTP-FLV...')
    if (await tryFlv(token)) {
      return
    }
  } else {
    // Default: try FLV first (lower latency)
    console.log('Trying HTTP-FLV...')
    if (await tryFlv(token)) {
      return
    }

    // 清理失败的 FLV 播放器
    if (flvPlayer) {
      flvPlayer.destroy()
      flvPlayer = null
    }

    // 降级到 HLS
    console.log('Trying HLS...')
    if (await tryHls(token)) {
      return
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

// 组件挂载时开始播放
onMounted(() => {
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
  isPlaying
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
  color: #4a9eff;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
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
  border: 3px solid #333;
  border-top-color: #4a9eff;
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
  background: #4a9eff;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.retry-btn:hover {
  background: #3a8eef;
}

.no-source-overlay {
  color: #888;
}
</style>
