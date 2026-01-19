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
            <span class="meta-value status-online">在线</span>
          </div>
          <div class="meta-block">
            <span class="meta-label">当前时间</span>
            <span class="meta-value" data-time>--:--</span>
          </div>
          <button class="ghost-button" type="button">全屏</button>
        </div>
      </header>

      <main class="dashboard">
        <section class="panel live-panel" data-animate>
          <div class="panel-header">
            <div>
              <p class="panel-kicker">实时监控</p>
              <h2>主入口摄像头</h2>
            </div>
            <div class="panel-actions">
              <div class="chip-row">
                <span class="chip live">LIVE</span>
                <span class="chip">Cam-A03</span>
                <span class="chip">1080p · 26fps</span>
              </div>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="video-frame">
            <div class="video-grid"></div>
            <div class="video-overlay">
              <div class="overlay-card">
                <span>当前人数</span>
                <strong>128</strong>
                <em>+12% / 5分钟</em>
              </div>
              <div class="overlay-card">
                <span>密度等级</span>
                <strong>中等</strong>
                <em>阈值 70%</em>
              </div>
            </div>
            <div class="video-caption">检测框 · 区域划分 · 轨迹叠加</div>
          </div>
          <div class="control-row">
            <div class="source-selector">
              <button class="primary" type="button">摄像头</button>
              <button type="button">视频上传</button>
              <button type="button">历史回放</button>
            </div>
            <div class="action-set">
              <button class="ghost-button" type="button">截图</button>
              <button class="ghost-button" type="button">导出片段</button>
              <button class="primary" type="button">开始分析</button>
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
              <strong>128</strong>
              <em>峰值 162</em>
            </div>
            <div class="stat-card">
              <span>入场速度</span>
              <strong>41 人/分</strong>
              <em>趋势 ↑</em>
            </div>
            <div class="stat-card">
              <span>拥挤指数</span>
              <strong>0.68</strong>
              <em>稳定</em>
            </div>
            <div class="stat-card">
              <span>预警次数</span>
              <strong>2</strong>
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
              <button class="ghost-button" type="button">自定义分区</button>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="region-list">
            <div class="region-row">
              <div class="region-info">
                <span>前区</span>
                <strong>52 人</strong>
              </div>
              <div class="bar">
                <div class="bar-fill high" style="width: 78%"></div>
              </div>
              <em>拥挤</em>
            </div>
            <div class="region-row">
              <div class="region-info">
                <span>中区</span>
                <strong>41 人</strong>
              </div>
              <div class="bar">
                <div class="bar-fill mid" style="width: 55%"></div>
              </div>
              <em>正常</em>
            </div>
            <div class="region-row">
              <div class="region-info">
                <span>后区</span>
                <strong>35 人</strong>
              </div>
              <div class="bar">
                <div class="bar-fill low" style="width: 38%"></div>
              </div>
              <em>宽松</em>
            </div>
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
              <button class="ghost-button" type="button">导出 CSV</button>
              <button class="drag-handle" type="button" aria-label="拖拽模块">拖拽</button>
            </div>
          </div>
          <div class="history-content">
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
            <div class="history-list">
              <div>
                <strong>10:24</strong>
                <span>峰值 162 人，前区触发一次预警</span>
              </div>
              <div>
                <strong>10:12</strong>
                <span>入口速度提升 8%</span>
              </div>
              <div>
                <strong>09:58</strong>
                <span>中区密度下降至 0.52</span>
              </div>
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
            <div class="alert-feed">
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
            <button class="primary full" type="button">发送预警通知</button>
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

const rangeInput = document.querySelector("[data-range-input]");
const rangeValue = document.querySelector("[data-range-value]");

if (rangeInput && rangeValue) {
  rangeValue.textContent = `${rangeInput.value}%`;
  rangeInput.addEventListener("input", (event) => {
    const target = event.target;
    if (!target || !("value" in target)) return;
    rangeValue.textContent = `${target.value}%`;
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
