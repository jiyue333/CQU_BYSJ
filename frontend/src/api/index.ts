/**
 * API 模块导出
 */

export * from './request'
export * from './streams'
export {
  createROI,
  listROIs,
  getROI,
  updateROI,
  deleteROI,
  listROITemplates,
  applyROIPreset,
  type Point,
  type DensityThresholds,
  type ROI,
  type ROICreate,
  type ROIUpdate,
  type ROIListResponse
} from './rois'
export { uploadFile, listFiles, getFile, deleteFile } from './files'
export {
  getHistory,
  getAggregatedHistory,
  exportHistory,
  downloadHistory,
  type AggregationGranularity,
  type HistoryStatResponse,
  type HistoryListResponse,
  type AggregatedStat,
  type AggregatedHistoryResponse,
  type HistoryQueryParams,
  type AggregatedQueryParams
} from './history'
export { getConfig, updateConfig, getConfigPresets } from './config'
export * from './alerts'
export * from './feedback'
