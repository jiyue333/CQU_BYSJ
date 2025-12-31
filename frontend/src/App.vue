<script setup lang="ts">
/**
 * 主应用组件
 * 集成视频源选择、播放器、热力图叠加、实时统计面板、配置管理、错误通知
 * Requirements: 5.1, 5.2, 5.3, 7.1, 8.1, 8.2, 8.3, 9.2, 9.4
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import VideoSourceSelector from './components/VideoSourceSelector.vue'
import VideoPlayer from './components/VideoPlayer.vue'
import HeatmapOverlay from './components/HeatmapOverlay.vue'
import StatsPanel from './components/StatsPanel.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import ErrorNotification from './components/ErrorNotification.vue'
import ConnectionIndicator from './components/ConnectionIndicator.vue'
import { useStreamsStore } from './stores/streams'
import type { VideoStream, StreamStatus, DetectionResult } from './types'

const store = useStreamsStore()

// 当前选中的流
const selectedStreamId = ref<string | null>(null)

// 热力图显示开关
const showHeatmap = ref(true)

// 删除确认对话框
const showDeleteConfirm = ref(false)
const streamToDelete = ref<string | null>(null)

// 视频容器尺寸
const videoContainerRef = ref<HTMLDivElement | null>(null)
const videoWidth = ref(640)
const videoHeight = ref(480)

// 计算属性
const selectedStream = computed<VideoStream | undefined>(() => {
  if (!selectedStreamId.value) return undefined
  return store.streams.get(selectedStreamId.value)
})

const currentResult = computed<DetectionResult | null>(() => {
  if (!selectedStreamId.value) return null
  return store.getDetectionResult(selectedStreamId.value) ?? null
})

const heatmapGrid = computed(() => {
  return currentResult.value?.heatmap_grid || null
})

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

// 启动流
async function handleStart(streamId?: string) {
  const targetId = streamId || selectedStreamId.value
  if (!targetId) return
  try {
    await store.startStream(targetId)
    // 订阅检测结果
    store.subscribeResult(targetId)
  } catch (err) {
    console.error('Failed to start stream:', err)
  }
}

// 停止流
async function handleStop(streamId?: string) {
  const targetId = streamId || selectedStreamId.value
  if (!targetId) return
  try {
    await store.stopStream(targetId)
  } catch (err) {
    console.error('Failed to stop stream:', err)
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
    if (selectedStreamId.value === targetId) {
      selectedStreamId.value = null
    }
  } catch (err) {
    console.error('Failed to delete stream:', err)
  } finally {
    showDeleteConfirm.value = false
    streamToDelete.value = null
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

// 更新视频容器尺寸
function updateVideoSize() {
  if (videoContainerRef.value) {
    videoWidth.value = videoContainerRef.value.clientWidth
    videoHeight.value = videoContainerRef.value.clientHeight
  }
}

// 监听窗口大小变化
onMounted(async () => {
  // 获取流列表
  try {
    await store.fetchStreams()
  } catch (err) {
    console.error('Failed to fetch streams:', err)
    // Error is already stored in store.error
  }

  // 订阅状态变更
  store.subscribeStatus()

  // 监听窗口大小
  window.addEventListener('resize', updateVideoSize)
  updateVideoSize()
})

onUnmounted(() => {
  store.cleanup()
  window.removeEventListener('resize', updateVideoSize)
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
</script>

<template>
  <div class="app">
    <!-- 错误通知 -->
    <ErrorNotification 
      :notifications="store.notifications" 
      @dismiss="onDismissNotification" 
    />

    <!-- 侧边栏 -->
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

        <!-- WebSocket 连接状态 -->
        <ConnectionIndicator :state="connectionState" />

        <div v-if="store.loading" class="loading">
          <span class="spinner"></span>
          加载中...
        </div>
        <div v-else-if="store.streamList.length === 0" class="empty">
          <span class="empty-icon">📭</span>
          <p>暂无视频流</p>
          <p class="hint">请在上方添加视频源</p>
        </div>
        <ul v-else class="stream-items">
          <li
            v-for="stream in store.streamList"
            :key="stream.stream_id"
            :class="{ active: stream.stream_id === selectedStreamId }"
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
      <ConfigPanel
        :stream-id="selectedStreamId"
        @error="onError"
      />
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 视频播放区 -->
      <div class="video-section">
        <div ref="videoContainerRef" class="video-container">
          <template v-if="selectedStream">
            <VideoPlayer
              :play-url="selectedStream.play_url"
              :stream-id="selectedStream.stream_id"
              :status="selectedStream.status"
            />
            <HeatmapOverlay
              :heatmap-grid="heatmapGrid"
              :visible="showHeatmap"
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

          <div class="control-toggles">
            <label class="toggle">
              <input v-model="showHeatmap" type="checkbox" />
              <span>显示热力图</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 实时统计面板 -->
      <StatsPanel :result="currentResult" />
    </main>

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
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: #121212;
  color: #fff;
}

.sidebar {
  width: 420px;
  background: #1a1a1a;
  border-right: 1px solid #333;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

/* 流列表样式 */
.stream-list {
  background: #1e1e1e;
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
  color: #fff;
  font-weight: 600;
}

.stream-stats {
  display: flex;
  gap: 8px;
}

.stat-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.stat-badge.running {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.stat-badge.total {
  background: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
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
  background: #252525;
}

.stream-items li:hover {
  background: #2a2a2a;
  border-color: #333;
}

.stream-items li.active {
  border-color: #4a9eff;
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
  color: #666;
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
  background: #333;
}

.action-btn:hover {
  transform: scale(1.1);
}

.action-btn.start {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.action-btn.start:hover {
  background: rgba(76, 175, 80, 0.3);
}

.action-btn.stop {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.action-btn.stop:hover {
  background: rgba(255, 152, 0, 0.3);
}

.action-btn.delete {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.action-btn.delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #888;
  padding: 20px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #333;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  color: #666;
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
  color: #555;
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

.video-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
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
  color: #666;
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
  background: #1e1e1e;
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

.btn-start {
  background: #4caf50;
  color: #fff;
}

.btn-start:hover {
  background: #43a047;
}

.btn-stop {
  background: #ff9800;
  color: #fff;
}

.btn-stop:hover {
  background: #f57c00;
}

.btn-delete {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.btn-delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

.control-toggles {
  display: flex;
  gap: 16px;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #aaa;
}

.toggle input {
  width: 18px;
  height: 18px;
  accent-color: #4a9eff;
}

/* 删除确认对话框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  border: 1px solid #333;
}

.modal-content h4 {
  margin: 0 0 12px;
  font-size: 18px;
  color: #fff;
}

.modal-content p {
  margin: 0 0 20px;
  color: #888;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel {
  background: #333;
  color: #fff;
}

.btn-cancel:hover {
  background: #444;
}

.btn-confirm-delete {
  background: #f44336;
  color: #fff;
}

.btn-confirm-delete:hover {
  background: #e53935;
}
</style>
