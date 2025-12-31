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
  type AggregatedStat,
  type AggregatedHistoryResponse
} from '../api/history'

// Props
const props = defineProps<{
  streamId: string
}>()

// 状态
const loading = ref(false)
const error = ref<string | null>(null)
const historyData = ref<AggregatedHistoryResponse | null>(null)

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
    historyData.value = await getAggregatedHistory(props.streamId, {
      granularity: granularity.value,
      ...timeRangeParams.value
    })
    
    // 绘制图表
    drawChart()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load history data'
  } finally {
    loading.value = false
  }
}

// 绘制图表
function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas || !historyData.value) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const data = historyData.value.data
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
  const maxCount = Math.max(...data.map(d => d.max_count), 1)
  const minCount = Math.min(...data.map(d => d.min_count), 0)
  const range = maxCount - minCount || 1
  
  // 绘制坐标轴
  ctx.strokeStyle = '#e0e0e0'
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
  ctx.fillStyle = '#666'
  ctx.font = '12px sans-serif'
  ctx.textAlign = 'right'
  
  const yTicks = 5
  for (let i = 0; i <= yTicks; i++) {
    const value = minCount + (range * i) / yTicks
    const y = height - padding.bottom - (chartHeight * i) / yTicks
    
    ctx.fillText(Math.round(value).toString(), padding.left - 5, y + 4)
    
    // 网格线
    ctx.strokeStyle = '#f0f0f0'
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(width - padding.right, y)
    ctx.stroke()
  }
  
  // 绘制数据
  if (chartType.value === 'line') {
    drawLineChart(ctx, data, padding, chartWidth, chartHeight, minCount, range)
  } else {
    drawBarChart(ctx, data, padding, chartWidth, chartHeight, minCount, range)
  }
  
  // 绘制 X 轴标签
  ctx.fillStyle = '#666'
  ctx.textAlign = 'center'
  
  const xLabelCount = Math.min(data.length, 6)
  const step = Math.floor(data.length / xLabelCount)
  
  for (let i = 0; i < data.length; i += step) {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const date = new Date(data[i].timestamp)
    const label = formatTimeLabel(date)
    
    ctx.fillText(label, x, height - padding.bottom + 20)
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
  range: number
) {
  const canvas = chartCanvas.value!
  const height = canvas.height
  
  // 绘制平均值线
  ctx.strokeStyle = '#4CAF50'
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
  ctx.strokeStyle = '#FF5722'
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
  ctx.fillStyle = '#4CAF50'
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1)
    const y = height - padding.bottom - (chartHeight * (d.avg_count - minCount)) / range
    
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, Math.PI * 2)
    ctx.fill()
  })
}

// 绘制柱状图
function drawBarChart(
  ctx: CanvasRenderingContext2D,
  data: AggregatedStat[],
  padding: { top: number; right: number; bottom: number; left: number },
  chartWidth: number,
  chartHeight: number,
  minCount: number,
  range: number
) {
  const canvas = chartCanvas.value!
  const height = canvas.height
  
  const barWidth = Math.max(chartWidth / data.length - 4, 2)
  
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth * i) / (data.length - 1 || 1) - barWidth / 2
    const barHeight = (chartHeight * (d.avg_count - minCount)) / range
    const y = height - padding.bottom - barHeight
    
    // 绘制柱子
    ctx.fillStyle = '#2196F3'
    ctx.fillRect(x, y, barWidth, barHeight)
    
    // 绘制边框
    ctx.strokeStyle = '#1976D2'
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

// 监听参数变化
watch([() => props.streamId, granularity, timeRange, customStartTime, customEndTime], () => {
  loadData()
})

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

onMounted(() => {
  if (chartCanvas.value) {
    chartCanvas.value.width = chartCanvas.value.parentElement?.clientWidth || 600
    chartCanvas.value.height = 300
  }
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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
          type="datetime-local"
          v-model="customStartTime"
          placeholder="开始时间"
        />
        <span>至</span>
        <input
          type="datetime-local"
          v-model="customEndTime"
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
        <select v-model="chartType">
          <option value="line">折线图</option>
          <option value="bar">柱状图</option>
        </select>
      </div>
      
      <!-- 导出按钮 -->
      <div class="control-group">
        <button @click="handleExport('csv')" :disabled="loading">导出 CSV</button>
        <button @click="handleExport('excel')" :disabled="loading">导出 Excel</button>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading">加载中...</div>
    
    <!-- 错误提示 -->
    <div v-if="error" class="error">{{ error }}</div>
    
    <!-- 图表 -->
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
    </div>
    
    <!-- 图例 -->
    <div class="legend">
      <div class="legend-item">
        <span class="legend-color" style="background: #4CAF50"></span>
        <span>平均人数</span>
      </div>
      <div class="legend-item">
        <span class="legend-color legend-dashed" style="border-color: #FF5722"></span>
        <span>最大人数</span>
      </div>
    </div>
    
    <!-- 统计摘要 -->
    <div v-if="historyData && historyData.data.length > 0" class="summary">
      <div class="summary-item">
        <span class="label">数据点数:</span>
        <span class="value">{{ historyData.data.length }}</span>
      </div>
      <div class="summary-item">
        <span class="label">平均人数:</span>
        <span class="value">
          {{ (historyData.data.reduce((sum, d) => sum + d.avg_count, 0) / historyData.data.length).toFixed(1) }}
        </span>
      </div>
      <div class="summary-item">
        <span class="label">最大人数:</span>
        <span class="value">
          {{ Math.max(...historyData.data.map(d => d.max_count)) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-chart {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 14px;
  color: #666;
}

.control-group select,
.control-group input {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.control-group button {
  padding: 6px 12px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.control-group button:hover {
  background: #1976D2;
}

.control-group button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error {
  padding: 12px;
  background: #ffebee;
  color: #c62828;
  border-radius: 4px;
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  min-height: 300px;
}

.chart-container canvas {
  width: 100%;
  height: 300px;
}

.legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
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
  border-top: 1px solid #eee;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.summary-item .label {
  font-size: 12px;
  color: #999;
}

.summary-item .value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}
</style>
