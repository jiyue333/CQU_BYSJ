<script setup lang="ts">
/**
 * 连接状态指示器组件
 * 显示 WebSocket 和流的连接状态
 * Requirements: 9.2, 9.4
 */

import { computed } from 'vue'
import type { StreamStatus } from '@/types'

export interface ConnectionState {
  websocket: boolean
  streamStatus?: StreamStatus
  reconnecting?: boolean
  reconnectAttempt?: number
  maxAttempts?: number
}

const props = defineProps<{
  state: ConnectionState
  compact?: boolean
}>()

// 计算整体状态
const overallStatus = computed(() => {
  if (!props.state.websocket) {
    return 'disconnected'
  }
  if (props.state.reconnecting) {
    return 'reconnecting'
  }
  if (props.state.streamStatus === 'error' || props.state.streamStatus === 'cooldown') {
    return 'warning'
  }
  if (props.state.streamStatus === 'running') {
    return 'connected'
  }
  return 'idle'
})

// 状态配置
const statusConfig = computed(() => {
  switch (overallStatus.value) {
    case 'connected':
      return {
        color: '#4caf50',
        bgColor: 'rgba(76, 175, 80, 0.15)',
        icon: '🟢',
        label: '已连接',
        pulse: false
      }
    case 'reconnecting':
      return {
        color: '#ff9800',
        bgColor: 'rgba(255, 152, 0, 0.15)',
        icon: '🟡',
        label: `重连中 (${props.state.reconnectAttempt || 0}/${props.state.maxAttempts || 5})`,
        pulse: true
      }
    case 'warning':
      return {
        color: '#ff9800',
        bgColor: 'rgba(255, 152, 0, 0.15)',
        icon: '🟠',
        label: props.state.streamStatus === 'cooldown' ? '冷却中' : '异常',
        pulse: false
      }
    case 'disconnected':
      return {
        color: '#f44336',
        bgColor: 'rgba(244, 67, 54, 0.15)',
        icon: '🔴',
        label: '未连接',
        pulse: false
      }
    default:
      return {
        color: '#9e9e9e',
        bgColor: 'rgba(158, 158, 158, 0.15)',
        icon: '⚪',
        label: '空闲',
        pulse: false
      }
  }
})
</script>

<template>
  <div 
    class="connection-indicator" 
    :class="{ compact, pulse: statusConfig.pulse }"
    :style="{ backgroundColor: statusConfig.bgColor }"
  >
    <span class="status-dot" :style="{ backgroundColor: statusConfig.color }"></span>
    <span v-if="!compact" class="status-label">{{ statusConfig.label }}</span>
  </div>
</template>

<style scoped>
.connection-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.connection-indicator.compact {
  padding: 4px 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color 0.3s ease;
}

.connection-indicator.pulse .status-dot {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.status-label {
  color: var(--color-text);
  white-space: nowrap;
}
</style>
