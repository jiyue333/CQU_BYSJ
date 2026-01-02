<script setup lang="ts">
/**
 * ROI 绘制组件
 * Canvas 多边形绘制、编辑与删除功能
 * Requirements: 3.1, 3.2
 */

import { ref, watch, onMounted, onUnmounted } from 'vue'
import type { Point, ROI, ROICreate } from '@/api/rois'

const props = defineProps<{
  width: number
  height: number
  rois: ROI[]
  selectedRoiId: string | null
  editMode: boolean
}>()

// 形状工具类型
type ShapeTool = 'polygon' | 'rectangle' | 'circle'
const activeTool = ref<ShapeTool>('polygon')

const emit = defineEmits<{
  (e: 'create', roi: ROICreate): void
  (e: 'update', roiId: string, points: Point[]): void
  (e: 'select', roiId: string | null): void
  (e: 'delete', roiId: string): void
}>()

// Canvas 引用
const canvasRef = ref<HTMLCanvasElement | null>(null)

// 绘制状态
const isDrawing = ref(false)
const currentPoints = ref<Point[]>([])
const hoveredRoiId = ref<string | null>(null)
const dragPointIndex = ref<number | null>(null)
const isDragging = ref(false)

// 矩形和圆形绘制的临时点
const startPoint = ref<Point | null>(null)
const endPoint = ref<Point | null>(null)

// 颜色配置
const COLORS = {
  default: 'rgba(74, 158, 255, 0.3)',
  defaultStroke: 'rgba(74, 158, 255, 0.8)',
  selected: 'rgba(255, 193, 7, 0.4)',
  selectedStroke: 'rgba(255, 193, 7, 1)',
  hovered: 'rgba(76, 175, 80, 0.3)',
  hoveredStroke: 'rgba(76, 175, 80, 0.8)',
  drawing: 'rgba(244, 67, 54, 0.3)',
  drawingStroke: 'rgba(244, 67, 54, 0.8)',
  point: '#fff',
  pointStroke: '#333'
}

// 点的半径
const POINT_RADIUS = 6
const POINT_HIT_RADIUS = 12

// 获取 Canvas 上下文
function getContext(): CanvasRenderingContext2D | null {
  return canvasRef.value?.getContext('2d') || null
}

// 获取鼠标在 Canvas 上的坐标
function getMousePos(e: MouseEvent): Point {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }

  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height

  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY
  }
}

// 判断点是否在多边形内（射线法）
function isPointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false
  const n = polygon.length

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const pi = polygon[i]
    const pj = polygon[j]
    if (!pi || !pj) continue

    const xi = pi.x
    const yi = pi.y
    const xj = pj.x
    const yj = pj.y

    if (yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi) {
      inside = !inside
    }
  }

  return inside
}

function getCirclePoints(center: Point, radius: Point): Point[] {
  const r = Math.sqrt(Math.pow(radius.x - center.x, 2) + Math.pow(radius.y - center.y, 2))
  const points: Point[] = []
  const segments = 32
  for (let i = 0; i < segments; i++) {
    const theta = (i / segments) * Math.PI * 2
    points.push({
      x: center.x + r * Math.cos(theta),
      y: center.y + r * Math.sin(theta)
    })
  }
  return points
}

function getRectanglePoints(start: Point, end: Point): Point[] {
  return [
    { x: start.x, y: start.y },
    { x: end.x, y: start.y },
    { x: end.x, y: end.y },
    { x: start.x, y: end.y }
  ]
}

// 判断点是否靠近某个顶点
function findNearPoint(pos: Point, points: Point[]): number | null {
  for (let i = 0; i < points.length; i++) {
    const p = points[i]
    if (!p) continue
    const dx = pos.x - p.x
    const dy = pos.y - p.y
    if (Math.sqrt(dx * dx + dy * dy) <= POINT_HIT_RADIUS) {
      return i
    }
  }
  return null
}

// 绘制多边形
function drawPolygon(
  ctx: CanvasRenderingContext2D,
  points: Point[],
  fillColor: string,
  strokeColor: string,
  showPoints: boolean = false
) {
  if (points.length < 2) return

  ctx.beginPath()
  const firstPoint = points[0]
  if (firstPoint) {
    ctx.moveTo(firstPoint.x, firstPoint.y)
  }

  for (let i = 1; i < points.length; i++) {
    const p = points[i]
    if (p) {
      ctx.lineTo(p.x, p.y)
    }
  }

  if (points.length >= 3) {
    ctx.closePath()
    ctx.fillStyle = fillColor
    ctx.fill()
  }

  ctx.strokeStyle = strokeColor
  ctx.lineWidth = 2
  ctx.stroke()

  // 绘制顶点
  if (showPoints) {
    for (const p of points) {
      ctx.beginPath()
      ctx.arc(p.x, p.y, POINT_RADIUS, 0, Math.PI * 2)
      ctx.fillStyle = COLORS.point
      ctx.fill()
      ctx.strokeStyle = COLORS.pointStroke
      ctx.lineWidth = 2
      ctx.stroke()
    }
  }
}

// 绘制 ROI 名称标签
function drawLabel(ctx: CanvasRenderingContext2D, roi: ROI) {
  if (roi.points.length < 3) return

  // 计算多边形中心
  let cx = 0
  let cy = 0
  for (const p of roi.points) {
    cx += p.x
    cy += p.y
  }
  cx /= roi.points.length
  cy /= roi.points.length

  // 绘制标签背景
  ctx.font = '14px sans-serif'
  const textWidth = ctx.measureText(roi.name).width
  const padding = 6
  const bgWidth = textWidth + padding * 2
  const bgHeight = 20

  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
  ctx.fillRect(cx - bgWidth / 2, cy - bgHeight / 2, bgWidth, bgHeight)

  // 绘制文字
  ctx.fillStyle = '#fff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(roi.name, cx, cy)
}

// 渲染所有内容
function render() {
  const ctx = getContext()
  if (!ctx) return

  // 清空画布
  ctx.clearRect(0, 0, props.width, props.height)

  // 绘制已有的 ROI
  for (const roi of props.rois) {
    const isSelected = roi.roi_id === props.selectedRoiId
    const isHovered = roi.roi_id === hoveredRoiId.value

    let fillColor = COLORS.default
    let strokeColor = COLORS.defaultStroke

    if (isSelected) {
      fillColor = COLORS.selected
      strokeColor = COLORS.selectedStroke
    } else if (isHovered) {
      fillColor = COLORS.hovered
      strokeColor = COLORS.hoveredStroke
    }

    drawPolygon(ctx, roi.points, fillColor, strokeColor, isSelected && props.editMode)
    drawLabel(ctx, roi)
  }

  // 绘制正在绘制的多边形
  if (isDrawing.value) {
    if (activeTool.value === 'polygon' && currentPoints.value.length > 0) {
      drawPolygon(ctx, currentPoints.value, COLORS.drawing, COLORS.drawingStroke, true)
    } else if ((activeTool.value === 'rectangle' || activeTool.value === 'circle') && startPoint.value && endPoint.value) {
      let points: Point[] = []
      if (activeTool.value === 'rectangle') {
        points = getRectanglePoints(startPoint.value, endPoint.value)
      } else if (activeTool.value === 'circle') {
        points = getCirclePoints(startPoint.value, endPoint.value)
      }
      drawPolygon(ctx, points, COLORS.drawing, COLORS.drawingStroke, true)
    }
  }
}

// 处理鼠标按下
function handleMouseDown(e: MouseEvent) {
  if (!props.editMode) return

  const pos = getMousePos(e)

  // 如果正在绘制新的 ROI
  if (isDrawing.value) {
    if (activeTool.value === 'polygon') {
      // 检查是否点击了第一个点（闭合多边形）
      if (currentPoints.value.length >= 3) {
        const firstPoint = currentPoints.value[0]
        if (firstPoint) {
          const dx = pos.x - firstPoint.x
          const dy = pos.y - firstPoint.y
          if (Math.sqrt(dx * dx + dy * dy) <= POINT_HIT_RADIUS) {
            // 完成绘制
            finishDrawing()
            return
          }
        }
      }
      // 添加新点
      currentPoints.value.push(pos)
      render()
    } else if (activeTool.value === 'rectangle' || activeTool.value === 'circle') {
      if (!startPoint.value) {
        startPoint.value = pos
        endPoint.value = pos
      } else {
        endPoint.value = pos
        finishDrawing()
      }
      render()
    }
    return
  }

  // 检查是否点击了选中 ROI 的顶点（开始拖拽）
  if (props.selectedRoiId) {
    const selectedRoi = props.rois.find((r) => r.roi_id === props.selectedRoiId)
    if (selectedRoi) {
      const pointIndex = findNearPoint(pos, selectedRoi.points)
      if (pointIndex !== null) {
        dragPointIndex.value = pointIndex
        isDragging.value = true
        return
      }
    }
  }

  // 检查是否点击了某个 ROI
  for (const roi of props.rois) {
    if (isPointInPolygon(pos, roi.points)) {
      emit('select', roi.roi_id)
      return
    }
  }

  // 点击空白区域，取消选择
  emit('select', null)
}

// 处理鼠标移动
function handleMouseMove(e: MouseEvent) {
  const pos = getMousePos(e)

  if (isDrawing.value) {
    if (activeTool.value === 'rectangle' || activeTool.value === 'circle') {
      if (startPoint.value) {
        endPoint.value = pos
        render()
      }
    }
    return
  }

  // 拖拽顶点
  if (isDragging.value && dragPointIndex.value !== null && props.selectedRoiId) {
    const selectedRoi = props.rois.find((r) => r.roi_id === props.selectedRoiId)
    if (selectedRoi) {
      // 更新顶点位置（创建新数组以触发响应式更新）
      const newPoints = [...selectedRoi.points]
      newPoints[dragPointIndex.value] = pos
      emit('update', props.selectedRoiId, newPoints)
    }
    return
  }

  // 更新悬停状态
  if (!isDrawing.value && !isDragging.value) {
    let found = false
    for (const roi of props.rois) {
      if (isPointInPolygon(pos, roi.points)) {
        hoveredRoiId.value = roi.roi_id
        found = true
        break
      }
    }
    if (!found) {
      hoveredRoiId.value = null
    }
    render()
  }
}

// 处理鼠标释放
function handleMouseUp() {
  if (isDragging.value) {
    isDragging.value = false
    dragPointIndex.value = null
  }
}

// 处理双击（开始绘制新 ROI）
function handleDoubleClick(e: MouseEvent) {
  if (!props.editMode || isDrawing.value) return

  const pos = getMousePos(e)

  // 检查是否双击了已有的 ROI（不开始新绘制）
  for (const roi of props.rois) {
    if (isPointInPolygon(pos, roi.points)) {
      return
    }
  }

  // 开始绘制新 ROI
  if (activeTool.value !== 'polygon') {
    // 对于矩形和圆形，双击不应触发绘制（因为单击已开始绘制）
    return
  }

  isDrawing.value = true
  currentPoints.value = [pos]
  emit('select', null)
  render()
}

// 处理键盘事件
function handleKeyDown(e: KeyboardEvent) {
  if (!props.editMode) return

  // ESC 取消绘制
  if (e.key === 'Escape' && isDrawing.value) {
    cancelDrawing()
  }

  // Delete 删除选中的 ROI
  if ((e.key === 'Delete' || e.key === 'Backspace') && props.selectedRoiId && !isDrawing.value) {
    emit('delete', props.selectedRoiId)
  }

  // Enter 完成绘制
  if (e.key === 'Enter' && isDrawing.value && currentPoints.value.length >= 3) {
    finishDrawing()
  }
}

// 完成绘制
function finishDrawing() {
  let points: Point[] = []
  if (activeTool.value === 'polygon') {
    points = [...currentPoints.value]
  } else if (activeTool.value === 'rectangle' && startPoint.value && endPoint.value) {
    points = getRectanglePoints(startPoint.value, endPoint.value)
  } else if (activeTool.value === 'circle' && startPoint.value && endPoint.value) {
    points = getCirclePoints(startPoint.value, endPoint.value)
  }

  if (points.length >= 3) {
    emit('create', {
      name: `区域 ${props.rois.length + 1}`,
      points
    })
  }
  cancelDrawing()
}

// 取消绘制
function cancelDrawing() {
  isDrawing.value = false
  currentPoints.value = []
  startPoint.value = null
  endPoint.value = null
  render()
}

// 监听 props 变化重新渲染
watch(
  () => [props.rois, props.selectedRoiId, props.width, props.height],
  () => {
    render()
  },
  { deep: true }
)

// 组件挂载
onMounted(() => {
  render()
  window.addEventListener('keydown', handleKeyDown)
})

// 组件卸载
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

// 暴露方法
defineExpose({
  startDrawing: () => {
    if (props.editMode && !isDrawing.value) {
      isDrawing.value = true
      currentPoints.value = []
      emit('select', null)
    }
  },
  cancelDrawing,
  finishDrawing
})
</script>

<template>
  <div class="drawer-container">
    <div v-if="editMode" class="tools-panel">
      <button
        class="tool-btn"
        :class="{ active: activeTool === 'polygon' }"
        title="多边形 (双击开始)"
        @click="activeTool = 'polygon'"
      >
        📐
      </button>
      <button
        class="tool-btn"
        :class="{ active: activeTool === 'rectangle' }"
        title="矩形 (点击拖拽)"
        @click="activeTool = 'rectangle'; isDrawing = true; currentPoints = []"
      >
        ⬜
      </button>
      <button
        class="tool-btn"
        :class="{ active: activeTool === 'circle' }"
        title="圆形 (点击中心拖拽半径)"
        @click="activeTool = 'circle'; isDrawing = true; currentPoints = []"
      >
        ⭕
      </button>
    </div>
    <canvas
      ref="canvasRef"
      class="roi-drawer"
      :width="width"
      :height="height"
      :class="{ 'edit-mode': editMode, drawing: isDrawing }"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @dblclick="handleDoubleClick"
    ></canvas>
  </div>
</template>

<style scoped>
.drawer-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.tools-panel {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  padding: 8px;
  border-radius: 8px;
  display: flex;
  gap: 8px;
  pointer-events: auto;
  z-index: 100;
}

.tool-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tool-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.roi-drawer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.roi-drawer.edit-mode {
  pointer-events: auto;
  cursor: crosshair;
}

.roi-drawer.drawing {
  cursor: crosshair;
}
</style>
