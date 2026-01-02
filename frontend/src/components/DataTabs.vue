<script setup lang="ts">
/**
 * 数据与配置 Tab 切换组件
 * 包含：实时统计、ROI 管理、历史图表
 */

import { ref, computed, watch } from 'vue'
import StatsPanel from './StatsPanel.vue'
import AlertsPanel from './AlertsPanel.vue'
import ROITemplateSelector from './ROITemplateSelector.vue'
import HistoryChart from './HistoryChart.vue'
import RealtimeChart from './RealtimeChart.vue'
import type { AlertEvent, DetectionResult, RegionStat, StatusMetrics } from '@/types'
import type { ROI, ROICreate, Point } from '@/api/rois'
import { listROIs, createROI, updateROI, deleteROI } from '@/api/rois'
import type { DrawMode } from './ROIDrawer.vue'

const props = defineProps<{
  streamId: string | null
  result: DetectionResult | null
  statusMetrics?: StatusMetrics | null
  alertEvents?: AlertEvent[]
}>()

const emit = defineEmits<{
  (e: 'roiModeChange', enabled: boolean): void
  (e: 'roisChange', rois: ROI[]): void
  (e: 'selectedRoiChange', roiId: string | null): void
  (e: 'drawModeChange', mode: DrawMode): void
}>()

// Tab 状态
type TabType = 'realtime' | 'roi' | 'alerts' | 'history'
const activeTab = ref<TabType>('realtime')

// ROI 状态
const rois = ref<ROI[]>([])
const selectedRoiId = ref<string | null>(null)
const roiEditMode = ref(false)
const roiDrawMode = ref<DrawMode>('polygon')
const roiLoading = ref(false)
const roiError = ref<string | null>(null)

// 编辑中的 ROI 名称
const editingRoiName = ref<string | null>(null)
const editNameValue = ref('')

// 区域统计数据
const regionStats = computed<RegionStat[]>(() => {
  return props.result?.region_stats || []
})

// 加载 ROI 列表
async function loadROIs() {
  if (!props.streamId) {
    rois.value = []
    return
  }
  
  roiLoading.value = true
  roiError.value = null
  
  try {
    const response = await listROIs(props.streamId)
    rois.value = response.rois
    emit('roisChange', rois.value)
  } catch (e) {
    roiError.value = e instanceof Error ? e.message : '加载 ROI 失败'
  } finally {
    roiLoading.value = false
  }
}

function handleTemplateApplied() {
  loadROIs()
}

// 创建 ROI
async function handleCreateROI(data: ROICreate) {
  if (!props.streamId) return
  
  try {
    const roi = await createROI(props.streamId, data)
    rois.value.push(roi)
    selectedRoiId.value = roi.roi_id
    emit('roisChange', rois.value)
    emit('selectedRoiChange', roi.roi_id)
  } catch (e) {
    roiError.value = e instanceof Error ? e.message : '创建 ROI 失败'
  }
}

// 更新 ROI 点位
async function handleUpdateROIPoints(roiId: string, points: Point[]) {
  if (!props.streamId) return
  
  try {
    const updated = await updateROI(props.streamId, roiId, { points })
    const index = rois.value.findIndex(r => r.roi_id === roiId)
    if (index !== -1) {
      rois.value[index] = updated
    }
    emit('roisChange', rois.value)
  } catch (e) {
    roiError.value = e instanceof Error ? e.message : '更新 ROI 失败'
  }
}

// 更新 ROI 名称
async function handleUpdateROIName(roiId: string) {
  if (!props.streamId || !editNameValue.value.trim()) {
    editingRoiName.value = null
    return
  }
  
  try {
    const updated = await updateROI(props.streamId, roiId, { name: editNameValue.value.trim() })
    const index = rois.value.findIndex(r => r.roi_id === roiId)
    if (index !== -1) {
      rois.value[index] = updated
    }
    emit('roisChange', rois.value)
  } catch (e) {
    roiError.value = e instanceof Error ? e.message : '更新名称失败'
  } finally {
    editingRoiName.value = null
  }
}

// 删除 ROI
async function handleDeleteROI(roiId: string) {
  if (!props.streamId) return
  
  try {
    await deleteROI(props.streamId, roiId)
    rois.value = rois.value.filter(r => r.roi_id !== roiId)
    if (selectedRoiId.value === roiId) {
      selectedRoiId.value = null
      emit('selectedRoiChange', null)
    }
    emit('roisChange', rois.value)
  } catch (e) {
    roiError.value = e instanceof Error ? e.message : '删除 ROI 失败'
  }
}

// 选择 ROI
function handleSelectROI(roiId: string | null) {
  selectedRoiId.value = roiId
  emit('selectedRoiChange', roiId)
}

// 开始编辑名称
function startEditName(roi: ROI) {
  editingRoiName.value = roi.roi_id
  editNameValue.value = roi.name
}

// 切换编辑模式
function toggleEditMode() {
  roiEditMode.value = !roiEditMode.value
  emit('roiModeChange', roiEditMode.value)
  // Reset draw mode to polygon
  roiDrawMode.value = 'polygon'
  emit('drawModeChange', 'polygon')
}

// 切换绘制模式
function setDrawMode(mode: DrawMode) {
  roiDrawMode.value = mode
  emit('drawModeChange', mode)
}

function setActiveTab(tab: TabType) {
  activeTab.value = tab
}

// 获取区域统计
function getRegionStat(roiId: string): RegionStat | undefined {
  return regionStats.value.find(s => s.region_id === roiId)
}

// 监听 streamId 变化
watch(() => props.streamId, () => {
  loadROIs()
  selectedRoiId.value = null
  roiEditMode.value = false
  emit('roiModeChange', false)
  emit('selectedRoiChange', null)
}, { immediate: true })

// 监听 Tab 切换
watch(activeTab, (newTab) => {
  if (newTab !== 'roi') {
    roiEditMode.value = false
    emit('roiModeChange', false)
  }
})

// 暴露方法给父组件
defineExpose({
  rois,
  selectedRoiId,
  roiEditMode,
  roiDrawMode,
  toggleEditMode,
  setActiveTab,
  handleCreateROI,
  handleUpdateROIPoints,
  handleDeleteROI,
  handleSelectROI
})
</script>

<template>
  <div class="data-tabs">
    <!-- Tab 头部 -->
    <div class="tab-header">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'realtime' }"
        @click="activeTab = 'realtime'"
      >
        📊 实时
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'roi' }"
        @click="activeTab = 'roi'"
      >
        🎯 ROI
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'history' }"
        @click="activeTab = 'history'"
      >
        📈 历史
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'alerts' }"
        @click="activeTab = 'alerts'"
      >
        🚨 告警
      </button>
    </div>

    <!-- Tab 内容 -->
    <div class="tab-content">
      <!-- 实时统计 -->
      <div v-if="activeTab === 'realtime'" class="tab-panel">
        <div class="panel-section">
          <StatsPanel :result="result" :metrics="statusMetrics" :stream-id="streamId" />
        </div>
        <div v-if="streamId" class="panel-section">
          <h4>实时趋势</h4>
          <RealtimeChart
            :stream-id="streamId"
            :result="result"
            :rois="rois"
          />
        </div>
      </div>

      <!-- ROI 管理 -->
      <div v-else-if="activeTab === 'roi'" class="tab-panel roi-panel">
        <div v-if="!streamId" class="empty-state">
          <span class="empty-icon">🎯</span>
          <p>请先选择视频流</p>
        </div>
        
        <template v-else>
          <ROITemplateSelector :stream-id="streamId" @applied="handleTemplateApplied" />
          <!-- ROI 工具栏 -->
          <div class="roi-toolbar">
            <button 
              class="tool-btn"
              :class="{ active: roiEditMode }"
              @click="toggleEditMode"
            >
              {{ roiEditMode ? '✓ 完成编辑' : '✏️ 编辑模式' }}
            </button>

            <template v-if="roiEditMode">
                <div class="separator"></div>
                <button
                    class="tool-btn icon-btn"
                    :class="{ active: roiDrawMode === 'polygon' }"
                    @click="setDrawMode('polygon')"
                    title="多边形"
                >
                    ⬡
                </button>
                <button
                    class="tool-btn icon-btn"
                    :class="{ active: roiDrawMode === 'rect' }"
                    @click="setDrawMode('rect')"
                    title="矩形"
                >
                    ⬜
                </button>
                <button
                    class="tool-btn icon-btn"
                    :class="{ active: roiDrawMode === 'circle' }"
                    @click="setDrawMode('circle')"
                    title="圆形"
                >
                    ⭕
                </button>
            </template>
          </div>
          <div v-if="roiEditMode" class="hint-bar">
             <span v-if="roiDrawMode === 'polygon'">双击开始绘制多边形，Enter 结束</span>
             <span v-else>按下鼠标拖拽绘制，松开结束</span>
          </div>

          <!-- 加载状态 -->
          <div v-if="roiLoading" class="loading">加载中...</div>
          
          <!-- 错误提示 -->
          <div v-if="roiError" class="error">{{ roiError }}</div>

          <!-- ROI 列表 -->
          <div v-if="rois.length === 0 && !roiLoading" class="empty-state small">
            <p>暂无 ROI 区域</p>
            <p class="hint">开启编辑模式后绘制感兴趣区域</p>
          </div>

          <ul v-else class="roi-list">
            <li 
              v-for="roi in rois" 
              :key="roi.roi_id"
              :class="{ selected: roi.roi_id === selectedRoiId }"
              @click="handleSelectROI(roi.roi_id)"
            >
              <div class="roi-info">
                <!-- 名称编辑 -->
                <template v-if="editingRoiName === roi.roi_id">
                  <input 
                    v-model="editNameValue"
                    class="name-input"
                    autofocus
                    @blur="handleUpdateROIName(roi.roi_id)"
                    @keyup.enter="handleUpdateROIName(roi.roi_id)"
                    @keyup.esc="editingRoiName = null"
                  />
                </template>
                <template v-else>
                  <span class="roi-name" @dblclick="startEditName(roi)">
                    {{ roi.name }}
                  </span>
                </template>
                
                <!-- 区域统计 -->
                <div v-if="getRegionStat(roi.roi_id)" class="roi-stat">
                  <span class="count">{{ getRegionStat(roi.roi_id)?.count }} 人</span>
                  <span 
                    class="level"
                    :class="getRegionStat(roi.roi_id)?.level"
                  >
                    {{ getRegionStat(roi.roi_id)?.level === 'low' ? '低' : 
                       getRegionStat(roi.roi_id)?.level === 'medium' ? '中' : '高' }}
                  </span>
                </div>
                <div v-else class="roi-stat empty">
                  <span class="no-data">暂无数据</span>
                </div>
              </div>
              
              <!-- 操作按钮 -->
              <div v-if="roiEditMode" class="roi-actions">
                <button 
                  class="action-btn delete"
                  title="删除"
                  @click.stop="handleDeleteROI(roi.roi_id)"
                >
                  🗑
                </button>
              </div>
            </li>
          </ul>

          <!-- 快捷键提示 -->
          <div v-if="roiEditMode" class="shortcuts">
             <template v-if="roiDrawMode === 'polygon'">
                <div class="shortcut"><kbd>双击</kbd> 开始</div>
                <div class="shortcut"><kbd>Enter</kbd> 完成</div>
             </template>
             <template v-else>
                <div class="shortcut"><kbd>拖拽</kbd> 绘制</div>
             </template>
            <div class="shortcut"><kbd>Esc</kbd> 取消</div>
            <div class="shortcut"><kbd>Delete</kbd> 删除</div>
          </div>
        </template>
      </div>

      <!-- 历史图表 -->
      <div v-else-if="activeTab === 'history'" class="tab-panel history-panel">
        <div v-if="!streamId" class="empty-state">
          <span class="empty-icon">📈</span>
          <p>请先选择视频流</p>
        </div>
        <HistoryChart v-else :stream-id="streamId" />
      </div>

      <!-- 告警历史 -->
      <div v-else-if="activeTab === 'alerts'" class="tab-panel alerts-panel">
        <AlertsPanel :stream-id="streamId" :live-events="alertEvents || []" :rois="rois" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-tabs {
  display: flex;
  flex-direction: column;
  background: var(--color-panel);
  border-radius: 12px;
  overflow: hidden;
  height: 100%; /* Fill available height */
}

.tab-header {
  display: flex;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--color-panel-alt);
  color: var(--color-text);
}

.tab-btn.active {
  background: var(--color-panel-alt);
  color: var(--color-primary);
  border-bottom: 2px solid var(--color-primary);
}

.tab-content {
  flex: 1;
  overflow-y: auto; /* Allow scrolling */
  min-height: 0; /* Enable flex child scrolling */
}

.tab-panel {
  padding: 16px;
  height: 100%;
}

.panel-section {
  margin-bottom: 20px;
}

.panel-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--color-text-subtle);
  height: 100%;
}

.empty-state.small {
  padding: 16px;
  height: auto;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
}

.empty-state .hint {
  font-size: 12px;
  color: var(--color-text-subtle);
  margin-top: 4px;
}

/* ROI 面板 */
.roi-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.separator {
    width: 1px;
    height: 24px;
    background: var(--color-border);
    margin: 0 4px;
}

.tool-btn {
  padding: 6px 12px;
  background: var(--color-border);
  border: none;
  border-radius: 6px;
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: var(--color-border-strong);
}

.tool-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.icon-btn {
    padding: 6px;
    width: 32px;
    height: 32px;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.hint-bar {
    font-size: 12px;
    color: var(--color-text-muted);
    margin-bottom: 12px;
    padding: 4px 8px;
    background: var(--color-panel-alt);
    border-radius: 4px;
}

.loading {
  text-align: center;
  padding: 16px;
  color: var(--color-text-muted);
}

.error {
  padding: 8px 12px;
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 12px;
}

.roi-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.roi-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--color-panel-alt);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.roi-list li:hover {
  background: var(--color-panel-hover);
}

.roi-list li.selected {
  border-color: var(--color-primary);
  background: rgba(74, 158, 255, 0.1);
}

.roi-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.roi-name {
  font-weight: 500;
  font-size: 14px;
}

.name-input {
  padding: 4px 8px;
  background: var(--color-input-bg);
  border: 1px solid var(--color-primary);
  border-radius: 4px;
  color: var(--color-text);
  font-size: 14px;
  width: 120px;
}

.roi-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.roi-stat .count {
  color: var(--color-text);
}

.roi-stat .level {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.roi-stat .level.low {
  background: rgba(76, 175, 80, 0.2);
  color: var(--color-success);
}

.roi-stat .level.medium {
  background: rgba(255, 152, 0, 0.2);
  color: var(--color-warning);
}

.roi-stat .level.high {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.roi-stat.empty .no-data {
  color: var(--color-text-subtle);
}

.roi-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  background: var(--color-border);
}

.action-btn.delete {
  background: rgba(244, 67, 54, 0.2);
  color: var(--color-danger);
}

.action-btn.delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

.shortcuts {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.shortcut {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.shortcut kbd {
  padding: 2px 6px;
  background: var(--color-border);
  border-radius: 4px;
  font-family: inherit;
  margin-right: 4px;
}

/* 历史面板 */
.history-panel {
  padding: 0;
}

.history-panel :deep(.history-chart) {
  background: transparent;
  box-shadow: none;
}

.history-panel :deep(.controls) {
  background: var(--color-panel-alt);
  border-radius: 8px;
  padding: 12px;
  margin: 16px;
  border-bottom: none;
}

.history-panel :deep(.control-group select),
.history-panel :deep(.control-group input) {
  background: var(--color-input-bg);
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.history-panel :deep(.control-group button) {
  background: var(--color-primary);
}

.history-panel :deep(.chart-container) {
  margin: 0 16px;
}

.history-panel :deep(.legend) {
  color: var(--color-text-muted);
}

.history-panel :deep(.summary) {
  border-color: var(--color-border);
  margin: 16px;
}

.history-panel :deep(.summary-item .label) {
  color: var(--color-text-subtle);
}

.history-panel :deep(.summary-item .value) {
  color: var(--color-text);
}
</style>
