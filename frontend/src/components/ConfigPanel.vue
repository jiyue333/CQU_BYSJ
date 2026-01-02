<script setup lang="ts">
/**
 * 配置管理面板组件
 * 方案 F：服务端渲染热力图配置
 * 提供置信度阈值、热力图网格、推理步长、叠加透明度等配置
 * Requirements: 8.1, 8.2, 8.3
 */

import { ref, watch, computed, onMounted } from 'vue'
import { getConfig, updateConfig, getConfigPresets } from '@/api'
import type { ConfigPreset, SystemConfig, SystemConfigUpdate } from '@/types'

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
const presets = ref<ConfigPreset[]>([])
const selectedPresetId = ref<string>('')

// 表单值（用于编辑）- 方案 F 配置项
const formValues = ref({
  confidence_threshold: 0.5,
  heatmap_grid_size: 20,
  heatmap_decay: 0.5,
  render_infer_stride: 3,
  render_overlay_alpha: 0.4,
  render_fps: 24,
  default_density_thresholds: {
    low: 0.3,
    medium: 0.6,
    high: 0.8
  }
})

// 是否有未保存的更改
const hasChanges = computed(() => {
  if (!config.value) return false
  return (
    formValues.value.confidence_threshold !== config.value.confidence_threshold ||
    formValues.value.heatmap_grid_size !== config.value.heatmap_grid_size ||
    formValues.value.heatmap_decay !== config.value.heatmap_decay ||
    formValues.value.render_infer_stride !== config.value.render_infer_stride ||
    formValues.value.render_overlay_alpha !== config.value.render_overlay_alpha ||
    formValues.value.render_fps !== config.value.render_fps ||
    formValues.value.default_density_thresholds.low !== config.value.default_density_thresholds.low ||
    formValues.value.default_density_thresholds.medium !== config.value.default_density_thresholds.medium ||
    formValues.value.default_density_thresholds.high !== config.value.default_density_thresholds.high
  )
})

// 计算实际推理帧率（render_fps / render_infer_stride）
const effectiveInferFps = computed(() => {
  const renderFps = formValues.value.render_fps
  return Math.round(renderFps / formValues.value.render_infer_stride)
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
      heatmap_grid_size: config.value.heatmap_grid_size,
      heatmap_decay: config.value.heatmap_decay,
      render_infer_stride: config.value.render_infer_stride,
      render_overlay_alpha: config.value.render_overlay_alpha,
      render_fps: config.value.render_fps,
      default_density_thresholds: {
        low: config.value.default_density_thresholds.low,
        medium: config.value.default_density_thresholds.medium,
        high: config.value.default_density_thresholds.high
      }
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
    if (formValues.value.heatmap_grid_size !== config.value?.heatmap_grid_size) {
      updateData.heatmap_grid_size = formValues.value.heatmap_grid_size
    }
    if (formValues.value.heatmap_decay !== config.value?.heatmap_decay) {
      updateData.heatmap_decay = formValues.value.heatmap_decay
    }
    if (formValues.value.render_infer_stride !== config.value?.render_infer_stride) {
      updateData.render_infer_stride = formValues.value.render_infer_stride
    }
    if (formValues.value.render_overlay_alpha !== config.value?.render_overlay_alpha) {
      updateData.render_overlay_alpha = formValues.value.render_overlay_alpha
    }
    if (formValues.value.render_fps !== config.value?.render_fps) {
      updateData.render_fps = formValues.value.render_fps
    }
    if (
      formValues.value.default_density_thresholds.low !== config.value?.default_density_thresholds.low ||
      formValues.value.default_density_thresholds.medium !== config.value?.default_density_thresholds.medium ||
      formValues.value.default_density_thresholds.high !== config.value?.default_density_thresholds.high
    ) {
      updateData.default_density_thresholds = { ...formValues.value.default_density_thresholds }
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
    heatmap_grid_size: 20,
    heatmap_decay: 0.5,
    render_infer_stride: 3,
    render_overlay_alpha: 0.4,
    render_fps: 24,
    default_density_thresholds: {
      low: 0.3,
      medium: 0.6,
      high: 0.8
    }
  }
}

// 取消更改
function cancelChanges() {
  if (config.value) {
    formValues.value = {
      confidence_threshold: config.value.confidence_threshold,
      heatmap_grid_size: config.value.heatmap_grid_size,
      heatmap_decay: config.value.heatmap_decay,
      render_infer_stride: config.value.render_infer_stride,
      render_overlay_alpha: config.value.render_overlay_alpha,
      render_fps: config.value.render_fps,
      default_density_thresholds: {
        low: config.value.default_density_thresholds.low,
        medium: config.value.default_density_thresholds.medium,
        high: config.value.default_density_thresholds.high
      }
    }
  }
}

async function loadPresets() {
  try {
    const response = await getConfigPresets()
    presets.value = response.presets
    if (presets.value.length > 0) {
      selectedPresetId.value = presets.value[0]?.id || ''
    }
  } catch {
    presets.value = []
  }
}

function applyPreset() {
  const preset = presets.value.find((item) => item.id === selectedPresetId.value)
  if (!preset) return
  formValues.value.render_fps = preset.render_fps
  formValues.value.render_infer_stride = preset.render_infer_stride
  formValues.value.heatmap_decay = preset.heatmap_decay
  formValues.value.render_overlay_alpha = preset.render_overlay_alpha
}

// 监听 streamId 变化
watch(() => props.streamId, loadConfig, { immediate: true })
onMounted(() => {
  loadPresets()
})
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
      <!-- 方案 F 提示 -->
      <div class="info-banner">
        <span class="info-icon">ℹ️</span>
        <span>热力图由服务端渲染，预计延迟 1-5 秒</span>
      </div>

      <!-- 配置预设 -->
      <div v-if="presets.length > 0" class="form-group">
        <label>
          <span class="label-text">配置预设</span>
          <span class="label-hint">快速切换渲染策略</span>
        </label>
        <div class="input-row">
          <select v-model="selectedPresetId" class="select-input">
            <option v-for="preset in presets" :key="preset.id" :value="preset.id">
              {{ preset.name }}
            </option>
          </select>
          <button class="btn btn-secondary small" @click="applyPreset">应用</button>
        </div>
      </div>

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

      <!-- 推理步长 -->
      <div class="form-group">
        <label>
          <span class="label-text">推理步长</span>
          <span class="label-hint">每 N 帧推理一次 (1-10)，当前约 {{ effectiveInferFps }} FPS</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.render_infer_stride"
            type="range"
            min="1"
            max="10"
            step="1"
            class="slider"
          />
          <input
            v-model.number="formValues.render_infer_stride"
            type="number"
            min="1"
            max="10"
            step="1"
            class="number-input"
          />
        </div>
      </div>

      <!-- 渲染帧率 -->
      <div class="form-group">
        <label>
          <span class="label-text">渲染帧率</span>
          <span class="label-hint">输出帧率 (10-60 FPS)</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.render_fps"
            type="range"
            min="10"
            max="60"
            step="1"
            class="slider"
          />
          <input
            v-model.number="formValues.render_fps"
            type="number"
            min="10"
            max="60"
            step="1"
            class="number-input"
          />
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

      <!-- 热力图衰减 -->
      <div class="form-group">
        <label>
          <span class="label-text">热力图衰减</span>
          <span class="label-hint">EMA 衰减 (0-1)</span>
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

      <!-- 默认密度阈值 -->
      <div class="form-group">
        <label>
          <span class="label-text">默认密度阈值</span>
          <span class="label-hint">新建 ROI 继承</span>
        </label>
        <div class="threshold-row">
          <div class="threshold-item">
            <span class="threshold-label">低</span>
            <input
              v-model.number="formValues.default_density_thresholds.low"
              type="number"
              min="0"
              max="1"
              step="0.05"
              class="number-input"
            />
          </div>
          <div class="threshold-item">
            <span class="threshold-label">中</span>
            <input
              v-model.number="formValues.default_density_thresholds.medium"
              type="number"
              min="0"
              max="1"
              step="0.05"
              class="number-input"
            />
          </div>
          <div class="threshold-item">
            <span class="threshold-label">高</span>
            <input
              v-model.number="formValues.default_density_thresholds.high"
              type="number"
              min="0"
              max="1"
              step="0.05"
              class="number-input"
            />
          </div>
        </div>
      </div>

      <!-- 热力图透明度 -->
      <div class="form-group">
        <label>
          <span class="label-text">热力图透明度</span>
          <span class="label-hint">叠加透明度 (0-1)，越大越明显</span>
        </label>
        <div class="input-row">
          <input
            v-model.number="formValues.render_overlay_alpha"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="slider"
          />
          <input
            v-model.number="formValues.render_overlay_alpha"
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
  background: var(--color-panel);
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text);
  font-weight: 600;
}

.no-stream {
  color: var(--color-text-subtle);
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
  color: var(--color-text-muted);
  padding: 20px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
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
  color: var(--color-danger);
  font-size: 14px;
}

.btn-retry {
  padding: 4px 12px;
  background: rgba(244, 67, 54, 0.2);
  border: none;
  border-radius: 4px;
  color: var(--color-danger);
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
  color: var(--color-text);
  font-weight: 500;
}

.label-hint {
  font-size: 12px;
  color: var(--color-text-subtle);
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
  background: var(--color-border);
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: var(--color-primary);
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
  background: var(--color-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.number-input {
  width: 70px;
  padding: 8px 10px;
  background: var(--color-input-bg);
  border: 1px solid var(--color-input-border);
  border-radius: 6px;
  color: var(--color-text);
  font-size: 14px;
  text-align: center;
}

.select-input {
  flex: 1;
  padding: 8px 10px;
  background: var(--color-input-bg);
  border: 1px solid var(--color-input-border);
  border-radius: 6px;
  color: var(--color-text);
  font-size: 14px;
}

.btn.small {
  padding: 6px 12px;
  font-size: 12px;
}

.threshold-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.threshold-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.threshold-label {
  font-size: 12px;
  color: var(--color-text-muted);
  width: 20px;
}

.number-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.info-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(33, 150, 243, 0.1);
  border: 1px solid rgba(33, 150, 243, 0.3);
  border-radius: 8px;
  font-size: 13px;
  color: #64b5f6;
}

.info-icon {
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
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
  background: var(--color-border);
  color: var(--color-text);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-border-strong);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-strong);
}
</style>
