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
              <span>拥挤指数</span>
              <strong data-stat-index>--</strong>
              <em>稳定</em>
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
              <h2>密度阈值</h2>
            </div>
            <div class="panel-actions">
              <span class="badge warn">高风险模式</span>
              <button class="ghost-button" type="button" data-action="export-alerts">导出告警</button>
            </div>
          </div>
          <div class="alert-body">
            <div class="threshold">
              <label for="thresholdRange">当前阈值</label>
              <div class="range-row">
                <input id="thresholdRange" type="range" min="40" max="95" value="70" data-range-input />
                <span data-range-value>70%</span>
              </div>
            </div>
          <div class="alert-feed" data-alert-list>
              <div>
                <strong>10:27</strong>
                <span>前区密度 0.82，建议疏导</span>
              </div>
              <div>
                <strong>10:19</strong>
                <span>后区密度回落至 0.41</span>
              </div>
              <div>
                <strong>10:11</strong>
                <span>系统检测到高峰人流波动</span>
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
const HISTORY_METRICS = [
  { key: "total_count_avg", label: "平均人数", unit: "人", digits: 0, color: "#3B8FF6", min: 0 },
  { key: "total_count_max", label: "最大人数", unit: "人", digits: 0, color: "#5BC0EB", min: 0 },
  { key: "total_count_min", label: "最小人数", unit: "人", digits: 0, color: "#2F7DE1", min: 0 },
  { key: "total_density_avg", label: "平均密度", unit: "", digits: 3, color: "#6BB6FF", min: 0 },
  {
    key: "crowd_index_avg",
    label: "平均拥挤指数",
    unit: "",
    digits: 2,
    color: "#E46A5E",
    min: 0,
    max: 1,
  },
] as const;

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
};

type SourceItem = {
  source_id: string;
  name?: string;
  source_type?: string;
  status?: string;
  created_at?: string;
};

type HistoryMetric = typeof HISTORY_METRICS[number];
type HistoryMetricKey = HistoryMetric["key"];

type HistorySummary = {
  total_count_avg?: number;
  total_count_max?: number;
  total_count_min?: number;
  total_density_avg?: number;
  crowd_index_avg?: number;
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
  crowd_index_avg?: number;
  regions?: Record<
    string,
    {
      total_count_avg?: number;
      total_count_max?: number;
      total_count_min?: number;
      total_density_avg?: number;
      crowd_index_avg?: number;
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
};

const state = {
  sourceId: null as string | null,
  sourceName: null as string | null,
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

const formatRate = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "--";
  return `${Math.round(value!)} 人/分`;
};

const formatIndex = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "--";
  return value!.toFixed(2);
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

const getMetricMeta = (metricKey: HistoryMetricKey) =>
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
  if (value! >= 0.008) return "拥挤";
  if (value! >= 0.005) return "正常";
  return "宽松";
};

const getDensityClass = (value: number | undefined | null) => {
  if (!Number.isFinite(value)) return "low";
  if (value! >= 0.008) return "high";
  if (value! >= 0.005) return "mid";
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

const scheduleAlertReconnect = (reason: string) => {
  if (!state.isAnalysisRunning || !state.sourceId) return;
  if (state.alertReconnectTimer) return;
  const delay = getRetryDelay(state.alertRetryCount);
  console.warn(`[ws] alert reconnect in ${delay}ms (${reason})`);
  state.alertReconnectTimer = window.setTimeout(() => {
    state.alertReconnectTimer = null;
    state.alertRetryCount += 1;
    connectAlerts(state.sourceId!);
  }, delay);
};

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

const updateRegions = (regions: RegionItem[]) => {
  if (!ui.regionList) return;
  ui.regionList.innerHTML = "";
  if (!regions.length) {
    const empty = document.createElement("div");
    empty.className = "region-note";
    empty.textContent = "暂无区域数据";
    ui.regionList.appendChild(empty);
    return;
  }

  const densities = regions.map((item) => item.density || 0);
  const maxDensity = Math.max(...densities, 0.001);

  regions.forEach((region) => {
    const row = document.createElement("div");
    row.className = "region-row";

    const info = document.createElement("div");
    info.className = "region-info";

    const name = document.createElement("span");
    name.textContent = region.name || "区域";
    const count = document.createElement("strong");
    count.textContent = `${formatCount(region.count)} 人`;

    info.appendChild(name);
    info.appendChild(count);

    const bar = document.createElement("div");
    bar.className = "bar";
    const barFill = document.createElement("div");
    const densityValue = region.density || 0;
    barFill.className = `bar-fill ${getDensityClass(densityValue)}`;
    barFill.style.width = `${Math.min(100, Math.round((densityValue / maxDensity) * 100))}%`;
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
  crowd_index?: number;
}) => {
  const total = payload.total_count;
  const density = payload.total_density;
  const crowdIndex = payload.crowd_index;

  if (typeof payload.frame === "string" && ui.videoFrame) {
    const src = payload.frame.startsWith("data:")
      ? payload.frame
      : `data:image/jpeg;base64,${payload.frame}`;
    ui.videoFrame.src = src;
  }

  setText(ui.totalCount, formatCount(total));
  setText(ui.statTotal, formatCount(total));

  if (Number.isFinite(density)) {
    setText(ui.statEntry, formatNumber(density, 3));
  }

  if (Number.isFinite(crowdIndex)) {
    setText(ui.statIndex, formatIndex(crowdIndex));
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

const connectAlerts = (sourceId: string) => {
  clearAlertReconnect();
  closeSocket(state.alertSocket);
  state.alertItems = [];
  updateAlertCount();
  renderAlerts(state.alertItems);
  const ws = new WebSocket(getWsUrl(`${WS_BASE}/alerts`, { source_id: sourceId }));
  state.alertSocket = ws;

  ws.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data) as
        | { type?: string; data?: AlertItem; items?: AlertItem[] }
        | AlertItem;
      if (payload && typeof payload === "object" && "type" in payload && payload.type === "alert") {
        const item = payload.data;
        if (item) {
          state.alertItems = [item, ...state.alertItems].slice(0, 10);
        }
      } else if (Array.isArray(payload.items)) {
        state.alertItems = payload.items;
      } else if ("alert_id" in payload && payload.alert_id) {
        state.alertItems = [payload as AlertItem, ...state.alertItems].slice(0, 10);
      }
      updateAlertCount();
      renderAlerts(state.alertItems);
    } catch (error) {
      console.error("预警推送解析失败", error);
    }
  });
  ws.addEventListener("error", () => {
    if (state.alertSocket === ws) {
      scheduleAlertReconnect("error");
    }
  });
  ws.addEventListener("close", () => {
    if (state.alertSocket === ws) {
      scheduleAlertReconnect("close");
    }
  });
};

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
    return data.sources || [];
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
  const crowdIndexAvg =
    Number.isFinite(data.crowd_index_avg) && data.crowd_index_avg !== undefined
      ? data.crowd_index_avg
      : average(toNumberArray(series.map((item) => item.crowd_index_avg)));

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
    summaryRows.push({ label: "平均密度", value: formatNumber(totalDensityAvg, 3) });
  }
  if (Number.isFinite(crowdIndexAvg)) {
    summaryRows.push({ label: "平均拥挤指数", value: formatNumber(crowdIndexAvg, 2) });
  }

  const regionAggregates: Record<
    string,
    {
      countSum: number;
      countCount: number;
      max?: number;
      min?: number;
      crowdSum: number;
      crowdCount: number;
    }
  > = {};

  series.forEach((item) => {
    if (!item.regions) return;
    Object.entries(item.regions).forEach(([regionId, stats]) => {
      if (!regionAggregates[regionId]) {
        regionAggregates[regionId] = {
          countSum: 0,
          countCount: 0,
          crowdSum: 0,
          crowdCount: 0,
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
      if (Number.isFinite(stats.crowd_index_avg)) {
        aggregate.crowdSum += stats.crowd_index_avg!;
        aggregate.crowdCount += 1;
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
      const crowdIndex =
        stats.crowdCount && stats.crowdCount > 0 ? stats.crowdSum / stats.crowdCount : undefined;
      const crowdText = Number.isFinite(crowdIndex)
        ? ` / 拥挤指数 ${formatNumber(crowdIndex, 2)}`
        : "";
      text.textContent = `均值 ${formatCount(avg)} / 峰值 ${formatCount(
        stats.max
      )} / 最低 ${formatCount(stats.min)}${crowdText}`;
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

const createRegion = async () => {
  if (!state.sourceId) return;
  const config = promptRegionConfig();
  if (!config) return;
  await apiPost(`/regions`, {
    source_id: state.sourceId,
    ...config,
  });
  await loadRegions();
};

const updateRegion = async (regionId: string) => {
  const existing = state.regionConfigs.find((item) => item.region_id === regionId);
  const config = promptRegionConfig(existing);
  if (!config) return;
  await apiRequest(`/regions/${encodeURIComponent(regionId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  await loadRegions();
};

const deleteRegion = async (regionId: string) => {
  const confirmed = window.confirm("确定删除该区域？");
  if (!confirmed) return;
  await apiRequest(`/regions/${encodeURIComponent(regionId)}`, { method: "DELETE" });
  await loadRegions();
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
    for (const region of state.regionConfigs) {
      if (!region.region_id) continue;
      await apiRequest(`/regions/${encodeURIComponent(region.region_id)}`, { method: "DELETE" });
    }
  }
  for (const region of template.regions) {
    await apiPost(`/regions`, {
      source_id: state.sourceId,
      name: region.name,
      color: region.color,
      points: region.points,
    });
  }
  await loadRegions();
};

const setSource = (sourceId: string, name?: string) => {
  state.sourceId = sourceId;
  state.sourceName = name || null;
  updateSourceInfo(name || null);
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
      const data = await apiPost<{ source_id: string; name?: string }>(`/sources/stream`, {
        url,
        name: "摄像头",
      });
      setSource(data.source_id, data.name || "摄像头");
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
        const data = await apiUpload(file);
        setSource(data.source_id, data.name || file.name);
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
      updateSourceInfo(null);
      closeSocket(state.realtimeSocket);
      closeSocket(state.alertSocket);
      clearRealtimeReconnect();
      clearAlertReconnect();
      state.isAnalysisRunning = false;
      setAnalysisStatus("idle");
      stopStatusPolling();
      return;
    }
    const name = ui.sourceSelect.selectedOptions[0]?.textContent?.trim();
    setSource(selectedId, name || selectedId);
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
      connectAlerts(state.sourceId!);
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
    try {
      await createRegion();
    } catch (error) {
      handleApiError(error);
    }
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
