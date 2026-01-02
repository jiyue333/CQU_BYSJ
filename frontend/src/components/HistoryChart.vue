<script setup lang="ts">
/**
 * 历史数据图表组件
 * 
 * 功能：
 * - 折线图显示人数趋势
 * - 柱状图显示区域密度对比
 * - 时间范围选择器
 * 
 * Requirements: 6.3
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  getAggregatedHistory,
  downloadHistory,
  type AggregationGranularity,
  type AggregatedStat
} from '../api/history'
import { useStreamsStore } from '@/stores/streams'

// Props
const props = defineProps<{
  streamId: string
}>()

// 状态
const loading = ref(false)
const error = ref<string | null>(null)
const historySeries = ref<Array<{
  streamId: string
  name: string
  color: string
  data: AggregatedStat[]
}>>([])

const store = useStreamsStore()

const selectedStreamIds = ref<string[]>([])

const SERIES_COLORS = ['#4CAF50', '#FF9800', '#2196F3', '#E91E63', '#00BCD4', '#FFC107']

// 图表类型
type ChartType = 'line' | 'bar'
const chartType = ref<ChartType>('line')

// 聚合粒度
const granularity = ref<AggregationGranularity>('minute')

// 时间范围预设
type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d' | 'custom'
const timeRange = ref<TimeRange>('1h')

// 自定义时间范围
const customStartTime = ref('')
const customEndTime = ref('')

// Canvas 引用
const chartCanvas = ref<HTMLCanvasElement | null>(null)

const primarySeries = computed(() => historySeries.value[0] || null)
const comparisonMode = computed(() => historySeries.value.length > 1)

const streamOptions = computed(() => store.streamList)
const primarySummary = computed(() => {
  const data = primarySeries.value?.data || []
  if (!data.length) return null
  const total = data.reduce((sum, item) => sum + item.avg_count, 0)
  return {
    points: data.length,
    avg: total / data.length,
    max: Math.max(...data.map((item) => item.max_count))
  }
})

// 计算时间范围
const timeRangeParams = computed(() => {
  const now = new Date()
  let startTime: Date
  
  switch (timeRange.value) {
    case '1h':
      startTime = new Date(now.getTime() - 60 * 60 * 1000)
      break
    case '6h':
      startTime = new Date(now.getTime() - 6 * 60 * 60 * 1000)
      break
    case '24h':
      startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      break
    case '7d':
      startTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      break
    case '30d':
      startTime = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    case 'custom':
      return {
        start_time: customStartTime.value || undefined,
        end_time: customEndTime.value || undefined
      }
    default:
      startTime = new Date(now.getTime() - 60 * 60 * 1000)
  }
  
  return {
    start_time: startTime.toISOString(),
    end_time: now.toISOString()
  }
})

// 加载数据
async function loadData() {
  if (!props.streamId) return
  
  loading.value = true
  error.value = null
  
  try {
    const targets = selectedStreamIds.value.length ? selectedStreamIds.value : [props.streamId]
    const responses = await Promise.all(
      targets.map((streamId) =>
        getAggregatedHistory(streamId, {
          granularity: granularity.value,
          ...timeRangeParams.value
        })
      )
    )
    historySeries.value = responses.map((response, index) => ({
      streamId: response.stream_id,
      name: store.streams.get(response.stream_id)?.name || response.stream_id,
      color: SERIES_COLORS[index % SERIES_COLORS.length] || '#000000',
      data: response.data
    }))

    if (chartType.value === 'bar' && comparisonMode.value) {
      chartType.value = 'line'
    }
    
    // 绘制图表
    drawChart()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load history data'
    historySeries.value = []
  } finally {
    loading.value = false
  }
}

// 绘制图表
function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas || historySeries.value.length === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const colors = getChartColors()
  
  const data = historySeries.value[0]?.data || []
  if (data.length === 0) return
  
  // 清空画布
  const width = canvas.width
  const height = canvas.height
  ctx.clearRect(0, 0, width, height)
  
  // 图表边距
  const padding = { top: 20, right: 20, bottom: 40, left: 50 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  
  // 计算数据范围
  const allValues = historySeries.value.flatMap((series) =>
    series.data.map((d) => d.avg_count)
  )
  const maxCount = Math.max(1, ...allValues)
  const minCount = Math.min(0, ...allValues)
  const range = maxCount - minCount || 1
  
  // 绘制坐标轴
  ctx.strokeStyle = colors.axis
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
  
  // 绘制 Y 轴刻度
  ctx.fillStyle = colors.text
  ctx.font = '12px sans-serif'
  ctx.textAlign = 'right'
  
  const yTicks = 5
  for (let i = 0; i <= yTicks; i++) {
    const value = minCount + (range * i) / yTicks
    const y = height - padding.bottom - (chartHeight * i) / yTicks
    
    ctx.fillText(Math.round(value).toString(), padding.left - 5, y + 4)
    
    // 网格线
    ctx.strokeStyle = colors.grid
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(width - padding.right, y)
    ctx.stroke()
  }
  
  // 绘制数据
  if (chartType.value === 'line') {
    if (comparisonMode.value) {
      drawComparisonLineChart(
        ctx,
        historySeries.value,
        data,
        padding,
        chartWidth,
        chartHeight,
        minCount,
        range
      )
    } else {
      drawLineChart(ctx, data, padding, chartWidth, chartHeight, minCount, range, colors)
    }
  } else {
    drawBarChart(ctx, data, padding, chartWidth, chartHeight, minCount, range, colors)
  }
  
  // 绘制 X 轴标签
  ctx.fillStyle = colors.text
  ctx.textAlign = 'center'
  
  const xLabelCount = Math.min(data.length, 6)
  const step = Math.floor(data.length / xLabelCount)
  
  for (let i = 0; i < data.length; i += step) {
    const item = data[i]
    if (!item) continue
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const date = new Date(item.timestamp)
    const label = formatTimeLabel(date)
    
    ctx.fillText(label, x, height - padding.bottom + 20)
  }
}

function getChartColors() {
  const styles = getComputedStyle(document.documentElement)
  return {
    axis: styles.getPropertyValue('--color-border-strong').trim() || '#444',
    grid: styles.getPropertyValue('--color-border').trim() || '#333',
    text: styles.getPropertyValue('--color-text-muted').trim() || '#888',
    avgLine: styles.getPropertyValue('--color-success').trim() || '#4CAF50',
    maxLine: styles.getPropertyValue('--color-warning').trim() || '#FF5722',
    bar: styles.getPropertyValue('--color-primary').trim() || '#2196F3',
    barStroke: styles.getPropertyValue('--color-primary-strong').trim() || '#1976D2'
  }
}

// 绘制折线图
function drawLineChart(
  ctx: CanvasRenderingContext2D,
  data: AggregatedStat[],
  padding: { top: number; right: number; bottom: number; left: number },
  chartWidth: number,
  chartHeight: number,
  minCount: number,
  range: number,
  colors: ReturnType<typeof getChartColors>
) {
  const canvas = chartCanvas.value!
  const height = canvas.height
  
  // 绘制平均值线
  ctx.strokeStyle = colors.avgLine
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const y = height - padding.bottom - (chartHeight * (d.avg_count - minCount)) / range
    
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // 绘制最大值线（虚线）
  ctx.strokeStyle = colors.maxLine
  ctx.lineWidth = 1
  ctx.setLineDash([5, 5])
  ctx.beginPath()
  
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const y = height - padding.bottom - (chartHeight * (d.max_count - minCount)) / range
    
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  ctx.setLineDash([])
  
  // 绘制数据点
  ctx.fillStyle = colors.avgLine
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const y = height - padding.bottom - (chartHeight * (d.avg_count - minCount)) / range
    
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, Math.PI * 2)
    ctx.fill()
  })
}

function drawComparisonLineChart(
  ctx: CanvasRenderingContext2D,
  seriesList: Array<{ data: AggregatedStat[]; color: string }>,
  baseData: AggregatedStat[],
  padding: { top: number; right: number; bottom: number; left: number },
  chartWidth: number,
  chartHeight: number,
  minCount: number,
  range: number
) {
  const canvas = chartCanvas.value!
  const height = canvas.height
  const baseTimestamps = baseData.map((item) => new Date(item.timestamp).getTime())

  for (const series of seriesList) {
    const lookup = new Map<number, AggregatedStat>()
    for (const item of series.data) {
      lookup.set(new Date(item.timestamp).getTime(), item)
    }

    ctx.strokeStyle = series.color
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.beginPath()

    let started = false
    baseTimestamps.forEach((ts, i) => {
      const item = lookup.get(ts)
      if (!item) {
        started = false
        return
      }
      const x = padding.left + (chartWidth * i) / (baseData.length - 1 || 1)
      const y = height - padding.bottom - (chartHeight * (item.avg_count - minCount)) / range
      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    })

    ctx.stroke()
  }
}

// 绘制柱状图
function drawBarChart(
  ctx: CanvasRenderingContext2D,
  data: AggregatedStat[],
  padding: { top: number; right: number; bottom: number; left: number },
  chartWidth: number,
  chartHeight: number,
  minCount: number,
  range: number,
  colors: ReturnType<typeof getChartColors>
) {
  const canvas = chartCanvas.value!
  const height = canvas.height
  
  const barWidth = Math.max(chartWidth / data.length - 4, 2)
  
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1) - barWidth / 2
    const barHeight = (chartHeight * (d.avg_count - minCount)) / range
    const y = height - padding.bottom - barHeight
    
    // 绘制柱子
    ctx.fillStyle = colors.bar
    ctx.fillRect(x, y, barWidth, barHeight)
    
    // 绘制边框
    ctx.strokeStyle = colors.barStroke
    ctx.lineWidth = 1
    ctx.strokeRect(x, y, barWidth, barHeight)
  })
}

// 格式化时间标签
function formatTimeLabel(date: Date): string {
  if (granularity.value === 'day') {
    return `${date.getMonth() + 1}/${date.getDate()}`
  } else if (granularity.value === 'hour') {
    return `${date.getHours()}:00`
  } else {
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
  }
}

// 导出数据
async function handleExport(format: 'csv' | 'excel') {
  try {
    await downloadHistory(props.streamId, format, timeRangeParams.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to export data'
  }
}

function toggleStreamSelection(streamId: string) {
  const current = new Set(selectedStreamIds.value)
  if (current.has(streamId)) {
    if (current.size === 1) return
    current.delete(streamId)
  } else {
    current.add(streamId)
  }
  selectedStreamIds.value = Array.from(current)
}

// 监听参数变化
watch(
  () => props.streamId,
  (streamId) => {
    if (streamId) {
      selectedStreamIds.value = [streamId]
    } else {
      selectedStreamIds.value = []
    }
  },
  { immediate: true }
)

watch([granularity, timeRange, customStartTime, customEndTime], () => {
  loadData()
})

watch(
  selectedStreamIds,
  () => {
    loadData()
  },
  { deep: true }
)

// 监听图表类型变化
watch(chartType, () => {
  drawChart()
})

// 窗口大小变化时重绘
function handleResize() {
  if (chartCanvas.value) {
    chartCanvas.value.width = chartCanvas.value.parentElement?.clientWidth || 600
    drawChart()
  }
}

function handleThemeChange() {
  drawChart()
}

onMounted(() => {
  if (chartCanvas.value) {
    chartCanvas.value.width = chartCanvas.value.parentElement?.clientWidth || 600
    chartCanvas.value.height = 300
  }
  window.addEventListener('resize', handleResize)
  window.addEventListener('theme-change', handleThemeChange)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('theme-change', handleThemeChange)
})
</script>

<template>
  <div class="history-chart">
    <!-- 控制栏 -->
    <div class="controls">
      <!-- 时间范围选择 -->
      <div class="control-group">
        <label>时间范围:</label>
        <select v-model="timeRange">
          <option value="1h">最近 1 小时</option>
          <option value="6h">最近 6 小时</option>
          <option value="24h">最近 24 小时</option>
          <option value="7d">最近 7 天</option>
          <option value="30d">最近 30 天</option>
          <option value="custom">自定义</option>
        </select>
      </div>
      
      <!-- 自定义时间范围 -->
      <div v-if="timeRange === 'custom'" class="control-group">
        <input
          v-model="customStartTime"
          type="datetime-local"
          placeholder="开始时间"
        />
        <span>至</span>
        <input
          v-model="customEndTime"
          type="datetime-local"
          placeholder="结束时间"
        />
      </div>
      
      <!-- 聚合粒度 -->
      <div class="control-group">
        <label>聚合粒度:</label>
        <select v-model="granularity">
          <option value="minute">分钟</option>
          <option value="hour">小时</option>
          <option value="day">天</option>
        </select>
      </div>
      
      <!-- 图表类型 -->
      <div class="control-group">
        <label>图表类型:</label>
        <select v-model="chartType" :disabled="comparisonMode">
          <option value="line">折线图</option>
          <option value="bar">柱状图</option>
        </select>
        <span v-if="comparisonMode" class="hint">对比模式仅支持折线图</span>
      </div>

      <!-- 多流对比 -->
      <div v-if="streamOptions.length > 1" class="control-group compare-group">
        <label>对比流:</label>
        <div class="compare-list">
          <label
            v-for="stream in streamOptions"
            :key="stream.stream_id"
            class="compare-item"
          >
            <input
              type="checkbox"
              :checked="selectedStreamIds.includes(stream.stream_id)"
              @change="toggleStreamSelection(stream.stream_id)"
            />
            <span :class="{ primary: stream.stream_id === selectedStreamIds[0] }">
              {{ stream.name }}
            </span>
          </label>
        </div>
      </div>
      
      <!-- 导出按钮 -->
      <div class="control-group">
        <button :disabled="loading" @click="handleExport('csv')">导出 CSV</button>
        <button :disabled="loading" @click="handleExport('excel')">导出 Excel</button>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading">加载中...</div>
    
    <!-- 错误提示 -->
    <div v-if="error" class="error">{{ error }}</div>
    
    <!-- 图表 -->
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
      <div v-if="!loading && primarySeries && primarySeries.data.length === 0" class="empty-state">
        <p>📊 当前时间范围无数据</p>
        <p>请尝试调整时间范围</p>
      </div>
    </div>
    
    <!-- 图例 -->
    <div class="legend">
      <template v-if="comparisonMode">
        <div v-for="series in historySeries" :key="series.streamId" class="legend-item">
          <span class="legend-color" :style="{ background: series.color }"></span>
          <span>{{ series.name }}</span>
        </div>
      </template>
      <template v-else>
        <div class="legend-item">
          <span class="legend-color" style="background: var(--color-success)"></span>
          <span>平均人数</span>
        </div>
        <div class="legend-item">
          <span class="legend-color legend-dashed" style="border-color: var(--color-warning)"></span>
          <span>最大人数</span>
        </div>
      </template>
    </div>
    
    <!-- 统计摘要 -->
    <div v-if="primarySummary" class="summary">
      <div class="summary-item">
        <span class="label">数据点数:</span>
        <span class="value">{{ primarySummary.points }}</span>
      </div>
      <div class="summary-item">
        <span class="label">平均人数:</span>
        <span class="value">
          {{ primarySummary.avg.toFixed(1) }}
        </span>
      </div>
      <div class="summary-item">
        <span class="label">最大人数:</span>
        <span class="value">
          {{ primarySummary.max }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-chart {
  padding: 16px;
  background: var(--color-panel);
  border-radius: 8px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group .hint {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.control-group label {
  font-size: 14px;
  color: var(--color-text-muted);
}

.control-group select,
.control-group input {
  padding: 6px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: 4px;
  font-size: 14px;
  background: var(--color-input-bg);
  color: var(--color-text);
}

.control-group select:focus,
.control-group input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.control-group button {
  padding: 6px 12px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.control-group button:hover {
  background: var(--color-primary-strong);
}

.control-group button:disabled {
  background: var(--color-border-strong);
  cursor: not-allowed;
}

.compare-group {
  align-items: flex-start;
  width: 100%;
}

.compare-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  max-width: 100%;
}

.compare-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--color-panel-alt);
  border: 1px solid var(--color-border);
}

.compare-item input {
  accent-color: var(--color-primary);
}

.compare-item span.primary {
  color: var(--color-primary);
  font-weight: 600;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text-muted);
}

.error {
  padding: 12px;
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
  border-radius: 4px;
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  min-height: 300px;
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 16px;
}

.chart-container canvas {
  width: 100%;
  height: 300px;
}

.legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 24px;
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.legend-color {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.legend-dashed {
  background: transparent;
  border-top: 2px dashed;
}

.summary {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.summary-item .label {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.summary-item .value {
  font-size: 24px;
  font-weight: bold;
  color: var(--color-text);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--color-text-subtle);
}

.empty-state p {
  margin: 8px 0 0;
}
</style>
