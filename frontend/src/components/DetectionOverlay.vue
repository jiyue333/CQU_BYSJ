<script setup lang="ts">
/**
 * 检测框叠加层
 */

import { computed } from 'vue'
import type { Detection } from '@/types'

const props = defineProps<{
  detections: Detection[]
  frameWidth: number
  frameHeight: number
  width: number
  height: number
}>()

const scaleX = computed(() => (props.frameWidth ? props.width / props.frameWidth : 1))
const scaleY = computed(() => (props.frameHeight ? props.height / props.frameHeight : 1))
</script>

<template>
  <svg class="detection-overlay" :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`">
    <g v-for="(det, idx) in detections" :key="idx">
      <rect
        :x="det.x * scaleX"
        :y="det.y * scaleY"
        :width="det.width * scaleX"
        :height="det.height * scaleY"
        class="det-box"
      />
      <text
        :x="(det.x + det.width) * scaleX"
        :y="det.y * scaleY - 4"
        class="det-label"
        text-anchor="end"
      >
        {{ (det.confidence * 100).toFixed(0) }}%
      </text>
    </g>
  </svg>
</template>

<style scoped>
.detection-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.det-box {
  fill: transparent;
  stroke: rgba(255, 255, 255, 0.7);
  stroke-width: 1.5;
}

.det-label {
  fill: #ffeb3b;
  font-size: 10px;
  font-weight: 600;
}
</style>
