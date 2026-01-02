<script setup lang="ts">
/**
 * 主应用组件
 * 集成视频源选择、播放器、热力图叠加、实时统计面板、配置管理、错误通知
 * ROI 绘制与区域密度显示
 * Requirements: 5.1, 5.2, 5.3, 7.1, 8.1, 8.2, 8.3, 9.2, 9.4, 3.1, 3.2, 3.3, P1.4
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Splitpanes, Pane } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'

import VideoSourceSelector from './components/VideoSourceSelector.vue'
import VideoPlayer from './components/VideoPlayer.vue'
import DataTabs from './components/DataTabs.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import ErrorNotification from './components/ErrorNotification.vue'
import ConnectionIndicator from './components/ConnectionIndicator.vue'
import ROIDrawer from './components/ROIDrawer.vue'
import RegionDensityDisplay from './components/RegionDensityDisplay.vue'
import DetectionOverlay from './components/DetectionOverlay.vue'
import StreamGrid from './components/StreamGrid.vue'
import { useStreamsStore } from './stores/streams'
import type { VideoStream, StreamStatus, DetectionResult } from './types'
import type { ROI, Point } from './api/rois'

const store = useStreamsStore()

// 当前选中的流
const selectedStreamId = ref<string | null>(null)

// 方案 F：服务端渲染热力图，前端无需延迟控制
const playbackDelaySec = ref(0)
const protocolPreference = ref<'auto' | 'webrtc' | 'flv' | 'hls'>('auto')

const PROTOCOL_STORAGE_KEY = 'ccs:playback:protocol'
const DELAY_STORAGE_KEY = 'ccs:playback:delay'
const THEME_STORAGE_KEY = 'ccs:theme'
const LAYOUT_PREF_KEY = 'ccs:layout'
const LAYOUT_V_PREF_KEY = 'ccs:layout:v'
const SHOW_DETECTIONS_KEY = 'ccs:show_detections'

const MAX_DELAY_SEC = 5

const theme = ref<'dark' | 'light'>('dark')

// 网格模式
const gridMode = ref(false)

// 叠加显示开关 (P1.4)
const showDetections = ref(true)

// 流搜索
const streamSearch = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)

// 面板折叠
const showConfigPanel = ref(true)
const showDataPanel = ref(true)
const showShortcutHelp = ref(false)
const refreshingAll = ref(false)

// 删除确认对话框
const showDeleteConfirm = ref(false)
const streamToDelete = ref<string | null>(null)

// ROI 相关状态
const rois = ref<ROI[]>([])
const selectedRoiId = ref<string | null>(null)
const roiEditMode = ref(false)
const dataTabsRef = ref<InstanceType<typeof DataTabs> | null>(null)

// 视频容器尺寸（用于 ROI 绘制）
const videoContainerRef = ref<HTMLDivElement | null>(null)
const videoWidth = ref(800)
const videoHeight = ref(450)

// 布局状态
const splitSize = ref(30) // Sidebar width percentage
const splitVSize = ref(60) // Video height percentage

// 计算属性
const selectedStream = computed<VideoStream | undefined>(() => {
  if (!selectedStreamId.value) return undefined
  return store.streams.get(selectedStreamId.value)
})

const latestResult = computed<DetectionResult | null>(() => {
  if (!selectedStreamId.value) return null
  return store.getDetectionResult(selectedStreamId.value) ?? null
})

// 简化：直接使用最新结果
const displayResult = computed<DetectionResult | null>(() => latestResult.value)

// 视频帧实际尺寸（从 displayResult 获取，或默认为 1920x1080）
const frameWidth = computed(() => displayResult.value?.frame_width || 1920)
const frameHeight = computed(() => displayResult.value?.frame_height || 1080)

// ROI 显示坐标转换：Frame Coordinates -> Canvas Coordinates
const displayRois = computed<ROI[]>(() => {
  if (!rois.value.length) return []

  const scaleX = videoWidth.value / frameWidth.value
  const scaleY = videoHeight.value / frameHeight.value

  return rois.value.map(roi => ({
    ...roi,
    points: roi.points.map(p => ({
      x: p.x * scaleX,
      y: p.y * scaleY
    }))
  }))
})

const statusMetrics = computed(() => {
  if (!selectedStreamId.value) return null
  return store.getStatusMetrics(selectedStreamId.value) ?? null
})

const alertEvents = computed(() => {
  if (!selectedStreamId.value) return []
  return store.getAlertEvents(selectedStreamId.value)
})

const streamFlash = ref<Record<string, 'success' | 'error'>>({})

const filteredStreams = computed(() => {
  const keyword = streamSearch.value.trim().toLowerCase()
  if (!keyword) return store.streamList
  return store.streamList.filter((stream) =>
    `${stream.name} ${stream.type}`.toLowerCase().includes(keyword)
  )
})

const gridItems = computed(() =>
  store.streamList.map((stream) => ({
    stream,
    result: store.getDetectionResult(stream.stream_id) ?? null
  }))
)

function loadPlaybackPrefs() {
  try {
    const storedProtocol = localStorage.getItem(PROTOCOL_STORAGE_KEY)
    if (storedProtocol === 'auto' || storedProtocol === 'webrtc' || storedProtocol === 'flv' || storedProtocol === 'hls') {
      protocolPreference.value = storedProtocol
    }
    const storedDelay = localStorage.getItem(DELAY_STORAGE_KEY)
    if (storedDelay) {
      const parsed = Number(storedDelay)
      if (Number.isFinite(parsed)) {
        playbackDelaySec.value = Math.min(Math.max(parsed, 0), MAX_DELAY_SEC)
      }
    }
    // Load showDetections preference
    const storedShowDetections = localStorage.getItem(SHOW_DETECTIONS_KEY)
    if (storedShowDetections !== null) {
      showDetections.value = storedShowDetections === 'true'
    }
  } catch {
    // Ignore storage errors
  }
}

function loadLayoutPrefs() {
  try {
    const stored = localStorage.getItem(LAYOUT_PREF_KEY)
    if (stored) {
      const val = parseFloat(stored)
      if (!isNaN(val) && val > 10 && val < 90) {
        splitSize.value = val
      }
    }
    const storedV = localStorage.getItem(LAYOUT_V_PREF_KEY)
    if (storedV) {
      const val = parseFloat(storedV)
      if (!isNaN(val) && val > 10 && val < 90) {
        splitVSize.value = val
      }
    }
  } catch {
    // Ignore
  }
}

function handleResize(panes: { min: number; max: number; size: number }[]) {
  if (panes[0]) {
    splitSize.value = panes[0].size
    localStorage.setItem(LAYOUT_PREF_KEY, String(splitSize.value))
    // Trigger video resize check
    setTimeout(updateVideoSize, 50)
  }
}

function handleVResize(panes: { min: number; max: number; size: number }[]) {
  if (panes[0]) {
    splitVSize.value = panes[0].size
    localStorage.setItem(LAYOUT_V_PREF_KEY, String(splitVSize.value))
    // Trigger video resize check
    setTimeout(updateVideoSize, 50)
  }
}

function applyTheme(value: 'dark' | 'light') {
  theme.value = value
  document.documentElement.dataset.theme = value
  window.dispatchEvent(new Event('theme-change'))
}

function loadThemePreference() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'dark' || stored === 'light') {
      applyTheme(stored)
      return
    }
  } catch {
    // Ignore storage errors
  }

  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    applyTheme('light')
  } else {
    applyTheme('dark')
  }
}

function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

// 连接状态
const connectionState = computed(() => ({
  websocket: store.wsConnected,
  streamStatus: selectedStream.value?.status,
  reconnecting: selectedStreamId.value 
    ? store.getReconnectionState(selectedStreamId.value)?.isReconnecting 
    : false,
  reconnectAttempt: selectedStreamId.value 
    ? store.getReconnectionState(selectedStreamId.value)?.attemptCount 
    : 0,
  maxAttempts: 5
}))

// 统计信息
const runningCount = computed(() => 
  store.streamList.filter(s => s.status === 'running').length
)
const totalCount = computed(() => store.streamList.length)

const shortcutHints = [
  { keys: 'G', action: '网格/单路切换' },
  { keys: 'F', action: '退出网格聚焦' },
  { keys: 'R', action: 'ROI 编辑开关' },
  { keys: 'Space', action: '启动/停止当前流' },
  { keys: '/', action: '聚焦搜索框' },
  { keys: '1-9', action: '快速切换流' },
  { keys: '`', action: '快捷键面板' }
]

// 处理流创建
function onStreamCreated(streamId: string) {
  selectedStreamId.value = streamId
}

// 处理错误
function onError(message: string) {
  console.error('Error:', message)
  store.showError(message)
}

// 处理通知关闭
function onDismissNotification(id: number) {
  store.removeNotification(id)
}

function triggerStreamFlash(streamId: string, type: 'success' | 'error') {
  streamFlash.value = { ...streamFlash.value, [streamId]: type }
  window.setTimeout(() => {
    const next = { ...streamFlash.value }
    delete next[streamId]
    streamFlash.value = next
  }, 900)
}

// 启动流
async function handleStart(streamId?: string) {
  const targetId = streamId || selectedStreamId.value
  if (!targetId) return
  try {
    await store.startStream(targetId)
    // 订阅检测结果
    store.subscribeResult(targetId)
    triggerStreamFlash(targetId, 'success')
  } catch (err) {
    console.error('Failed to start stream:', err)
    triggerStreamFlash(targetId, 'error')
  }
}

// 停止流
async function handleStop(streamId?: string) {
  const targetId = streamId || selectedStreamId.value
  if (!targetId) return
  try {
    await store.stopStream(targetId)
    triggerStreamFlash(targetId, 'success')
  } catch (err) {
    console.error('Failed to stop stream:', err)
    triggerStreamFlash(targetId, 'error')
  }
}

// 显示删除确认
function confirmDelete(streamId: string, event?: Event) {
  event?.stopPropagation()
  streamToDelete.value = streamId
  showDeleteConfirm.value = true
}

// 取消删除
function cancelDelete() {
  showDeleteConfirm.value = false
  streamToDelete.value = null
}

// 确认删除流
async function handleDelete() {
  const targetId = streamToDelete.value
  if (!targetId) return
  try {
    await store.deleteStream(targetId)
    triggerStreamFlash(targetId, 'success')
    if (selectedStreamId.value === targetId) {
      selectedStreamId.value = null
    }
  } catch (err) {
    console.error('Failed to delete stream:', err)
    triggerStreamFlash(targetId, 'error')
  } finally {
    showDeleteConfirm.value = false
    streamToDelete.value = null
  }
}

async function refreshAllStreams() {
  if (refreshingAll.value) return
  refreshingAll.value = true
  try {
    await store.fetchStreams()
    if (selectedStreamId.value) {
      const stream = store.streams.get(selectedStreamId.value)
      if (stream?.status === 'running') {
        store.subscribeResult(selectedStreamId.value)
      }
    }
    store.showInfo('已刷新全部流状态')
  } catch (err) {
    console.error('Failed to refresh streams:', err)
  } finally {
    refreshingAll.value = false
  }
}

// 选择流
function selectStream(streamId: string) {
  // 取消之前的订阅
  if (selectedStreamId.value && selectedStreamId.value !== streamId) {
    store.unsubscribeResult(selectedStreamId.value)
  }

  selectedStreamId.value = streamId

  // 如果流正在运行，订阅结果
  const stream = store.streams.get(streamId)
  if (stream?.status === 'running') {
    store.subscribeResult(streamId)
  }
}

// 监听选中流的状态变化，当流变为 running 时自动订阅结果
watch(
  () => selectedStream.value?.status,
  (newStatus, oldStatus) => {
    if (!selectedStreamId.value) return
    
    // 当流状态变为 running 时，自动订阅检测结果
    if (newStatus === 'running' && oldStatus !== 'running') {
      store.subscribeResult(selectedStreamId.value)
    }
    // 当流状态从 running 变为其他状态时，取消订阅
    else if (oldStatus === 'running' && newStatus !== 'running') {
      store.unsubscribeResult(selectedStreamId.value)
    }
  }
)

watch(protocolPreference, (value) => {
  try {
    localStorage.setItem(PROTOCOL_STORAGE_KEY, value)
  } catch {
    // Ignore storage errors
  }
})

watch(playbackDelaySec, (value) => {
  try {
    localStorage.setItem(DELAY_STORAGE_KEY, String(value))
  } catch {
    // Ignore storage errors
  }
})

watch(theme, (value) => {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, value)
  } catch {
    // Ignore storage errors
  }
})

watch(showDetections, (value) => {
  try {
    localStorage.setItem(SHOW_DETECTIONS_KEY, String(value))
  } catch {
    // Ignore storage errors
  }
})

watch(gridMode, (enabled) => {
  if (enabled) {
    roiEditMode.value = false
  }
  if (enabled) {
    for (const stream of store.streamList) {
      if (stream.status === 'running') {
        store.subscribeResult(stream.stream_id)
      }
    }
  } else {
    for (const stream of store.streamList) {
      if (stream.stream_id !== selectedStreamId.value && stream.status === 'running') {
        store.unsubscribeResult(stream.stream_id)
      }
    }
  }
})

// 监听窗口大小变化
onMounted(async () => {
  loadThemePreference()
  loadPlaybackPrefs()
  loadLayoutPrefs()
  // 获取流列表
  try {
    await store.fetchStreams()
  } catch (err) {
    console.error('Failed to fetch streams:', err)
    // Error is already stored in store.error
  }

  // 订阅状态变更
  store.subscribeStatus()
  store.subscribeAlerts()

  // 监听视频容器尺寸变化
  if (videoContainerRef.value) {
    updateVideoSize()
    // eslint-disable-next-line no-undef
    resizeObserver = new ResizeObserver(() => {
      updateVideoSize()
    })
    resizeObserver.observe(videoContainerRef.value)
  }

  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  store.cleanup()
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  window.removeEventListener('keydown', handleKeydown)
})

// 状态配置
interface StatusConfig {
  color: string
  bgColor: string
  icon: string
  label: string
}

const STATUS_CONFIG: Record<StreamStatus, StatusConfig> = {
  running: {
    color: '#4caf50',
    bgColor: 'rgba(76, 175, 80, 0.15)',
    icon: '🟢',
    label: '运行中'
  },
  starting: {
    color: '#ff9800',
    bgColor: 'rgba(255, 152, 0, 0.15)',
    icon: '🟡',
    label: '启动中'
  },
  stopped: {
    color: '#9e9e9e',
    bgColor: 'rgba(158, 158, 158, 0.15)',
    icon: '⚪',
    label: '已停止'
  },
  error: {
    color: '#f44336',
    bgColor: 'rgba(244, 67, 54, 0.15)',
    icon: '🔴',
    label: '错误'
  },
  cooldown: {
    color: '#2196f3',
    bgColor: 'rgba(33, 150, 243, 0.15)',
    icon: '🔵',
    label: '冷却中'
  }
}

function getStatusConfig(status: StreamStatus): StatusConfig {
  return STATUS_CONFIG[status] || STATUS_CONFIG.stopped
}

// 获取流类型图标
function getTypeIcon(type: string): string {
  switch (type) {
    case 'file': return '📁'
    case 'webcam': return '📷'
    case 'rtsp': return '📡'
    default: return '📹'
  }
}

// 判断是否可以启动
function canStart(status: StreamStatus): boolean {
  return status === 'stopped' || status === 'error'
}

// 判断是否可以停止
function canStop(status: StreamStatus): boolean {
  return status === 'running' || status === 'starting'
}

// ROI 模式变更
function handleRoiModeChange(enabled: boolean) {
  roiEditMode.value = enabled
}

// ROI 列表变更
function handleRoisChange(newRois: ROI[]) {
  rois.value = newRois
}

// 选中 ROI 变更
function handleSelectedRoiChange(roiId: string | null) {
  selectedRoiId.value = roiId
}

// 辅助：坐标转换 Canvas Coordinates -> Frame Coordinates
function scalePointsToFrame(points: Point[]): Point[] {
  const scaleX = frameWidth.value / videoWidth.value
  const scaleY = frameHeight.value / videoHeight.value

  return points.map(p => ({
    x: p.x * scaleX,
    y: p.y * scaleY
  }))
}

// ROI 创建（从 ROIDrawer 触发）
// 接收的 points 是 Canvas 坐标，需转换为 Frame 坐标
function handleRoiCreate(data: { name: string; points: Point[] }) {
  dataTabsRef.value?.handleCreateROI({
    ...data,
    points: scalePointsToFrame(data.points)
  })
}

// ROI 更新（从 ROIDrawer 触发）
// 接收的 points 是 Canvas 坐标，需转换为 Frame 坐标
function handleRoiUpdate(roiId: string, points: Point[]) {
  dataTabsRef.value?.handleUpdateROIPoints(roiId, scalePointsToFrame(points))
}

// ROI 选择（从 ROIDrawer 触发）
function handleRoiSelect(roiId: string | null) {
  selectedRoiId.value = roiId
  dataTabsRef.value?.handleSelectROI(roiId)
}

// ROI 删除（从 ROIDrawer 触发）
function handleRoiDelete(roiId: string) {
  dataTabsRef.value?.handleDeleteROI(roiId)
}

function handleGridSelect(streamId: string) {
  selectStream(streamId)
}

// 更新视频容器尺寸
function updateVideoSize() {
  if (videoContainerRef.value) {
    const rect = videoContainerRef.value.getBoundingClientRect()
    videoWidth.value = rect.width
    videoHeight.value = rect.height
  }
}

function isTypingTarget(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  if (!target) return false
  const tag = target.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable
}

function handleKeydown(event: KeyboardEvent) {
  if (isTypingTarget(event)) return

  if (event.key === 'g' || event.key === 'G') {
    gridMode.value = !gridMode.value
  } else if (event.key === 'f' || event.key === 'F') {
    gridMode.value = false
  } else if (event.key === 'r' || event.key === 'R') {
    showDataPanel.value = true
    dataTabsRef.value?.setActiveTab('roi')
    dataTabsRef.value?.toggleEditMode()
  } else if (event.key === ' ') {
    event.preventDefault()
    if (!selectedStream.value) return
    if (canStop(selectedStream.value.status)) {
      handleStop()
    } else if (canStart(selectedStream.value.status)) {
      handleStart()
    }
  } else if (event.key === '/') {
    event.preventDefault()
    searchInputRef.value?.focus()
  } else if (event.key === '`' || event.key === '?') {
    showShortcutHelp.value = !showShortcutHelp.value
  } else if (/^[1-9]$/.test(event.key)) {
    const index = Number(event.key) - 1
    const target = filteredStreams.value[index]
    if (target) {
      selectStream(target.stream_id)
    }
  }
}

// 监听窗口大小变化
let resizeObserver: typeof window.ResizeObserver.prototype | null = null
</script>

<template>
  <div class="app">
    <!-- 错误通知 -->
    <ErrorNotification 
      :notifications="store.notifications" 
      @dismiss="onDismissNotification" 
    />

    <Splitpanes class="default-theme" @resize="handleResize">
      <!-- 侧边栏 -->
      <Pane :size="splitSize" :min-size="20" class="sidebar-pane">
        <aside class="sidebar">
          <!-- 视频源选择器 -->
          <VideoSourceSelector @created="onStreamCreated" @error="onError" />

          <!-- 流列表 -->
          <div class="stream-list">
            <div class="stream-list-header">
              <h3>📹 视频流管理</h3>
              <div class="stream-stats">
                <span class="stat-badge running">{{ runningCount }} 运行</span>
                <span class="stat-badge total">{{ totalCount }} 总计</span>
              </div>
            </div>

            <div class="stream-search">
              <input
                ref="searchInputRef"
                v-model="streamSearch"
                type="text"
                placeholder="搜索流 (/)"
              />
            </div>

            <!-- WebSocket 连接状态 -->
            <ConnectionIndicator :state="connectionState" />

            <div v-if="store.loading" class="loading">
              <span class="spinner"></span>
              加载中...
            </div>
            <div v-else-if="filteredStreams.length === 0" class="empty">
              <span class="empty-icon">📭</span>
              <p>{{ streamSearch ? '无匹配结果' : '暂无视频流' }}</p>
              <p class="hint">{{ streamSearch ? '请调整搜索关键词' : '请在上方添加视频源' }}</p>
            </div>
            <ul v-else class="stream-items">
              <li
                v-for="stream in filteredStreams"
                :key="stream.stream_id"
                :class="{
                  active: stream.stream_id === selectedStreamId,
                  'flash-success': streamFlash[stream.stream_id] === 'success',
                  'flash-error': streamFlash[stream.stream_id] === 'error'
                }"
                :style="{ backgroundColor: stream.stream_id === selectedStreamId ? getStatusConfig(stream.status).bgColor : undefined }"
                @click="selectStream(stream.stream_id)"
              >
                <div class="stream-main">
                  <div class="stream-icon">{{ getTypeIcon(stream.type) }}</div>
                  <div class="stream-info">
                    <span class="stream-name">{{ stream.name }}</span>
                    <span class="stream-type">{{ stream.type.toUpperCase() }}</span>
                  </div>
                </div>
                <div class="stream-actions">
                  <span
                    class="stream-status-badge"
                    :style="{
                      color: getStatusConfig(stream.status).color,
                      backgroundColor: getStatusConfig(stream.status).bgColor
                    }"
                  >
                    {{ getStatusConfig(stream.status).icon }} {{ getStatusConfig(stream.status).label }}
                  </span>
                  <div class="action-buttons">
                    <button
                      v-if="canStart(stream.status)"
                      class="action-btn start"
                      title="启动"
                      @click.stop="handleStart(stream.stream_id)"
                    >
                      ▶
                    </button>
                    <button
                      v-if="canStop(stream.status)"
                      class="action-btn stop"
                      title="停止"
                      @click.stop="handleStop(stream.stream_id)"
                    >
                      ⏹
                    </button>
                    <button
                      class="action-btn delete"
                      title="删除"
                      @click.stop="confirmDelete(stream.stream_id, $event)"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              </li>
            </ul>
          </div>

          <!-- 配置管理面板 -->
          <div class="panel-toggle">
            <span>配置面板</span>
            <button class="btn btn-secondary" @click="showConfigPanel = !showConfigPanel">
              {{ showConfigPanel ? '收起' : '展开' }}
            </button>
          </div>
          <ConfigPanel
            v-if="showConfigPanel"
            :stream-id="selectedStreamId"
            @error="onError"
          />
        </aside>
      </Pane>

      <!-- 主内容区 -->
      <Pane :size="100 - splitSize" class="main-pane">
        <main class="main-content">
          <div class="global-actions">
            <div class="global-status">
              <ConnectionIndicator :state="connectionState" compact />
              <div class="status-summary">
                <span>运行 {{ runningCount }} / {{ totalCount }}</span>
              </div>
            </div>
            <div class="global-controls">
              <button class="btn btn-secondary" :disabled="refreshingAll" @click="refreshAllStreams">
                {{ refreshingAll ? '刷新中...' : '刷新所有流' }}
              </button>
              <button class="btn btn-secondary" @click="toggleTheme">
                {{ theme === 'dark' ? '浅色模式' : '深色模式' }}
              </button>
              <button class="btn btn-secondary" @click="showShortcutHelp = true">快捷键</button>
            </div>
          </div>

          <div v-if="gridMode" class="grid-section">
            <div class="grid-header">
              <h3>🧩 多路流网格</h3>
              <button class="btn btn-secondary" @click="gridMode = false">退出网格</button>
            </div>
            <StreamGrid :items="gridItems" :selected-id="selectedStreamId" @select="handleGridSelect" />
          </div>

          <Splitpanes v-else horizontal @resize="handleVResize">
            <!-- 视频播放区 -->
            <Pane :size="splitVSize" :min-size="20">
              <div class="video-section">
                <div v-if="selectedStream" class="video-toolbar">
                  <div class="toolbar-group">
                    <label>协议</label>
                    <select v-model="protocolPreference" class="toolbar-select">
                      <option value="auto">自动</option>
                      <option value="webrtc">WebRTC</option>
                      <option value="flv">HTTP-FLV</option>
                      <option value="hls">HLS</option>
                    </select>
                  </div>
                  <div class="toolbar-group">
                    <label>播放延迟</label>
                    <input v-model.number="playbackDelaySec" type="range" min="0" max="5" step="0.5" />
                    <span>{{ playbackDelaySec }}s</span>
                  </div>
                  <!-- 检测框开关 -->
                  <div class="toolbar-group checkbox-group">
                    <label>
                      <input type="checkbox" v-model="showDetections" />
                      显示检测框
                    </label>
                  </div>
                  <button class="btn btn-secondary" @click="gridMode = true">网格模式</button>
                </div>

                <div ref="videoContainerRef" class="video-container">
                  <template v-if="selectedStream">
                    <VideoPlayer
                      :play-url="selectedStream.play_url"
                      :webrtc-url="selectedStream.webrtc_url"
                      :stream-id="selectedStream.stream_id"
                      :status="selectedStream.status"
                      :playback-delay-sec="playbackDelaySec"
                      :preferred-protocol="protocolPreference"
                    />
                    <DetectionOverlay
                      v-if="showDetections && displayResult?.detections?.length && !roiEditMode"
                      :detections="displayResult.detections"
                      :frame-width="displayResult.frame_width"
                      :frame-height="displayResult.frame_height"
                      :width="videoWidth"
                      :height="videoHeight"
                    />
                    <!-- ROI 绘制层（编辑模式） -->
                    <!-- 传入 displayRois (Canvas 坐标) -->
                    <ROIDrawer
                      v-if="roiEditMode"
                      :width="videoWidth"
                      :height="videoHeight"
                      :rois="displayRois"
                      :selected-roi-id="selectedRoiId"
                      :edit-mode="roiEditMode"
                      @create="handleRoiCreate"
                      @update="handleRoiUpdate"
                      @select="handleRoiSelect"
                      @delete="handleRoiDelete"
                    />
                    <!-- 区域密度显示层（非编辑模式且有 ROI） -->
                    <!-- 传入 displayRois (Canvas 坐标) -->
                    <RegionDensityDisplay
                      v-else-if="rois.length > 0"
                      :region-stats="displayResult?.region_stats || []"
                      :rois="displayRois"
                      :width="videoWidth"
                      :height="videoHeight"
                    />
                  </template>
                  <div v-else class="no-stream">
                    <span class="no-stream-icon">📺</span>
                    <p>请选择或创建视频流</p>
                  </div>
                </div>

                <!-- 控制栏 -->
                <div v-if="selectedStream" class="controls">
                  <div class="control-info">
                    <span class="control-stream-name">{{ selectedStream.name }}</span>
                    <span
                      class="control-status"
                      :style="{ color: getStatusConfig(selectedStream.status).color }"
                    >
                      {{ getStatusConfig(selectedStream.status).icon }} {{ getStatusConfig(selectedStream.status).label }}
                    </span>
                  </div>
                  <div class="control-buttons">
                    <button
                      v-if="canStart(selectedStream.status)"
                      class="btn btn-start"
                      @click="handleStart()"
                    >
                      ▶ 开始
                    </button>
                    <button
                      v-if="canStop(selectedStream.status)"
                      class="btn btn-stop"
                      @click="handleStop()"
                    >
                      ⏹ 停止
                    </button>
                    <button
                      class="btn btn-delete"
                      @click="confirmDelete(selectedStream.stream_id)"
                    >
                      🗑 删除
                    </button>
                  </div>
                </div>
              </div>
            </Pane>

            <!-- 数据与配置 Tab 面板 -->
            <Pane :size="100 - splitVSize" class="data-pane">
              <div class="panel-toggle">
                <span>数据面板</span>
                <button class="btn btn-secondary" @click="showDataPanel = !showDataPanel">
                  {{ showDataPanel ? '收起' : '展开' }}
                </button>
              </div>
              <DataTabs
                v-if="showDataPanel"
                ref="dataTabsRef"
                :stream-id="selectedStreamId"
                :result="displayResult"
                :status-metrics="statusMetrics"
                :alert-events="alertEvents"
                @roi-mode-change="handleRoiModeChange"
                @rois-change="handleRoisChange"
                @selected-roi-change="handleSelectedRoiChange"
              />
            </Pane>
          </Splitpanes>
        </main>
      </Pane>
    </Splitpanes>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="modal-content" @click.stop>
        <h4>确认删除</h4>
        <p>确定要删除此视频流吗？此操作无法撤销。</p>
        <div class="modal-actions">
          <button class="btn btn-cancel" @click="cancelDelete">取消</button>
          <button class="btn btn-confirm-delete" @click="handleDelete">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 快捷键帮助 -->
    <div v-if="showShortcutHelp" class="modal-overlay" @click="showShortcutHelp = false">
      <div class="modal-content shortcuts-modal" @click.stop>
        <h4>快捷键</h4>
        <div class="shortcut-list">
          <div v-for="item in shortcutHints" :key="item.keys" class="shortcut-row">
            <kbd>{{ item.keys }}</kbd>
            <span>{{ item.action }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showShortcutHelp = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: var(--color-bg);
  color: var(--color-text);
}

/* Splitpanes specific styles */
:deep(.splitpanes__splitter) {
  background-color: var(--color-border);
  position: relative;
}

:deep(.splitpanes__splitter:before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  transition: opacity 0.4s;
  background-color: var(--color-primary);
  opacity: 0;
  z-index: 1;
}

:deep(.splitpanes__splitter:hover:before) {
  opacity: 1;
}

:deep(.splitpanes--vertical > .splitpanes__splitter:before) {
  left: -2px;
  right: -2px;
  height: 100%;
}

:deep(.splitpanes--horizontal > .splitpanes__splitter:before) {
  top: -2px;
  bottom: -2px;
  width: 100%;
}

.sidebar-pane {
  background: var(--color-surface);
  overflow: auto;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  height: 100%;
}

.main-pane {
  display: flex;
  flex-direction: column;
}

/* 流列表样式 */
.stream-list {
  background: var(--color-panel);
  border-radius: 12px;
  padding: 16px;
}

.stream-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stream-list-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text);
  font-weight: 600;
}

.stream-stats {
  display: flex;
  gap: 8px;
}

.stream-search {
  margin-bottom: 10px;
}

.stream-search input {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--color-input-border);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 13px;
}

.stream-search input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.stat-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.stat-badge.running {
  background: rgba(76, 175, 80, 0.2);
  color: var(--color-success);
}

.stat-badge.total {
  background: rgba(158, 158, 158, 0.2);
  color: var(--color-text-muted);
}

.stream-items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stream-items li {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  background: var(--color-panel-alt);
}

.stream-items li:hover {
  background: var(--color-panel-hover);
  border-color: var(--color-border);
}

.stream-items li.active {
  border-color: var(--color-primary);
}

.stream-items li.flash-success {
  border-color: var(--color-success);
  animation: flash-success 0.8s ease;
}

.stream-items li.flash-error {
  border-color: var(--color-danger);
  animation: flash-error 0.8s ease;
}

.stream-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stream-icon {
  font-size: 20px;
}

.stream-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.stream-name {
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stream-type {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.stream-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stream-status-badge {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  background: var(--color-border);
}

.action-btn:hover {
  transform: scale(1.1);
}

.action-btn.start {
  background: rgba(76, 175, 80, 0.2);
  color: var(--color-success);
}

.action-btn.start:hover {
  background: rgba(76, 175, 80, 0.3);
}

.action-btn.stop {
  background: rgba(255, 152, 0, 0.2);
  color: var(--color-warning);
}

.action-btn.stop:hover {
  background: rgba(255, 152, 0, 0.3);
}

.action-btn.delete {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.action-btn.delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted);
  padding: 20px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes flash-success {
  0% {
    box-shadow: 0 0 0 0 var(--color-success-glow);
  }
  100% {
    box-shadow: 0 0 0 14px rgba(0, 0, 0, 0);
  }
}

@keyframes flash-error {
  0% {
    box-shadow: 0 0 0 0 var(--color-danger-glow);
  }
  100% {
    box-shadow: 0 0 0 14px rgba(0, 0, 0, 0);
  }
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  color: var(--color-text-subtle);
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty p {
  margin: 0;
}

.empty .hint {
  font-size: 12px;
  margin-top: 4px;
  color: var(--color-text-subtle);
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 16px;
  overflow: hidden;
}

.panel-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--color-panel);
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 13px;
}

.global-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--color-panel);
  border-radius: 10px;
  border: 1px solid var(--color-border);
  gap: 12px;
}

.global-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-summary {
  font-size: 12px;
  color: var(--color-text-muted);
}

.global-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.video-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  height: 100%;
}

.video-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--color-panel);
  border-radius: 10px;
  border: 1px solid var(--color-border);
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.toolbar-select {
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 12px;
}

.grid-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  overflow: auto;
}

.grid-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.grid-header h3 {
  margin: 0;
  font-size: 16px;
}

.video-container {
  flex: 1;
  position: relative;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
}

.no-stream {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-subtle);
}

.no-stream-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.no-stream p {
  margin: 0;
  font-size: 16px;
}

/* 控制栏 */
.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-panel);
  border-radius: 10px;
}

.control-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-stream-name {
  font-weight: 500;
  font-size: 14px;
}

.control-status {
  font-size: 12px;
}

.control-buttons {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.btn-secondary {
  background: var(--color-border);
  color: var(--color-text);
}

.btn-secondary:hover {
  background: var(--color-border-strong);
}

.btn-start {
  background: var(--color-success);
  color: #fff;
}

.btn-start:hover {
  background: #43a047;
}

.btn-stop {
  background: var(--color-warning);
  color: #fff;
}

.btn-stop:hover {
  background: #f57c00;
}

.btn-delete {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.btn-delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

/* 删除确认对话框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-panel);
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  border: 1px solid var(--color-border);
}

.modal-content h4 {
  margin: 0 0 12px;
  font-size: 18px;
  color: var(--color-text);
}

.modal-content p {
  margin: 0 0 20px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.shortcuts-modal {
  max-width: 420px;
  width: 100%;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.shortcut-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--color-panel-alt);
  border: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-muted);
}

.shortcut-row kbd {
  background: var(--color-border);
  border: 1px solid var(--color-border-strong);
  border-radius: 6px;
  padding: 4px 8px;
  color: var(--color-text);
  font-size: 12px;
  min-width: 46px;
  text-align: center;
}

.btn-cancel {
  background: var(--color-border);
  color: var(--color-text);
}

.btn-cancel:hover {
  background: var(--color-border-strong);
}

.btn-confirm-delete {
  background: var(--color-danger);
  color: #fff;
}

.btn-confirm-delete:hover {
  background: #e53935;
}

.data-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
  padding-top: 12px;
}
</style>
