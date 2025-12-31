<script setup lang="ts">
/**
 * 热力图叠加组件
 * Canvas 叠加层 + EMA 平滑过渡
 * Requirements: 4.2, 4.3, 4.4, 4.5
 */

import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  heatmapGrid: number[][] | null
  visible: boolean
  width: number
  height: number
}>()

// EMA 平滑参数
const EMA_ALPHA = 0.3

// Canvas 引用
const canvasRef = ref<HTMLCanvasElement | null>(null)

// EMA 平滑后的热力图数据
const smoothedGrid = ref<number[][] | null>(null)

// 颜色映射：值 (0-1) → 颜色
function valueToColor(value: number): string {
  // 使用 HSL 颜色空间：蓝色(240°) → 红色(0°)
  // value 0 → 蓝色（冷）
  // value 1 → 红色（热）
  const hue = (1 - value) * 240
  const saturation = 80
  const lightness = 50
  const alpha = Math.min(value * 0.8 + 0.1, 0.8) // 透明度随值变化

  return `hsla(${hue}, ${saturation}%, ${lightness}%, ${alpha})`
}

// Clamp value to [0, 1] range
function clamp(value: number): number {
  return Math.max(0, Math.min(1, value))
}

// EMA 平滑算法
function applyEMA(newGrid: number[][]): number[][] {
  const newRows = newGrid.length
  const newCols = newGrid[0]?.length ?? 0
  
  // Reset if dimensions changed (both rows and cols)
  if (!smoothedGrid.value || 
      smoothedGrid.value.length !== newRows ||
      (smoothedGrid.value[0]?.length ?? 0) !== newCols) {
    // 首帧或尺寸变化，直接使用原始值（clamped）
    return newGrid.map((row) => row.map(clamp))
  }

  // EMA: smoothed = alpha * new + (1 - alpha) * old
  return newGrid.map((row, i) =>
    row.map((val, j) => {
      const clampedVal = clamp(val)
      const oldVal = smoothedGrid.value![i]?.[j] ?? 0
      return clamp(EMA_ALPHA * clampedVal + (1 - EMA_ALPHA) * oldVal)
    })
  )
}

// 渲染热力图
function render() {
  const canvas = canvasRef.value
  if (!canvas || !smoothedGrid.value || !props.visible) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const grid = smoothedGrid.value
  const rows = grid.length
  const firstRow = grid[0]
  const cols = firstRow ? firstRow.length : 0

  if (rows === 0 || cols === 0) return

  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 计算每个格子的大小
  const cellWidth = canvas.width / cols
  const cellHeight = canvas.height / rows

  // 绘制热力图
  for (let i = 0; i < rows; i++) {
    const row = grid[i]
    if (!row) continue
    for (let j = 0; j < cols; j++) {
      const value = row[j]
      if (value !== undefined && value > 0.01) {
        // 忽略极小值
        ctx.fillStyle = valueToColor(value)
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight)
      }
    }
  }

  // 添加高斯模糊效果使热力图更平滑
  // 注意：这会影响性能，可以根据需要调整
  ctx.filter = 'blur(8px)'
  ctx.drawImage(canvas, 0, 0)
  ctx.filter = 'none'
}

// 监听热力图数据变化
watch(
  () => props.heatmapGrid,
  (newGrid) => {
    if (newGrid && newGrid.length > 0) {
      smoothedGrid.value = applyEMA(newGrid)
      render()
    }
  },
  { deep: true }
)

// 监听可见性变化
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      render()
    } else {
      // 隐藏时清空画布
      const canvas = canvasRef.value
      if (canvas) {
        const ctx = canvas.getContext('2d')
        ctx?.clearRect(0, 0, canvas.width, canvas.height)
      }
    }
  }
)

// 监听尺寸变化
watch(
  () => [props.width, props.height],
  () => {
    render()
  }
)

// 组件挂载
onMounted(() => {
  if (props.heatmapGrid && props.visible) {
    smoothedGrid.value = props.heatmapGrid.map((row) => [...row])
    render()
  }
})

// 重置 EMA 状态
function reset() {
  smoothedGrid.value = null
  const canvas = canvasRef.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    ctx?.clearRect(0, 0, canvas.width, canvas.height)
  }
}

defineExpose({
  reset
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="heatmap-overlay"
    :width="width"
    :height="height"
    :style="{ display: visible ? 'block' : 'none' }"
  ></canvas>
</template>

<style scoped>
.heatmap-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
