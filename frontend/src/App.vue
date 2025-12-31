<script setup lang="ts">
/**
 * 主应用组件
 * 集成视频源选择、播放器、热力图叠加
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import VideoSourceSelector from './components/VideoSourceSelector.vue'
import VideoPlayer from './components/VideoPlayer.vue'
import HeatmapOverlay from './components/HeatmapOverlay.vue'
import { useStreamsStore } from './stores/streams'
import type { VideoStream } from './types'

const store = useStreamsStore()

// 当前选中的流
const selectedStreamId = ref<string | null>(null)

// 热力图显示开关
const showHeatmap = ref(true)

// 视频容器尺寸
const videoContainerRef = ref<HTMLDivElement | null>(null)
const videoWidth = ref(640)
const videoHeight = ref(480)

// 计算属性
const selectedStream = computed<VideoStream | undefined>(() => {
  if (!selectedStreamId.value) return undefined
  return store.streams.get(selectedStreamId.value)
})

const currentResult = computed(() => {
  if (!selectedStreamId.value) return null
  return store.getDetectionResult(selectedStreamId.value)
})

const heatmapGrid = computed(() => {
  return currentResult.value?.heatmap_grid || null
})

// 处理流创建
function onStreamCreated(streamId: string) {
  selectedStreamId.value = streamId
}

// 处理错误
function onError(message: string) {
  console.error('Error:', message)
}

// 启动流
async function handleStart() {
  if (!selectedStreamId.value) return
  try {
    await store.startStream(selectedStreamId.value)
    // 订阅检测结果
    store.subscribeResult(selectedStreamId.value)
  } catch (err) {
    console.error('Failed to start stream:', err)
  }
}

// 停止流
async function handleStop() {
  if (!selectedStreamId.value) return
  try {
    await store.stopStream(selectedStreamId.value)
  } catch (err) {
    console.error('Failed to stop stream:', err)
  }
}

// 删除流
async function handleDelete() {
  if (!selectedStreamId.value) return
  try {
    await store.deleteStream(selectedStreamId.value)
    selectedStreamId.value = null
  } catch (err) {
    console.error('Failed to delete stream:', err)
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

// 状态颜色映射
function getStatusColor(status: string): string {
  switch (status) {
    case 'running':
      return '#4caf50'
    case 'starting':
      return '#ff9800'
    case 'stopped':
      return '#9e9e9e'
    case 'error':
      return '#f44336'
    case 'cooldown':
      return '#2196f3'
    default:
      return '#9e9e9e'
  }
}
</script>

<template>
  <div class="app">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <!-- 视频源选择器 -->
      <VideoSourceSelector @created="onStreamCreated" @error="onError" />

      <!-- 流列表 -->
      <div class="stream-list">
        <h3>视频流列表</h3>
        <div v-if="store.loading" class="loading">加载中...</div>
        <div v-else-if="store.streamList.length === 0" class="empty">暂无视频流</div>
        <ul v-else>
          <li
            v-for="stream in store.streamList"
            :key="stream.stream_id"
            :class="{ active: stream.stream_id === selectedStreamId }"
            @click="selectStream(stream.stream_id)"
          >
            <span class="stream-name">{{ stream.name }}</span>
            <span class="stream-status" :style="{ color: getStatusColor(stream.status) }">
              {{ stream.status }}
            </span>
          </li>
        </ul>
      </div>
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
            />
            <HeatmapOverlay
              :heatmap-grid="heatmapGrid"
              :visible="showHeatmap"
              :width="videoWidth"
              :height="videoHeight"
            />
          </template>
          <div v-else class="no-stream">
            <p>请选择或创建视频流</p>
          </div>
        </div>

        <!-- 控制栏 -->
        <div v-if="selectedStream" class="controls">
          <div class="control-buttons">
            <button
              v-if="selectedStream.status === 'stopped' || selectedStream.status === 'error'"
              class="btn btn-start"
              @click="handleStart"
            >
              ▶ 开始
            </button>
            <button
              v-if="selectedStream.status === 'running' || selectedStream.status === 'starting'"
              class="btn btn-stop"
              @click="handleStop"
            >
              ⏹ 停止
            </button>
            <button class="btn btn-delete" @click="handleDelete">🗑 删除</button>
          </div>

          <div class="control-toggles">
            <label class="toggle">
              <input v-model="showHeatmap" type="checkbox" />
              <span>显示热力图</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 统计面板 -->
      <div v-if="currentResult" class="stats-panel">
        <h3>实时统计</h3>
        <div class="stat-item">
          <span class="stat-label">总人数</span>
          <span class="stat-value">{{ currentResult.total_count }}</span>
        </div>
        <div v-for="region in currentResult.region_stats" :key="region.region_id" class="stat-item">
          <span class="stat-label">{{ region.region_name }}</span>
          <span class="stat-value">
            {{ region.count }} 人
            <span :class="['density-level', region.level]">{{ region.level.toUpperCase() }}</span>
          </span>
        </div>
      </div>
    </main>
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

.stream-list {
  background: #1a1a1a;
  border-radius: 8px;
}

.stream-list h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #aaa;
}

.stream-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.stream-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.stream-list li:hover {
  background: #2a2a2a;
}

.stream-list li.active {
  background: #333;
  border-left: 3px solid #4a9eff;
}

.stream-name {
  font-weight: 500;
}

.stream-status {
  font-size: 12px;
  text-transform: uppercase;
}

.loading,
.empty {
  color: #888;
  text-align: center;
  padding: 20px;
}

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
  border-radius: 8px;
  overflow: hidden;
}

.no-stream {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #1a1a1a;
  border-radius: 8px;
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
  transition: background 0.2s;
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
  background: #f44336;
  color: #fff;
}

.btn-delete:hover {
  background: #e53935;
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
}

.toggle input {
  width: 18px;
  height: 18px;
}

.stats-panel {
  background: #1a1a1a;
  border-radius: 8px;
  padding: 16px;
}

.stats-panel h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #aaa;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #333;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #888;
}

.stat-value {
  font-weight: 500;
  font-size: 18px;
}

.density-level {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 8px;
}

.density-level.low {
  background: #4caf50;
  color: #fff;
}

.density-level.medium {
  background: #ff9800;
  color: #fff;
}

.density-level.high {
  background: #f44336;
  color: #fff;
}
</style>
