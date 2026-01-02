<script setup lang="ts">
/**
 * 多路流网格视图
 * 支持多路同时播放、不同的网格布局 (Auto, 2x2, 3x3)
 * Requirements: P2.2
 */

import { ref, computed } from 'vue'
import type { DetectionResult, VideoStream } from '@/types'
import VideoPlayer from './VideoPlayer.vue'

const props = defineProps<{
  items: Array<{
    stream: VideoStream
    result?: DetectionResult | null
  }>
  selectedId: string | null
}>()

const emit = defineEmits<{
  (e: 'select', streamId: string): void
}>()

// 布局模式
type LayoutMode = 'auto' | '2x2' | '3x3'
const layoutMode = ref<LayoutMode>('auto')

// 计算网格样式
const gridStyle = computed(() => {
  const count = props.items.length
  
  if (layoutMode.value === '2x2') {
    return {
      gridTemplateColumns: 'repeat(2, 1fr)',
      gridTemplateRows: 'repeat(2, 1fr)'
    }
  }
  
  if (layoutMode.value === '3x3') {
    return {
      gridTemplateColumns: 'repeat(3, 1fr)',
      gridTemplateRows: 'repeat(3, 1fr)'
    }
  }

  // Auto mode logic
  if (count <= 1) return { gridTemplateColumns: '1fr' }
  if (count <= 4) return { gridTemplateColumns: 'repeat(2, 1fr)', gridTemplateRows: 'repeat(2, 1fr)' }
  if (count <= 9) return { gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(3, 1fr)' }
  
  return { gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }
})

const activeItems = computed(() => {
  if (layoutMode.value === '2x2') return props.items.slice(0, 4)
  if (layoutMode.value === '3x3') return props.items.slice(0, 9)
  return props.items
})

function handleLayoutChange(mode: LayoutMode) {
  layoutMode.value = mode
}

function handleSelect(streamId: string) {
  emit('select', streamId)
}
</script>

<template>
  <div class="stream-grid-container">
    <!-- 工具栏 -->
    <div class="grid-toolbar">
      <div class="layout-selector">
        <span class="label">布局:</span>
        <button 
          class="mode-btn" 
          :class="{ active: layoutMode === 'auto' }"
          @click="handleLayoutChange('auto')"
        >
          自动
        </button>
        <button 
          class="mode-btn" 
          :class="{ active: layoutMode === '2x2' }"
          @click="handleLayoutChange('2x2')"
        >
          2x2
        </button>
        <button 
          class="mode-btn" 
          :class="{ active: layoutMode === '3x3' }"
          @click="handleLayoutChange('3x3')"
        >
          3x3
        </button>
      </div>
      <div class="grid-stats">
        {{ activeItems.length }} 路视频
      </div>
    </div>

    <!-- 视频网格 -->
    <div class="stream-grid" :style="gridStyle">
      <div
        v-for="item in activeItems"
        :key="item.stream.stream_id"
        class="grid-item"
        :class="{ 
          selected: item.stream.stream_id === selectedId,
          error: item.stream.status === 'error'
        }"
        @click="handleSelect(item.stream.stream_id)"
      >
        <!-- 视频播放器 -->
        <VideoPlayer
          class="grid-video"
          :play-url="item.stream.play_url"
          :webrtc-url="item.stream.webrtc_url"
          :stream-id="item.stream.stream_id"
          :status="undefined" 
          :preferred-protocol="'auto'"
        />

        <!-- 信息遮罩层 -->
        <div class="grid-overlay">
          <div class="header">
            <span class="stream-name">{{ item.stream.name }}</span>
            <span class="status-dot" :class="item.stream.status"></span>
          </div>
          
          <div class="stats" v-if="item.result">
            <span class="count">{{ item.result.total_count }}</span>
            <span class="unit">人</span>
          </div>
          <div class="no-data" v-else>--</div>
        </div>
      </div>
      
      <!-- 补充占位符 (为了保持网格形状) -->
      <template v-if="layoutMode === '2x2' && activeItems.length < 4">
        <div v-for="n in (4 - activeItems.length)" :key="`placeholder-${n}`" class="grid-item placeholder">
          <span class="empty-icon">📺</span>
        </div>
      </template>
      <template v-if="layoutMode === '3x3' && activeItems.length < 9">
        <div v-for="n in (9 - activeItems.length)" :key="`placeholder-${n}`" class="grid-item placeholder">
          <span class="empty-icon">📺</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.stream-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.grid-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
}

.layout-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-panel);
  padding: 4px;
  border-radius: 8px;
}

.label {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 0 4px;
}

.mode-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.mode-btn:hover {
  text-decoration: underline;
}

.mode-btn.active {
  background: var(--color-border);
  color: var(--color-primary);
  font-weight: 500;
}

.grid-stats {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.stream-grid {
  display: grid;
  gap: 8px;
  flex: 1;
  overflow: auto;
  padding: 4px;
}

.grid-item {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: border-color 0.2s;
  aspect-ratio: 16 / 9;
}

.grid-item.selected {
  border-color: var(--color-primary);
}

.grid-item.error {
  border-color: var(--color-danger);
}

.grid-item.placeholder {
  background: var(--color-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
}

.empty-icon {
  font-size: 32px;
  opacity: 0.2;
}

/* 强制 VideoPlayer 适应容器 */
.grid-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 覆盖层 */
.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  /* 渐变遮罩增强文字可读性 */
  background: linear-gradient(to bottom, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 70%, rgba(0,0,0,0.6) 100%);
  pointer-events: none; /* 让点击穿透到 grid-item */
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stream-name {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80%;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-subtle);
  box-shadow: 0 0 4px rgba(0,0,0,0.5);
}

.status-dot.running { background: var(--color-success); }
.status-dot.stopped { background: var(--color-text-muted); }
.status-dot.error { background: var(--color-danger); }
.status-dot.starting { background: var(--color-warning); }

.stats {
  align-self: flex-end;
  display: flex;
  align-items: baseline;
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}

.count {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
}

.unit {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-left: 2px;
}

.no-data {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 14px;
  color: var(--color-text-subtle);
}

/* 修改 VideoPlayer 内部样式以适应网格 */
:deep(.video-player) {
  width: 100%;
  height: 100%;
}

:deep(.video-element) {
  height: 100%;
}

/* 隐藏部分 VideoPlayer 的覆盖层以保持整洁 */
:deep(.protocol-badge),
:deep(.delay-hint),
:deep(.status-badge),
:deep(.latency-badge),
:deep(.webrtc-metrics) {
  display: none !important;
}
</style>
