<script setup lang="ts">
/**
 * ROI 模板选择器
 */

import { ref, watch } from 'vue'
import type { ROITemplate } from '@/types'
import { applyROIPreset, listROITemplates } from '@/api'

const props = defineProps<{
  streamId: string | null
}>()

const emit = defineEmits<{
  (e: 'applied'): void
}>()

const templates = ref<ROITemplate[]>([])
const selectedTemplateId = ref<string>('')
const loading = ref(false)
const error = ref('')
const applying = ref(false)
const replaceExisting = ref(false)

async function loadTemplates() {
  loading.value = true
  error.value = ''
  try {
    const response = await listROITemplates()
    templates.value = response.templates
    if (!selectedTemplateId.value && templates.value.length > 0) {
      selectedTemplateId.value = templates.value[0]?.id || ''
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载模板失败'
  } finally {
    loading.value = false
  }
}

async function applyTemplate() {
  if (!props.streamId || !selectedTemplateId.value) return
  applying.value = true
  error.value = ''
  try {
    await applyROIPreset(props.streamId, selectedTemplateId.value, replaceExisting.value)
    emit('applied')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '应用模板失败'
  } finally {
    applying.value = false
  }
}

watch(
  () => props.streamId,
  () => {
    if (props.streamId) {
      loadTemplates()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="roi-template-selector">
    <div class="selector-header">
      <span class="title">ROI 模板</span>
    </div>
    <div v-if="loading" class="loading">加载模板...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="selector-body">
      <select v-model="selectedTemplateId" class="template-select">
        <option v-for="template in templates" :key="template.id" :value="template.id">
          {{ template.name }}
        </option>
      </select>
      <label class="replace-toggle">
        <input type="checkbox" v-model="replaceExisting" />
        覆盖现有 ROI
      </label>
      <button
        class="apply-btn"
        :disabled="!streamId || !selectedTemplateId || applying"
        @click="applyTemplate"
      >
        {{ applying ? '应用中...' : '应用模板' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.roi-template-selector {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 10px;
  border: 1px solid var(--color-border);
  margin-bottom: 12px;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.title {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.selector-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: 12px;
}

.replace-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.apply-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.apply-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading,
.error {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
