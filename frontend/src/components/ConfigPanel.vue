<script setup lang="ts">
/**
 * 配置管理面板组件
 * 提供置信度阈值、密度等级阈值、推理频率等配置
 * Requirements: 8.1, 8.2, 8.3
 */

import { ref, watch, computed } from 'vue'
import { getConfig, updateConfig } from '@/api'
import type { SystemConfig, SystemConfigUpdate } from '@/types'

const props = defineProps<{
  streamId: string | null
}>()

const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'updated'): void
}>()

// 配置状态
const config = ref<SystemConfig | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

// 表单值（用于编辑）
const formValues = ref({
  confidence_threshold: 0.5,
  inference_fps: 2,
  heatmap_grid_size: 20,
  heatmap_decay: 0.3
})

// 是否有未保存的更改
const hasChanges = computed(() => {
  if (!config.value) return false
  return (
    formValues.value.confidence_threshold !== config.value.confidence_threshold ||
    formValues.value.inference_fps !== config.value.inference_fps ||
    formValues.value.heatmap_grid_size !== config.value.heatmap_grid_size ||
    formValues.value.heatmap_decay !== config.value.heatmap_decay
  )
})

// 加载配置
async function loadConfig() {
  if (!props.streamId) {
    config.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    config.value = await getConfig(props.streamId)
    // 同步表单值
    formValues.value = {
      confidence_threshold: config.value.confidence_threshold,
      inference_fps: config.value.inference_fps,
      heatmap_grid_size: config.value.heatmap_grid_size,
      heatmap_decay: config.value.heatmap_decay
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : '加载配置失败'
    error.value = message
    emit('error', message)
  } finally {
    loading.value = false
  }
}

// 保存配置
async function saveConfig() {
  if (!props.streamId || !hasChanges.value) return

  saving.value = true
  error.value = null

  try {
    const updateData: SystemConfigUpdate = {}
    
    if (formValues.value.confidence_threshold !== config.value?.confidence_threshold) {
      updateData.confidence_threshold = formValues.value.confidence_threshold
    }
    if (formValues.value.inference_fps !== config.value?.inference_fps) {
      updateData.inference_fps = formValues.value.inference_fps
    }
    if (formValues.value.heatmap_grid_size !== config.value?.heatmap_grid_size) {
      updateData.heatmap_grid_size = formValues.value.heatmap_grid_size
    }
    if (formValues.value.heatmap_decay !== config.value?.heatmap_decay) {
      updateData.heatmap_decay = formValues.value.heatmap_decay
    }

    config.value = await updateConfig(props.streamId, updateData)
    emit('updated')
  } catch (err) {
    const message = err instanceof Error ? err.message : '保存配置失败'
    error.value = message
    emit('error', message)
  } finally {
    saving.value = false
  }
}

// 重置为默认值
function resetToDefaults() {
  formValues.value = {
    confidence_threshold: 0.5,
    inference_fps: 2,
    heatmap_grid_size: 20,
    heatmap_decay: 0.3
  }
}

// 取消更改
function cancelChanges() {
  if (config.value) {
    formValues.value = {
      confidence_threshold: config.value.confidence_threshold,
      inference_fps: config.value.inference_fps,
      heatmap_grid_size: config.value.heatmap_grid_size,
      heatmap_decay: config.value.heatmap_decay
    }
  }
}

// 监听 streamId 变化
watch(() => props.streamId, loadConfig, { immediate: true })
</script>

<template>
  <div class="config-panel">
    <div class="panel-header">
      <h3>⚙️ 配置管理</h3>
    </div>

    <div v-if="!streamId" class="no-stream">
      <p>请先选择视频流</p>
    </div>

    <div v-else-if="loading" class="loading">
      <span class="spinner"></span>
      加载配置中...
    </div>

    <div v-else-if="error" class="error">
      <span>❌ {{ error }}</span>
      <button class="btn-retry" @click="loadConfig">重试</button>
    </div>

    <div v-else class="config-form">
      <!-- 置信度阈值 -->
      <div class="form-group">
        <label>
          <span class="label-text">检测置信度阈值</span>
          <span class="label-hint">过滤低置信度检测结果 (0-1)</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.confidence_threshold"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="slider"
          />
          <input
            v-model.number="formValues.confidence_threshold"
            type="number"
            min="0"
            max="1"
            step="0.05"
            class="number-input"
          />
        </div>
      </div>

      <!-- 推理频率 -->
      <div class="form-group">
        <label>
          <span class="label-text">推理频率 (FPS)</span>
          <span class="label-hint">每秒推理帧数 (1-3)</span>
        </label>
        <div class="input-row">
          <div class="fps-buttons">
            <button
              v-for="fps in [1, 2, 3]"
              :key="fps"
              :class="['fps-btn', { active: formValues.inference_fps === fps }]"
              @click="formValues.inference_fps = fps"
            >
              {{ fps }} FPS
            </button>
          </div>
        </div>
      </div>

      <!-- 热力图网格大小 -->
      <div class="form-group">
        <label>
          <span class="label-text">热力图网格大小</span>
          <span class="label-hint">网格分辨率 (5-100)</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.heatmap_grid_size"
            type="range"
            min="5"
            max="100"
            step="5"
            class="slider"
          />
          <input
            v-model.number="formValues.heatmap_grid_size"
            type="number"
            min="5"
            max="100"
            step="5"
            class="number-input"
          />
        </div>
      </div>

      <!-- 热力图衰减因子 -->
      <div class="form-group">
        <label>
          <span class="label-text">热力图平滑因子 (α)</span>
          <span class="label-hint">EMA 平滑系数，越大越敏感 (0-1)</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.heatmap_decay"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="slider"
          />
          <input
            v-model.number="formValues.heatmap_decay"
            type="number"
            min="0"
            max="1"
            step="0.05"
            class="number-input"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button
          class="btn btn-secondary"
          :disabled="!hasChanges"
          @click="cancelChanges"
        >
          取消
        </button>
        <button
          class="btn btn-secondary"
          @click="resetToDefaults"
        >
          恢复默认
        </button>
        <button
          class="btn btn-primary"
          :disabled="!hasChanges || saving"
          @click="saveConfig"
        >
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-panel {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
  font-weight: 600;
}

.no-stream {
  color: #666;
  text-align: center;
  padding: 20px;
}

.no-stream p {
  margin: 0;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #888;
  padding: 20px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #333;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: rgba(244, 67, 54, 0.1);
  border-radius: 8px;
  color: #f44336;
  font-size: 14px;
}

.btn-retry {
  padding: 4px 12px;
  background: rgba(244, 67, 54, 0.2);
  border: none;
  border-radius: 4px;
  color: #f44336;
  cursor: pointer;
  font-size: 12px;
}

.btn-retry:hover {
  background: rgba(244, 67, 54, 0.3);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label-text {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.label-hint {
  font-size: 12px;
  color: #666;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #333;
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: #4a9eff;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: #4a9eff;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.number-input {
  width: 70px;
  padding: 8px 10px;
  background: #252525;
  border: 1px solid #333;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  text-align: center;
}

.number-input:focus {
  outline: none;
  border-color: #4a9eff;
}

.fps-buttons {
  display: flex;
  gap: 8px;
}

.fps-btn {
  flex: 1;
  padding: 10px 16px;
  background: #252525;
  border: 1px solid #333;
  border-radius: 6px;
  color: #888;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.fps-btn:hover {
  background: #2a2a2a;
  border-color: #444;
}

.fps-btn.active {
  background: rgba(74, 158, 255, 0.15);
  border-color: #4a9eff;
  color: #4a9eff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #333;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #333;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background: #444;
}

.btn-primary {
  background: #4a9eff;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #3d8ce6;
}
</style>
