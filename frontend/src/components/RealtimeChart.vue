<script setup lang="ts">
/**
 * 实时数据折线图组件
 *
 * 功能：
 * - 实时显示检测人数趋势
 * - 支持全局/ROI 维度切换
 * - 滑动窗口机制（自动丢弃旧数据）
 *
 * Requirements: P0.2
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import type { DetectionResult } from '@/types'
import type { ROI } from '@/api/rois'

// Props
const props = defineProps<{
  streamId: string
  result: DetectionResult | null
  rois: ROI[]
}>()

// 状态
const selectedRegionId = ref<string>('global') // 'global' or roi_id
const timeWindow = ref<number>(60) // seconds

// Canvas 引用
const chartCanvas = ref<HTMLCanvasElement | null>(null)

// 数据点接口
interface DataPoint {
  ts: number // timestamp (seconds)
  count: number
  density: number
}

// 缓存的数据序列
// streamId -> regionId -> DataPoint[]
const dataCache = ref<Map<string, Map<string, DataPoint[]>>>(new Map())

// 计算当前要显示的数据
const currentSeries = computed(() => {
  if (!props.streamId) return []
  const streamCache = dataCache.value.get(props.streamId)
  if (!streamCache) return []
  return streamCache.get(selectedRegionId.value) || []
})

// 添加数据点
function addDataPoint(result: DetectionResult) {
  const ts = result.timestamp
  const sid = result.stream_id

  if (!dataCache.value.has(sid)) {
    dataCache.value.set(sid, new Map())
  }
  const streamCache = dataCache.value.get(sid)
  if (!streamCache) return

  // 1. Global Data
  if (!streamCache.has('global')) {
    streamCache.set('global', [])
  }
  const globalSeries = streamCache.get('global')
  if (globalSeries) {
    globalSeries.push({
      ts,
      count: result.total_count,
      density: 0 // Global density not strictly defined, or maybe average?
    })

    // Prune old data
    const cutoff = ts - timeWindow.value
    const first = globalSeries[0]
    while (globalSeries.length > 0 && first && first.ts < cutoff) {
      globalSeries.shift()
    }
  }
  // 2. Region Data
  if (result.region_stats) {
    const cutoff = ts - timeWindow.value
    for (const stat of result.region_stats) {
      if (!streamCache.has(stat.region_id)) {
        streamCache.set(stat.region_id, [])
      }
      const regionSeries = streamCache.get(stat.region_id)
      if (regionSeries) {
        regionSeries.push({
          ts,
          count: stat.count,
          density: stat.density
        })
        // Prune
        const first = regionSeries[0]
        while (regionSeries.length > 0 && first && first.ts < cutoff) {
          regionSeries.shift()
        }
      }
    }
  }
}

// 监听新结果
watch(
  () => props.result,
  (newResult) => {
    if (newResult && newResult.stream_id === props.streamId) {
      addDataPoint(newResult)
      drawChart()
    }
  }
)

// 监听配置变化
watch([timeWindow, selectedRegionId], () => {
  // Trigger redraw immediately, pruning will happen on next data arrival or we can force prune here
  // Ideally force prune
  drawChart()
})

// 绘制图表
function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const width = canvas.width
  const height = canvas.height
  const padding = { top: 20, right: 40, bottom: 30, left: 40 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  // 清空画布
  ctx.clearRect(0, 0, width, height)

  const data = currentSeries.value
  if (data.length < 2) {
    // 绘制空状态提示
    ctx.fillStyle = '#888'
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('等待数据...', width / 2, height / 2)
    return
  }

  // 计算范围
  // const now = Date.now() / 1000
  const lastPoint = data[data.length - 1]
  if (!lastPoint) return
  const maxTime = lastPoint.ts
  const minTime = maxTime - timeWindow.value // Fixed window

  const counts = data.map(d => d.count)
  const maxCount = Math.max(5, ...counts) * 1.2 // 留 20% 顶部空间
  const minCount = 0

  // 绘制坐标轴
  ctx.strokeStyle = '#444'
  ctx.lineWidth = 1

  // Y 轴
  ctx.beginPath()
  ctx.moveTo(padding.left, padding.top)
  ctx.lineTo(padding.left, height - padding.bottom)
  ctx.stroke()

  // X 轴
  ctx.beginPath()
  ctx.moveTo(padding.left, height - padding.bottom)
  ctx.lineTo(width - padding.right, height - padding.bottom)
  ctx.stroke()

  // Y 轴刻度
  ctx.fillStyle = '#888'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  const ySteps = 5
  for (let i = 0; i <= ySteps; i++) {
    const val = Math.round(minCount + (maxCount - minCount) * (i / ySteps))
    const y = height - padding.bottom - (chartHeight * (i / ySteps))
    ctx.fillText(val.toString(), padding.left - 5, y)

    // Grid
    ctx.strokeStyle = '#333'
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(width - padding.right, y)
    ctx.stroke()
  }

  // 绘制折线
  ctx.strokeStyle = '#4CAF50'
  ctx.lineWidth = 2
  ctx.beginPath()

  let started = false
  for (const p of data) {
    if (p.ts < minTime) continue

    const xRatio = (p.ts - minTime) / timeWindow.value
    const yRatio = (p.count - minCount) / (maxCount - minCount)

    const x = padding.left + chartWidth * xRatio
    const y = height - padding.bottom - chartHeight * yRatio

    if (!started) {
      ctx.moveTo(x, y)
      started = true
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()

  // 绘制 X 轴时间标签 (0s, -30s, -60s)
  ctx.fillStyle = '#888'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'

  const xSteps = 6 // 每 10s 一个标签 (if window 60s)
  for (let i = 0; i <= xSteps; i++) {
    const timeOffset = timeWindow.value * (1 - i / xSteps)
    const label = `-${Math.round(timeOffset)}s`
    const x = padding.left + chartWidth * (i / xSteps)
    ctx.fillText(label, x, height - padding.bottom + 5)
  }
}

// Handle resize
function handleResize() {
  if (chartCanvas.value && chartCanvas.value.parentElement) {
    chartCanvas.value.width = chartCanvas.value.parentElement.clientWidth
    drawChart()
  }
}

onMounted(() => {
  if (chartCanvas.value && chartCanvas.value.parentElement) {
    chartCanvas.value.width = chartCanvas.value.parentElement.clientWidth
    chartCanvas.value.height = 200
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

watch(
  () => props.streamId,
  () => {
    // Stream changed, redraw (cache persists for simplicity, or clear?)
    // dataCache.value.clear() // Optional: clear cache on stream change
    drawChart()
  }
)
</script>

<template>
  <div class="realtime-chart">
    <div class="controls">
      <!-- 区域选择 -->
      <select v-model="selectedRegionId" class="control-select">
        <option value="global">全局 (Global)</option>
        <option v-for="roi in rois" :key="roi.roi_id" :value="roi.roi_id">
          {{ roi.name }}
        </option>
      </select>

      <!-- 时间窗口 -->
      <select v-model="timeWindow" class="control-select">
        <option :value="60">1 分钟</option>
        <option :value="300">5 分钟</option>
      </select>
    </div>

    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.realtime-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--color-panel-alt);
  padding: 12px;
  border-radius: 8px;
}

.controls {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.control-select {
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--color-input-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 12px;
}

.chart-wrapper {
  position: relative;
  width: 100%;
  height: 200px;
}

canvas {
  width: 100%;
  height: 100%;
}
</style>
