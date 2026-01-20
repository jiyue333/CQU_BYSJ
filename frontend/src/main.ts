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
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="video-frame">
            <div class="video-grid"></div>
            <img class="video-stream" data-video-frame alt="实时画面" />
            <div class="video-overlay">
              <div class="overlay-card">
                <span>当前人数</span>
                <strong data-total-count>--</strong>
                <em data-total-trend>--</em>
              </div>
              <div class="overlay-card">
                <span>密度等级</span>
                <strong data-density-level>--</strong>
                <em data-density-value>--</em>
              </div>
            </div>
            <div class="video-caption">检测框 · 区域划分 · 轨迹叠加</div>
          </div>
          <div class="control-row">
            <div class="source-selector">
              <button class="primary" type="button" data-action="source-camera">摄像头</button>
              <button type="button" data-action="source-upload">视频上传</button>
              <button type="button" data-action="source-history">历史回放</button>
            </div>
            <div class="action-set">
              <button class="ghost-button" type="button" data-action="snapshot">截图</button>
              <button class="ghost-button" type="button" data-action="export-clip">导出片段</button>
              <button class="primary" type="button" data-action="start-analysis">开始分析</button>
              <button class="ghost-button" type="button" data-action="stop-analysis">停止分析</button>
            </div>
          </div>
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
        </section>

        <section class="panel stat-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">核心指标</p>
              <h2>实时统计</h2>
            </div>
            <div class="panel-actions">
              <span class="badge">最近 10 秒更新</span>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="stat-grid">
            <div class="stat-card">
              <span>总人数</span>
              <strong data-stat-total>--</strong>
              <em>峰值 162</em>
            </div>
            <div class="stat-card">
              <span>入场速度</span>
              <strong data-stat-entry>--</strong>
              <em>趋势 ↑</em>
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
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
        </section>

        <section class="panel region-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">区域密度</p>
              <h2>前/中/后区对比</h2>
            </div>
            <div class="panel-actions">
              <button class="ghost-button" type="button" data-action="custom-regions">自定义分区</button>
              <button class="ghost-button" type="button" data-action="add-region">新增区域</button>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="region-list" data-region-list>
          </div>
          <div class="region-note">
            建议：前区人流密度接近预警阈值，建议引导分流。
          </div>
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
        </section>

        <section class="panel heatmap-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">密度热力图</p>
              <h2>空间分布</h2>
            </div>
            <div class="panel-actions">
              <div class="chip-row">
                <span class="chip">自动校准</span>
                <span class="chip">更新 2s</span>
              </div>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="heatmap">
            <div class="heat-row">
              <span class="heat-cell hot"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
            </div>
            <div class="heat-row">
              <span class="heat-cell hot"></span>
              <span class="heat-cell hot"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
            </div>
            <div class="heat-row">
              <span class="heat-cell warm"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
            </div>
            <div class="heat-row">
              <span class="heat-cell warm"></span>
              <span class="heat-cell warm"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
              <span class="heat-cell cool"></span>
            </div>
          </div>
          <div class="heatmap-legend">
            <span>低</span>
            <div class="legend-bar"></div>
            <span>高</span>
          </div>
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
        </section>

        <section class="panel history-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">历史趋势</p>
              <h2>近 30 分钟</h2>
            </div>
            <div class="panel-actions">
              <button class="ghost-button" type="button" data-action="refresh-history">刷新</button>
              <button class="ghost-button" type="button" data-action="export-csv">导出 CSV</button>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="history-content">
            <div class="source-manager">
              <div class="source-header">
                <span>数据源管理</span>
                <button class="ghost-button" type="button" data-action="refresh-sources">刷新</button>
              </div>
              <div class="source-list" data-source-list></div>
            </div>
            <svg viewBox="0 0 420 140" aria-label="历史趋势图" role="img">
              <polyline
                fill="none"
                stroke="var(--accent)"
                stroke-width="3"
                points="0,120 40,100 80,90 120,70 160,80 200,50 240,65 280,60 320,40 360,50 420,30"
              />
              <polyline
                fill="none"
                stroke="var(--accent-soft)"
                stroke-width="2"
                points="0,130 40,120 80,105 120,100 160,115 200,80 240,95 280,85 320,78 360,86 420,70"
              />
            </svg>
            <div class="history-list" data-history-list>
            </div>
          </div>
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
        </section>

        <section class="panel alert-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">预警配置</p>
              <h2>密度阈值</h2>
            </div>
            <div class="panel-actions">
              <span class="badge warn">高风险模式</span>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
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
          <button class="resize-handle" type="button" aria-label="拉伸模块"></button>
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

const ui = {
  systemStatus: document.querySelector<HTMLElement>("[data-system-status]"),
  sourceTitle: document.querySelector<HTMLElement>("[data-source-title]"),
  sourceName: document.querySelector<HTMLElement>("[data-source-name]"),
  sourceMeta: document.querySelector<HTMLElement>("[data-source-meta]"),
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
  sourceList: document.querySelector<HTMLElement>("[data-source-list]"),
  videoFrame: document.querySelector<HTMLImageElement>("[data-video-frame]"),
  thresholdInput,
  thresholdValue,
  actionButtons: {
    sourceCamera: document.querySelector<HTMLElement>("[data-action='source-camera']"),
    sourceUpload: document.querySelector<HTMLElement>("[data-action='source-upload']"),
    sourceHistory: document.querySelector<HTMLElement>("[data-action='source-history']"),
    startAnalysis: document.querySelector<HTMLElement>("[data-action='start-analysis']"),
    stopAnalysis: document.querySelector<HTMLElement>("[data-action='stop-analysis']"),
    refreshHistory: document.querySelector<HTMLElement>("[data-action='refresh-history']"),
    refreshSources: document.querySelector<HTMLElement>("[data-action='refresh-sources']"),
    exportCsv: document.querySelector<HTMLElement>("[data-action='export-csv']"),
    exportClip: document.querySelector<HTMLElement>("[data-action='export-clip']"),
    snapshot: document.querySelector<HTMLElement>("[data-action='snapshot']"),
    customRegions: document.querySelector<HTMLElement>("[data-action='custom-regions']"),
    addRegion: document.querySelector<HTMLElement>("[data-action='add-region']"),
    fullscreen: document.querySelector<HTMLElement>("[data-action='fullscreen']"),
  },
};

const state = {
  sourceId: null as string | null,
  sourceName: null as string | null,
  realtimeSocket: null as WebSocket | null,
  alertSocket: null as WebSocket | null,
  alertItems: [] as AlertItem[],
  thresholdConfig: null as Record<string, unknown> | null,
  regionConfigs: [] as RegionItem[],
  analysisStatusTimer: null as number | null,
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

const getWsUrl = (path: string, params: Record<string, string>) => {
  const url = new URL(path, window.location.origin);
  url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
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

    const label = document.createElement("em");
    label.textContent = getDensityLevel(densityValue);

    row.appendChild(info);
    row.appendChild(bar);
    row.appendChild(label);
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

  items.slice(0, 3).forEach((item) => {
    const row = document.createElement("div");
    const time = document.createElement("strong");
    const text = document.createElement("span");
    time.textContent = (item.timestamp || item.time || "--:--").slice(11, 16);
    text.textContent =
      item.message ||
      `${item.region_name || item.region || "区域"} ${item.level || ""}`.trim();
    row.appendChild(time);
    row.appendChild(text);
    ui.alertList.appendChild(row);
  });
};

const updateAlertCount = () => {
  setText(ui.statAlerts, `${state.alertItems.length}`);
};

const updateRealtime = (payload: {
  frame?: string;
  total_count?: number;
  total_density?: number;
  regions?: RegionItem[];
  crowd_index?: number;
  entry_speed?: number;
}) => {
  const total = payload.total_count;
  const density = payload.total_density;
  const entrySpeed = payload.entry_speed;
  const crowdIndex = payload.crowd_index;

  if (typeof payload.frame === "string" && ui.videoFrame) {
    const src = payload.frame.startsWith("data:")
      ? payload.frame
      : `data:image/jpeg;base64,${payload.frame}`;
    ui.videoFrame.src = src;
  }

  setText(ui.totalCount, formatCount(total));
  setText(ui.statTotal, formatCount(total));

  if (Number.isFinite(entrySpeed)) {
    const entryText = formatRate(entrySpeed);
    setText(ui.statEntry, entryText);
    setText(ui.totalTrend, `入口速度 ${entryText}`);
  }

  if (Number.isFinite(crowdIndex)) {
    setText(ui.statIndex, formatIndex(crowdIndex));
  }

  setText(ui.densityLevel, getDensityLevel(density));
  setText(ui.densityValue, Number.isFinite(density) ? `密度 ${formatNumber(density, 3)}` : "--");

  if (Array.isArray(payload.regions)) {
    updateRegions(payload.regions);
  }

};

const closeSocket = (socket: WebSocket | null) => {
  if (!socket) return;
  socket.close();
};

const connectRealtime = (sourceId: string) => {
  closeSocket(state.realtimeSocket);
  updateSystemStatus("connecting");
  const ws = new WebSocket(getWsUrl(`${WS_BASE}/realtime`, { source_id: sourceId }));
  state.realtimeSocket = ws;

  ws.addEventListener("open", () => updateSystemStatus("online"));
  ws.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data) as Record<string, unknown>;
      updateRealtime(payload as Parameters<typeof updateRealtime>[0]);
    } catch (error) {
      console.error("实时推送解析失败", error);
    }
  });
  ws.addEventListener("error", () => updateSystemStatus("offline"));
  ws.addEventListener("close", () => {
    if (state.realtimeSocket === ws) {
      updateSystemStatus("offline");
    }
  });
};

const connectAlerts = (sourceId: string) => {
  closeSocket(state.alertSocket);
  state.alertItems = [];
  updateAlertCount();
  renderAlerts(state.alertItems);
  const ws = new WebSocket(getWsUrl(`${WS_BASE}/alerts`, { source_id: sourceId }));
  state.alertSocket = ws;

  ws.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data) as { items?: AlertItem[] } & AlertItem;
      if (Array.isArray(payload.items)) {
        state.alertItems = payload.items;
      } else if (payload.alert_id) {
        state.alertItems = [payload, ...state.alertItems].slice(0, 10);
      }
      updateAlertCount();
      renderAlerts(state.alertItems);
    } catch (error) {
      console.error("预警推送解析失败", error);
    }
  });
};

const ensureSourceSelected = () => {
  if (state.sourceId) return true;
  alert("请先选择或上传数据源");
  return false;
};

const handleApiError = (error: unknown) => {
  const message = error instanceof Error ? error.message : "请求失败";
  console.error(message);
  alert(message);
};

const setSource = (sourceId: string, name?: string) => {
  state.sourceId = sourceId;
  state.sourceName = name || null;
  updateSourceInfo(name || null);
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

if (ui.actionButtons.sourceHistory) {
  ui.actionButtons.sourceHistory.addEventListener("click", async () => {
    try {
      const data = await apiGet<{ sources?: { source_id: string; name?: string }[] }>(`/sources`);
      const sources = data.sources || [];
      if (!sources.length) {
        alert("暂无可用数据源");
        return;
      }
      const options = sources
        .map((source, index) => `${index + 1}. ${source.name || source.source_id}`)
        .join("\n");
      const choice = window.prompt(`请选择数据源：\n${options}`, "1");
      if (!choice) return;
      const index = Number(choice) - 1;
      const selected = sources[index] || sources.find((item) => item.source_id === choice);
      if (!selected) {
        alert("选择无效");
        return;
      }
      setSource(selected.source_id, selected.name || "历史回放");
      await loadThreshold();
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
      connectRealtime(state.sourceId!);
      connectAlerts(state.sourceId!);
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.snapshot) {
  ui.actionButtons.snapshot.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    try {
      const data = await apiPost<{ url?: string }>(`/frame/snapshot`, { source_id: state.sourceId });
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.exportClip) {
  ui.actionButtons.exportClip.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    const to = new Date();
    const from = new Date(to.getTime() - 5 * 60 * 1000);
    try {
      const data = await apiPost<{ url?: string }>(`/clip/export`, {
        source_id: state.sourceId,
        from: from.toISOString(),
        to: to.toISOString(),
      });
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (error) {
      handleApiError(error);
    }
  });
}

if (ui.actionButtons.exportCsv) {
  ui.actionButtons.exportCsv.addEventListener("click", async () => {
    if (!ensureSourceSelected()) return;
    const to = new Date();
    const from = new Date(to.getTime() - 30 * 60 * 1000);
    try {
      const data = await apiGet<{ url?: string }>(
        `/export?source_id=${encodeURIComponent(state.sourceId!)}&from=${encodeURIComponent(
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
      await apiGet(`/regions?source_id=${encodeURIComponent(state.sourceId!)}`);
      alert("区域配置接口已触发，请在后端实现配置流程。");
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
    const handle = panel.querySelector(".drag-handle");
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
      const enableDrag = () => {
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

  window.addEventListener("resize", normalizePanelSpans);
}
