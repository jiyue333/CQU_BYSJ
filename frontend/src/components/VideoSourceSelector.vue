<script setup lang="ts">
/**
 * 视频源选择组件
 * 支持本地视频文件、浏览器摄像头、RTSP 地址
 * Requirements: 1.1, 1.2, 1.3, 1.5
 */

import { ref, computed } from 'vue'
import type { StreamType, VideoStreamCreate } from '@/types'
import { uploadFile } from '@/api/files'
import { useStreamsStore } from '@/stores/streams'

const emit = defineEmits<{
  created: [streamId: string]
  error: [message: string]
}>()

const store = useStreamsStore()

// 表单状态
const sourceType = ref<StreamType>('file')
const streamName = ref('')
const rtspUrl = ref('')
const selectedFile = ref<File | null>(null)
const uploadProgress = ref(0)
const isSubmitting = ref(false)
const errorMessage = ref('')

// 文件输入引用
const fileInput = ref<HTMLInputElement | null>(null)

// 表单验证
const isValid = computed(() => {
  if (!streamName.value.trim()) return false

  switch (sourceType.value) {
    case 'file':
      return selectedFile.value !== null
    case 'rtsp':
      return rtspUrl.value.startsWith('rtsp://') || rtspUrl.value.startsWith('rtsps://')
    case 'webcam':
      return true
    default:
      return false
  }
})

// 选择文件
function onFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    const file = input.files[0]
    if (file) {
      selectedFile.value = file
      // 自动填充名称
      if (!streamName.value) {
        streamName.value = file.name.replace(/\.[^/.]+$/, '')
      }
    }
  }
}

// 触发文件选择
function triggerFileSelect() {
  fileInput.value?.click()
}

// 请求摄像头权限
async function requestCameraPermission(): Promise<boolean> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    // 立即停止，只是检查权限
    stream.getTracks().forEach((track) => track.stop())
    return true
  } catch (err) {
    console.error('Camera permission denied:', err)
    return false
  }
}

// 提交表单
async function handleSubmit() {
  if (!isValid.value || isSubmitting.value) return

  isSubmitting.value = true
  errorMessage.value = ''
  uploadProgress.value = 0

  try {
    const createData: VideoStreamCreate = {
      name: streamName.value.trim(),
      type: sourceType.value
    }

    // 根据类型处理
    if (sourceType.value === 'file') {
      if (!selectedFile.value) throw new Error('请选择文件')
      // 上传文件
      const uploadResult = await uploadFile(selectedFile.value, (progress) => {
        uploadProgress.value = progress
      })
      createData.file_id = uploadResult.file_id
    } else if (sourceType.value === 'rtsp') {
      createData.source_url = rtspUrl.value.trim()
    } else if (sourceType.value === 'webcam') {
      // 检查摄像头权限
      const hasPermission = await requestCameraPermission()
      if (!hasPermission) {
        throw new Error('摄像头权限被拒绝，请在浏览器设置中允许访问摄像头')
      }
    }

    // 创建流
    const stream = await store.createStream(createData)
    emit('created', stream.stream_id)

    // 重置表单
    resetForm()
  } catch (err) {
    const message = err instanceof Error ? err.message : '创建失败'
    errorMessage.value = message
    emit('error', message)
  } finally {
    isSubmitting.value = false
  }
}

// 重置表单
function resetForm() {
  streamName.value = ''
  rtspUrl.value = ''
  selectedFile.value = null
  uploadProgress.value = 0
  errorMessage.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div class="video-source-selector">
    <h3>添加视频源</h3>

    <!-- 源类型选择 -->
    <div class="source-type-tabs">
      <button
        :class="{ active: sourceType === 'file' }"
        type="button"
        @click="sourceType = 'file'"
      >
        📁 本地文件
      </button>
      <button
        :class="{ active: sourceType === 'webcam' }"
        type="button"
        @click="sourceType = 'webcam'"
      >
        📷 摄像头
      </button>
      <button
        :class="{ active: sourceType === 'rtsp' }"
        type="button"
        @click="sourceType = 'rtsp'"
      >
        📡 RTSP
      </button>
    </div>

    <form class="source-form" @submit.prevent="handleSubmit">
      <!-- 名称输入 -->
      <div class="form-group">
        <label for="stream-name">名称</label>
        <input
          id="stream-name"
          v-model="streamName"
          type="text"
          placeholder="输入视频流名称"
          maxlength="255"
          required
        />
      </div>

      <!-- 本地文件选择 -->
      <div v-if="sourceType === 'file'" class="form-group">
        <label>视频文件</label>
        <input
          ref="fileInput"
          type="file"
          accept=".mp4,.avi,.mkv,.mov,.webm,.flv"
          style="display: none"
          @change="onFileSelect"
        />
        <div class="file-select-area" @click="triggerFileSelect">
          <template v-if="selectedFile">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
          </template>
          <template v-else>
            <span class="placeholder">点击选择视频文件</span>
            <span class="hint">支持 MP4, AVI, MKV, MOV, WebM, FLV</span>
          </template>
        </div>
        <!-- 上传进度 -->
        <div v-if="uploadProgress > 0 && uploadProgress < 100" class="progress-bar">
          <div class="progress" :style="{ width: uploadProgress + '%' }"></div>
          <span class="progress-text">{{ uploadProgress.toFixed(0) }}%</span>
        </div>
      </div>

      <!-- 摄像头说明 -->
      <div v-if="sourceType === 'webcam'" class="form-group">
        <div class="webcam-info">
          <p>📷 将使用浏览器摄像头</p>
          <p class="hint">点击创建后会请求摄像头权限</p>
        </div>
      </div>

      <!-- RTSP 地址输入 -->
      <div v-if="sourceType === 'rtsp'" class="form-group">
        <label for="rtsp-url">RTSP 地址</label>
        <input
          id="rtsp-url"
          v-model="rtspUrl"
          type="text"
          placeholder="rtsp://192.168.1.100:554/stream"
        />
        <span class="hint">支持 rtsp:// 和 rtsps:// 协议</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <!-- 提交按钮 -->
      <button type="submit" class="submit-btn" :disabled="!isValid || isSubmitting">
        <span v-if="isSubmitting">
          {{ sourceType === 'file' && uploadProgress < 100 ? '上传中...' : '创建中...' }}
        </span>
        <span v-else>创建视频流</span>
      </button>
    </form>
  </div>
</template>

<style scoped>
.video-source-selector {
  padding: 16px;
  background: #1a1a1a;
  border-radius: 8px;
  max-width: 400px;
}

h3 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #fff;
}

.source-type-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.source-type-tabs button {
  flex: 1;
  padding: 10px;
  border: 1px solid #333;
  background: #2a2a2a;
  color: #888;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-type-tabs button:hover {
  background: #333;
  color: #fff;
}

.source-type-tabs button.active {
  background: #4a9eff;
  border-color: #4a9eff;
  color: #fff;
}

.source-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  color: #aaa;
}

.form-group input[type='text'] {
  padding: 10px 12px;
  border: 1px solid #333;
  background: #2a2a2a;
  color: #fff;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input[type='text']:focus {
  outline: none;
  border-color: #4a9eff;
}

.file-select-area {
  padding: 20px;
  border: 2px dashed #333;
  border-radius: 6px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.file-select-area:hover {
  border-color: #4a9eff;
  background: rgba(74, 158, 255, 0.1);
}

.file-name {
  display: block;
  color: #fff;
  font-weight: 500;
}

.file-size {
  display: block;
  color: #888;
  font-size: 12px;
  margin-top: 4px;
}

.placeholder {
  display: block;
  color: #888;
}

.hint {
  display: block;
  color: #666;
  font-size: 12px;
  margin-top: 4px;
}

.progress-bar {
  position: relative;
  height: 20px;
  background: #2a2a2a;
  border-radius: 4px;
  overflow: hidden;
}

.progress {
  height: 100%;
  background: #4a9eff;
  transition: width 0.3s;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: #fff;
}

.webcam-info {
  padding: 20px;
  background: #2a2a2a;
  border-radius: 6px;
  text-align: center;
}

.webcam-info p {
  margin: 0;
  color: #fff;
}

.webcam-info .hint {
  margin-top: 8px;
}

.error-message {
  padding: 10px;
  background: rgba(255, 77, 77, 0.1);
  border: 1px solid #ff4d4d;
  border-radius: 6px;
  color: #ff4d4d;
  font-size: 14px;
}

.submit-btn {
  padding: 12px;
  background: #4a9eff;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #3a8eef;
}

.submit-btn:disabled {
  background: #333;
  color: #666;
  cursor: not-allowed;
}
</style>
