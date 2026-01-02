<script setup lang="ts">
/**
 * 实时统计面板组件
 * 显示当前总人数和各区域密度
 * Requirements: 5.1, 5.2, 5.3
 */

import { computed, ref, watch } from 'vue'
import type { DetectionResult, StatusMetrics } from '@/types'
import { submitFeedback } from '@/api/feedback'

const props = defineProps<{
  result: DetectionResult | null
  metrics?: StatusMetrics | null
  streamId?: string | null
}>()

// 动画状态
const animatedCount = ref(0)
const isCountAnimating = ref(false)

// 密度等级配置
const DENSITY_CONFIG = {
  low: {
    color: '#4caf50',
    bgColor: 'rgba(76, 175, 80, 0.15)',
    label: '低密度'
  },
  medium: {
    color: '#ff9800',
    bgColor: 'rgba(255, 152, 0, 0.15)',
    label: '中密度'
  },
  high: {
    color: '#f44336',
    bgColor: 'rgba(244, 67, 54, 0.15)',
    label: '高密度'
  }
}

// 计算属性
const totalCount = computed(() => props.result?.total_count ?? 0)
const regionStats = computed(() => props.result?.region_stats ?? [])
const timestamp = computed(() => {
  if (!props.result?.timestamp) return null
  return new Date(props.result.timestamp * 1000).toLocaleTimeString()
})

const metrics = computed(() => props.metrics ?? null)

const confidenceBuckets = computed(() => {
  const buckets = Array.from({ length: 10 }, () => 0)
  if (!props.result?.detections?.length) return buckets
  for (const det of props.result.detections) {
    const idx = Math.min(9, Math.floor(det.confidence * 10))
    if (buckets[idx] !== undefined) {
      buckets[idx] += 1
    }
  }
  return buckets
})

const maxBucket = computed(() => Math.max(1, ...confidenceBuckets.value))

const healthLabel = computed(() => {
  const health = metrics.value?.health
  if (!health) return '未知'
  if (health === 'healthy') return '健康'
  if (health === 'degraded') return '降级'
  if (health === 'cooldown') return '冷却'
  return '异常'
})

const healthColor = computed(() => {
  const health = metrics.value?.health
  if (health === 'healthy') return '#4caf50'
  if (health === 'degraded') return '#ff9800'
  if (health === 'cooldown') return '#2196f3'
  return '#f44336'
})

const showFeedback = ref(false)
const feedbackMessage = ref('')
const feedbackSending = ref(false)
const feedbackError = ref('')

async function sendFeedback() {
  if (!props.streamId) return
  feedbackSending.value = true
  feedbackError.value = ''
  try {
    await submitFeedback({
      stream_id: props.streamId,
      message: feedbackMessage.value.trim() || undefined,
      payload: props.result
        ? {
            timestamp: props.result.timestamp,
            total_count: props.result.total_count,
            detection_count: props.result.detections.length,
            frame_width: props.result.frame_width,
            frame_height: props.result.frame_height
          }
        : {}
    })
    feedbackMessage.value = ''
    showFeedback.value = false
  } catch (err) {
    feedbackError.value = err instanceof Error ? err.message : '提交失败'
  } finally {
    feedbackSending.value = false
  }
}

// 监听总人数变化，触发动画
watch(totalCount, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    animateCount(oldVal ?? 0, newVal)
  }
}, { immediate: true })

// 数字动画
function animateCount(from: number, to: number) {
  isCountAnimating.value = true
  const duration = 300 // ms
  const startTime = performance.now()
  const diff = to - from

  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    
    // 使用 easeOutQuad 缓动函数
    const easeProgress = 1 - (1 - progress) * (1 - progress)
    animatedCount.value = Math.round(from + diff * easeProgress)

    if (progress < 1) {
      requestAnimationFrame(update)
    } else {
      isCountAnimating.value = false
    }
  }

  requestAnimationFrame(update)
}

// 获取密度等级配置
function getDensityConfig(level: string) {
  return DENSITY_CONFIG[level as keyof typeof DENSITY_CONFIG] || DENSITY_CONFIG.low
}

// 格式化密度百分比
function formatDensity(density: number): string {
  return (density * 100).toFixed(1) + '%'
}
</script>

<template>
  <div class="stats-panel">
    <div class="panel-header">
      <h3>📊 实时统计</h3>
      <span v-if="timestamp" class="timestamp">{{ timestamp }}</span>
    </div>

    <!-- 无数据状态 -->
    <div v-if="!result" class="no-data">
      <span class="icon">📡</span>
      <p>等待检测数据...</p>
    </div>

    <template v-else>
      <!-- 总人数卡片 -->
      <div class="total-count-card">
        <div class="count-label">当前总人数</div>
        <div class="count-value" :class="{ animating: isCountAnimating }">
          {{ animatedCount }}
          <span class="unit">人</span>
        </div>
      </div>

      <!-- 状态指标 -->
      <div v-if="metrics" class="metrics-card">
        <div class="section-title">渲染状态</div>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">渲染 FPS</span>
            <span class="metric-value">{{ metrics.render_fps_actual }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">推理 FPS</span>
            <span class="metric-value">{{ metrics.infer_fps_actual }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">延迟</span>
            <span class="metric-value">{{ metrics.latency_ms }} ms</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">健康</span>
            <span class="metric-value" :style="{ color: healthColor }">{{ healthLabel }}</span>
          </div>
        </div>
      </div>

      <!-- 置信度分布 -->
      <div class="confidence-card">
        <div class="section-title">置信度分布</div>
        <div class="confidence-bars">
          <div
            v-for="(count, idx) in confidenceBuckets"
            :key="idx"
            class="confidence-bar"
          >
            <div
              class="confidence-fill"
              :style="{ height: `${(count / maxBucket) * 100}%` }"
            ></div>
            <span class="confidence-label">{{ idx * 10 }}%</span>
          </div>
        </div>
      </div>

      <!-- 反馈入口 -->
      <div class="feedback-card">
        <div class="section-title">反馈入口</div>
        <button class="feedback-toggle" @click="showFeedback = !showFeedback">
          {{ showFeedback ? '取消反馈' : '提交反馈' }}
        </button>
        <div v-if="showFeedback" class="feedback-form">
          <textarea
            v-model="feedbackMessage"
            class="feedback-input"
            placeholder="描述问题或建议..."
          ></textarea>
          <div class="feedback-actions">
            <span v-if="feedbackError" class="feedback-error">{{ feedbackError }}</span>
            <button class="feedback-submit" :disabled="feedbackSending" @click="sendFeedback">
              {{ feedbackSending ? '提交中...' : '提交' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 区域统计列表 -->
      <div v-if="regionStats.length > 0" class="region-stats">
        <div class="section-title">区域密度</div>
        <div
          v-for="region in regionStats"
          :key="region.region_id"
          class="region-item"
          :style="{ backgroundColor: getDensityConfig(region.level).bgColor }"
        >
          <div class="region-info">
            <span class="region-name">{{ region.region_name }}</span>
            <span
              class="density-badge"
              :style="{ 
                backgroundColor: getDensityConfig(region.level).color,
                color: '#fff'
              }"
            >
              {{ getDensityConfig(region.level).label }}
            </span>
          </div>
          <div class="region-data">
            <div class="data-item">
              <span class="data-value">{{ region.count }}</span>
              <span class="data-label">人数</span>
            </div>
            <div class="data-item">
              <span class="data-value" :style="{ color: getDensityConfig(region.level).color }">
                {{ formatDensity(region.density) }}
              </span>
              <span class="data-label">密度</span>
            </div>
          </div>
          <!-- 密度进度条 -->
          <div class="density-bar">
            <div
              class="density-fill"
              :style="{
                width: Math.min(region.density * 100, 100) + '%',
                backgroundColor: getDensityConfig(region.level).color
              }"
            ></div>
          </div>
        </div>
      </div>

      <!-- 无区域数据 -->
      <div v-else class="no-regions">
        <span class="hint">暂无区域统计数据</span>
        <span class="sub-hint">请先绘制感兴趣区域 (ROI)</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-panel {
  background: var(--color-panel);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text);
  font-weight: 600;
}

.timestamp {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: monospace;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: var(--color-text-subtle);
}

.no-data .icon {
  font-size: 32px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

/* 总人数卡片 */
.total-count-card {
  background: linear-gradient(135deg, var(--color-panel-alt) 0%, var(--color-surface) 100%);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  border: 1px solid var(--color-border);
}

.count-label {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-bottom: 8px;
}

.count-value {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1;
  transition: transform 0.15s ease;
}

.count-value.animating {
  transform: scale(1.05);
}

.count-value .unit {
  font-size: 18px;
  font-weight: 400;
  color: var(--color-text-muted);
  margin-left: 4px;
}

/* 区域统计 */
.region-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 状态指标 */
.metrics-card {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 8px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 11px;
  color: var(--color-text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 16px;
  color: var(--color-text);
  font-weight: 600;
}

/* 置信度分布 */
.confidence-card {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
}

.confidence-bars {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
  margin-top: 10px;
  align-items: end;
}

.confidence-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.confidence-fill {
  width: 100%;
  min-height: 4px;
  border-radius: 4px;
  background: linear-gradient(180deg, var(--color-primary), var(--color-primary-strong));
  transition: height 0.3s ease;
}

.confidence-label {
  font-size: 9px;
  color: var(--color-text-subtle);
}

/* 反馈入口 */
.feedback-card {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
}

.feedback-toggle {
  margin-top: 8px;
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  background: var(--color-border);
  color: var(--color-text);
  cursor: pointer;
  font-size: 12px;
}

.feedback-toggle:hover {
  background: var(--color-border-strong);
}

.feedback-form {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedback-input {
  min-height: 80px;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 12px;
  resize: vertical;
}

.feedback-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.feedback-error {
  font-size: 11px;
  color: var(--color-danger);
}

.feedback-submit {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.feedback-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.section-title {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.region-item {
  border-radius: 8px;
  padding: 12px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.region-item:hover {
  border-color: var(--color-border);
}

.region-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.region-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.density-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.region-data {
  display: flex;
  gap: 24px;
  margin-bottom: 10px;
}

.data-item {
  display: flex;
  flex-direction: column;
}

.data-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.2;
}

.data-label {
  font-size: 11px;
  color: var(--color-text-subtle);
  margin-top: 2px;
}

/* 密度进度条 */
.density-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.density-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease, background-color 0.3s ease;
}

/* 无区域数据 */
.no-regions {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  text-align: center;
}

.no-regions .hint {
  color: var(--color-text-subtle);
  font-size: 14px;
}

.no-regions .sub-hint {
  color: var(--color-text-subtle);
  font-size: 12px;
  margin-top: 4px;
}
</style>
