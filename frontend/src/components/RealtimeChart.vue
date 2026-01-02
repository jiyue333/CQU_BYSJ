<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { DetectionResult } from '@/types'
import type { ROI } from '@/api/rois'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent
])

const props = defineProps<{
  streamId: string | null
  result: DetectionResult | null
  rois: ROI[]
}>()

// Data storage for the chart
const chartData = ref<{
  time: string[]
  global: number[]
  rois: Record<string, number[]>
}>({
  time: [],
  global: [],
  rois: {}
})

// Configuration
const windowSizeMinutes = ref(1) // Default 1 minute
const selectedMetric = ref<'count' | 'density'>('count')
const selectedRoiId = ref<string>('global') // 'global' or roi_id

const updateInterval = 1000 // Update every 1 second
let updateTimer: number | null = null

// Initialize ROI data arrays
watch(() => props.rois, (newRois) => {
  newRois.forEach(roi => {
    if (!chartData.value.rois[roi.roi_id]) {
      chartData.value.rois[roi.roi_id] = []
    }
  })
}, { immediate: true })

function updateChartData() {
  if (!props.streamId) return

  const now = new Date()
  const timeLabel = now.toLocaleTimeString()

  // Add time
  chartData.value.time.push(timeLabel)

  // Add global data
  // Use 'total_count' instead of 'count' based on DetectionResult type
  const globalValue = selectedMetric.value === 'count'
    ? (props.result?.total_count || 0)
    : 0 // Global density is not available in DetectionResult, defaulting to 0

  chartData.value.global.push(globalValue)

  // Add ROI data
  props.rois.forEach(roi => {
    const stat = props.result?.region_stats?.find(s => s.region_id === roi.roi_id)
    let val = 0
    if (stat) {
      if (selectedMetric.value === 'count') {
        val = stat.count
      } else if (selectedMetric.value === 'density') {
        val = stat.density
      }
    }
    if (!chartData.value.rois[roi.roi_id]) {
      chartData.value.rois[roi.roi_id] = []
    }
    // Check if array exists (it should, but for safety)
    const roiData = chartData.value.rois[roi.roi_id]
    if (roiData) {
      roiData.push(val)
    }
  })

  // Trim data based on window size
  // Assuming 1 update per second
  const maxDataPoints = windowSizeMinutes.value * 60
  if (chartData.value.time.length > maxDataPoints) {
    chartData.value.time.shift()
    chartData.value.global.shift()
    Object.keys(chartData.value.rois).forEach(key => {
      const roiData = chartData.value.rois[key]
      if (roiData) {
        roiData.shift()
      }
    })
  }
}

// Chart Options
const chartOption = computed(() => {
  const isDark = document.documentElement.dataset.theme === 'dark'
  const textColor = isDark ? '#e5e7eb' : '#374151'
  const gridColor = isDark ? '#374151' : '#e5e7eb'

  let seriesName = '全局'
  let seriesData = chartData.value.global

  if (selectedRoiId.value !== 'global') {
    const roi = props.rois.find(r => r.roi_id === selectedRoiId.value)
    seriesName = roi ? roi.name : 'Unknown ROI'
    seriesData = chartData.value.rois[selectedRoiId.value] || []
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? 'rgba(31, 41, 55, 0.9)' : 'rgba(255, 255, 255, 0.9)',
      borderColor: gridColor,
      textStyle: { color: textColor }
    },
    grid: {
      top: 40,
      right: 20,
      bottom: 40,
      left: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: chartData.value.time,
      axisLine: { lineStyle: { color: gridColor } },
      axisLabel: { color: textColor }
    },
    yAxis: {
      type: 'value',
      name: selectedMetric.value === 'count' ? '人数' : '密度',
      axisLine: { lineStyle: { color: gridColor } },
      axisLabel: { color: textColor },
      splitLine: { lineStyle: { color: gridColor, type: 'dashed' } }
    },
    series: [
      {
        name: seriesName,
        type: 'line',
        data: seriesData,
        smooth: true,
        showSymbol: false,
        areaStyle: {
          opacity: 0.2
        },
        itemStyle: {
          color: '#3b82f6'
        }
      }
    ],
    animation: false // Performance optimization for real-time update
  }
})

// Watchers
watch(() => props.streamId, () => {
  // Reset data on stream change
  chartData.value = { time: [], global: [], rois: {} }
})

onMounted(() => {
  updateTimer = window.setInterval(updateChartData, updateInterval)
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
})

</script>

<template>
  <div class="realtime-chart">
    <div class="chart-controls">
      <div class="control-group">
        <label>时间窗口</label>
        <select v-model="windowSizeMinutes">
          <option :value="1">1 分钟</option>
          <option :value="5">5 分钟</option>
          <option :value="10">10 分钟</option>
        </select>
      </div>
      <div class="control-group">
        <label>指标</label>
        <select v-model="selectedMetric">
          <option value="count">人数</option>
          <option value="density">密度</option>
        </select>
      </div>
      <div class="control-group">
        <label>区域</label>
        <select v-model="selectedRoiId">
          <option value="global">全局</option>
          <option v-for="roi in rois" :key="roi.roi_id" :value="roi.roi_id">
            {{ roi.name }}
          </option>
        </select>
      </div>
    </div>
    <div class="chart-container">
      <VChart class="chart" :option="chartOption" autoresize />
    </div>
  </div>
</template>

<style scoped>
.realtime-chart {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-top: 12px;
}

.chart-controls {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.control-group label {
  color: var(--color-text-muted);
}

.control-group select {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 12px;
}

.chart-container {
  flex: 1;
  min-height: 200px;
  width: 100%;
}

.chart {
  height: 100%;
  width: 100%;
}
</style>
