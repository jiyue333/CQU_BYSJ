<script setup lang="ts">
/**
 * 错误通知组件
 * 显示 toast 风格的错误提示
 * Requirements: 9.2
 */

import { ref, watch } from 'vue'

export interface Notification {
  id: number
  type: 'error' | 'warning' | 'success' | 'info'
  message: string
  duration?: number
}

const props = defineProps<{
  notifications: Notification[]
}>()

const emit = defineEmits<{
  dismiss: [id: number]
}>()

// 自动关闭定时器
const timers = ref<Map<number, ReturnType<typeof setTimeout>>>(new Map())

// 监听新通知，设置自动关闭
watch(
  () => props.notifications,
  (newNotifications) => {
    for (const notification of newNotifications) {
      if (!timers.value.has(notification.id) && notification.duration !== 0) {
        const duration = notification.duration || 5000
        const timer = setTimeout(() => {
          emit('dismiss', notification.id)
          timers.value.delete(notification.id)
        }, duration)
        timers.value.set(notification.id, timer)
      }
    }
  },
  { deep: true, immediate: true }
)

// 手动关闭
function dismiss(id: number) {
  const timer = timers.value.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.value.delete(id)
  }
  emit('dismiss', id)
}

// 获取图标
function getIcon(type: Notification['type']): string {
  switch (type) {
    case 'error': return '❌'
    case 'warning': return '⚠️'
    case 'success': return '✅'
    case 'info': return 'ℹ️'
    default: return 'ℹ️'
  }
}
</script>

<template>
  <div class="notification-container">
    <TransitionGroup name="notification">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="notification"
        :class="notification.type"
      >
        <span class="notification-icon">{{ getIcon(notification.type) }}</span>
        <span class="notification-message">{{ notification.message }}</span>
        <button class="notification-close" @click="dismiss(notification.id)">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.notification-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 400px;
}

.notification {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  background: #2a2a2a;
  border: 1px solid #333;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: #fff;
  font-size: 14px;
}

.notification.error {
  background: rgba(244, 67, 54, 0.15);
  border-color: #f44336;
}

.notification.warning {
  background: rgba(255, 152, 0, 0.15);
  border-color: #ff9800;
}

.notification.success {
  background: rgba(76, 175, 80, 0.15);
  border-color: #4caf50;
}

.notification.info {
  background: rgba(33, 150, 243, 0.15);
  border-color: #2196f3;
}

.notification-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.notification-message {
  flex: 1;
  word-break: break-word;
}

.notification-close {
  background: none;
  border: none;
  color: #888;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  transition: color 0.2s;
}

.notification-close:hover {
  color: #fff;
}

/* 动画 */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
