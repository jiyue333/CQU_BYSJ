<script setup lang="ts">
/**
 * ROI 绘制组件
 * Canvas 多边形绘制、编辑与删除功能
 * Requirements: 3.1, 3.2, P0.3
 */

import { ref, watch, onMounted, onUnmounted } from 'vue'
import type { Point, ROI, ROICreate } from '@/api/rois'

export type DrawMode = 'polygon' | 'rect' | 'circle'

const props = defineProps<{
  width: number
  height: number
  rois: ROI[]
  selectedRoiId: string | null
  editMode: boolean
  drawMode?: DrawMode
}>()

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
const currentPoints = ref<Point[]>([]) // Used for Polygon
const drawStartPoint = ref<Point | null>(null) // Used for Rect/Circle
const drawEndPoint = ref<Point | null>(null) // Used for Rect/Circle

const hoveredRoiId = ref<string | null>(null)
const dragPointIndex = ref<number | null>(null)
const isDragging = ref(false)

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

// 生成矩形点
function getRectPoints(p1: Point, p2: Point): Point[] {
  return [
    { x: p1.x, y: p1.y },
    { x: p2.x, y: p1.y },
    { x: p2.x, y: p2.y },
    { x: p1.x, y: p2.y }
  ]
}

// 生成圆形点（多边形近似）
function getCirclePoints(center: Point, edge: Point, segments = 32): Point[] {
  const dx = edge.x - center.x
  const dy = edge.y - center.y
  const radius = Math.sqrt(dx * dx + dy * dy)

  const points: Point[] = []
  for (let i = 0; i < segments; i++) {
    const angle = (i / segments) * Math.PI * 2
    points.push({
      x: center.x + Math.cos(angle) * radius,
      y: center.y + Math.sin(angle) * radius
    })
  }
  return points
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

  // 绘制正在绘制的图形
  if (isDrawing.value) {
    let points: Point[] = []

    if (props.drawMode === 'rect' && drawStartPoint.value && drawEndPoint.value) {
      points = getRectPoints(drawStartPoint.value, drawEndPoint.value)
    } else if (props.drawMode === 'circle' && drawStartPoint.value && drawEndPoint.value) {
      points = getCirclePoints(drawStartPoint.value, drawEndPoint.value)
    } else if (currentPoints.value.length > 0) {
      points = currentPoints.value
    }

    if (points.length > 0) {
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
    if (props.drawMode === 'polygon' || !props.drawMode) {
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
    } else {
        // Rect/Circle logic: MouseDown starts drawing
        if (!drawStartPoint.value) {
            drawStartPoint.value = pos
            drawEndPoint.value = pos
        } else {
             // Second click finishes drawing (if we wanted click-click interaction)
             // But usually drag is better. Let's support drag for shapes.
             // Actually, if we are in drawing mode, we probably started by double click or external trigger?
             // But existing Polygon logic starts with DoubleClick.
             // Let's adapt:
             // Polygon: Click to add points.
             // Rect/Circle: Press to start, Drag to size, Release to finish.
        }
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

  // Rect/Circle 模式下直接开始绘制（按下即开始）
  if ((props.drawMode === 'rect' || props.drawMode === 'circle') && !isDrawing.value) {
      isDrawing.value = true
      drawStartPoint.value = pos
      drawEndPoint.value = pos
      emit('select', null)
      return
  }

  // 点击空白区域，取消选择
  emit('select', null)
}

// 处理鼠标移动
function handleMouseMove(e: MouseEvent) {
  const pos = getMousePos(e)

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

  // 绘制中更新
  if (isDrawing.value) {
      if (props.drawMode === 'rect' || props.drawMode === 'circle') {
          if (drawStartPoint.value) {
              drawEndPoint.value = pos
              render()
          }
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

  // Finish Rect/Circle drawing on release
  if (isDrawing.value && (props.drawMode === 'rect' || props.drawMode === 'circle')) {
      finishDrawing()
  }
}

// 处理双击（开始绘制新 ROI - Polygon 模式）
function handleDoubleClick(e: MouseEvent) {
  if (!props.editMode || isDrawing.value) return
  if (props.drawMode && props.drawMode !== 'polygon') return // Rect/Circle use drag

  const pos = getMousePos(e)

  // 检查是否双击了已有的 ROI（不开始新绘制）
  for (const roi of props.rois) {
    if (isPointInPolygon(pos, roi.points)) {
      return
    }
  }

  // 开始绘制新 ROI
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
  if (e.key === 'Enter' && isDrawing.value) {
      finishDrawing()
  }
}

// 完成绘制
function finishDrawing() {
  let points: Point[] = []

  if (props.drawMode === 'rect' && drawStartPoint.value && drawEndPoint.value) {
      points = getRectPoints(drawStartPoint.value, drawEndPoint.value)
  } else if (props.drawMode === 'circle' && drawStartPoint.value && drawEndPoint.value) {
      points = getCirclePoints(drawStartPoint.value, drawEndPoint.value)
  } else {
      points = [...currentPoints.value]
  }

  if (points.length >= 3) {
    emit('create', {
      name: `区域 ${props.rois.length + 1}`,
      points: points
    })
  }
  cancelDrawing()
}

// 取消绘制
function cancelDrawing() {
  isDrawing.value = false
  currentPoints.value = []
  drawStartPoint.value = null
  drawEndPoint.value = null
  render()
}

// 监听 props 变化重新渲染
watch(
  () => [props.rois, props.selectedRoiId, props.width, props.height, props.drawMode],
  () => {
    // If drawMode changes, cancel current drawing
    if (isDrawing.value) cancelDrawing()
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
</template>

<style scoped>
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
