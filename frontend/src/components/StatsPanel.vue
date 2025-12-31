<script setup lang="ts">
/**
 * 实时统计面板组件
 * 显示当前总人数和各区域密度
 * Requirements: 5.1, 5.2, 5.3
 */

import { computed, ref, watch } from 'vue'
import type { DetectionResult } from '@/types'

const props = defineProps<{
  result: DetectionResult | null
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
  background: #1e1e1e;
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
  color: #fff;
  font-weight: 600;
}

.timestamp {
  font-size: 12px;
  color: #888;
  font-family: monospace;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: #666;
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
  background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  border: 1px solid #333;
}

.count-label {
  font-size: 14px;
  color: #888;
  margin-bottom: 8px;
}

.count-value {
  font-size: 48px;
  font-weight: 700;
  color: #4a9eff;
  line-height: 1;
  transition: transform 0.15s ease;
}

.count-value.animating {
  transform: scale(1.05);
}

.count-value .unit {
  font-size: 18px;
  font-weight: 400;
  color: #888;
  margin-left: 4px;
}

/* 区域统计 */
.region-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 13px;
  color: #888;
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
  border-color: rgba(255, 255, 255, 0.1);
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
  color: #fff;
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
  color: #fff;
  line-height: 1.2;
}

.data-label {
  font-size: 11px;
  color: #666;
  margin-top: 2px;
}

/* 密度进度条 */
.density-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
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
  color: #666;
  font-size: 14px;
}

.no-regions .sub-hint {
  color: #555;
  font-size: 12px;
  margin-top: 4px;
}
</style>
