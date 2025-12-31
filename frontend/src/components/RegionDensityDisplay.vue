<script setup lang="ts">
/**
 * 区域密度显示组件
 * 显示每个区域的密度值和密度等级颜色标识
 * Requirements: 3.3, 3.4, 5.2
 */

import { computed } from 'vue'
import type { RegionStat } from '@/types'
import type { ROI } from '@/api/rois'

const props = defineProps<{
  regionStats: RegionStat[]
  rois: ROI[]
  width: number
  height: number
}>()

// 密度等级颜色映射
const DENSITY_COLORS = {
  low: {
    fill: 'rgba(76, 175, 80, 0.3)',
    stroke: 'rgba(76, 175, 80, 0.8)',
    text: '#4caf50',
    label: '低'
  },
  medium: {
    fill: 'rgba(255, 152, 0, 0.3)',
    stroke: 'rgba(255, 152, 0, 0.8)',
    text: '#ff9800',
    label: '中'
  },
  high: {
    fill: 'rgba(244, 67, 54, 0.3)',
    stroke: 'rgba(244, 67, 54, 0.8)',
    text: '#f44336',
    label: '高'
  }
}

// 合并 ROI 和统计数据
interface RegionDisplay {
  roi: ROI
  stat: RegionStat | null
  center: { x: number; y: number }
}

const regionsWithStats = computed<RegionDisplay[]>(() => {
  return props.rois.map((roi) => {
    const stat = props.regionStats.find((s) => s.region_id === roi.roi_id) || null

    // 计算多边形中心
    let cx = 0
    let cy = 0
    for (const p of roi.points) {
      cx += p.x
      cy += p.y
    }
    cx /= roi.points.length
    cy /= roi.points.length

    return {
      roi,
      stat,
      center: { x: cx, y: cy }
    }
  })
})

// 获取密度等级颜色
function getDensityColor(level: string | undefined) {
  if (!level) return DENSITY_COLORS.low
  return DENSITY_COLORS[level as keyof typeof DENSITY_COLORS] || DENSITY_COLORS.low
}

// 格式化密度值
function formatDensity(density: number): string {
  return (density * 100).toFixed(1) + '%'
}

// 计算多边形路径
function getPolygonPath(points: { x: number; y: number }[]): string {
  if (points.length < 3) return ''
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z'
}
</script>

<template>
  <svg class="region-density-display" :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`">
    <!-- 绘制每个区域的密度覆盖层 -->
    <g v-for="region in regionsWithStats" :key="region.roi.roi_id" class="region-group">
      <!-- 多边形区域 -->
      <path
        :d="getPolygonPath(region.roi.points)"
        :fill="getDensityColor(region.stat?.level).fill"
        :stroke="getDensityColor(region.stat?.level).stroke"
        stroke-width="2"
        class="region-polygon"
      />

      <!-- 区域信息标签 -->
      <g v-if="region.stat" class="region-label" :transform="`translate(${region.center.x}, ${region.center.y})`">
        <!-- 背景框 -->
        <rect x="-50" y="-30" width="100" height="60" rx="6" fill="rgba(0, 0, 0, 0.8)" />

        <!-- 区域名称 -->
        <text y="-12" text-anchor="middle" fill="#fff" font-size="12" font-weight="500">
          {{ region.roi.name }}
        </text>

        <!-- 人数 -->
        <text y="6" text-anchor="middle" fill="#fff" font-size="16" font-weight="bold">
          {{ region.stat.count }} 人
        </text>

        <!-- 密度等级 -->
        <text y="24" text-anchor="middle" :fill="getDensityColor(region.stat.level).text" font-size="12" font-weight="500">
          密度: {{ formatDensity(region.stat.density) }}
          <tspan :fill="getDensityColor(region.stat.level).text" font-weight="bold">
            ({{ getDensityColor(region.stat.level).label }})
          </tspan>
        </text>
      </g>

      <!-- 无统计数据时显示区域名称 -->
      <g v-else class="region-label" :transform="`translate(${region.center.x}, ${region.center.y})`">
        <rect x="-40" y="-12" width="80" height="24" rx="4" fill="rgba(0, 0, 0, 0.7)" />
        <text y="4" text-anchor="middle" fill="#888" font-size="12">
          {{ region.roi.name }}
        </text>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.region-density-display {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.region-polygon {
  transition:
    fill 0.3s ease,
    stroke 0.3s ease;
}

.region-label {
  transition: opacity 0.3s ease;
}

.region-group:hover .region-polygon {
  filter: brightness(1.2);
}
</style>
