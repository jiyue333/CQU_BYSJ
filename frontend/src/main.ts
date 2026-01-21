import * as echarts from "echarts";

const app = document.querySelector("#app");

if (app) {
  app.innerHTML = `
    <div class="app-shell">
      <header class="top-bar">
        <div class="brand">
          <div class="logo">FlowLens</div>
          <div class="subtitle">YOLO 实时人流计数与密度洞察</div>
        </div>
        <div class="top-meta">
          <div class="meta-block">
            <span class="meta-label">系统状态</span>
            <span class="meta-value status-online" data-system-status>在线</span>
          </div>
          <div class="meta-block">
            <span class="meta-label">当前时间</span>
            <span class="meta-value" data-time>--:--</span>
          </div>
          <button class="ghost-button" type="button" data-action="fullscreen">全屏</button>
        </div>
      </header>

      <main class="dashboard">
        <section class="panel live-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">实时监控</p>
              <h2 data-source-title>主入口摄像头</h2>
            </div>
            <div class="panel-actions">
              <div class="chip-row">
                <span class="chip live">LIVE</span>
                <span class="chip" data-source-name>Cam-A03</span>
                <span class="chip" data-source-meta>1080p · 26fps</span>
                <span class="chip" data-analysis-status>待机</span>
              </div>
            </div>
          </div>
          <div class="video-frame">
            <div class="video-grid"></div>
            <img class="video-stream" data-video-frame alt="实时画面" />
            <div class="video-caption">检测框 · 区域划分 · 轨迹叠加</div>
          </div>
          <div class="control-row">
            <div class="source-selector">
              <button class="primary" type="button" data-action="source-camera">摄像头</button>
              <button type="button" data-action="source-upload">视频上传</button>
              <select class="ghost-select" data-source-select>
                <option value="">选择数据源</option>
              </select>
              <button class="ghost-button danger" type="button" data-action="delete-source">删除</button>
            </div>
            <div class="action-set">
              <button class="ghost-button" type="button" data-action="snapshot">截图</button>
              <button class="ghost-button" type="button" data-action="export-clip">导出片段</button>
              <button class="primary" type="button" data-action="start-analysis">开始分析</button>
              <button class="ghost-button" type="button" data-action="stop-analysis">停止分析</button>
            </div>
          </div>
        </section>

        <section class="panel stat-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">核心指标</p>
              <h2>实时统计</h2>
            </div>
            <div class="panel-actions">
              <span class="badge">最近 10 秒更新</span>
            </div>
          </div>
          <div class="stat-grid">
            <div class="stat-card">
              <span>总人数</span>
              <strong data-stat-total>--</strong>
              <em>峰值 162</em>
            </div>
            <div class="stat-card">
              <span>密度</span>
              <strong data-stat-entry>--</strong>
              <em>密度系数</em>
            </div>
            <div class="stat-card">
              <span>密度等级</span>
              <strong data-stat-index>--</strong>
              <em>实时状态</em>
            </div>
            <div class="stat-card">
              <span>预警次数</span>
              <strong data-stat-alerts>--</strong>
              <em>近 1 小时</em>
            </div>
          </div>
          <div class="stat-footer">
            <div class="legend">
              <span class="dot low"></span>低密度
            </div>
            <div class="legend">
              <span class="dot mid"></span>中密度
            </div>
            <div class="legend">
              <span class="dot high"></span>高密度
            </div>
          </div>
        </section>

        <section class="panel region-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">区域密度</p>
              <h2>前/中/后区对比</h2>
            </div>
            <div class="panel-actions">
              <select class="ghost-select" data-region-template>
                <option value="">区域模板</option>
                <option value="front-middle-back">前/中/后三区</option>
                <option value="left-middle-right">左/中/右三区</option>
                <option value="quadrants">四象限</option>
              </select>
              <button class="ghost-button" type="button" data-action="apply-region-template">应用模板</button>
              <button class="ghost-button" type="button" data-action="custom-regions">自定义分区</button>
              <button class="ghost-button" type="button" data-action="add-region">新增区域</button>
            </div>
          </div>
          <div class="region-list" data-region-list>
          </div>
          <div class="region-note">
            建议：前区人流密度接近预警阈值，建议引导分流。
          </div>
        </section>

        <section class="panel history-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">历史趋势</p>
              <h2>近 30 分钟</h2>
            </div>
            <div class="panel-actions">
              <select class="ghost-select" data-history-source-select>
                <option value="">选择数据源</option>
              </select>
              <select class="ghost-select" data-history-region-select>
                <option value="">全部区域</option>
              </select>
              <select class="ghost-select" data-history-interval-select>
                <option value="1m">1 分钟</option>
                <option value="5m">5 分钟</option>
                <option value="1h">1 小时</option>
              </select>
              <select class="ghost-select" data-history-metric-select></select>
              <select class="ghost-select" data-history-export-format>
                <option value="csv">CSV</option>
                <option value="xlsx">XLSX</option>
              </select>
              <button class="ghost-button" type="button" data-action="refresh-history">刷新</button>
              <button class="ghost-button" type="button" data-action="export-history">导出</button>
            </div>
          </div>
          <div class="history-content">
            <div class="history-chart" data-history-chart></div>
            <div class="history-list" data-history-list>
            </div>
          </div>
        </section>

        <section class="panel alert-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">预警配置</p>
              <h2>区域阈值</h2>
            </div>
            <div class="panel-actions">
              <button class="ghost-button" type="button" data-action="export-alerts">导出告警</button>
            </div>
          </div>
          <div class="alert-body">
            <div class="region-threshold-list" data-region-threshold-list>
              <div class="region-note">暂无区域配置</div>
            </div>
            <div class="alert-section-divider">
              <span>最近告警</span>
            </div>
            <div class="alert-feed" data-alert-list>
              <div>
                <strong>--:--</strong>
                <span>暂无预警</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer class="footer">
        <span>© 2024 FlowLens · 人流计数与密度分析系统</span>
        <span>模型：YOLOv8n · 模式：实时推理</span>
      </footer>
    </div>

    <!-- 区域配置弹窗 -->
    <div class="modal-overlay" data-region-modal>
      <div class="modal-container">
        <div class="modal-header">
          <h3 data-modal-title>区域配置</h3>
          <button class="modal-close" type="button" data-action="close-modal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="regionName">区域名称</label>
            <input type="text" id="regionName" class="form-input" placeholder="如：前区、入口A" data-region-name />
          </div>
          <div class="form-group color-picker">
            <label>区域颜色</label>
            <input type="color" value="#3B8FF6" data-region-color />
            <input type="text" class="form-input" value="#3B8FF6" data-region-color-text />
          </div>
          <div class="form-section">
            <div class="form-section-title">人数阈值</div>
            <div class="form-row">
              <div class="form-group">
                <label for="countWarning">警告阈值</label>
                <input type="number" id="countWarning" class="form-input" placeholder="可选" min="0" data-count-warning />
                <small>触发黄色预警</small>
              </div>
              <div class="form-group">
                <label for="countCritical">严重阈值</label>
                <input type="number" id="countCritical" class="form-input" placeholder="可选" min="0" data-count-critical />
                <small>触发红色预警</small>
              </div>
            </div>
          </div>
          <div class="form-section">
            <div class="form-section-title">密度阈值</div>
            <div class="form-row">
              <div class="form-group">
                <label for="densityWarning">警告阈值</label>
                <input type="number" id="densityWarning" class="form-input" placeholder="可选" min="0" max="100" step="0.1" data-density-warning />
                <small>密度 0-100</small>
              </div>
              <div class="form-group">
                <label for="densityCritical">严重阈值</label>
                <input type="number" id="densityCritical" class="form-input" placeholder="可选" min="0" max="100" step="0.1" data-density-critical />
                <small>密度 0-100</small>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="ghost-button" type="button" data-action="cancel-modal">取消</button>
          <button class="primary" type="button" data-action="confirm-modal">确定</button>
        </div>
      </div>
    </div>
  `;
}

const timeEl = document.querySelector("[data-time]");

const updateTime = () => {
  if (!timeEl) return;
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  timeEl.textContent = `${hours}:${minutes}:${seconds}`;
};

updateTime();
setInterval(updateTime, 1000);

const thresholdInput = document.querySelector<HTMLInputElement>("[data-range-input]");
const thresholdValue = document.querySelector<HTMLElement>("[data-range-value]");

if (thresholdInput && thresholdValue) {
  thresholdValue.textContent = `${thresholdInput.value}%`;
  thresholdInput.addEventListener("input", (event) => {
    const target = event.target;
    if (!target || !("value" in target)) return;
    thresholdValue.textContent = `${target.value}%`;
  });
}

const API_BASE = "/api";
const WS_BASE = "/api/ws";
const WS_RETRY_BASE_MS = 1000;
const WS_RETRY_MAX_MS = 10000;
const HISTORY_METRICS: readonly {
  key: string;
  label: string;
  unit: string;
  digits: number;
  color: string;
  min: number;
  max?: number;
}[] = [
  { key: "total_count_avg", label: "平均人数", unit: "人", digits: 0, color: "#3B8FF6", min: 0 },
  { key: "total_count_max", label: "最大人数", unit: "人", digits: 0, color: "#5BC0EB", min: 0 },
  { key: "total_count_min", label: "最小人数", unit: "人", digits: 0, color: "#2F7DE1", min: 0 },
  { key: "total_density_avg", label: "平均密度", unit: "", digits: 2, color: "#6BB6FF", min: 0, max: 100 },
];

const REGION_TEMPLATES = [
  {
    id: "front-middle-back",
    label: "前/中/后三区",
    regions: [
      { name: "前区", color: "#3B8FF6", points: [[0, 66], [100, 66], [100, 100], [0, 100]] },
      { name: "中区", color: "#5BC0EB", points: [[0, 33], [100, 33], [100, 66], [0, 66]] },
      { name: "后区", color: "#2F7DE1", points: [[0, 0], [100, 0], [100, 33], [0, 33]] },
    ],
  },
  {
    id: "left-middle-right",
    label: "左/中/右三区",
    regions: [
      { name: "左区", color: "#3B8FF6", points: [[0, 0], [33, 0], [33, 100], [0, 100]] },
      { name: "中区", color: "#5BC0EB", points: [[33, 0], [66, 0], [66, 100], [33, 100]] },
      { name: "右区", color: "#2F7DE1", points: [[66, 0], [100, 0], [100, 100], [66, 100]] },
    ],
  },
  {
    id: "quadrants",
    label: "四象限",
    regions: [
      { name: "左上", color: "#3B8FF6", points: [[0, 0], [50, 0], [50, 50], [0, 50]] },
      { name: "右上", color: "#5BC0EB", points: [[50, 0], [100, 0], [100, 50], [50, 50]] },
      { name: "左下", color: "#2F7DE1", points: [[0, 50], [50, 50], [50, 100], [0, 100]] },
      { name: "右下", color: "#6BB6FF", points: [[50, 50], [100, 50], [100, 100], [50, 100]] },
    ],
  },
] as const;

type ApiEnvelope<T> = {
  code: number;
  data: T;
  msg: string;
};

type AlertItem = {
  alert_id?: string;
  alert_type?: string;
  level?: string;
  region_name?: string;
  region?: string;
  region_id?: string;
  regionId?: string;
  current_value?: number;
  threshold?: number;
  timestamp?: string;
  time?: string;
  message?: string;
};

type RegionItem = {
  region_id?: string;
  name?: string;
  count?: number;
  density?: number;
  points?: number[][];
  color?: string;
  count_warning?: number | null;
  count_critical?: number | null;
  density_warning?: number | null;
  density_critical?: number | null;
};

type SourceItem = {
  source_id: string;
  name?: string;
  source_type?: string;
  status?: string;
  video_width?: number;
  video_height?: number;
  video_fps?: number;
  created_at?: string;
};

type HistoryMetricKey = string;
type HistoryMetric = typeof HISTORY_METRICS[number];

type HistorySummary = {
  total_count_avg?: number;
  total_count_max?: number;
  total_count_min?: number;
  total_density_avg?: number;
};

type HistorySeriesPoint = {
  time: string;
  value: number;
};

type HistorySeriesItem = {
  time: string;
  total_count_avg?: number;
  total_count_max?: number;
  total_count_min?: number;
  total_density_avg?: number;
  regions?: Record<
    string,
    {
      total_count_avg?: number;
      total_count_max?: number;
      total_count_min?: number;
      total_density_avg?: number;
    }
  >;
};

type HistoryResponse = HistorySummary & {
  series?: HistorySeriesItem[];
};

const ui = {
  systemStatus: document.querySelector<HTMLElement>("[data-system-status]"),
  sourceTitle: document.querySelector<HTMLElement>("[data-source-title]"),
  sourceName: document.querySelector<HTMLElement>("[data-source-name]"),
  sourceMeta: document.querySelector<HTMLElement>("[data-source-meta]"),
  sourceSelect: document.querySelector<HTMLSelectElement>("[data-source-select]"),
  analysisStatus: document.querySelector<HTMLElement>("[data-analysis-status]"),
  totalCount: document.querySelector<HTMLElement>("[data-total-count]"),
  totalTrend: document.querySelector<HTMLElement>("[data-total-trend]"),
  densityLevel: document.querySelector<HTMLElement>("[data-density-level]"),
  densityValue: document.querySelector<HTMLElement>("[data-density-value]"),
  statTotal: document.querySelector<HTMLElement>("[data-stat-total]"),
  statEntry: document.querySelector<HTMLElement>("[data-stat-entry]"),
  statIndex: document.querySelector<HTMLElement>("[data-stat-index]"),
  statAlerts: document.querySelector<HTMLElement>("[data-stat-alerts]"),
  regionList: document.querySelector<HTMLElement>("[data-region-list]"),
  alertList: document.querySelector<HTMLElement>("[data-alert-list]"),
  historyList: document.querySelector<HTMLElement>("[data-history-list]"),
  historyChart: document.querySelector<HTMLElement>("[data-history-chart]"),
  historySourceSelect: document.querySelector<HTMLSelectElement>("[data-history-source-select]"),
  historyRegionSelect: document.querySelector<HTMLSelectElement>("[data-history-region-select]"),
  historyIntervalSelect: document.querySelector<HTMLSelectElement>("[data-history-interval-select]"),
  historyMetricSelect: document.querySelector<HTMLSelectElement>("[data-history-metric-select]"),
  historyExportFormat: document.querySelector<HTMLSelectElement>("[data-history-export-format]"),
  regionTemplateSelect: document.querySelector<HTMLSelectElement>("[data-region-template]"),
  videoFrame: document.querySelector<HTMLImageElement>("[data-video-frame]"),
  videoFrameContainer: document.querySelector<HTMLElement>(".video-frame"),
  thresholdInput,
  thresholdValue,
  actionButtons: {
    sourceCamera: document.querySelector<HTMLElement>("[data-action='source-camera']"),
    sourceUpload: document.querySelector<HTMLElement>("[data-action='source-upload']"),
    deleteSource: document.querySelector<HTMLElement>("[data-action='delete-source']"),
    startAnalysis: document.querySelector<HTMLElement>("[data-action='start-analysis']"),
    stopAnalysis: document.querySelector<HTMLElement>("[data-action='stop-analysis']"),
    refreshHistory: document.querySelector<HTMLElement>("[data-action='refresh-history']"),
    exportHistory: document.querySelector<HTMLElement>("[data-action='export-history']"),
    exportAlerts: document.querySelector<HTMLElement>("[data-action='export-alerts']"),
    exportClip: document.querySelector<HTMLElement>("[data-action='export-clip']"),
    snapshot: document.querySelector<HTMLElement>("[data-action='snapshot']"),
    customRegions: document.querySelector<HTMLElement>("[data-action='custom-regions']"),
    addRegion: document.querySelector<HTMLElement>("[data-action='add-region']"),
    applyRegionTemplate: document.querySelector<HTMLElement>("[data-action='apply-region-template']"),
    fullscreen: document.querySelector<HTMLElement>("[data-action='fullscreen']"),
  },
  // 区域配置弹窗
  regionModal: document.querySelector<HTMLElement>("[data-region-modal]"),
  modalTitle: document.querySelector<HTMLElement>("[data-modal-title]"),
  regionNameInput: document.querySelector<HTMLInputElement>("[data-region-name]"),
  regionColorInput: document.querySelector<HTMLInputElement>("[data-region-color]"),
  regionColorText: document.querySelector<HTMLInputElement>("[data-region-color-text]"),
  countWarningInput: document.querySelector<HTMLInputElement>("[data-count-warning]"),
  countCriticalInput: document.querySelector<HTMLInputElement>("[data-count-critical]"),
  densityWarningInput: document.querySelector<HTMLInputElement>("[data-density-warning]"),
  densityCriticalInput: document.querySelector<HTMLInputElement>("[data-density-critical]"),
  regionThresholdList: document.querySelector<HTMLElement>("[data-region-threshold-list]"),
};

const state = {
  sourceId: null as string | null,
  sourceName: null as string | null,
  videoWidth: null as number | null,
  videoHeight: null as number | null,
  sourcesCache: [] as SourceItem[],
  realtimeSocket: null as WebSocket | null,
  alertSocket: null as WebSocket | null,
  realtimeReconnectTimer: null as number | null,
  alertReconnectTimer: null as number | null,
  realtimeRetryCount: 0,
  alertRetryCount: 0,
  isAnalysisRunning: false,
  alertItems: [] as AlertItem[],
  thresholdConfig: null as Record<string, unknown> | null,
  regionConfigs: [] as RegionItem[],
  analysisStatusTimer: null as number | null,
  historySourceId: null as string | null,
  historySourceName: "未选择",
  historyRegionId: null as string | null,
  historyRegionName: null as string | null,
  historyInterval: "1m" as "1m" | "5m" | "1h",
  historyMetric: "total_count_avg" as HistoryMetricKey,
  historyChart: null as echarts.ECharts | null,
  historyData: null as HistoryResponse | null,
  historyRegions: [] as RegionItem[],
  gridPickerActive: false,
  gridPickerPoints: [] as Array<{ x: number; y: number }>,
};

const setText = (element: HTMLElement | null, value: string) => {
  if (!element) return;
  element.textContent = value;
};

const formatNumber = (value: number | undefined | null, digits = 0) => {
  if (!Number.isFinite(value)) return "--";
  return value!.toFixed(digits);
};

const formatCount = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "--";
  return `${Math.round(value!)}`;
};

const toNumberArray = (values: Array<number | undefined>) =>
  values.filter((value): value is number => Number.isFinite(value));

const average = (values: number[]) => {
  if (!values.length) return undefined;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
};

const maxValue = (values: number[]) => {
  if (!values.length) return undefined;
  return Math.max(...values);
};

const minValue = (values: number[]) => {
  if (!values.length) return undefined;
  return Math.min(...values);
};

const getMetricMeta = (metricKey: HistoryMetricKey): HistoryMetric =>
  HISTORY_METRICS.find((item) => item.key === metricKey) || HISTORY_METRICS[0];

const formatMetricValue = (metricKey: HistoryMetricKey, value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "--";
  const meta = getMetricMeta(metricKey);
  return value!.toFixed(meta.digits);
};

const formatHistoryTime = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  const hours = String(parsed.getHours()).padStart(2, "0");
  const minutes = String(parsed.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
};

const getDensityLevel = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "--";
  if (value! >= 6) return "拥挤";
  if (value! >= 3) return "正常";
  return "宽松";
};

const getDensityClass = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "low";
  if (value! >= 6) return "high";
  if (value! >= 3) return "mid";
  return "low";
};

const updateSystemStatus = (status: "online" | "offline" | "connecting") => {
  if (!ui.systemStatus) return;
  ui.systemStatus.classList.toggle("status-online", status === "online");
  setText(ui.systemStatus, status === "online" ? "在线" : status === "connecting" ? "连接中" : "离线");
};

const setAnalysisStatus = (status: string, progress?: number) => {
  if (!ui.analysisStatus) return;
  const labels: Record<string, string> = {
    running: "运行中",
    stopped: "已停止",
    idle: "待机",
  };
  const base = labels[status] || status;
  const label = progress !== undefined ? `${base} ${Math.round(progress * 100)}%` : base;
  ui.analysisStatus.textContent = label;
};

const getWsUrl = (path: string, params: Record<string, string>) => {
  const url = new URL(path, window.location.origin);
  url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
};

const getRetryDelay = (attempt: number) =>
  Math.min(WS_RETRY_MAX_MS, WS_RETRY_BASE_MS * 2 ** Math.min(attempt, 5));

const clearRealtimeReconnect = () => {
  if (state.realtimeReconnectTimer) {
    window.clearTimeout(state.realtimeReconnectTimer);
    state.realtimeReconnectTimer = null;
  }
};

const clearAlertReconnect = () => {
  if (state.alertReconnectTimer) {
    window.clearTimeout(state.alertReconnectTimer);
    state.alertReconnectTimer = null;
  }
};

const scheduleRealtimeReconnect = (reason: string) => {
  if (!state.isAnalysisRunning || !state.sourceId) return;
  if (state.realtimeReconnectTimer) return;
  const delay = getRetryDelay(state.realtimeRetryCount);
  console.warn(`[ws] realtime reconnect in ${delay}ms (${reason})`);
  state.realtimeReconnectTimer = window.setTimeout(() => {
    state.realtimeReconnectTimer = null;
    state.realtimeRetryCount += 1;
    connectRealtime(state.sourceId!);
  }, delay);
};

// 注意：告警通过 realtime WebSocket 推送，不再需要单独的 alert WebSocket

const parseApiPayload = <T>(payload: unknown): T => {
  if (!payload || typeof payload !== "object") return payload as T;
  const maybeEnvelope = payload as ApiEnvelope<T>;
  if (typeof maybeEnvelope.code === "number" && "data" in maybeEnvelope) {
    if (maybeEnvelope.code !== 0) {
      throw new Error(maybeEnvelope.msg || "请求失败");
    }
    return maybeEnvelope.data;
  }
  return payload as T;
};

const apiRequest = async <T>(path: string, options: RequestInit = {}) => {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = (payload as { msg?: string }).msg || response.statusText;
    throw new Error(message);
  }
  return parseApiPayload<T>(payload);
};

const apiGet = <T>(path: string) => apiRequest<T>(path);

const apiPost = <T>(path: string, body: unknown) =>
  apiRequest<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

const apiUpload = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<{ source_id: string; name?: string }>(`/sources/upload`, {
    method: "POST",
    body: formData,
  });
};

const updateSourceInfo = (name: string | null) => {
  if (ui.sourceTitle) {
    ui.sourceTitle.textContent = name || "实时监控";
  }
  if (ui.sourceName) {
    ui.sourceName.textContent = name || "--";
  }
  if (ui.sourceMeta) {
    ui.sourceMeta.textContent = state.sourceId ? `ID ${state.sourceId.slice(0, 6)}` : "未选择";
  }
};

// 更新视频容器的宽高比
const updateVideoAspectRatio = () => {
  if (!ui.videoFrameContainer) return;
  if (state.videoWidth && state.videoHeight && state.videoWidth > 0 && state.videoHeight > 0) {
    ui.videoFrameContainer.style.setProperty("--video-aspect-ratio", `${state.videoWidth} / ${state.videoHeight}`);
  } else {
    ui.videoFrameContainer.style.removeProperty("--video-aspect-ratio");
  }
};

// 棋盘点选相关常量
const GRID_COLS = 10;
const GRID_ROWS = 10;

// 创建棋盘点选覆盖层
const createGridPickerOverlay = (): HTMLElement => {
  const overlay = document.createElement("div");
  overlay.className = "grid-picker-overlay";

  // 创建网格点
  for (let row = 0; row <= GRID_ROWS; row++) {
    for (let col = 0; col <= GRID_COLS; col++) {
      const point = document.createElement("div");
      point.className = "grid-point";
      point.style.left = `${(col / GRID_COLS) * 100}%`;
      point.style.top = `${(row / GRID_ROWS) * 100}%`;
      point.dataset.col = String(col);
      point.dataset.row = String(row);
      point.addEventListener("click", (e) => {
        e.stopPropagation();
        const x = (col / GRID_COLS) * 100;
        const y = (row / GRID_ROWS) * 100;
        handleGridPointClick(x, y, point);
      });
      overlay.appendChild(point);
    }
  }

  // 创建多边形 SVG 容器
  const polygonSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  polygonSvg.classList.add("grid-polygon");
  polygonSvg.setAttribute("width", "100%");
  polygonSvg.setAttribute("height", "100%");
  polygonSvg.style.position = "absolute";
  polygonSvg.style.inset = "0";
  polygonSvg.style.pointerEvents = "none";
  overlay.appendChild(polygonSvg);

  // 创建工具栏
  const toolbar = document.createElement("div");
  toolbar.className = "grid-picker-toolbar";

  // 添加拖拽提示图标
  const dragHint = document.createElement("span");
  dragHint.className = "drag-hint";
  dragHint.textContent = "⋮⋮";
  dragHint.title = "拖拽移动";
  toolbar.appendChild(dragHint);

  // 拖拽状态
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let toolbarStartX = 0;
  let toolbarStartY = 0;

  const onMouseDown = (e: MouseEvent) => {
    // 如果点击的是按钮，不启动拖拽
    if ((e.target as HTMLElement).tagName === "BUTTON") return;

    isDragging = true;
    toolbar.classList.add("dragging");
    dragStartX = e.clientX;
    dragStartY = e.clientY;

    const rect = toolbar.getBoundingClientRect();
    const parentRect = overlay.getBoundingClientRect();
    toolbarStartX = rect.left - parentRect.left;
    toolbarStartY = rect.top - parentRect.top;

    e.preventDefault();
  };

  const onMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;

    const parentRect = overlay.getBoundingClientRect();
    const toolbarRect = toolbar.getBoundingClientRect();

    // 计算新位置（限制在父容器内）
    let newX = toolbarStartX + dx;
    let newY = toolbarStartY + dy;

    // 边界限制
    newX = Math.max(0, Math.min(newX, parentRect.width - toolbarRect.width));
    newY = Math.max(0, Math.min(newY, parentRect.height - toolbarRect.height));

    // 移除默认的居中 transform，使用绝对定位
    toolbar.style.transform = "none";
    toolbar.style.left = `${newX}px`;
    toolbar.style.top = `${newY}px`;
    toolbar.style.bottom = "auto";
  };

  const onMouseUp = () => {
    if (isDragging) {
      isDragging = false;
      toolbar.classList.remove("dragging");
    }
  };

  toolbar.addEventListener("mousedown", onMouseDown);
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);

  // 清理函数存储在 overlay 上，关闭时调用
  (overlay as any)._cleanupDrag = () => {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  const undoBtn = document.createElement("button");
  undoBtn.type = "button";
  undoBtn.className = "btn-undo";
  undoBtn.textContent = "撤销";
  undoBtn.addEventListener("click", () => {
    if (state.gridPickerPoints.length > 0) {
      state.gridPickerPoints.pop();
      updateGridPickerVisual(overlay);
    }
  });

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "btn-cancel";
  cancelBtn.textContent = "取消";
  cancelBtn.addEventListener("click", () => {
    closeGridPicker();
  });

  const confirmBtn = document.createElement("button");
  confirmBtn.type = "button";
  confirmBtn.className = "btn-confirm";
  confirmBtn.textContent = "确认";
  confirmBtn.addEventListener("click", async () => {
    if (state.gridPickerPoints.length < 3) {
      alert("请至少选择 3 个点来创建多边形区域");
      return;
    }
    await confirmGridPickerRegion();
  });

  toolbar.appendChild(undoBtn);
  toolbar.appendChild(cancelBtn);
  toolbar.appendChild(confirmBtn);
  overlay.appendChild(toolbar);

  return overlay;
};

// 处理网格点点击
const handleGridPointClick = (x: number, y: number, pointEl: HTMLElement) => {
  // 检查是否已存在该点
  const existingIndex = state.gridPickerPoints.findIndex(
    (p) => Math.abs(p.x - x) < 0.1 && Math.abs(p.y - y) < 0.1
  );

  if (existingIndex >= 0) {
    // 如果点击的是第一个点且有3个以上的点，则闭合多边形
    if (existingIndex === 0 && state.gridPickerPoints.length >= 3) {
      confirmGridPickerRegion();
      return;
    }
    // 否则取消选择该点
    state.gridPickerPoints.splice(existingIndex, 1);
    pointEl.classList.remove("selected");
  } else {
    // 添加新点
    state.gridPickerPoints.push({ x, y });
    pointEl.classList.add("selected");
  }

  // 更新可视化
  const overlay = ui.videoFrameContainer?.querySelector(".grid-picker-overlay");
  if (overlay) {
    updateGridPickerVisual(overlay as HTMLElement);
  }
};

// 更新棋盘点选可视化
const updateGridPickerVisual = (overlay: HTMLElement) => {
  // 更新点的选中状态
  overlay.querySelectorAll(".grid-point").forEach((point) => {
    const col = parseInt(point.getAttribute("data-col") || "0", 10);
    const row = parseInt(point.getAttribute("data-row") || "0", 10);
    const x = (col / GRID_COLS) * 100;
    const y = (row / GRID_ROWS) * 100;
    const isSelected = state.gridPickerPoints.some(
      (p) => Math.abs(p.x - x) < 0.1 && Math.abs(p.y - y) < 0.1
    );
    point.classList.toggle("selected", isSelected);
  });

  // 更新多边形（使用排序后的点，实时预览正确的多边形形状）
  const svg = overlay.querySelector(".grid-polygon");
  if (svg) {
    svg.innerHTML = "";
    if (state.gridPickerPoints.length >= 2) {
      // 对点进行极坐标排序
      const sortedPoints = getSortedPreviewPoints(state.gridPickerPoints);

      const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      const pointsStr = sortedPoints
        .map((p) => `${p.x}%,${p.y}%`)
        .join(" ");
      polyline.setAttribute("points", pointsStr);
      polyline.setAttribute("fill", "rgba(59, 143, 246, 0.2)");
      polyline.setAttribute("stroke", "rgba(59, 143, 246, 0.8)");
      polyline.setAttribute("stroke-width", "2");
      svg.appendChild(polyline);
    }
  }
};

// 获取排序后的预览点（内联极坐标排序，避免函数定义顺序问题）
const getSortedPreviewPoints = (
  points: Array<{ x: number; y: number }>
): Array<{ x: number; y: number }> => {
  if (points.length < 3) return [...points];
  const centerX = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const centerY = points.reduce((sum, p) => sum + p.y, 0) / points.length;
  return [...points].sort((a, b) => {
    const angleA = Math.atan2(a.y - centerY, a.x - centerX);
    const angleB = Math.atan2(b.y - centerY, b.x - centerX);
    return angleA - angleB;
  });
};

// 打开棋盘点选器
const openGridPicker = () => {
  if (!ui.videoFrameContainer) return;
  if (state.gridPickerActive) return;

  state.gridPickerActive = true;
  state.gridPickerPoints = [];

  const overlay = createGridPickerOverlay();
  ui.videoFrameContainer.appendChild(overlay);
};

// 关闭棋盘点选器
const closeGridPicker = () => {
  if (!ui.videoFrameContainer) return;
  state.gridPickerActive = false;
  state.gridPickerPoints = [];
  const overlay = ui.videoFrameContainer.querySelector(".grid-picker-overlay");
  if (overlay) {
    // 清理拖拽事件监听器
    if ((overlay as any)._cleanupDrag) {
      (overlay as any)._cleanupDrag();
    }
    overlay.remove();
  }
};

// ==============================
// 区域配置弹窗相关
// ==============================

interface RegionFormData {
  name: string;
  color: string;
  count_warning: number | null;
  count_critical: number | null;
  density_warning: number | null;
  density_critical: number | null;
}

// 弹窗回调
let _modalResolve: ((data: RegionFormData | null) => void) | null = null;

// 显示区域配置弹窗
const showRegionModal = (
  title: string,
  initial?: Partial<RegionFormData>
): Promise<RegionFormData | null> => {
  return new Promise((resolve) => {
    _modalResolve = resolve;

    // 设置标题
    if (ui.modalTitle) {
      ui.modalTitle.textContent = title;
    }

    // 填充初始值
    if (ui.regionNameInput) {
      ui.regionNameInput.value = initial?.name || "";
    }
    if (ui.regionColorInput) {
      ui.regionColorInput.value = initial?.color || "#3B8FF6";
    }
    if (ui.regionColorText) {
      ui.regionColorText.value = initial?.color || "#3B8FF6";
    }
    if (ui.countWarningInput) {
      ui.countWarningInput.value = initial?.count_warning != null ? String(initial.count_warning) : "";
    }
    if (ui.countCriticalInput) {
      ui.countCriticalInput.value = initial?.count_critical != null ? String(initial.count_critical) : "";
    }
    if (ui.densityWarningInput) {
      ui.densityWarningInput.value = initial?.density_warning != null ? String(initial.density_warning) : "";
    }
    if (ui.densityCriticalInput) {
      ui.densityCriticalInput.value = initial?.density_critical != null ? String(initial.density_critical) : "";
    }

    // 显示弹窗
    ui.regionModal?.classList.add("visible");

    // 聚焦名称输入框
    setTimeout(() => ui.regionNameInput?.focus(), 100);
  });
};

// 隐藏区域配置弹窗
const hideRegionModal = () => {
  ui.regionModal?.classList.remove("visible");
  if (_modalResolve) {
    _modalResolve(null);
    _modalResolve = null;
  }
};

// 确认弹窗
const confirmRegionModal = () => {
  if (!_modalResolve) return;

  const name = ui.regionNameInput?.value.trim() || "";
  if (!name) {
    alert("请输入区域名称");
    ui.regionNameInput?.focus();
    return;
  }

  const color = ui.regionColorInput?.value || "#3B8FF6";

  const countWarningVal = ui.countWarningInput?.value.trim();
  const countCriticalVal = ui.countCriticalInput?.value.trim();
  const densityWarningVal = ui.densityWarningInput?.value.trim();
  const densityCriticalVal = ui.densityCriticalInput?.value.trim();

  const data: RegionFormData = {
    name,
    color,
    count_warning: countWarningVal ? parseInt(countWarningVal, 10) : null,
    count_critical: countCriticalVal ? parseInt(countCriticalVal, 10) : null,
    density_warning: densityWarningVal ? parseFloat(densityWarningVal) : null,
    density_critical: densityCriticalVal ? parseFloat(densityCriticalVal) : null,
  };

  ui.regionModal?.classList.remove("visible");
  _modalResolve(data);
  _modalResolve = null;
};

// 同步颜色选择器和文本框
if (ui.regionColorInput && ui.regionColorText) {
  ui.regionColorInput.addEventListener("input", () => {
    if (ui.regionColorText) {
      ui.regionColorText.value = ui.regionColorInput!.value;
    }
  });
  ui.regionColorText.addEventListener("input", () => {
    const val = ui.regionColorText!.value;
    if (/^#[0-9A-Fa-f]{6}$/.test(val) && ui.regionColorInput) {
      ui.regionColorInput.value = val;
    }
  });
}

// 弹窗按钮事件
document.addEventListener("click", (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;

  const action = target.dataset.action || target.closest("button")?.dataset.action;

  if (action === "close-modal" || action === "cancel-modal") {
    hideRegionModal();
  } else if (action === "confirm-modal") {
    confirmRegionModal();
  }
});

// 点击遮罩层关闭弹窗
ui.regionModal?.addEventListener("click", (e) => {
  if (e.target === ui.regionModal) {
    hideRegionModal();
  }
});

// ESC 关闭弹窗
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && ui.regionModal?.classList.contains("visible")) {
    hideRegionModal();
  }
});

// 确认棋盘点选区域
const confirmGridPickerRegion = async () => {
  if (state.gridPickerPoints.length < 3) {
    alert("请至少选择 3 个点来创建多边形区域");
    return;
  }

  // 使用极坐标排序，确保点按顺时针顺序排列，避免自相交多边形
  const sortedPoints = getSortedPreviewPoints(state.gridPickerPoints);

  // 转换点为坐标数组
  const points = sortedPoints.map((p) => [p.x, p.y]);

  closeGridPicker();

  // 显示区域配置弹窗
  const formData = await showRegionModal("新增区域");
  if (!formData) {
    return;
  }

  if (!state.sourceId) return;

  const wasRunning = state.isAnalysisRunning;
  if (wasRunning) {
    await stopAnalysis();
  }

  try {
    await apiPost(`/regions`, {
      source_id: state.sourceId,
      name: formData.name,
      color: formData.color,
      points,
      count_warning: formData.count_warning,
      count_critical: formData.count_critical,
      density_warning: formData.density_warning,
      density_critical: formData.density_critical,
    });
    await loadRegions();
  } catch (error) {
    handleApiError(error);
  }

  if (wasRunning) {
    await startAnalysis();
  }
};

const updateRegions = (regions: RegionItem[]) => {
  if (!ui.regionList) return;

  if (!regions.length) {
    ui.regionList.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "region-note";
    empty.textContent = "暂无区域数据";
    ui.regionList.appendChild(empty);
    return;
  }

  // 获取现有的行元素（按区域名索引）
  const existingRows = new Map<string, HTMLElement>();
  ui.regionList.querySelectorAll<HTMLElement>(".region-row").forEach((row) => {
    const nameEl = row.querySelector(".region-info span");
    if (nameEl?.textContent) {
      existingRows.set(nameEl.textContent, row);
    }
  });

  // 清除非 region-row 的元素（如 region-note）
  ui.regionList.querySelectorAll(".region-note").forEach((el) => el.remove());

  // 记录需要保留的区域名
  const activeNames = new Set(regions.map((r) => r.name || "区域"));

  // 移除不再存在的区域行
  existingRows.forEach((row, name) => {
    if (!activeNames.has(name)) {
      row.remove();
    }
  });

  regions.forEach((region) => {
    const regionName = region.name || "区域";
    const densityValue = region.density || 0;
    // 密度值范围 0-10，乘以 10 作为进度条百分比
    const barWidthPercent = Math.min(100, Math.round(densityValue * 10));
    const densityClass = getDensityClass(densityValue);

    let row = existingRows.get(regionName);

    if (row) {
      // 更新现有行
      const countEl = row.querySelector<HTMLElement>(".region-info strong");
      if (countEl) {
        countEl.textContent = `${formatCount(region.count)} 人`;
      }

      const barFill = row.querySelector<HTMLElement>(".bar-fill");
      if (barFill) {
        barFill.style.width = `${barWidthPercent}%`;
        barFill.className = `bar-fill ${densityClass}`;
      }

      const labelEl = row.querySelector<HTMLElement>(".region-meta em");
      if (labelEl) {
        labelEl.textContent = getDensityLevel(densityValue);
      }

      // 检查是否需要添加/更新编辑按钮
      const config = state.regionConfigs.find((item) => item.name === region.name);
      const existingActions = row.querySelector<HTMLElement>(".region-actions");
      if (config?.region_id && !existingActions) {
        // 需要添加编辑按钮但还没有
        const meta = row.querySelector<HTMLElement>(".region-meta");
        if (meta) {
          const actions = document.createElement("div");
          actions.className = "region-actions";

          const editButton = document.createElement("button");
          editButton.type = "button";
          editButton.className = "mini-button";
          editButton.textContent = "编辑";
          editButton.dataset.action = "edit-region";
          editButton.dataset.regionId = config.region_id;
          actions.appendChild(editButton);

          const deleteButton = document.createElement("button");
          deleteButton.type = "button";
          deleteButton.className = "mini-button danger";
          deleteButton.textContent = "删除";
          deleteButton.dataset.action = "delete-region";
          deleteButton.dataset.regionId = config.region_id;
          actions.appendChild(deleteButton);

          meta.appendChild(actions);
        }
      }
    } else {
      // 创建新行
      row = document.createElement("div");
      row.className = "region-row";

      const info = document.createElement("div");
      info.className = "region-info";

      const name = document.createElement("span");
      name.textContent = regionName;
      const count = document.createElement("strong");
      count.textContent = `${formatCount(region.count)} 人`;

      info.appendChild(name);
      info.appendChild(count);

      const bar = document.createElement("div");
      bar.className = "bar";
      const barFill = document.createElement("div");
      barFill.className = `bar-fill ${densityClass}`;
      // 先设置 0 宽度，然后在下一帧设置目标宽度，触发过渡动画
      barFill.style.width = "0%";
      bar.appendChild(barFill);

      const meta = document.createElement("div");
      meta.className = "region-meta";

      const label = document.createElement("em");
      label.textContent = getDensityLevel(densityValue);

      const actions = document.createElement("div");
      actions.className = "region-actions";
      const config = state.regionConfigs.find((item) => item.name === region.name);
      if (config?.region_id) {
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "mini-button";
        editButton.textContent = "编辑";
        editButton.dataset.action = "edit-region";
        editButton.dataset.regionId = config.region_id;
        actions.appendChild(editButton);

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "mini-button danger";
        deleteButton.textContent = "删除";
        deleteButton.dataset.action = "delete-region";
        deleteButton.dataset.regionId = config.region_id;
        actions.appendChild(deleteButton);
      }

      meta.appendChild(label);
      if (actions.childElementCount > 0) {
        meta.appendChild(actions);
      }

      row.appendChild(info);
      row.appendChild(bar);
      row.appendChild(meta);
      ui.regionList.appendChild(row);

      // 使用 requestAnimationFrame 触发过渡动画
      requestAnimationFrame(() => {
        barFill.style.width = `${barWidthPercent}%`;
      });
    }
  });
};

// 渲染区域阈值配置列表（在预警配置面板中）
const renderRegionThresholds = () => {
  if (!ui.regionThresholdList) return;
  ui.regionThresholdList.innerHTML = "";

  const regions = state.regionConfigs.filter((r) => r.region_id);

  if (!regions.length) {
    const empty = document.createElement("div");
    empty.className = "region-note";
    empty.textContent = "暂无区域配置";
    ui.regionThresholdList.appendChild(empty);
    return;
  }

  regions.forEach((region) => {
    const item = document.createElement("div");
    item.className = "region-threshold-item";

    const info = document.createElement("div");
    info.className = "region-threshold-info";

    const name = document.createElement("div");
    name.className = "region-threshold-name";

    const colorDot = document.createElement("span");
    colorDot.className = "color-dot";
    colorDot.style.background = region.color || "#3B8FF6";

    const nameText = document.createElement("span");
    nameText.textContent = region.name || "区域";

    name.appendChild(colorDot);
    name.appendChild(nameText);

    const values = document.createElement("div");
    values.className = "region-threshold-values";

    // 人数阈值
    if (region.count_warning != null || region.count_critical != null) {
      if (region.count_warning != null) {
        const warn = document.createElement("span");
        warn.innerHTML = `<span class="warn-icon">⚠</span>人数≥${region.count_warning}`;
        values.appendChild(warn);
      }
      if (region.count_critical != null) {
        const crit = document.createElement("span");
        crit.innerHTML = `<span class="crit-icon">🔴</span>人数≥${region.count_critical}`;
        values.appendChild(crit);
      }
    }

    // 密度阈值
    if (region.density_warning != null || region.density_critical != null) {
      if (region.density_warning != null) {
        const warn = document.createElement("span");
        warn.innerHTML = `<span class="warn-icon">⚠</span>密度≥${region.density_warning}`;
        values.appendChild(warn);
      }
      if (region.density_critical != null) {
        const crit = document.createElement("span");
        crit.innerHTML = `<span class="crit-icon">🔴</span>密度≥${region.density_critical}`;
        values.appendChild(crit);
      }
    }

    if (!values.childElementCount) {
      values.innerHTML = "<span>未设置阈值</span>";
    }

    info.appendChild(name);
    info.appendChild(values);

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "mini-button";
    editBtn.textContent = "编辑";
    editBtn.dataset.action = "edit-region";
    editBtn.dataset.regionId = region.region_id;

    item.appendChild(info);
    item.appendChild(editBtn);
    ui.regionThresholdList.appendChild(item);
  });
};

const renderAlerts = (items: AlertItem[]) => {
  if (!ui.alertList) return;
  ui.alertList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    const time = document.createElement("strong");
    const text = document.createElement("span");
    time.textContent = "--:--";
    text.textContent = "暂无预警";
    empty.appendChild(time);
    empty.appendChild(text);
    ui.alertList.appendChild(empty);
    return;
  }

  items.slice(0, 5).forEach((item) => {
    const row = document.createElement("div");
    const time = document.createElement("strong");
    const text = document.createElement("span");
    time.textContent = (item.timestamp || item.time || "--:--").slice(11, 16);
    const regionLabel =
      item.region_name || item.region || item.regionId || item.region_id || "区域";
    text.textContent =
      item.message || `${regionLabel} ${item.level || ""}`.trim();
    row.appendChild(time);
    row.appendChild(text);
    ui.alertList.appendChild(row);
  });
};

const updateAlertCount = () => {
  setText(ui.statAlerts, `${state.alertItems.length}`);
};

const normalizeRealtimeRegions = (regions: unknown): RegionItem[] | null => {
  if (Array.isArray(regions)) {
    return regions as RegionItem[];
  }
  if (!regions || typeof regions !== "object") return null;
  const regionMap = new Map<string, string>();
  state.regionConfigs.forEach((item) => {
    if (item.region_id) {
      regionMap.set(item.region_id, item.name || item.region_id);
    }
  });
  return Object.entries(regions as Record<string, Record<string, unknown>>).map(
    ([regionId, stats]) => {
      const name =
        regionMap.get(regionId) ||
        (typeof stats.name === "string" ? stats.name : undefined) ||
        regionId;
      const count =
        typeof stats.count === "number"
          ? stats.count
          : typeof stats.total_count_avg === "number"
          ? stats.total_count_avg
          : typeof stats.total_count === "number"
          ? stats.total_count
          : undefined;
      const density =
        typeof stats.density === "number"
          ? stats.density
          : typeof stats.total_density_avg === "number"
          ? stats.total_density_avg
          : typeof stats.total_density === "number"
          ? stats.total_density
          : undefined;
      return { name, count, density };
    }
  );
};

const updateRealtime = (payload: {
  frame?: string;
  total_count?: number;
  total_density?: number;
  regions?: unknown;
}) => {
  const total = payload.total_count;
  const density = payload.total_density;

  if (typeof payload.frame === "string" && ui.videoFrame) {
    const src = payload.frame.startsWith("data:")
      ? payload.frame
      : `data:image/jpeg;base64,${payload.frame}`;
    ui.videoFrame.src = src;
  }

  setText(ui.totalCount, formatCount(total));
  setText(ui.statTotal, formatCount(total));

  if (Number.isFinite(density)) {
    setText(ui.statEntry, formatNumber(density, 2));
    setText(ui.statIndex, getDensityLevel(density));
  }

  const normalizedRegions = normalizeRealtimeRegions(payload.regions);
  if (normalizedRegions) {
    updateRegions(normalizedRegions);
  }

};

const closeSocket = (socket: WebSocket | null) => {
  if (!socket) return;
  socket.close();
};

const connectRealtime = (sourceId: string) => {
  clearRealtimeReconnect();
  closeSocket(state.realtimeSocket);
  updateSystemStatus("connecting");
  const ws = new WebSocket(getWsUrl(`${WS_BASE}/realtime`, { source_id: sourceId }));
  state.realtimeSocket = ws;

  ws.addEventListener("open", () => {
    updateSystemStatus("online");
    state.realtimeRetryCount = 0;
  });
  ws.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data) as
        | { type?: string; data?: Record<string, unknown> }
        | Record<string, unknown>;
      if (payload && typeof payload === "object" && "type" in payload && "data" in payload) {
        if (payload.type === "frame" && payload.data) {
          console.log("[ws] frame", payload.data);
          updateRealtime(payload.data as Parameters<typeof updateRealtime>[0]);
        } else if (payload.type === "alert" && payload.data) {
          const alertItem = payload.data as AlertItem;
          state.alertItems = [alertItem, ...state.alertItems].slice(0, 10);
          updateAlertCount();
          renderAlerts(state.alertItems);
        }
        return;
      }
      updateRealtime(payload as Parameters<typeof updateRealtime>[0]);
    } catch (error) {
      console.error("实时推送解析失败", error);
    }
  });
  ws.addEventListener("error", () => {
    updateSystemStatus("offline");
    if (state.realtimeSocket === ws) {
      scheduleRealtimeReconnect("error");
    }
  });
  ws.addEventListener("close", () => {
    if (state.realtimeSocket === ws) {
      updateSystemStatus("offline");
      scheduleRealtimeReconnect("close");
    }
  });
};

// connectAlerts 已移除 - 告警通过 realtime WebSocket 推送

const ensureSourceSelected = () => {
  if (state.sourceId) return true;
  alert("请先选择或上传数据源");
  return false;
};

const ensureHistorySourceSelected = () => {
  if (state.historySourceId) return true;
  alert("请先选择历史数据源");
  return false;
};

const handleApiError = (error: unknown) => {
  const message = error instanceof Error ? error.message : "请求失败";
  console.error(message);
  alert(message);
};

const loadSources = async () => {
  try {
    const data = await apiGet<{ sources?: SourceItem[] }>(`/sources`);
    const sources = data.sources || [];
    state.sourcesCache = sources;
    return sources;
  } catch (error) {
    console.error("数据源加载失败", error);
    return [];
  }
};

const refreshHistorySourceOptions = async () => {
  if (!ui.historySourceSelect) return;
  const sources = await loadSources();
  ui.historySourceSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "选择数据源";
  ui.historySourceSelect.appendChild(placeholder);
  sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source.source_id;
    option.textContent = source.name || source.source_id;
    ui.historySourceSelect.appendChild(option);
  });
  if (state.historySourceId) {
    ui.historySourceSelect.value = state.historySourceId;
  }
};

const refreshSourceOptions = async () => {
  if (!ui.sourceSelect) return;
  const sources = await loadSources();
  ui.sourceSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "选择数据源";
  ui.sourceSelect.appendChild(placeholder);
  sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source.source_id;
    option.textContent = source.name || source.source_id;
    ui.sourceSelect?.appendChild(option);
  });
  if (state.sourceId) {
    ui.sourceSelect.value = state.sourceId;
  }
};

const refreshHistoryRegionOptions = async () => {
  if (!ui.historyRegionSelect) return;
  ui.historyRegionSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "全部区域";
  ui.historyRegionSelect.appendChild(placeholder);
  if (!state.historySourceId) {
    ui.historyRegionSelect.value = "";
    state.historyRegions = [];
    return;
  }
  try {
    const data = await apiGet<{ regions?: RegionItem[] }>(
      `/regions?source_id=${encodeURIComponent(state.historySourceId)}`
    );
    state.historyRegions = data.regions || [];
    state.historyRegions.forEach((region) => {
      if (!region.region_id) return;
      if (region.name === "全部区域") return;
      const option = document.createElement("option");
      option.value = region.region_id;
      option.textContent = region.name || region.region_id;
      ui.historyRegionSelect?.appendChild(option);
    });
  } catch (error) {
    console.error("历史区域加载失败", error);
  }
  if (state.historyRegionId && ui.historyRegionSelect) {
    ui.historyRegionSelect.value = state.historyRegionId;
  } else {
    ui.historyRegionSelect.value = "";
  }
};

const populateHistoryMetricSelect = () => {
  if (!ui.historyMetricSelect) return;
  ui.historyMetricSelect.innerHTML = "";
  HISTORY_METRICS.forEach((metric) => {
    const option = document.createElement("option");
    option.value = metric.key;
    option.textContent = metric.label;
    ui.historyMetricSelect.appendChild(option);
  });
  ui.historyMetricSelect.value = state.historyMetric;
};

const loadRegions = async () => {
  if (!state.sourceId) return;
  try {
    const data = await apiGet<{ regions?: RegionItem[] }>(
      `/regions?source_id=${encodeURIComponent(state.sourceId)}`
    );
    state.regionConfigs = data.regions || [];
    updateRegions(
      state.regionConfigs.map((item) => ({
        name: item.name,
        count: item.count ?? 0,
        density: item.density ?? 0,
      }))
    );
    // 同步更新预警配置面板的区域阈值列表
    renderRegionThresholds();
  } catch (error) {
    console.error("区域配置加载失败", error);
  }
};

const renderHistoryList = (data: HistoryResponse) => {
  if (!ui.historyList) return;
  ui.historyList.innerHTML = "";

  const summaryRows: Array<{ label: string; value: string }> = [];
  const series = data.series || [];

  const totalCountAvg =
    Number.isFinite(data.total_count_avg) && data.total_count_avg !== undefined
      ? data.total_count_avg
      : average(toNumberArray(series.map((item) => item.total_count_avg)));
  const totalCountMax =
    Number.isFinite(data.total_count_max) && data.total_count_max !== undefined
      ? data.total_count_max
      : maxValue(toNumberArray(series.map((item) => item.total_count_max)));
  const totalCountMin =
    Number.isFinite(data.total_count_min) && data.total_count_min !== undefined
      ? data.total_count_min
      : minValue(toNumberArray(series.map((item) => item.total_count_min)));
  const totalDensityAvg =
    Number.isFinite(data.total_density_avg) && data.total_density_avg !== undefined
      ? data.total_density_avg
      : average(toNumberArray(series.map((item) => item.total_density_avg)));

  if (Number.isFinite(totalCountAvg)) {
    summaryRows.push({ label: "平均人数", value: formatCount(totalCountAvg) });
  }
  if (Number.isFinite(totalCountMax)) {
    summaryRows.push({ label: "最大人数", value: formatCount(totalCountMax) });
  }
  if (Number.isFinite(totalCountMin)) {
    summaryRows.push({ label: "最小人数", value: formatCount(totalCountMin) });
  }
  if (Number.isFinite(totalDensityAvg)) {
    summaryRows.push({ label: "平均密度", value: formatNumber(totalDensityAvg, 2) });
  }

  const regionAggregates: Record<
    string,
    {
      countSum: number;
      countCount: number;
      max?: number;
      min?: number;
      densitySum: number;
      densityCount: number;
    }
  > = {};

  series.forEach((item) => {
    if (!item.regions) return;
    Object.entries(item.regions).forEach(([regionId, stats]) => {
      if (!regionAggregates[regionId]) {
        regionAggregates[regionId] = {
          countSum: 0,
          countCount: 0,
          densitySum: 0,
          densityCount: 0,
        };
      }
      const aggregate = regionAggregates[regionId];
      if (Number.isFinite(stats.total_count_avg)) {
        aggregate.countSum += stats.total_count_avg!;
        aggregate.countCount += 1;
      }
      if (Number.isFinite(stats.total_count_max)) {
        aggregate.max =
          aggregate.max === undefined
            ? stats.total_count_max
            : Math.max(aggregate.max, stats.total_count_max!);
      }
      if (Number.isFinite(stats.total_count_min)) {
        aggregate.min =
          aggregate.min === undefined
            ? stats.total_count_min
            : Math.min(aggregate.min, stats.total_count_min!);
      }
      if (Number.isFinite(stats.total_density_avg)) {
        aggregate.densitySum += stats.total_density_avg!;
        aggregate.densityCount += 1;
      }
    });
  });

  if (summaryRows.length === 0 && Object.keys(regionAggregates).length === 0) {
    const empty = document.createElement("div");
    const time = document.createElement("strong");
    const text = document.createElement("span");
    time.textContent = "--:--";
    text.textContent = "暂无历史数据";
    empty.appendChild(time);
    empty.appendChild(text);
    ui.historyList.appendChild(empty);
    return;
  }

  summaryRows.forEach((item) => {
    const row = document.createElement("div");
    const label = document.createElement("strong");
    const text = document.createElement("span");
    label.textContent = item.label;
    text.textContent = item.value;
    row.appendChild(label);
    row.appendChild(text);
    ui.historyList.appendChild(row);
  });

  if (state.historyRegionId) {
    const regionNameMap = new Map<string, string>();
    state.historyRegions.forEach((item) => {
      if (item.region_id) {
        regionNameMap.set(item.region_id, item.name || item.region_id);
      }
    });
    Object.entries(regionAggregates).forEach(([regionId, stats]) => {
      if (regionId !== state.historyRegionId) {
        return;
      }
      const row = document.createElement("div");
      const label = document.createElement("strong");
      const text = document.createElement("span");
      const regionName =
        regionNameMap.get(regionId) || state.historyRegionName || regionId;
      label.textContent = regionName;
      const avg = stats.countCount ? stats.countSum / stats.countCount : undefined;
      const densityAvg =
        stats.densityCount && stats.densityCount > 0 ? stats.densitySum / stats.densityCount : undefined;
      const densityText = Number.isFinite(densityAvg)
        ? ` / 密度 ${formatNumber(densityAvg, 2)}`
        : "";
      text.textContent = `均值 ${formatCount(avg)} / 峰值 ${formatCount(
        stats.max
      )} / 最低 ${formatCount(stats.min)}${densityText}`;
      row.appendChild(label);
      row.appendChild(text);
      ui.historyList.appendChild(row);
    });
  }
};

const buildHistorySeries = (data: HistoryResponse): HistorySeriesPoint[] => {
  const series = data.series || [];
  const regionKey = state.historyRegionId || state.historyRegionName;
  return series.map((item) => {
    let value: number | undefined;
    if (regionKey && item.regions?.[regionKey]) {
      value = item.regions[regionKey][state.historyMetric];
    } else {
      value = item[state.historyMetric];
    }
    return {
      time: item.time,
      value: Number.isFinite(value) ? (value as number) : NaN,
    };
  });
};

const renderHistoryFromCache = () => {
  if (!state.historyData) {
    renderHistoryEmpty("请选择历史数据源");
    return;
  }
  renderHistoryList(state.historyData);
  const points = buildHistorySeries(state.historyData);
  const hasValid = points.some((point) => Number.isFinite(point.value));
  if (!hasValid) {
    renderHistoryEmpty("暂无历史趋势数据");
    return;
  }
  renderHistoryChart(state.historyMetric, points);
};

const loadHistory = async () => {
  if (!state.historySourceId) {
    if (ui.historyList) {
      ui.historyList.innerHTML = "";
      const empty = document.createElement("div");
      const time = document.createElement("strong");
      const text = document.createElement("span");
      time.textContent = "--:--";
      text.textContent = "请选择历史数据源";
      empty.appendChild(time);
      empty.appendChild(text);
      ui.historyList.appendChild(empty);
    }
    renderHistoryEmpty("请选择历史数据源");
    state.historyData = null;
    return;
  }
  try {
    const to = new Date();
    const from = new Date(to.getTime() - 30 * 60 * 1000);
    let url = `/history?source_id=${encodeURIComponent(state.historySourceId)}&from=${encodeURIComponent(
      from.toISOString()
    )}&to=${encodeURIComponent(to.toISOString())}&interval=${encodeURIComponent(
      state.historyInterval
    )}`;
    // 如果选择了区域，附加 region_id 参数
    if (state.historyRegionId) {
      url += `&region_id=${encodeURIComponent(state.historyRegionId)}`;
    }
    const data = await apiGet<HistoryResponse>(url);
    state.historyData = data;
    renderHistoryFromCache();
  } catch (error) {
    console.error("历史数据加载失败", error);
    renderHistoryEmpty("历史数据加载失败");
  }
};

const renderHistoryEmpty = (message: string) => {
  if (!state.historyChart) return;
  state.historyChart.clear();
  state.historyChart.setOption({
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { show: false },
    yAxis: { show: false },
    series: [],
    graphic: {
      type: "text",
      left: "center",
      top: "middle",
      style: {
        text: message,
        fill: "#7C8DA6",
        fontSize: 12,
      },
    },
  });
};

const renderHistoryChart = (metricKey: HistoryMetricKey, points: HistorySeriesPoint[]) => {
  if (!state.historyChart) return;
  const meta = getMetricMeta(metricKey);
  const sorted = [...points].sort(
    (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
  );
  const values = sorted.map((item) => item.value).filter((value) => Number.isFinite(value));
  if (!values.length) {
    renderHistoryEmpty("暂无历史数据");
    return;
  }

  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const yMax =
    meta.max ??
    (maxValue === minValue ? maxValue + 1 : Math.ceil(maxValue * 1.05 * 1000) / 1000);
  const yMin = meta.min ?? (minValue > 0 ? 0 : Math.floor(minValue * 0.95 * 1000) / 1000);

  state.historyChart.setOption({
    color: [meta.color],
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) =>
        `${formatMetricValue(metricKey, Number(value))}${meta.unit ? ` ${meta.unit}` : ""}`,
    },
    grid: { left: 20, right: 20, top: 18, bottom: 32, containLabel: true },
    xAxis: {
      type: "category",
      data: sorted.map((item) => item.time),
      axisLabel: {
        color: "#6F829B",
        formatter: formatHistoryTime,
      },
      axisLine: { lineStyle: { color: "rgba(59, 143, 246, 0.2)" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      min: yMin,
      max: yMax,
      name: meta.label,
      nameTextStyle: { color: "#8AA1C1", padding: [0, 0, 8, 0] },
      axisLabel: {
        color: "#6F829B",
        formatter: (value: number) => formatMetricValue(metricKey, value),
      },
      splitLine: { lineStyle: { color: "rgba(59, 143, 246, 0.12)" } },
    },
    series: [
      {
        name: meta.label,
        type: "line",
        data: sorted.map((item) => item.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        areaStyle: { color: meta.color, opacity: 0.18 },
      },
    ],
    graphic: [],
  });
};

const initHistoryChart = () => {
  if (!ui.historyChart) return;
  state.historyChart = echarts.init(ui.historyChart);
  renderHistoryEmpty("请选择历史数据源");
};

const loadRecentAlerts = async () => {
  if (!state.sourceId) return;
  try {
    const data = await apiGet<{ items?: AlertItem[] }>(
      `/alerts/recent?source_id=${encodeURIComponent(state.sourceId)}`
    );
    state.alertItems = data.items || [];
    updateAlertCount();
    renderAlerts(state.alertItems);
  } catch (error) {
    console.error("告警记录加载失败", error);
  }
};

const loadAnalysisStatus = async () => {
  if (!state.sourceId) return;
  try {
    const data = await apiGet<{ status?: string; progress?: number }>(
      `/analysis/status?source_id=${encodeURIComponent(state.sourceId)}`
    );
    if (data.status) {
      setAnalysisStatus(data.status, data.progress);
    }
  } catch (error) {
    console.error("状态查询失败", error);
  }
};

const startStatusPolling = () => {
  if (state.analysisStatusTimer) {
    window.clearInterval(state.analysisStatusTimer);
  }
  state.analysisStatusTimer = window.setInterval(loadAnalysisStatus, 5000);
};

const stopStatusPolling = () => {
  if (state.analysisStatusTimer) {
    window.clearInterval(state.analysisStatusTimer);
    state.analysisStatusTimer = null;
  }
};

const setHistoryMetric = (metricKey: HistoryMetricKey) => {
  state.historyMetric = metricKey;
  if (ui.historyMetricSelect) {
    ui.historyMetricSelect.value = metricKey;
  }
  renderHistoryFromCache();
};

const setHistoryInterval = (interval: "1m" | "5m" | "1h") => {
  state.historyInterval = interval;
  if (ui.historyIntervalSelect) {
    ui.historyIntervalSelect.value = interval;
  }
};

const parsePointsInput = (input: string) => {
  const parsed = JSON.parse(input);
  if (!Array.isArray(parsed)) {
    throw new Error("坐标格式必须是二维数组");
  }
  return parsed as number[][];
};

const promptRegionConfig = (existing?: RegionItem) => {
  const name = window.prompt("区域名称", existing?.name || "");
  if (!name) return null;
  const color = window.prompt("区域颜色（如 #3B8FF6）", existing?.color || "#3B8FF6");
  if (!color) return null;
  const defaultPoints = existing?.points ? JSON.stringify(existing.points) : "[[0,0],[100,0],[100,100],[0,100]]";
  const pointsInput = window.prompt("区域坐标（JSON 数组）", defaultPoints);
  if (!pointsInput) return null;
  try {
    const points = parsePointsInput(pointsInput);
    return { name, color, points };
  } catch (error) {
    alert("坐标格式有误，请输入合法的 JSON 数组");
    return null;
  }
};

// 停止分析任务
const stopAnalysis = async (): Promise<boolean> => {
  if (!state.sourceId || !state.isAnalysisRunning) return false;
  try {
    state.isAnalysisRunning = false;
    await apiPost(`/analysis/stop`, { source_id: state.sourceId });
    closeSocket(state.realtimeSocket);
    closeSocket(state.alertSocket);
    clearRealtimeReconnect();
    clearAlertReconnect();
    setAnalysisStatus("stopped");
    stopStatusPolling();
    return true;
  } catch (error) {
    console.error("停止分析失败", error);
    return false;
  }
};

// 开始分析任务
const startAnalysis = async (): Promise<boolean> => {
  if (!state.sourceId) return false;
  try {
    await apiPost(`/analysis/start`, { source_id: state.sourceId });
    state.isAnalysisRunning = true;
    connectRealtime(state.sourceId);
    // 加载历史告警（告警通过 realtime WebSocket 推送，无需单独连接）
    await loadRecentAlerts();
    setAnalysisStatus("running");
    startStatusPolling();
    return true;
  } catch (error) {
    state.isAnalysisRunning = false;
    console.error("开始分析失败", error);
    return false;
  }
};

// 如果分析正在运行，重启分析任务（用于区域变更后生效）
const restartAnalysisIfRunning = async (): Promise<void> => {
  if (!state.isAnalysisRunning) return;
  await stopAnalysis();
  // 短暂延迟确保后端已完全停止
  await new Promise((resolve) => setTimeout(resolve, 500));
  await startAnalysis();
};

const createRegion = async () => {
  if (!state.sourceId) return;
  const config = promptRegionConfig();
  if (!config) return;
  const wasRunning = state.isAnalysisRunning;
  if (wasRunning) {
    await stopAnalysis();
  }
  await apiPost(`/regions`, {
    source_id: state.sourceId,
    ...config,
  });
  await loadRegions();
  if (wasRunning) {
    await startAnalysis();
  }
};

const updateRegion = async (regionId: string) => {
  const existing = state.regionConfigs.find((item) => item.region_id === regionId);
  if (!existing) return;

  // 使用弹窗显示现有配置
  const formData = await showRegionModal("编辑区域", {
    name: existing.name,
    color: existing.color,
    count_warning: existing.count_warning,
    count_critical: existing.count_critical,
    density_warning: existing.density_warning,
    density_critical: existing.density_critical,
  });

  if (!formData) return;

  const wasRunning = state.isAnalysisRunning;
  if (wasRunning) {
    await stopAnalysis();
  }
  await apiRequest(`/regions/${encodeURIComponent(regionId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: formData.name,
      color: formData.color,
      count_warning: formData.count_warning,
      count_critical: formData.count_critical,
      density_warning: formData.density_warning,
      density_critical: formData.density_critical,
    }),
  });
  await loadRegions();
  if (wasRunning) {
    await startAnalysis();
  }
};

const deleteRegion = async (regionId: string) => {
  const confirmed = window.confirm("确定删除该区域？");
  if (!confirmed) return;
  const wasRunning = state.isAnalysisRunning;
  if (wasRunning) {
    await stopAnalysis();
  }
  await apiRequest(`/regions/${encodeURIComponent(regionId)}`, { method: "DELETE" });
  await loadRegions();
  if (wasRunning) {
    await startAnalysis();
  }
};

const applyRegionTemplate = async () => {
  if (!ensureSourceSelected()) return;
  await loadRegions();
  const templateId = ui.regionTemplateSelect?.value || "";
  if (!templateId) {
    alert("请选择区域模板");
    return;
  }
  const template = REGION_TEMPLATES.find((item) => item.id === templateId);
  if (!template) return;
  const hasExisting = state.regionConfigs.some((item) => item.region_id);
  if (hasExisting) {
    const confirmed = window.confirm("将覆盖当前区域配置，是否继续？");
    if (!confirmed) return;
  }
  const wasRunning = state.isAnalysisRunning;
  if (wasRunning) {
    await stopAnalysis();
  }
  // 删除现有区域
  for (const region of state.regionConfigs) {
    if (!region.region_id) continue;
    await apiRequest(`/regions/${encodeURIComponent(region.region_id)}`, { method: "DELETE" });
  }
  // 创建新区域
  for (const region of template.regions) {
    await apiPost(`/regions`, {
      source_id: state.sourceId,
      name: region.name,
      color: region.color,
      points: region.points,
    });
  }
  await loadRegions();
  if (wasRunning) {
    await startAnalysis();
  }
};

const setSource = (sourceId: string, name?: string, width?: number, height?: number) => {
  state.sourceId = sourceId;
  state.sourceName = name || null;
  state.videoWidth = width || null;
  state.videoHeight = height || null;
  updateSourceInfo(name || null);
  updateVideoAspectRatio();
  void loadRegions();
  void loadAnalysisStatus();
  void loadRecentAlerts();
  void refreshHistorySourceOptions();
  void refreshSourceOptions();
  if (ui.sourceSelect) {
    ui.sourceSelect.value = sourceId;
  }
};

const setHistorySource = (sourceId: string, name?: string) => {
  state.historySourceId = sourceId;
  state.historySourceName = name || sourceId;
  state.historyRegionId = null;
  state.historyRegionName = null;
  void loadHistory();
  void refreshHistoryRegionOptions();
  if (ui.historySourceSelect) {
    ui.historySourceSelect.value = sourceId;
  }
};

const loadThreshold = async () => {
  if (!state.sourceId) return;
  try {
    const data = await apiGet<Record<string, unknown>>(
      `/alerts/threshold?source_id=${encodeURIComponent(state.sourceId)}`
    );
    state.thresholdConfig = data;
    const value = data["total_warning_threshold"];
    if (ui.thresholdInput && typeof value === "number") {
      ui.thresholdInput.value = String(value);
      if (ui.thresholdValue) {
        ui.thresholdValue.textContent = `${value}%`;
      }
    }
  } catch (error) {
    console.error("阈值获取失败", error);
  }
};

const scheduleThresholdUpdate = (() => {
  let timer: number | null = null;
  return () => {
    if (!state.sourceId || !ui.thresholdInput) return;
    if (timer) {
      window.clearTimeout(timer);
    }
    timer = window.setTimeout(async () => {
      const value = Number(ui.thresholdInput?.value);
      const payload = {
        source_id: state.sourceId,
        total_warning_threshold: value,
        total_critical_threshold: state.thresholdConfig?.["total_critical_threshold"],
      };
      try {
        await apiPost(`/alerts/threshold`, payload);
      } catch (error) {
        console.error("阈值更新失败", error);
      }
    }, 400);
  };
})();

if (ui.thresholdInput) {
  ui.thresholdInput.addEventListener("input", scheduleThresholdUpdate);
}

const loadSystemStatus = async () => {
  try {
    const data = await apiGet<{ status?: string }>(`/status`);
    updateSystemStatus(data.status === "running" ? "online" : "offline");
  } catch (error) {
    updateSystemStatus("offline");
  }
};

loadSystemStatus();
populateHistoryMetricSelect();
initHistoryChart();
void refreshHistorySourceOptions();
void refreshSourceOptions();
setHistoryMetric(state.historyMetric);
setHistoryInterval(state.historyInterval);

if (ui.actionButtons.fullscreen) {
  ui.actionButtons.fullscreen.addEventListener("click", () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined);
      return;
    }
    document.documentElement.requestFullscreen().catch(() => undefined);
  });
}

if (ui.actionButtons.sourceCamera) {
  ui.actionButtons.sourceCamera.addEventListener("click", async () => {
    const url = window.prompt("请输入摄像头/推流地址", "rtsp://");
    if (!url) return;
    try {
      const data = await apiPost<SourceItem>(`/sources/stream`, {
        url,
        name: "摄像头",
      });
      setSource(data.source_id, data.name || "摄像头", data.video_width, data.video_height);
      await loadThreshold();
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.sourceUpload) {
  ui.actionButtons.sourceUpload.addEventListener("click", () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "video/*";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const data = await apiUpload(file) as SourceItem;
        setSource(data.source_id, data.name || file.name, data.video_width, data.video_height);
        await loadThreshold();
      } catch (error) {
        handleApiError(error);
      }
    };
    input.click();
  });
}

if (ui.sourceSelect) {
  ui.sourceSelect.addEventListener("change", () => {
    const selectedId = ui.sourceSelect?.value || "";
    if (!selectedId) {
      state.sourceId = null;
      state.sourceName = null;
      state.videoWidth = null;
      state.videoHeight = null;
      updateSourceInfo(null);
      updateVideoAspectRatio();
      closeSocket(state.realtimeSocket);
      closeSocket(state.alertSocket);
      clearRealtimeReconnect();
      clearAlertReconnect();
      state.isAnalysisRunning = false;
      setAnalysisStatus("idle");
      stopStatusPolling();
      return;
    }
    // 从缓存中查找完整的数据源信息
    const source = state.sourcesCache.find((s) => s.source_id === selectedId);
    const name = source?.name || ui.sourceSelect.selectedOptions[0]?.textContent?.trim() || selectedId;
    setSource(selectedId, name, source?.video_width, source?.video_height);
  });
}

if (ui.actionButtons.deleteSource) {
  ui.actionButtons.deleteSource.addEventListener("click", async () => {
    const selectedId = ui.sourceSelect?.value || state.sourceId || "";
    if (!selectedId) {
      alert("请先选择要删除的数据源");
      return;
    }
    const selectedName = ui.sourceSelect?.selectedOptions[0]?.textContent?.trim() || selectedId;
    const confirmed = window.confirm(`确定删除数据源「${selectedName}」？`);
    if (!confirmed) return;
    try {
      if (selectedId === state.sourceId) {
        state.isAnalysisRunning = false;
        try {
          await apiPost(`/analysis/stop`, { source_id: selectedId });
        } catch {
          // ignore stop errors to allow deletion
        }
        closeSocket(state.realtimeSocket);
        closeSocket(state.alertSocket);
        clearRealtimeReconnect();
        clearAlertReconnect();
        stopStatusPolling();
      }
      await apiRequest(`/sources/${encodeURIComponent(selectedId)}`, { method: "DELETE" });
      if (selectedId === state.sourceId) {
        state.sourceId = null;
        state.sourceName = null;
        updateSourceInfo(null);
        setAnalysisStatus("idle");
      }
      if (selectedId === state.historySourceId) {
        state.historySourceId = null;
        state.historySourceName = "未选择";
        state.historyRegionId = null;
        state.historyRegionName = null;
        state.historyData = null;
        if (ui.historySourceSelect) {
          ui.historySourceSelect.value = "";
        }
        if (ui.historyRegionSelect) {
          ui.historyRegionSelect.value = "";
        }
        renderHistoryEmpty("请选择历史数据源");
      }
      await refreshSourceOptions();
      await refreshHistorySourceOptions();
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.startAnalysis) {
  ui.actionButtons.startAnalysis.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    try {
      await apiPost(`/analysis/start`, { source_id: state.sourceId });
      state.isAnalysisRunning = true;
      connectRealtime(state.sourceId!);
      // 加载历史告警（告警通过 realtime WebSocket 推送，无需单独连接）
      await loadRecentAlerts();
      setAnalysisStatus("running");
      startStatusPolling();
    } catch (error) {
      state.isAnalysisRunning = false;
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.stopAnalysis) {
  ui.actionButtons.stopAnalysis.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    try {
      state.isAnalysisRunning = false;
      await apiPost(`/analysis/stop`, { source_id: state.sourceId });
      closeSocket(state.realtimeSocket);
      closeSocket(state.alertSocket);
      clearRealtimeReconnect();
      clearAlertReconnect();
      setAnalysisStatus("stopped");
      stopStatusPolling();
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.snapshot) {
  ui.actionButtons.snapshot.addEventListener("click", async () => {
    alert("截图功能暂未实现");
  });
}

if (ui.actionButtons.exportClip) {
  ui.actionButtons.exportClip.addEventListener("click", async () => {
    alert("导出片段功能暂未实现");
  });
}

if (ui.actionButtons.refreshHistory) {
  ui.actionButtons.refreshHistory.addEventListener("click", async () => {
    await loadHistory();
  });
}

if (ui.actionButtons.exportHistory) {
  ui.actionButtons.exportHistory.addEventListener("click", async () => {
    if (!ensureHistorySourceSelected()) return;
    const to = new Date();
    const from = new Date(to.getTime() - 30 * 60 * 1000);
    const format = ui.historyExportFormat?.value || "csv";
    try {
      const data = await apiGet<{ url?: string }>(
        `/export?source_id=${encodeURIComponent(state.historySourceId!)}&from=${encodeURIComponent(
          from.toISOString()
        )}&to=${encodeURIComponent(to.toISOString())}&format=${encodeURIComponent(format)}`
      );
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.exportAlerts) {
  ui.actionButtons.exportAlerts.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    const to = new Date();
    const from = new Date(to.getTime() - 24 * 60 * 60 * 1000);
    try {
      const data = await apiGet<{ url?: string }>(
        `/alerts/export?source_id=${encodeURIComponent(state.sourceId!)}&from=${encodeURIComponent(
          from.toISOString()
        )}&to=${encodeURIComponent(to.toISOString())}&format=csv`
      );
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.customRegions) {
  ui.actionButtons.customRegions.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    try {
      await loadRegions();
      alert("区域配置已刷新，可在列表中编辑或删除。");
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.addRegion) {
  ui.actionButtons.addRegion.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    // 使用棋盘点选方式新增区域
    openGridPicker();
  });
}

if (ui.actionButtons.applyRegionTemplate) {
  ui.actionButtons.applyRegionTemplate.addEventListener("click", async () => {
    try {
      await applyRegionTemplate();
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.historySourceSelect) {
  ui.historySourceSelect.addEventListener("change", async () => {
    const selectedId = ui.historySourceSelect?.value || "";
    if (!selectedId) {
      state.historySourceId = null;
      state.historySourceName = "未选择";
      state.historyRegionId = null;
      state.historyRegionName = null;
      state.historyRegions = [];
      if (ui.historyRegionSelect) {
        ui.historyRegionSelect.value = "";
      }
      await loadHistory();
      renderHistoryEmpty("请选择历史数据源");
      return;
    }
    const name = ui.historySourceSelect.selectedOptions[0]?.textContent?.trim();
    setHistorySource(selectedId, name || selectedId);
  });
}

if (ui.historyRegionSelect) {
  ui.historyRegionSelect.addEventListener("change", () => {
    const selectedId = ui.historyRegionSelect?.value || "";
    state.historyRegionId = selectedId || null;
    state.historyRegionName = selectedId
      ? ui.historyRegionSelect?.selectedOptions[0]?.textContent?.trim() || null
      : null;
    renderHistoryFromCache();
  });
}

if (ui.historyIntervalSelect) {
  ui.historyIntervalSelect.addEventListener("change", async () => {
    const value = ui.historyIntervalSelect?.value as "1m" | "5m" | "1h";
    setHistoryInterval(value || "1m");
    await loadHistory();
  });
}

if (ui.historyMetricSelect) {
  ui.historyMetricSelect.addEventListener("change", () => {
    const value = ui.historyMetricSelect?.value as HistoryMetricKey;
    if (!value) return;
    setHistoryMetric(value);
  });
}

if (ui.regionList) {
  ui.regionList.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const button = target.closest("button");
    if (!button) return;
    const regionId = button.dataset.regionId;
    if (!regionId) return;
    try {
      if (button.dataset.action === "edit-region") {
        await updateRegion(regionId);
      }
      if (button.dataset.action === "delete-region") {
        await deleteRegion(regionId);
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

// 预警配置面板区域阈值列表的编辑按钮事件
if (ui.regionThresholdList) {
  ui.regionThresholdList.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const button = target.closest("button");
    if (!button) return;
    const regionId = button.dataset.regionId;
    if (!regionId) return;
    try {
      if (button.dataset.action === "edit-region") {
        await updateRegion(regionId);
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

const dashboard = document.querySelector<HTMLElement>(".dashboard");

if (dashboard) {
  const panels = Array.from(dashboard.querySelectorAll<HTMLElement>(".panel"));
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

  const getPanelSpan = (panel: HTMLElement, name: string, fallback: number) => {
    const raw = window.getComputedStyle(panel).getPropertyValue(name).trim();
    const parsed = parseInt(raw, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const getGridMetrics = () => {
    const style = window.getComputedStyle(dashboard);
    const columnGap = parseFloat(style.columnGap) || 0;
    const rowGap = parseFloat(style.rowGap) || 0;
    const rowSize = parseFloat(style.getPropertyValue("--row-size")) || 140;
    const columns = style.gridTemplateColumns
      .split(" ")
      .map((value) => parseFloat(value))
      .filter((value) => Number.isFinite(value));
    const columnCount = columns.length || 12;
    const columnWidth =
      columns[0] || (dashboard.clientWidth - columnGap * (columnCount - 1)) / columnCount;

    return {
      columnCount,
      columnWidth,
      columnGap,
      rowGap,
      rowSize,
    };
  };

  const getPanelGridStart = (panel: HTMLElement, metrics: ReturnType<typeof getGridMetrics>) => {
    const panelRect = panel.getBoundingClientRect();
    const gridRect = dashboard.getBoundingClientRect();
    const colStep = metrics.columnWidth + metrics.columnGap;
    const rowStep = metrics.rowSize + metrics.rowGap;
    const colStart = clamp(Math.round((panelRect.left - gridRect.left) / colStep) + 1, 1, metrics.columnCount);
    const rowStart = Math.max(1, Math.round((panelRect.top - gridRect.top) / rowStep) + 1);

    return { colStart, rowStart };
  };

  const normalizePanelSpans = () => {
    const { columnCount, rowGap, rowSize } = getGridMetrics();
    const rowStep = rowSize + rowGap;
    const maxRowSpan = Math.max(1, Math.round((dashboard.scrollHeight + rowSize) / rowStep));

    panels.forEach((panel) => {
      const inlineCol = panel.style.getPropertyValue("--panel-col-span");
      const inlineRow = panel.style.getPropertyValue("--panel-row-span");
      const inlineColStart = panel.style.getPropertyValue("--panel-col-start");
      const inlineRowStart = panel.style.getPropertyValue("--panel-row-start");

      if (inlineCol || inlineColStart) {
        const currentSpan = inlineCol ? parseInt(inlineCol, 10) || 1 : getPanelSpan(panel, "--panel-col-span", 1);
        let colSpan = clamp(currentSpan, 1, columnCount);

        if (inlineColStart) {
          const currentStart = parseInt(inlineColStart, 10) || 1;
          const maxColStart = Math.max(1, columnCount - colSpan + 1);
          const colStart = clamp(currentStart, 1, maxColStart);
          panel.style.setProperty("--panel-col-start", `${colStart}`);
          colSpan = clamp(colSpan, 1, columnCount - colStart + 1);
        }

        panel.style.setProperty("--panel-col-span", `${colSpan}`);
      }

      if (inlineRow || inlineRowStart) {
        const currentSpan = inlineRow ? parseInt(inlineRow, 10) || 1 : getPanelSpan(panel, "--panel-row-span", 1);
        let rowSpan = clamp(currentSpan, 1, maxRowSpan);

        if (inlineRowStart) {
          const currentStart = parseInt(inlineRowStart, 10) || 1;
          const maxRowStart = Math.max(1, maxRowSpan - rowSpan + 1);
          const rowStart = clamp(currentStart, 1, maxRowStart);
          panel.style.setProperty("--panel-row-start", `${rowStart}`);
          rowSpan = clamp(rowSpan, 1, maxRowSpan - rowStart + 1);
        }

        panel.style.setProperty("--panel-row-span", `${rowSpan}`);
      }
    });
  };

  panels.forEach((panel) => {
    const handle = panel.querySelector(".panel-header");
    panel.querySelectorAll(".resize-handle").forEach((existing) => existing.remove());

    const resizeDirections = ["top", "right", "bottom", "left"];
    const resizeHandles = resizeDirections.map((direction) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "resize-handle";
      button.dataset.direction = direction;
      button.setAttribute("aria-label", "拉伸模块");
      panel.appendChild(button);
      return button;
    });

    panel.setAttribute("draggable", "false");

    if (handle) {
      const isInteractive = (target: EventTarget | null) =>
        target instanceof HTMLElement &&
        Boolean(target.closest("button, select, input, textarea, option, a"));

      const enableDrag = (event: PointerEvent) => {
        if (isInteractive(event.target)) return;
        panel.setAttribute("draggable", "true");
        panel.classList.add("drag-ready");
      };

      const disableDrag = () => {
        panel.setAttribute("draggable", "false");
        panel.classList.remove("drag-ready");
      };

      handle.addEventListener("pointerdown", enableDrag);
      handle.addEventListener("pointerup", disableDrag);
      handle.addEventListener("pointerleave", disableDrag);
      handle.addEventListener("pointercancel", disableDrag);
    }

    if (resizeHandles.length > 0) {
      resizeHandles.forEach((resizeHandle) => {
        resizeHandle.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          event.stopPropagation();
          resizeHandle.setPointerCapture(event.pointerId);
          panel.setAttribute("draggable", "false");
          panel.classList.remove("drag-ready");
          panel.classList.add("resizing");

          const direction = resizeHandle.dataset.direction || "right";
          const startX = event.clientX;
          const startY = event.clientY;
          const metrics = getGridMetrics();
          const rowStep = metrics.rowSize + metrics.rowGap;
          const colStep = metrics.columnWidth + metrics.columnGap;
          const startColSpan = getPanelSpan(panel, "--panel-col-span", 1);
          const startRowSpan = getPanelSpan(panel, "--panel-row-span", 1);
          const { colStart: computedColStart, rowStart: computedRowStart } = getPanelGridStart(panel, metrics);
          const inlineColStart = panel.style.getPropertyValue("--panel-col-start");
          const inlineRowStart = panel.style.getPropertyValue("--panel-row-start");
          const startColStart = inlineColStart ? parseInt(inlineColStart, 10) || computedColStart : computedColStart;
          const startRowStart = inlineRowStart ? parseInt(inlineRowStart, 10) || computedRowStart : computedRowStart;

          if (direction === "left") {
            panel.dataset.lockCol = "true";
          }
          if (direction === "top") {
            panel.dataset.lockRow = "true";
          }

          const onMove = (moveEvent: PointerEvent) => {
            let nextColSpan = startColSpan;
            let nextRowSpan = startRowSpan;
            let nextColStart = startColStart;
            let nextRowStart = startRowStart;
            const deltaCols = Math.round((moveEvent.clientX - startX) / colStep);
            const deltaRows = Math.round((moveEvent.clientY - startY) / rowStep);

            if (direction === "left") {
              nextColStart = clamp(startColStart + deltaCols, 1, startColStart + startColSpan - 1);
              nextColSpan = clamp(
                startColSpan - (nextColStart - startColStart),
                1,
                metrics.columnCount - nextColStart + 1
              );
            }

            if (direction === "right") {
              nextColSpan = clamp(startColSpan + deltaCols, 1, metrics.columnCount - startColStart + 1);
            }

            if (direction === "top") {
              const maxRowSpan = Math.max(1, Math.round((dashboard.scrollHeight + metrics.rowSize) / rowStep));
              nextRowStart = clamp(startRowStart + deltaRows, 1, startRowStart + startRowSpan - 1);
              nextRowSpan = clamp(startRowSpan - (nextRowStart - startRowStart), 1, maxRowSpan);
            }

            if (direction === "bottom") {
              const maxRowSpan = Math.max(1, Math.round((dashboard.scrollHeight + metrics.rowSize) / rowStep));
              nextRowSpan = clamp(startRowSpan + deltaRows, 1, maxRowSpan);
            }

            panel.style.setProperty("--panel-col-span", `${nextColSpan}`);
            panel.style.setProperty("--panel-row-span", `${nextRowSpan}`);

            if (panel.dataset.lockCol === "true" || inlineColStart) {
              panel.style.setProperty("--panel-col-start", `${nextColStart}`);
            }

            if (panel.dataset.lockRow === "true" || inlineRowStart) {
              panel.style.setProperty("--panel-row-start", `${nextRowStart}`);
            }
          };

          const onUp = () => {
            panel.classList.remove("resizing");
            resizeHandle.releasePointerCapture(event.pointerId);
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
            window.removeEventListener("pointercancel", onUp);
            normalizePanelSpans();
            state.historyChart?.resize();
          };

          window.addEventListener("pointermove", onMove);
          window.addEventListener("pointerup", onUp);
          window.addEventListener("pointercancel", onUp);
        });
      });
    }

    panel.addEventListener("dragstart", (event) => {
      if (!panel.classList.contains("drag-ready")) {
        event.preventDefault();
        return;
      }
      if (panel.dataset.lockCol === "true") {
        panel.style.removeProperty("--panel-col-start");
      }
      if (panel.dataset.lockRow === "true") {
        panel.style.removeProperty("--panel-row-start");
      }
      panel.classList.add("dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", "");
      }
    });

    panel.addEventListener("dragend", () => {
      panel.classList.remove("dragging");
      panel.classList.remove("drag-ready");
      panel.setAttribute("draggable", "false");

      if (panel.dataset.lockCol === "true" || panel.dataset.lockRow === "true") {
        requestAnimationFrame(() => {
          const metrics = getGridMetrics();
          const { colStart, rowStart } = getPanelGridStart(panel, metrics);
          if (panel.dataset.lockCol === "true") {
            panel.style.setProperty("--panel-col-start", `${colStart}`);
          }
          if (panel.dataset.lockRow === "true") {
            panel.style.setProperty("--panel-row-start", `${rowStart}`);
          }
          normalizePanelSpans();
          state.historyChart?.resize();
        });
      }
    });
  });

  dashboard.addEventListener("dragover", (event) => {
    event.preventDefault();
    const dragging = dashboard.querySelector(".panel.dragging");
    if (!dragging) return;

    const target = (event.target instanceof HTMLElement)
      ? event.target.closest(".panel")
      : null;

    if (!target || target === dragging) return;

    const rect = target.getBoundingClientRect();
    const insertBefore = event.clientY < rect.top + rect.height / 2;
    const anchor = insertBefore ? target : target.nextElementSibling;
    dashboard.insertBefore(dragging, anchor);
  });

  dashboard.addEventListener("drop", (event) => {
    event.preventDefault();
  });

  window.addEventListener("resize", () => {
    normalizePanelSpans();
    state.historyChart?.resize();
  });
}
