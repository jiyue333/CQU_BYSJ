<script setup lang="ts">
/**
 * 告警面板
 */

import { computed, ref, watch } from 'vue'
import type { AlertEvent, AlertRule, DensityLevel } from '@/types'
import type { ROI } from '@/api/rois'
import { acknowledgeAlert, createAlertRule, deleteAlertRule, listAlertEvents, listAlertRules, updateAlertRule } from '@/api/alerts'

const props = defineProps<{
  streamId: string | null
  liveEvents: AlertEvent[]
  rois?: ROI[]
}>()

const loading = ref(false)
const error = ref('')
const historyEvents = ref<AlertEvent[]>([])
const rules = ref<AlertRule[]>([])
const ruleForm = ref({
  roi_id: '',
  threshold_type: 'density' as 'density' | 'count',
  threshold_value: 0.7,
  level: 'high' as DensityLevel,
  min_duration_sec: 3,
  cooldown_sec: 60,
  enabled: true
})

const mergedEvents = computed(() => {
  const map = new Map<string, AlertEvent>()
  for (const event of historyEvents.value) {
    map.set(event.id, event)
  }
  for (const event of props.liveEvents) {
    map.set(event.id, event)
  }
  return Array.from(map.values()).sort((a, b) => b.start_ts - a.start_ts)
})

async function loadEvents() {
  if (!props.streamId) {
    historyEvents.value = []
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await listAlertEvents({ stream_id: props.streamId, limit: 100 })
    historyEvents.value = response.events
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载告警失败'
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  if (!props.streamId) {
    rules.value = []
    return
  }
  try {
    const response = await listAlertRules(props.streamId)
    rules.value = response.rules
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载规则失败'
  }
}

async function createRule() {
  if (!props.streamId) return
  error.value = ''
  try {
    const created = await createAlertRule({
      stream_id: props.streamId,
      roi_id: ruleForm.value.roi_id || null,
      threshold_type: ruleForm.value.threshold_type,
      threshold_value: ruleForm.value.threshold_value,
      level: ruleForm.value.level,
      min_duration_sec: ruleForm.value.min_duration_sec,
      cooldown_sec: ruleForm.value.cooldown_sec,
      enabled: ruleForm.value.enabled
    })
    rules.value = [created, ...rules.value]
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建规则失败'
  }
}

async function toggleRule(rule: AlertRule) {
  try {
    const updated = await updateAlertRule(rule.id, { enabled: !rule.enabled })
    rules.value = rules.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新规则失败'
  }
}

async function removeRule(rule: AlertRule) {
  try {
    await deleteAlertRule(rule.id)
    rules.value = rules.value.filter((item) => item.id !== rule.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除规则失败'
  }
}

async function handleAck(event: AlertEvent) {
  try {
    const updated = await acknowledgeAlert(event.id)
    historyEvents.value = historyEvents.value.map((item) =>
      item.id === updated.id ? updated : item
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '确认失败'
  }
}

function formatTs(ts: number | undefined | null): string {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString()
}

watch(
  () => props.streamId,
  () => {
    loadEvents()
    loadRules()
  },
  { immediate: true }
)
</script>

<template>
  <div class="alerts-panel">
    <div class="panel-header">
      <h3>🚨 告警历史</h3>
    </div>

    <div v-if="!streamId" class="empty-state">
      <span class="empty-icon">🚨</span>
      <p>请先选择视频流</p>
    </div>

    <div v-else-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-if="streamId" class="rules-panel">
      <div class="rules-header">
        <span>规则配置</span>
      </div>
      <div class="rule-form">
        <select v-model="ruleForm.roi_id" class="rule-input">
          <option value="">全局规则</option>
          <option v-for="roi in rois || []" :key="roi.roi_id" :value="roi.roi_id">
            {{ roi.name }}
          </option>
        </select>
        <div class="rule-row">
          <select v-model="ruleForm.threshold_type" class="rule-input">
            <option value="density">密度</option>
            <option value="count">人数</option>
          </select>
          <input v-model.number="ruleForm.threshold_value" type="number" min="0" step="0.1" class="rule-input" />
          <select v-model="ruleForm.level" class="rule-input">
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="low">低</option>
          </select>
        </div>
        <div class="rule-row">
          <input v-model.number="ruleForm.min_duration_sec" type="number" min="0" class="rule-input" placeholder="持续(秒)" />
          <input v-model.number="ruleForm.cooldown_sec" type="number" min="0" class="rule-input" placeholder="冷却(秒)" />
          <button class="rule-btn" @click="createRule">新增规则</button>
        </div>
      </div>
      <div v-if="rules.length === 0" class="empty-state small">
        <p>暂无规则</p>
      </div>
      <ul v-else class="rule-list">
        <li v-for="rule in rules" :key="rule.id" class="rule-item">
          <div class="rule-info">
            <span class="rule-badge">{{ rule.threshold_type }}</span>
            <span class="rule-value">{{ rule.threshold_value ?? '--' }}</span>
            <span class="rule-level">{{ rule.level }}</span>
            <span class="rule-roi">{{ rule.roi_id ? 'ROI' : '全局' }}</span>
          </div>
          <div class="rule-actions">
            <button class="rule-toggle" @click="toggleRule(rule)">
              {{ rule.enabled ? '禁用' : '启用' }}
            </button>
            <button class="rule-delete" @click="removeRule(rule)">删除</button>
          </div>
        </li>
      </ul>
    </div>

    <div v-else-if="mergedEvents.length === 0" class="empty-state small">
      <p>暂无告警记录</p>
    </div>

    <ul v-else class="alert-list">
      <li v-for="event in mergedEvents" :key="event.id" class="alert-item">
        <div class="alert-main">
          <span class="alert-level" :class="event.level">{{ event.level.toUpperCase() }}</span>
          <div class="alert-info">
            <div class="alert-message">{{ event.message || '高密度预警' }}</div>
            <div class="alert-meta">
              <span>开始: {{ formatTs(event.start_ts) }}</span>
              <span>结束: {{ formatTs(event.end_ts) }}</span>
              <span>峰值密度: {{ event.peak_density }}</span>
              <span>峰值人数: {{ event.count_peak }}</span>
            </div>
          </div>
        </div>
        <div class="alert-actions">
          <span class="alert-status" :class="{ active: !event.end_ts }">
            {{ event.end_ts ? '已结束' : '进行中' }}
          </span>
          <button
            v-if="!event.acknowledged"
            class="ack-btn"
            @click="handleAck(event)"
          >
            确认
          </button>
          <span v-else class="ack-label">已确认</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.alerts-panel {
  background: var(--color-panel);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text);
}

.loading,
.error {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

.alert-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rules-panel {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 10px;
  border: 1px solid var(--color-border);
}

.rules-header {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rule-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.rule-row {
  display: flex;
  gap: 8px;
}

.rule-input {
  flex: 1;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 12px;
}

.rule-btn {
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.rule-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  border-radius: 6px;
  background: var(--color-panel);
  border: 1px solid var(--color-border);
}

.rule-info {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.rule-badge {
  color: var(--color-primary);
}

.rule-actions {
  display: flex;
  gap: 6px;
}

.rule-toggle,
.rule-delete {
  padding: 4px 8px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
}

.rule-toggle {
  background: var(--color-border);
  color: var(--color-text);
}

.rule-delete {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.alert-item {
  background: var(--color-panel-alt);
  border-radius: 8px;
  border: 1px solid var(--color-border);
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.alert-main {
  display: flex;
  gap: 10px;
  flex: 1;
}

.alert-level {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  align-self: flex-start;
}

.alert-level.low {
  background: rgba(76, 175, 80, 0.2);
  color: var(--color-success);
}

.alert-level.medium {
  background: rgba(255, 152, 0, 0.2);
  color: var(--color-warning);
}

.alert-level.high {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.alert-message {
  color: var(--color-text);
  font-size: 13px;
  margin-bottom: 4px;
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.alert-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.alert-status {
  font-size: 11px;
  color: var(--color-text-muted);
}

.alert-status.active {
  color: var(--color-danger);
}

.ack-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-size: 11px;
  cursor: pointer;
}

.ack-label {
  font-size: 11px;
  color: var(--color-success);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  color: var(--color-text-subtle);
}

.empty-state.small {
  padding: 12px;
}

.empty-icon {
  font-size: 28px;
  margin-bottom: 6px;
}
</style>
