<template>
  <div class="console-shell">
    <aside class="nav-rail">
      <button class="brand-lockup" type="button" @click="scrollToSection('overview')">
        <span class="brand-lockup__mark">
          <IconSymbol name="overview" :size="18" />
        </span>
        <span class="brand-lockup__text">
          <strong>人流分析</strong>
        </span>
      </button>

      <nav class="nav-list" aria-label="页面导航">
        <button
          v-for="item in navigationItems"
          :key="item.key"
          class="nav-item"
          :class="{ 'is-active': activeSection === item.key }"
          type="button"
          @click="scrollToSection(item.key)"
        >
          <IconSymbol :name="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

    </aside>

    <div class="workspace">
      <header class="workspace-header">
        <div class="workspace-header__copy">
          <h1>人流分析</h1>
        </div>

        <div class="workspace-header__actions">
          <div class="status-chip" :data-tone="systemTone">
            <IconSymbol name="spark" :size="16" />
            <span>{{ systemStatusLabel }}</span>
          </div>
          <div class="status-chip">
            <IconSymbol name="clock" :size="16" />
            <span>{{ nowLabel }}</span>
          </div>
          <button class="button button--soft" type="button" @click="refreshDashboard">
            <IconSymbol name="refresh" :size="16" />
            <span>刷新</span>
          </button>
          <button class="button button--primary" type="button" @click="openConfigCenter()">
            <IconSymbol name="sliders" :size="16" />
            <span>配置中心</span>
          </button>
        </div>
      </header>

      <main class="workspace-content">
        <section ref="overviewSection" class="section-block">
          <div class="hero-grid">
            <article class="panel panel--hero">
              <div class="panel-head">
                <div>
                  <h3>{{ selectedSource?.name || "未接入数据源" }}</h3>
                </div>
                <div class="panel-head__actions panel-head__actions--hero">
                  <button class="source-trigger" type="button" @click="openSourcePicker">
                    <span class="source-trigger__main">
                      <span class="source-trigger__icon">
                        <IconSymbol :name="selectedSource?.source_type === 'stream' ? 'camera' : 'film'" :size="16" />
                      </span>
                      <span class="source-trigger__copy">
                        <strong>{{ selectedSource?.name || (sources.length ? "选择数据源" : "暂无数据源") }}</strong>
                      </span>
                    </span>
                    <IconSymbol name="chevron-down" :size="16" />
                  </button>
                  <button class="button button--ghost button--tiny" type="button" @click="openSourceModal('stream')">
                    <IconSymbol name="plus" :size="16" />
                    <span>新增</span>
                  </button>
                  <button
                    class="button button--ghost"
                    type="button"
                    :disabled="!selectedSource"
                    @click="openExportModal('history')"
                  >
                    <IconSymbol name="export" :size="16" />
                    <span>导出</span>
                  </button>
                </div>
              </div>

              <div class="video-stage" :class="{ 'is-empty': !frameSrc }" :style="videoStageStyle">
                <img v-if="frameSrc" :src="frameSrc" alt="实时监控画面" class="video-stage__frame" />
                <div class="video-stage__grid"></div>

                <div v-if="!frameSrc" class="video-stage__empty">
                  <span class="video-stage__empty-icon">
                    <IconSymbol name="camera" :size="28" />
                  </span>
                  <h4>{{ selectedSource ? "未开始分析" : "未接入数据源" }}</h4>
                </div>

                <div v-if="frameSrc" class="video-stage__footer">
                  <span class="soft-chip" :data-tone="densityTone">
                    <IconSymbol name="target" :size="14" />
                    <span>{{ densityLabel }}</span>
                  </span>
                  <span>{{ liveTimestampLabel }}</span>
                </div>
              </div>

              <div class="action-bar">
                <button
                  class="button button--primary"
                  type="button"
                  :disabled="!selectedSource || busy.analysis"
                  @click="startAnalysis"
                >
                  <IconSymbol name="play" :size="16" />
                  <span>{{ busy.analysis && analysisStatus !== 'running' ? "启动中..." : "开始分析" }}</span>
                </button>
                <button
                  class="button button--soft"
                  type="button"
                  :disabled="!selectedSource || analysisStatus !== 'running' || busy.analysis"
                  @click="stopAnalysis"
                >
                  <IconSymbol name="pause" :size="16" />
                  <span>{{ busy.analysis && analysisStatus === 'running' ? "停止中..." : "停止分析" }}</span>
                </button>
                <button
                  class="button button--ghost"
                  type="button"
                  :disabled="!selectedSource || selectedSource.source_type !== 'file'"
                  @click="openExportModal('clip')"
                >
                  <IconSymbol name="film" :size="16" />
                  <span>导出片段</span>
                </button>
                <button
                  class="button button--ghost button--danger"
                  type="button"
                  :disabled="!selectedSource"
                  @click="requestDeleteSource(selectedSource!)"
                >
                  <IconSymbol name="trash" :size="16" />
                  <span>删除当前源</span>
                </button>
              </div>
            </article>

            <article class="panel panel--insight panel--fill">
              <div class="panel-head">
                <div>
                  <h3>系统</h3>
                </div>
              </div>

              <div class="system-grid">
                <div class="system-card">
                  <span>在线源</span>
                  <strong>{{ systemStatus.active_sources }}/{{ sources.length }}</strong>
                </div>
                <div class="system-card">
                  <span>内存占用</span>
                  <strong>{{ formatPercent(systemStatus.memory_usage) }}</strong>
                </div>
                <div class="system-card">
                  <span>GPU 占用</span>
                  <strong>{{ formatPercent(systemStatus.gpu_usage) }}</strong>
                </div>
                <div class="system-card">
                  <span>运行时长</span>
                  <strong>{{ uptimeLabel }}</strong>
                </div>
              </div>

              <div class="insight-section">
                <div class="panel-head panel-head--compact">
                  <div>
                    <h3>区域</h3>
                  </div>
                  <button class="button button--ghost button--tiny" type="button" @click="openConfigCenter('regions')">
                    <IconSymbol name="sliders" :size="16" />
                    <span>配置</span>
                  </button>
                </div>

                <div v-if="regionSummaryRows.length" class="region-stack region-stack--hero">
                  <article
                    v-for="region in regionSummaryRows"
                    :key="region.region_id"
                    class="region-row"
                    :data-tone="region.tone"
                  >
                    <div class="region-row__meta">
                      <span class="region-swatch" :style="{ backgroundColor: region.color }"></span>
                      <div>
                        <strong>{{ region.name }}</strong>
                      </div>
                    </div>
                    <div class="region-row__stats">
                      <span>人数 {{ formatCount(region.count) }}</span>
                      <span>密度 {{ formatDecimal(region.density, 2) }} 人/m²</span>
                    </div>
                    <button class="icon-button" type="button" @click="openRegionModal(region)">
                      <IconSymbol name="edit" :size="16" />
                    </button>
                  </article>
                </div>
                <div v-else class="empty-box empty-box--fill">
                  <IconSymbol name="target" :size="18" />
                  <span>暂无区域</span>
                </div>
              </div>
            </article>
          </div>

              <div class="metric-grid">
                <article
                  v-for="card in summaryCards"
              :key="card.label"
              class="metric-card"
              :data-tone="card.tone"
            >
                <div class="metric-card__head">
                  <span class="metric-card__icon">
                    <IconSymbol :name="card.icon" :size="16" />
                  </span>
                  <span>{{ card.label }}</span>
                </div>
                <strong>{{ card.value }}</strong>
              </article>
            </div>
        </section>

        <section ref="historySection" class="section-block">
          <div class="section-caption">
            <div class="section-caption__title">
              <h2>趋势</h2>
              <span class="soft-chip">
                <IconSymbol name="history" :size="14" />
                <span>{{ historyWindowLabel(historyWindow) }} · {{ historyIntervalLabel(historyInterval) }}</span>
              </span>
            </div>
          </div>

          <div class="history-toolbar">
            <div class="toggle-group">
              <button
                v-for="item in windowOptions"
                :key="item.value"
                class="toggle-group__item"
                :class="{ 'is-active': historyWindow === item.value }"
                type="button"
                @click="historyWindow = item.value"
              >
                {{ item.label }}
              </button>
            </div>

            <div class="history-toolbar__filters">
              <select v-model="historyMetric" class="field field--select">
                <option v-for="metric in historyMetrics" :key="metric.key" :value="metric.key">
                  {{ metric.label }}
                </option>
              </select>

              <select v-model="historyInterval" class="field field--select">
                <option value="1m">1 分钟</option>
                <option value="5m">5 分钟</option>
                <option value="1h">1 小时</option>
              </select>

              <select v-model="historyRegionId" class="field field--select">
                <option value="all">全局汇总</option>
                <option v-for="region in regions" :key="region.region_id" :value="region.region_id">
                  {{ region.name }}
                </option>
              </select>
            </div>

            <button class="button button--soft" type="button" :disabled="busy.history" @click="refreshHistory()">
              <IconSymbol name="refresh" :size="16" />
              <span>{{ busy.history ? "刷新中..." : "刷新" }}</span>
            </button>
            <button class="button button--ghost" type="button" :disabled="!selectedSource" @click="openExportModal('history')">
              <IconSymbol name="export" :size="16" />
              <span>导出数据</span>
            </button>
          </div>

          <div class="history-grid">
            <article class="panel panel--chart">
              <div class="panel-head">
                <div>
                  <h3>{{ historyMetricMeta.label }}</h3>
                </div>
              </div>
              <div ref="historyChartRef" class="chart-surface"></div>
            </article>

            <article class="panel panel--fill panel--history-side">
              <div class="panel-head">
                <div>
                  <h3>摘要</h3>
                </div>
              </div>

              <div class="history-stat-grid">
                <div class="history-stat-card">
                  <span>最新</span>
                  <strong>{{ historyStatCards.latest }}</strong>
                </div>
                <div class="history-stat-card">
                  <span>最高</span>
                  <strong>{{ historyStatCards.max }}</strong>
                </div>
                <div class="history-stat-card">
                  <span>最低</span>
                  <strong>{{ historyStatCards.min }}</strong>
                </div>
                <div class="history-stat-card" :data-tone="historyTrendTone">
                  <span>波动</span>
                  <strong>{{ historyStatCards.delta }}</strong>
                </div>
              </div>

              <div v-if="historyRows.length" class="history-list">
                <article v-for="row in historyRows" :key="row.time" class="history-row">
                  <div>
                    <strong>{{ row.label }}</strong>
                    <small>{{ row.time }}</small>
                  </div>
                  <span>{{ row.value }}</span>
                </article>
              </div>
              <div v-else class="empty-box">
                <IconSymbol name="history" :size="18" />
                <span>暂无历史数据</span>
              </div>
            </article>
          </div>
        </section>

        <section ref="alertsSection" class="section-block">
          <div class="section-caption">
            <div class="section-caption__title">
              <h2>风险</h2>
              <span class="soft-chip" data-tone="danger">
                <IconSymbol name="warning" :size="14" />
                <span>最近 {{ recentAlerts.length }} 条</span>
              </span>
            </div>
          </div>

          <div class="alerts-grid">
            <article class="panel panel--fill panel--alerts-records">
              <div class="panel-head">
                <div>
                  <h3>记录</h3>
                </div>
                <button class="button button--ghost" type="button" :disabled="!selectedSource" @click="openExportModal('alerts')">
                  <IconSymbol name="export" :size="16" />
                  <span>导出记录</span>
                </button>
              </div>

              <div v-if="recentAlerts.length" class="alert-stack alert-stack--full stack-scroll">
                <article
                  v-for="alert in recentAlerts"
                  :key="alert.alert_id"
                  class="alert-row"
                  :data-tone="alertTone(alert.level)"
                >
                  <div class="alert-row__icon">
                    <IconSymbol name="warning" :size="16" />
                  </div>
                  <div class="alert-row__content">
                    <strong>{{ alert.region_name || "全局区域" }}</strong>
                    <p>{{ alert.message || alert.alert_type }}</p>
                    <small>{{ formatDateTime(alert.timestamp) }}</small>
                  </div>
                  <span class="alert-row__value">{{ alert.current_value }}/{{ alert.threshold }}</span>
                </article>
              </div>
              <div v-else class="empty-box">
                <IconSymbol name="check" :size="18" />
                <span>暂无告警记录</span>
              </div>
            </article>

            <article class="panel panel--fill panel--alerts-summary">
              <div class="alerts-summary-stack">
                <section class="alerts-summary-item" data-tone="danger">
                  <div class="metric-card__head">
                    <span class="metric-card__icon">
                      <IconSymbol name="warning" :size="16" />
                    </span>
                    <span>严重告警</span>
                  </div>
                  <strong>{{ criticalAlertCount }}</strong>
                </section>
                <section class="alerts-summary-item" data-tone="warning">
                  <div class="metric-card__head">
                    <span class="metric-card__icon">
                      <IconSymbol name="alert" :size="16" />
                    </span>
                    <span>普通告警</span>
                  </div>
                  <strong>{{ warningAlertCount }}</strong>
                </section>
                <section class="alerts-summary-item" data-tone="primary">
                  <div class="metric-card__head">
                    <span class="metric-card__icon">
                      <IconSymbol name="target" :size="16" />
                    </span>
                    <span>风险焦点</span>
                  </div>
                  <small>{{ hottestRegionHint }}</small>
                  <strong>{{ hottestRegionDisplayName }}</strong>
                </section>
                <section class="alerts-summary-item" data-tone="neutral">
                  <div class="metric-card__head">
                    <span class="metric-card__icon">
                      <IconSymbol name="clock" :size="16" />
                    </span>
                    <span>冷却时间</span>
                  </div>
                  <strong>{{ thresholdForm.cooldown }}s</strong>
                </section>
              </div>
            </article>
          </div>
        </section>
      </main>
    </div>

    <transition name="modal-fade">
      <div v-if="drawerOpen" class="modal-overlay modal-overlay--config" @click.self="drawerOpen = false">
        <aside class="config-drawer config-drawer--modal">
          <div class="config-drawer__header">
            <div>
              <span class="section-eyebrow">Config</span>
              <h2>配置中心</h2>
            </div>
            <button class="icon-button" type="button" @click="drawerOpen = false">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <div class="config-drawer__tabs toggle-group">
            <button
              v-for="item in configTabs"
              :key="item.key"
              class="toggle-group__item"
              :class="{ 'is-active': configSection === item.key }"
              type="button"
              @click="configSection = item.key"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="config-drawer__body">
        <section v-if="configSection === 'thresholds'" class="drawer-section">
          <div class="drawer-section__head">
            <div>
              <h3>总量阈值</h3>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-group">
              <span>总人数预警</span>
              <input v-model.number="thresholdForm.totalWarning" class="field" type="number" min="0" :disabled="!selectedSourceId" />
            </label>
            <label class="field-group">
              <span>总人数严重</span>
              <input v-model.number="thresholdForm.totalCritical" class="field" type="number" min="0" :disabled="!selectedSourceId" />
            </label>
            <label class="field-group">
              <span>区域默认预警</span>
              <input v-model.number="thresholdForm.regionWarning" class="field" type="number" min="0" :disabled="!selectedSourceId" />
            </label>
            <label class="field-group">
              <span>区域默认严重</span>
              <input v-model.number="thresholdForm.regionCritical" class="field" type="number" min="0" :disabled="!selectedSourceId" />
            </label>
            <label class="field-group">
              <span>冷却时间（秒）</span>
              <input v-model.number="thresholdForm.cooldown" class="field" type="number" min="0" :disabled="!selectedSourceId" />
            </label>
          </div>

          <button
            class="button button--primary button--full"
            type="button"
            :disabled="!selectedSourceId || busy.thresholds"
            @click="saveThresholds"
          >
            <IconSymbol name="save" :size="16" />
            <span>{{ busy.thresholds ? "保存中..." : "保存阈值" }}</span>
          </button>
        </section>

        <section v-else-if="configSection === 'layouts'" class="drawer-section">
          <div class="drawer-section__head">
            <div>
              <h3>布局模板</h3>
            </div>
          </div>

          <div class="template-stack">
            <article v-for="layout in regionLayouts" :key="layout.id" class="template-card">
              <div>
                <strong>{{ layout.label }}</strong>
              </div>
              <button
                class="button button--ghost button--tiny"
                type="button"
                :disabled="!selectedSourceId || busy.template"
                @click="requestApplyLayout(layout.id)"
              >
                <IconSymbol name="target" :size="14" />
                <span>应用</span>
              </button>
            </article>
          </div>
        </section>

        <section v-else class="drawer-section">
          <div class="drawer-section__head">
            <div>
              <h3>区域列表</h3>
            </div>
            <button class="button button--soft button--tiny" type="button" @click="openRegionModal()">
              <IconSymbol name="plus" :size="14" />
              <span>新增</span>
            </button>
          </div>

          <div v-if="regions.length" class="drawer-region-stack">
            <article v-for="region in regionSummaryRows" :key="region.region_id" class="drawer-region-card">
              <div class="drawer-region-card__main">
                <span class="region-swatch" :style="{ backgroundColor: region.color }"></span>
                <div>
                  <strong>{{ region.name }}</strong>
                  <small>{{ region.thresholdText }}</small>
                </div>
              </div>
              <div class="drawer-region-card__actions">
                <button class="icon-button" type="button" @click="openRegionModal(region)">
                  <IconSymbol name="edit" :size="16" />
                </button>
                <button class="icon-button icon-button--danger" type="button" @click="requestDeleteRegion(region)">
                  <IconSymbol name="trash" :size="16" />
                </button>
              </div>
            </article>
          </div>
          <div v-else class="empty-box empty-box--drawer">
            <IconSymbol name="target" :size="16" />
            <span>暂无区域</span>
          </div>
        </section>
          </div>
        </aside>
      </div>
    </transition>

    <transition-group name="toast" tag="div" class="toast-stack" aria-live="polite">
      <article v-for="toast in toasts" :key="toast.id" class="toast-card" :data-tone="toast.tone">
        <span class="toast-card__icon">
          <IconSymbol :name="toast.tone === 'success' ? 'check' : toast.tone === 'info' ? 'spark' : 'warning'" :size="14" />
        </span>
        <span>{{ toast.message }}</span>
        <button class="icon-button" type="button" @click="removeToast(toast.id)">
          <IconSymbol name="close" :size="14" />
        </button>
      </article>
    </transition-group>

    <transition name="modal-fade">
      <div v-if="sourcePickerOpen" class="modal-overlay" @click.self="closeSourcePicker">
        <div class="modal-card modal-card--picker">
          <div class="modal-head">
            <div>
              <span class="section-eyebrow">Source</span>
              <h3>选择数据源</h3>
            </div>
            <button class="icon-button" type="button" @click="closeSourcePicker">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <div v-if="sources.length" class="source-stack source-stack--picker">
            <button
              v-for="source in sources"
              :key="source.source_id"
              class="source-card source-card--picker"
              :class="{ 'is-active': source.source_id === selectedSourceId }"
              type="button"
              @click="selectSourceFromPicker(source.source_id)"
            >
              <div class="source-card__main">
                <span class="source-card__icon">
                  <IconSymbol :name="source.source_type === 'stream' ? 'camera' : 'film'" :size="16" />
                </span>
                <span class="source-card__copy">
                  <strong>{{ source.name }}</strong>
                  <small>{{ formatSourceMeta(source) }}</small>
                </span>
              </div>
              <span v-if="source.source_id === selectedSourceId" class="soft-chip soft-chip--selected">
                <IconSymbol name="check" :size="14" />
                <span>当前</span>
              </span>
            </button>
          </div>
          <div v-else class="empty-box">
            <IconSymbol name="source" :size="18" />
            <span>暂无数据源</span>
          </div>

          <div class="modal-actions">
            <button class="button button--soft" type="button" @click="closeSourcePicker">关闭</button>
            <button class="button button--primary" type="button" @click="openSourceModal('stream')">
              <IconSymbol name="plus" :size="16" />
              <span>新增数据源</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="modal-fade">
      <div v-if="sourceModal.open" class="modal-overlay" @click.self="closeSourceModal">
        <div class="modal-card">
          <div class="modal-head">
            <div>
              <span class="section-eyebrow">Source</span>
              <h3>添加数据源</h3>
            </div>
            <button class="icon-button" type="button" @click="closeSourceModal">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <div class="toggle-group toggle-group--modal">
            <button
              class="toggle-group__item"
              :class="{ 'is-active': sourceModal.mode === 'stream' }"
              type="button"
              @click="sourceModal.mode = 'stream'"
            >
              流地址
            </button>
            <button
              class="toggle-group__item"
              :class="{ 'is-active': sourceModal.mode === 'upload' }"
              type="button"
              @click="sourceModal.mode = 'upload'"
            >
              上传视频
            </button>
          </div>

          <div v-if="sourceModal.mode === 'stream'" class="form-grid">
            <label class="field-group">
              <span>数据源名称</span>
              <input v-model.trim="sourceModal.name" class="field" type="text" placeholder="例如：主入口摄像头" />
            </label>
            <label class="field-group">
              <span>流地址</span>
              <input v-model.trim="sourceModal.url" class="field" type="text" placeholder="rtsp:// 或 http:// ..." />
            </label>
          </div>

          <div v-else class="form-grid">
            <label class="field-group">
              <span>选择视频文件</span>
              <input
                ref="fileInputRef"
                class="field"
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.flv,video/*"
                @change="handleSourceFileChange"
              />
            </label>
            <div v-if="sourceModal.file" class="drawer-note">{{ sourceModal.file.name }}</div>
          </div>

          <div class="modal-actions">
            <button class="button button--soft" type="button" @click="closeSourceModal">取消</button>
            <button class="button button--primary" type="button" :disabled="busy.sourceSubmit" @click="submitSourceModal">
              <IconSymbol :name="sourceModal.mode === 'stream' ? 'camera' : 'upload'" :size="16" />
              <span>{{ busy.sourceSubmit ? "处理中..." : sourceModal.mode === 'stream' ? "接入数据源" : "上传并创建" }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="modal-fade">
      <div v-if="regionModal.open" class="modal-overlay" @click.self="closeRegionModal">
        <div class="modal-card modal-card--region">
          <div class="modal-head">
            <div>
              <span class="section-eyebrow">Region</span>
              <h3>{{ regionModal.regionId ? "编辑区域" : "新增区域" }}</h3>
            </div>
            <button class="icon-button" type="button" @click="closeRegionModal">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <div class="region-editor">
            <section class="region-editor__stage-panel">
              <div class="region-editor__toolbar">
                <div class="toggle-group">
                  <button
                    class="toggle-group__item"
                    :class="{ 'is-active': regionEditor.tool === 'polygon' }"
                    type="button"
                    @click="setRegionEditorTool('polygon')"
                  >
                    多边形
                  </button>
                  <button
                    class="toggle-group__item"
                    :class="{ 'is-active': regionEditor.tool === 'rectangle' }"
                    type="button"
                    @click="setRegionEditorTool('rectangle')"
                  >
                    矩形
                  </button>
                </div>

                <div class="region-editor__toolbar-actions">
                  <button
                    class="button button--ghost button--tiny"
                    type="button"
                    :disabled="!regionEditor.points.length"
                    @click="undoRegionPoint"
                  >
                    撤销一点
                  </button>
                  <button
                    class="button button--ghost button--tiny"
                    type="button"
                    :disabled="!regionEditor.points.length"
                    @click="clearRegionEditor"
                  >
                    清空
                  </button>
                  <button
                    class="button button--soft button--tiny"
                    type="button"
                    :disabled="regionEditor.points.length < 3 || regionEditor.isClosed"
                    @click="finishPolygon"
                  >
                    完成闭合
                  </button>
                </div>
              </div>

              <div class="region-editor__quick-row">
                <span class="region-editor__quick-label">快捷区域</span>
                <button
                  v-for="preset in regionPresets"
                  :key="preset.id"
                  class="button button--ghost button--tiny"
                  type="button"
                  @click="applyRegionPreset(preset.id)"
                >
                  {{ preset.label }}
                </button>
              </div>

              <div
                ref="regionStageRef"
                class="region-editor__stage"
                :class="{ 'is-empty': !frameSrc }"
                @click="handleRegionStageClick"
                @dblclick.prevent="handleRegionStageDoubleClick"
                @pointerdown="handleRegionStagePointerDown"
                @pointermove="handleRegionStagePointerMove"
                @pointerleave="handleRegionStagePointerLeave"
              >
                <img v-if="frameSrc" :src="frameSrc" alt="区域编辑预览画面" class="region-editor__frame" />
                <div class="video-stage__grid region-editor__grid"></div>

                <div v-if="!frameSrc" class="region-editor__fallback">
                  <span class="video-stage__empty-icon">
                    <IconSymbol name="camera" :size="28" />
                  </span>
                  <div>
                    <strong>等待画面</strong>
                    <small>没有实时帧时，仍可按比例预设区域。</small>
                  </div>
                </div>

                <svg class="region-editor__overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                  <g v-for="region in regionEditorReferenceRegions" :key="region.region_id">
                    <polygon
                      :points="toSvgPoints(region.points)"
                      class="region-editor__reference"
                      :style="{ fill: region.color, stroke: region.color }"
                    />
                  </g>

                  <polygon
                    v-if="regionEditor.points.length >= 3"
                    :points="regionEditorPolygonPoints"
                    class="region-editor__draft-fill"
                    :class="{ 'is-closed': regionEditor.isClosed }"
                    :style="{ fill: regionModal.color, stroke: regionModal.color }"
                    @pointerdown.stop="startRegionPolygonDrag"
                  />

                  <polyline
                    v-if="regionEditorPreviewPoints"
                    :points="regionEditorPreviewPoints"
                    class="region-editor__draft-line"
                    :style="{ stroke: regionModal.color }"
                  />
                </svg>

                <button
                  v-for="(point, index) in regionEditor.points"
                  :key="`${index}-${point[0]}-${point[1]}`"
                  class="region-editor__handle"
                  :class="{
                    'is-first': index === 0 && !regionEditor.isClosed && regionEditor.points.length >= 3,
                    'is-active': regionDrag.mode === 'vertex' && regionDrag.index === index,
                  }"
                  type="button"
                  :style="regionHandleStyle(point)"
                  @pointerdown.stop="startRegionHandleDrag(index, $event)"
                >
                  <span class="sr-only">编辑第 {{ index + 1 }} 个顶点</span>
                </button>
              </div>

              <div class="region-editor__stage-meta">
                <span>{{ regionEditorHint }}</span>
                <span>{{ regionEditorStatus }}</span>
              </div>
            </section>

            <aside class="region-editor__sidebar">
              <div class="form-grid form-grid--double">
                <label class="field-group">
                  <span>区域名称</span>
                  <input v-model.trim="regionModal.name" class="field" type="text" placeholder="例如：入口通道" />
                </label>
                <label class="field-group">
                  <span>颜色</span>
                  <input v-model="regionModal.color" class="field field--color" type="color" />
                </label>
              </div>

              <div class="region-editor__summary">
                <span class="soft-chip">
                  <IconSymbol name="target" :size="14" />
                  <span>{{ regionEditor.points.length }} 个顶点</span>
                </span>
                <span class="soft-chip" :data-tone="regionEditor.isClosed ? 'success' : 'warning'">
                  <IconSymbol :name="regionEditor.isClosed ? 'check' : 'warning'" :size="14" />
                  <span>{{ regionEditor.isClosed ? "已闭合" : "待闭合" }}</span>
                </span>
              </div>

              <div class="form-grid form-grid--double">
                <label class="field-group">
                  <span>人数预警</span>
                  <input v-model="regionModal.countWarning" class="field" type="number" min="0" />
                </label>
                <label class="field-group">
                  <span>人数严重</span>
                  <input v-model="regionModal.countCritical" class="field" type="number" min="0" />
                </label>
                <label class="field-group">
                  <span>密度预警 (人/m²)</span>
                  <input v-model="regionModal.densityWarning" class="field" type="number" min="0" step="0.1" placeholder="如 2.0" />
                </label>
                <label class="field-group">
                  <span>密度严重 (人/m²)</span>
                  <input v-model="regionModal.densityCritical" class="field" type="number" min="0" step="0.1" placeholder="如 4.0" />
                </label>
              </div>

              <div class="region-editor__advanced">
                <div class="region-editor__advanced-head">
                  <div>
                    <strong>高级设置</strong>
                    <small>仅在需要精修时编辑坐标 JSON。</small>
                  </div>
                  <button class="button button--ghost button--tiny" type="button" @click="regionModal.showAdvanced = !regionModal.showAdvanced">
                    {{ regionModal.showAdvanced ? "收起" : "展开" }}
                  </button>
                </div>

                <div v-if="regionModal.showAdvanced" class="region-editor__advanced-body">
                  <label class="field-group">
                    <span>坐标点（0-100 百分比）</span>
                    <textarea v-model="regionModal.pointsText" class="field field--textarea" rows="8"></textarea>
                  </label>
                  <button class="button button--soft button--tiny" type="button" @click="applyRegionTextToCanvas">
                    更新画布
                  </button>
                </div>
              </div>
            </aside>
          </div>

          <div class="modal-actions">
            <button class="button button--soft" type="button" @click="closeRegionModal">取消</button>
            <button class="button button--primary" type="button" :disabled="busy.regionSubmit" @click="submitRegionModal">
              <IconSymbol name="save" :size="16" />
              <span>{{ busy.regionSubmit ? "保存中..." : "保存区域" }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="modal-fade">
      <div v-if="exportModal.open" class="modal-overlay" @click.self="closeExportModal">
        <div class="modal-card">
          <div class="modal-head">
            <div>
              <span class="section-eyebrow">Export</span>
              <h3>{{ exportTitle }}</h3>
            </div>
            <button class="icon-button" type="button" @click="closeExportModal">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <div v-if="exportModal.kind !== 'clip'" class="form-grid">
            <label class="field-group">
              <span>时间范围</span>
              <select v-model="exportModal.range" class="field field--select">
                <option v-for="item in windowOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </option>
              </select>
            </label>
            <label class="field-group">
              <span>导出格式</span>
              <select v-model="exportModal.format" class="field field--select">
                <option value="csv">CSV</option>
                <option value="xlsx">XLSX</option>
              </select>
            </label>
          </div>
          <div class="modal-actions">
            <button class="button button--soft" type="button" @click="closeExportModal">取消</button>
            <button class="button button--primary" type="button" :disabled="busy.exportSubmit" @click="submitExportModal">
              <IconSymbol name="export" :size="16" />
              <span>{{ busy.exportSubmit ? "导出中..." : "开始导出" }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="modal-fade">
      <div v-if="confirmDialog.open" class="modal-overlay" @click.self="closeConfirmDialog">
        <div class="modal-card modal-card--confirm" :data-tone="confirmDialog.tone">
          <div class="modal-head">
            <div>
              <span class="section-eyebrow">Confirm</span>
              <h3>{{ confirmDialog.title }}</h3>
            </div>
            <button class="icon-button" type="button" @click="closeConfirmDialog">
              <IconSymbol name="close" :size="16" />
            </button>
          </div>

          <p class="confirm-copy">{{ confirmDialog.message }}</p>

          <div class="modal-actions">
            <button class="button button--soft" type="button" @click="closeConfirmDialog">取消</button>
            <button class="button button--primary" type="button" :disabled="confirmDialog.pending" @click="runConfirmAction">
              <IconSymbol name="warning" :size="16" />
              <span>{{ confirmDialog.pending ? "处理中..." : confirmDialog.actionLabel }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import {
  computed,
  defineComponent,
  h,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { apiDelete, apiGet, apiPost, apiPut, apiUpload, buildWsUrl, resolveAssetUrl } from "@/api";
import type {
  AlertRecentItem,
  AlertRecentResponse,
  AlertThresholdConfig,
  AnalysisStatusValue,
  HistoryMetricKey,
  HistoryResponse,
  HistorySeriesItem,
  Region,
  RegionListResponse,
  RealtimeFrame,
  SocketEnvelope,
  SourceListResponse,
  SystemStatus,
  VideoSource,
} from "@/types";

type SectionKey = "overview" | "history" | "alerts";
type ToastTone = "info" | "success" | "warning" | "error";
type SourceModalMode = "stream" | "upload";
type ExportKind = "history" | "alerts" | "clip";
type HistoryWindow = "30m" | "6h" | "24h";
type HistoryInterval = "1m" | "5m" | "1h";
type ConfigSection = "thresholds" | "layouts" | "regions";
type RegionEditorTool = "polygon" | "rectangle";
type RegionPoint = [number, number];
type RegionDragMode = "none" | "vertex" | "shape" | "rectangle";

type RegionDraft = {
  name: string;
  color: string;
  points: number[][];
  count_warning: number | null;
  count_critical: number | null;
  density_warning: number | null;
  density_critical: number | null;
};

const navigationItems: Array<{ key: SectionKey; label: string; icon: string }> = [
  { key: "overview", label: "总览", icon: "overview" },
  { key: "history", label: "趋势", icon: "history" },
  { key: "alerts", label: "风险", icon: "alert" },
];

const historyMetrics = [
  { key: "total_count_avg", label: "平均人数", digits: 0, color: "#2563EB" },
  { key: "total_count_max", label: "峰值人数", digits: 0, color: "#2563EB" },
  { key: "total_count_min", label: "最低人数", digits: 0, color: "#0F766E" },
  { key: "total_density_avg", label: "平均密度 (人/m²)", digits: 2, color: "#F97316" },
] as const satisfies ReadonlyArray<{
  key: HistoryMetricKey;
  label: string;
  digits: number;
  color: string;
}>;

const windowOptions: Array<{ value: HistoryWindow; label: string }> = [
  { value: "30m", label: "近 30 分钟" },
  { value: "6h", label: "近 6 小时" },
  { value: "24h", label: "近 24 小时" },
];

const configTabs: Array<{ key: ConfigSection; label: string }> = [
  { key: "thresholds", label: "阈值" },
  { key: "layouts", label: "模板" },
  { key: "regions", label: "区域" },
];

const defaultRegionThresholds = {
  count_warning: 50,
  count_critical: 100,
  density_warning: 2,
  density_critical: 4,
};

const regionLayouts: Array<{ id: string; label: string; description: string; regions: RegionDraft[] }> = [
  {
    id: "all",
    label: "整幅区域",
    description: "最适合首次接入，直接观察整体密度变化。",
    regions: [
      {
        name: "全部区域",
        color: "#2563EB",
        points: [[0, 0], [100, 0], [100, 100], [0, 100]],
        ...defaultRegionThresholds,
      },
    ],
  },
  {
    id: "left-middle-right",
    label: "左中右三区",
    description: "适合通道型场景，便于比较左右流量差异。",
    regions: [
      {
        name: "左区",
        color: "#2563EB",
        points: [[0, 0], [33, 0], [33, 100], [0, 100]],
        ...defaultRegionThresholds,
      },
      {
        name: "中区",
        color: "#0EA5E9",
        points: [[33, 0], [66, 0], [66, 100], [33, 100]],
        ...defaultRegionThresholds,
      },
      {
        name: "右区",
        color: "#F97316",
        points: [[66, 0], [100, 0], [100, 100], [66, 100]],
        ...defaultRegionThresholds,
      },
    ],
  },
  {
    id: "front-middle-back",
    label: "前中后三区",
    description: "适合镜头纵深明显的场景，能快速发现拥堵段。",
    regions: [
      {
        name: "前区",
        color: "#2563EB",
        points: [[0, 66], [100, 66], [100, 100], [0, 100]],
        ...defaultRegionThresholds,
      },
      {
        name: "中区",
        color: "#22C55E",
        points: [[0, 33], [100, 33], [100, 66], [0, 66]],
        ...defaultRegionThresholds,
      },
      {
        name: "后区",
        color: "#F97316",
        points: [[0, 0], [100, 0], [100, 33], [0, 33]],
        ...defaultRegionThresholds,
      },
    ],
  },
  {
    id: "quadrants",
    label: "四象限",
    description: "适合开阔区域或大厅，快速定位热点聚集方向。",
    regions: [
      {
        name: "左上",
        color: "#2563EB",
        points: [[0, 0], [50, 0], [50, 50], [0, 50]],
        ...defaultRegionThresholds,
      },
      {
        name: "右上",
        color: "#06B6D4",
        points: [[50, 0], [100, 0], [100, 50], [50, 50]],
        ...defaultRegionThresholds,
      },
      {
        name: "左下",
        color: "#0F766E",
        points: [[0, 50], [50, 50], [50, 100], [0, 100]],
        ...defaultRegionThresholds,
      },
      {
        name: "右下",
        color: "#F97316",
        points: [[50, 50], [100, 50], [100, 100], [50, 100]],
        ...defaultRegionThresholds,
      },
    ],
  },
];

const regionPresets = [
  { id: "full", label: "全域", points: [[0, 0], [100, 0], [100, 100], [0, 100]] },
  { id: "left", label: "左半区", points: [[0, 0], [50, 0], [50, 100], [0, 100]] },
  { id: "right", label: "右半区", points: [[50, 0], [100, 0], [100, 100], [50, 100]] },
  { id: "center", label: "中心区", points: [[25, 20], [75, 20], [75, 80], [25, 80]] },
];

const iconMap: Record<string, string> = {
  overview: '<rect x="3" y="3" width="8" height="8" rx="1"></rect><rect x="13" y="3" width="8" height="5" rx="1"></rect><rect x="13" y="10" width="8" height="11" rx="1"></rect><rect x="3" y="13" width="8" height="8" rx="1"></rect>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7"></path><path d="M3 4v5h5"></path><path d="M12 7v5l4 2"></path>',
  alert: '<path d="M10.3 3.9 1.8 18A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path>',
  sliders: '<path d="M4 6h6"></path><path d="M14 6h6"></path><circle cx="12" cy="6" r="2"></circle><path d="M4 12h10"></path><path d="M18 12h2"></path><circle cx="16" cy="12" r="2"></circle><path d="M4 18h3"></path><path d="M11 18h9"></path><circle cx="9" cy="18" r="2"></circle>',
  plus: '<path d="M12 5v14"></path><path d="M5 12h14"></path>',
  camera: '<path d="M5 7h3l2-2h4l2 2h3v10H5z"></path><circle cx="12" cy="12" r="3.5"></circle>',
  upload: '<path d="M12 16V5"></path><path d="m7 10 5-5 5 5"></path><path d="M4 19h16"></path>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36"></path><path d="M21 3v6h-6"></path>',
  spark: '<path d="M13 3 4 14h6l-1 7 9-11h-6z"></path>',
  clock: '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path>',
  play: '<path d="M8 6.5v11l9-5.5z"></path>',
  pause: '<path d="M8 6h3v12H8z"></path><path d="M13 6h3v12h-3z"></path>',
  film: '<path d="M4 5h16v14H4z"></path><path d="M8 5v14"></path><path d="M16 5v14"></path><path d="M4 9h4"></path><path d="M4 15h4"></path><path d="M16 9h4"></path><path d="M16 15h4"></path>',
  export: '<path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M4 19h16"></path>',
  trash: '<path d="M4 7h16"></path><path d="M9 7V4h6v3"></path><path d="M6 7l1 12h10l1-12"></path><path d="M10 11v6"></path><path d="M14 11v6"></path>',
  target: '<circle cx="12" cy="12" r="8"></circle><path d="M12 8v8"></path><path d="M8 12h8"></path>',
  chart: '<path d="M4 19V5"></path><path d="M4 19h16"></path><path d="m7 14 4-4 3 2 4-5"></path>',
  area: '<path d="M4 18 9 10l4 4 7-8"></path><path d="M4 18h16"></path><path d="M4 18V6"></path>',
  check: '<path d="m5 12 4 4 10-10"></path>',
  warning: '<path d="M10.3 3.9 1.8 18A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path>',
  edit: '<path d="M4 20h4l10-10-4-4L4 16v4Z"></path><path d="m14 6 4 4"></path>',
  close: '<path d="M6 6 18 18"></path><path d="M18 6 6 18"></path>',
  save: '<path d="M5 4h11l3 3v13H5z"></path><path d="M8 4v5h8"></path><path d="M8 20v-6h8v6"></path>',
  source: '<path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h10"></path>',
  "chevron-down": '<path d="m6 9 6 6 6-6"></path>',
};

const IconSymbol = defineComponent({
  name: "IconSymbol",
  props: {
    name: {
      type: String,
      required: true,
    },
    size: {
      type: Number,
      default: 18,
    },
  },
  setup(props) {
    return () =>
      h("svg", {
        class: "icon-symbol",
        width: props.size,
        height: props.size,
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        "stroke-width": 1.8,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "aria-hidden": "true",
        focusable: "false",
        innerHTML: iconMap[props.name] || iconMap.overview,
      });
  },
});

const overviewSection = ref<HTMLElement | null>(null);
const historySection = ref<HTMLElement | null>(null);
const alertsSection = ref<HTMLElement | null>(null);
const historyChartRef = ref<HTMLDivElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const activeSection = ref<SectionKey>("overview");
const drawerOpen = ref(false);
const configSection = ref<ConfigSection>("thresholds");
const nowLabel = ref("");

const systemStatus = reactive<SystemStatus>({
  status: "offline",
  uptime: 0,
  active_sources: 0,
  gpu_usage: null,
  memory_usage: null,
});

const sources = ref<VideoSource[]>([]);
const sourcePickerOpen = ref(false);
const selectedSourceId = ref("");
const analysisStatus = ref<AnalysisStatusValue>("ready");
const analysisStartedAt = ref<string | null>(null);
const recentAlerts = ref<AlertRecentItem[]>([]);
const regions = ref<Region[]>([]);
const historyData = ref<HistoryResponse>({ series: [] });
const historyInterval = ref<HistoryInterval>("1m");
const historyWindow = ref<HistoryWindow>("6h");
const historyMetric = ref<HistoryMetricKey>("total_count_avg");
const historyRegionId = ref("all");

const thresholdForm = reactive({
  totalWarning: 80,
  totalCritical: 120,
  regionWarning: 40,
  regionCritical: 70,
  cooldown: 30,
});

const sourceModal = reactive({
  open: false,
  mode: "stream" as SourceModalMode,
  name: "",
  url: "",
  file: null as File | null,
});

const regionModal = reactive({
  open: false,
  regionId: "",
  name: "",
  color: "#2563EB",
  pointsText: "[]",
  countWarning: String(defaultRegionThresholds.count_warning),
  countCritical: String(defaultRegionThresholds.count_critical),
  densityWarning: String(defaultRegionThresholds.density_warning),
  densityCritical: String(defaultRegionThresholds.density_critical),
  showAdvanced: false,
});

const exportModal = reactive({
  open: false,
  kind: "history" as ExportKind,
  range: "6h" as HistoryWindow,
  format: "csv" as "csv" | "xlsx",
});

const confirmDialog = reactive({
  open: false,
  title: "",
  message: "",
  actionLabel: "确认",
  tone: "warning" as ToastTone,
  pending: false,
});

const toasts = ref<Array<{ id: number; tone: ToastTone; message: string }>>([]);
const busy = reactive({
  sources: false,
  context: false,
  history: false,
  thresholds: false,
  sourceSubmit: false,
  regionSubmit: false,
  exportSubmit: false,
  analysis: false,
  template: false,
});

const liveFrame = ref<RealtimeFrame | null>(null);
const historyChart = ref<echarts.ECharts | null>(null);
const regionStageRef = ref<HTMLElement | null>(null);

const regionEditor = reactive({
  tool: "polygon" as RegionEditorTool,
  points: [] as RegionPoint[],
  isClosed: false,
  hoverPoint: null as RegionPoint | null,
});

const regionDrag = reactive({
  mode: "none" as RegionDragMode,
  index: -1,
  start: null as RegionPoint | null,
  startPoints: [] as RegionPoint[],
  didMove: false,
  ignoreNextClick: false,
});

let confirmAction: (() => Promise<void> | void) | null = null;
let toastSeed = 0;
let clockTimer: number | null = null;
let pollTimer: number | null = null;
let realtimeSocket: WebSocket | null = null;
let reconnectTimer: number | null = null;
let heartbeatTimer: number | null = null;
let reconnectAttempts = 0;
let initialPromptShown = false;

function openConfigCenter(section: ConfigSection = "thresholds") {
  configSection.value = section;
  drawerOpen.value = true;
}

const selectedSource = computed(
  () => sources.value.find((item) => item.source_id === selectedSourceId.value) || null
);

const lastHistoryPoint = computed(() => {
  const items = historyData.value.series || [];
  return items.length ? items[items.length - 1] : null;
});

const historyMetricMeta = computed(
  () => historyMetrics.find((item) => item.key === historyMetric.value) || historyMetrics[0]
);

const frameSrc = computed(() => (liveFrame.value ? `data:image/jpeg;base64,${liveFrame.value.frame}` : ""));

const displayTotals = computed(() => ({
  totalCount: liveFrame.value?.total_count ?? lastHistoryPoint.value?.total_count_avg ?? null,
  totalDensity: liveFrame.value?.total_density ?? lastHistoryPoint.value?.total_density_avg ?? null,
  entrySpeed: liveFrame.value?.entry_speed ?? null,
}));

const densityTone = computed(() => getDensityTone(displayTotals.value.totalDensity));
const densityLabel = computed(() => getDensityLabel(displayTotals.value.totalDensity));

const systemTone = computed(() => (systemStatus.status === "running" ? "success" : "warning"));
const systemStatusLabel = computed(() =>
  systemStatus.status === "running" ? "系统在线" : "系统未就绪"
);

const uptimeLabel = computed(() => formatUptime(systemStatus.uptime));

function formatSourceMeta(source: VideoSource) {
  const parts = [
    source.source_type === "stream" ? "摄像头 / 推流" : "本地视频",
    source.video_width && source.video_height ? `${source.video_width}×${source.video_height}` : "",
    source.video_fps ? `${Math.round(source.video_fps)} fps` : "",
  ].filter(Boolean);
  return parts.join(" · ") || "等待读取元信息";
}

const liveTimestampLabel = computed(() => {
  if (liveFrame.value?.ts) {
    return `最后更新 ${formatDateTime(liveFrame.value.ts)}`;
  }
  if (analysisStatus.value === "running") {
    return "已启动分析，等待首帧画面";
  }
  return "尚未开始分析";
});

const videoStageStyle = computed(() => {
  const width = selectedSource.value?.video_width;
  const height = selectedSource.value?.video_height;
  return width && height ? { aspectRatio: `${width} / ${height}` } : { aspectRatio: "16 / 9" };
});

const summaryCards = computed(() => [
  {
    label: "当前人数",
    value: formatCount(displayTotals.value.totalCount),
    hint: liveFrame.value ? "来自实时画面" : "使用最近历史值回填",
    tone: "primary",
    icon: "spark",
  },
  {
    label: "平均密度",
    value: formatDecimal(displayTotals.value.totalDensity, 2),
    hint: densityLabel.value,
    tone: densityTone.value,
    icon: "target",
  },
  {
    label: "历史点位",
    value: String(historyData.value.series.length),
    hint: `${historyWindowLabel(historyWindow.value)} · ${historyIntervalLabel(historyInterval.value)}`,
    tone: "neutral",
    icon: "chart",
  },
]);

const regionSummaryRows = computed(() =>
  regions.value.map((region) => {
    const liveRegion = liveFrame.value?.regions?.[region.region_id];
    const historyRegion = lastHistoryPoint.value?.regions?.[region.region_id];
    const count = liveRegion?.total_count_avg ?? historyRegion?.total_count_avg ?? null;
    const density = liveRegion?.total_density_avg ?? historyRegion?.total_density_avg ?? null;
    const tone = getRegionTone(region, count, density);
    return {
      ...region,
      count,
      density,
      tone,
      description: `${formatCount(count)} 人 · 密度 ${formatDecimal(density, 2)} 人/m²`,
      thresholdText: buildThresholdText(region),
    };
  })
);

const regionEditorReferenceRegions = computed(() =>
  regions.value.filter((region) => region.region_id !== regionModal.regionId)
);

const regionEditorPolygonPoints = computed(() => toSvgPoints(regionEditor.points));

const regionEditorPreviewPoints = computed(() => {
  if (!regionEditor.points.length) return "";
  if (regionEditor.isClosed || !regionEditor.hoverPoint) {
    return toSvgPoints(regionEditor.points);
  }
  return toSvgPoints([...regionEditor.points, regionEditor.hoverPoint]);
});

const regionEditorHint = computed(() =>
  regionEditor.tool === "polygon"
    ? "单击画面逐点标区，双击或点击完成闭合。"
    : "按住拖拽生成矩形区域。"
);

const regionEditorStatus = computed(() => {
  if (!regionEditor.points.length) {
    return "尚未选点";
  }
  if (regionEditor.isClosed) {
    return "可拖动顶点或整块区域微调";
  }
  return "继续加点或点击完成闭合";
});

const rankedRegionSnapshots = computed(() =>
  [...regionSummaryRows.value].sort((a, b) => (Number(b.density ?? -1) || -1) - (Number(a.density ?? -1) || -1))
);

const historySeriesPoints = computed(() =>
  (historyData.value.series || []).map((item) => {
    const value = resolveHistoryValue(item, historyMetric.value, historyRegionId.value);
    return {
      time: item.time,
      label: formatTime(item.time),
      raw: value,
      value: formatDecimal(value, historyMetricMeta.value.digits),
    };
  })
);

const historyRows = computed(() => historySeriesPoints.value.slice(-8).reverse());

const historyStatCards = computed(() => {
  const values = historySeriesPoints.value
    .map((item) => item.raw)
    .filter((value): value is number => Number.isFinite(value));

  if (!values.length) {
    return { latest: "--", max: "--", min: "--", delta: "--" };
  }

  const latest = values[values.length - 1];
  const first = values[0];
  const delta = latest - first;

  return {
    latest: formatDecimal(latest, historyMetricMeta.value.digits),
    max: formatDecimal(Math.max(...values), historyMetricMeta.value.digits),
    min: formatDecimal(Math.min(...values), historyMetricMeta.value.digits),
    delta: `${delta >= 0 ? "+" : ""}${formatDecimal(delta, historyMetricMeta.value.digits)}`,
  };
});

const historyTrendTone = computed(() => {
  const latest =
    historySeriesPoints.value.length > 0
      ? historySeriesPoints.value[historySeriesPoints.value.length - 1]?.raw ?? 0
      : 0;
  const first = historySeriesPoints.value[0]?.raw ?? 0;
  return latest - first >= 0 ? "warning" : "success";
});

const criticalAlertCount = computed(
  () => recentAlerts.value.filter((item) => item.level === "critical").length
);
const warningAlertCount = computed(
  () => recentAlerts.value.filter((item) => item.level === "warning").length
);

function isGlobalRegion(points: number[][]) {
  if (points.length !== 4) return false;
  const normalized = points
    .map(([x, y]) => [Math.round(Number(x)), Math.round(Number(y))] as const)
    .sort(([ax, ay], [bx, by]) => (ax === bx ? ay - by : ax - bx));
  const corners = [
    [0, 0],
    [0, 100],
    [100, 0],
    [100, 100],
  ] as const;
  return normalized.every(([x, y], index) => x === corners[index][0] && y === corners[index][1]);
}

const hottestRegionDisplay = computed(() => {
  const region = rankedRegionSnapshots.value[0];
  if (!region) {
    return {
      name: "未配置区域",
      hint: "请先划分监测区域",
    };
  }

  if (isGlobalRegion(region.points)) {
    return {
      name: "全局区域",
      hint: "当前按整幅画面统计",
    };
  }

  return {
    name: region.name,
    hint: "当前密度最高区域",
  };
});

const hottestRegionDisplayName = computed(() => hottestRegionDisplay.value.name);
const hottestRegionHint = computed(() => hottestRegionDisplay.value.hint);

const exportTitle = computed(() => {
  if (exportModal.kind === "history") return "导出历史数据";
  if (exportModal.kind === "alerts") return "导出告警记录";
  return "导出原始片段";
});

function formatCount(value: number | null | undefined) {
  if (!Number.isFinite(value)) return "--";
  return `${Math.round(value as number)}`;
}

function formatDecimal(value: number | null | undefined, digits = 0) {
  if (!Number.isFinite(value)) return "--";
  return (value as number).toFixed(digits);
}

function formatPercent(value: number | null | undefined) {
  if (!Number.isFinite(value)) return "未采集";
  return `${Math.round((value as number) * 100)}%`;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTime(value: string | null | undefined) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatUptime(totalSeconds: number) {
  if (!Number.isFinite(totalSeconds)) return "--";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function historyWindowLabel(value: HistoryWindow) {
  return windowOptions.find((item) => item.value === value)?.label || value;
}

function historyIntervalLabel(value: HistoryInterval) {
  const map: Record<HistoryInterval, string> = {
    "1m": "1 分钟粒度",
    "5m": "5 分钟粒度",
    "1h": "1 小时粒度",
  };
  return map[value];
}

function getDensityLabel(value: number | null | undefined) {
  if (!Number.isFinite(value)) return "暂无密度";
  if ((value as number) >= 4) return "拥挤";
  if ((value as number) >= 2) return "关注";
  return "平稳";
}

function getDensityTone(value: number | null | undefined) {
  if (!Number.isFinite(value)) return "neutral";
  if ((value as number) >= 4) return "danger";
  if ((value as number) >= 2) return "warning";
  return "success";
}

function buildThresholdText(region: Region) {
  const countPart =
    region.count_warning != null || region.count_critical != null
      ? `人数 ${region.count_warning ?? "-"} / ${region.count_critical ?? "-"}`
      : "人数阈值未设置";
  const densityPart =
    region.density_warning != null || region.density_critical != null
      ? `密度 ${region.density_warning ?? "-"} / ${region.density_critical ?? "-"}`
      : "密度阈值未设置";
  return `${countPart} · ${densityPart}`;
}

function getRegionTone(region: Region, count: number | null, density: number | null) {
  if (region.count_critical != null && Number.isFinite(count) && (count as number) >= region.count_critical) {
    return "danger";
  }
  if (
    region.density_critical != null &&
    Number.isFinite(density) &&
    (density as number) >= region.density_critical
  ) {
    return "danger";
  }
  if (region.count_warning != null && Number.isFinite(count) && (count as number) >= region.count_warning) {
    return "warning";
  }
  if (
    region.density_warning != null &&
    Number.isFinite(density) &&
    (density as number) >= region.density_warning
  ) {
    return "warning";
  }
  return "success";
}

function alertTone(level: string) {
  return level === "critical" ? "danger" : "warning";
}

function resolveHistoryValue(item: HistorySeriesItem, metric: HistoryMetricKey, regionId: string) {
  if (regionId !== "all") {
    const regionItem = item.regions?.[regionId];
    return regionItem ? regionItem[metric] : null;
  }
  return item[metric];
}

function pushToast(message: string, tone: ToastTone = "info", duration = 3200) {
  const id = ++toastSeed;
  toasts.value.push({ id, tone, message });
  window.setTimeout(() => removeToast(id), duration);
}

function removeToast(id: number) {
  toasts.value = toasts.value.filter((item) => item.id !== id);
}

function extractErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) return error.message;
  return "操作失败，请稍后重试";
}

function resetLiveFrame() {
  liveFrame.value = null;
}

function resetSourceContext() {
  selectedSourceId.value = "";
  analysisStatus.value = "ready";
  analysisStartedAt.value = null;
  recentAlerts.value = [];
  regions.value = [];
  historyData.value = { series: [] };
  resetLiveFrame();
  disconnectRealtime();
}

async function loadSystemStatus() {
  try {
    const data = await apiGet<SystemStatus>("/status");
    Object.assign(systemStatus, data);
  } catch {
    systemStatus.status = "offline";
  }
}

async function loadSources(preferredSourceId?: string) {
  busy.sources = true;
  try {
    const data = await apiGet<SourceListResponse>("/sources");
    sources.value = [...(data.sources || [])].sort((a, b) => b.created_at.localeCompare(a.created_at));

    const nextId =
      preferredSourceId && sources.value.some((item) => item.source_id === preferredSourceId)
        ? preferredSourceId
        : sources.value.some((item) => item.source_id === selectedSourceId.value)
          ? selectedSourceId.value
          : sources.value[0]?.source_id || "";

    if (!nextId) {
      resetSourceContext();
      if (!initialPromptShown) {
        initialPromptShown = true;
        openSourceModal("stream");
      }
      return;
    }

    selectedSourceId.value = nextId;
    await loadSourceContext(nextId);
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.sources = false;
  }
}

async function loadSourceContext(sourceId: string) {
  busy.context = true;
  historyRegionId.value = "all";
  resetLiveFrame();
  disconnectRealtime();

  const tasks = await Promise.allSettled([
    loadAnalysisState(sourceId),
    loadRegions(sourceId),
    loadThresholds(sourceId),
    loadRecentAlerts(sourceId),
    refreshHistory(sourceId),
  ]);

  busy.context = false;

  if (tasks.some((item) => item.status === "rejected")) {
    pushToast("部分数据刷新失败，已显示可用内容。", "warning");
  }

  if (analysisStatus.value === "running" && sourceId === selectedSourceId.value) {
    connectRealtime();
  }
}

async function loadAnalysisState(sourceId: string) {
  try {
    const data = await apiGet<{ source_id: string; status: AnalysisStatusValue; start_time?: string | null }>(
      `/analysis/status?source_id=${encodeURIComponent(sourceId)}`
    );
    if (sourceId !== selectedSourceId.value) return;
    analysisStatus.value = data.status;
    analysisStartedAt.value = data.start_time || null;
  } catch {
    if (sourceId !== selectedSourceId.value) return;
    analysisStatus.value = "ready";
    analysisStartedAt.value = null;
  }
}

async function loadRegions(sourceId: string) {
  const data = await apiGet<RegionListResponse>(`/regions?source_id=${encodeURIComponent(sourceId)}`);
  if (sourceId !== selectedSourceId.value) return;
  regions.value = data.regions || [];
}

async function loadThresholds(sourceId: string) {
  const data = await apiGet<AlertThresholdConfig>(
    `/alerts/threshold?source_id=${encodeURIComponent(sourceId)}`
  );
  if (sourceId !== selectedSourceId.value) return;
  thresholdForm.totalWarning = data.total_warning_threshold;
  thresholdForm.totalCritical = data.total_critical_threshold;
  thresholdForm.regionWarning = data.default_region_warning;
  thresholdForm.regionCritical = data.default_region_critical;
  thresholdForm.cooldown = data.cooldown_seconds;
}

async function loadRecentAlerts(sourceId: string) {
  const data = await apiGet<AlertRecentResponse>(`/alerts/recent?source_id=${encodeURIComponent(sourceId)}`);
  if (sourceId !== selectedSourceId.value) return;
  recentAlerts.value = data.items || [];
}

function resolveRange(windowKey: HistoryWindow) {
  const end = new Date();
  const start = new Date(end);

  if (windowKey === "30m") start.setMinutes(start.getMinutes() - 30);
  if (windowKey === "6h") start.setHours(start.getHours() - 6);
  if (windowKey === "24h") start.setHours(start.getHours() - 24);

  return {
    from: start.toISOString(),
    to: end.toISOString(),
  };
}

async function refreshHistory(sourceId = selectedSourceId.value) {
  if (!sourceId) {
    historyData.value = { series: [] };
    renderHistoryChart();
    return;
  }

  busy.history = true;
  try {
    const range = resolveRange(historyWindow.value);
    const query = new URLSearchParams({
      source_id: sourceId,
      from: range.from,
      to: range.to,
      interval: historyInterval.value,
    });

    const data = await apiGet<HistoryResponse>(`/history?${query.toString()}`);
    if (sourceId !== selectedSourceId.value) return;
    historyData.value = { series: data.series || [] };
    await nextTick();
    renderHistoryChart();
  } catch (error) {
    if (sourceId !== selectedSourceId.value) return;
    historyData.value = { series: [] };
    renderHistoryChart();
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.history = false;
  }
}

function ensureChart() {
  if (!historyChartRef.value) return;
  if (!historyChart.value) {
    historyChart.value = echarts.init(historyChartRef.value);
  }
}

function recreateChart() {
  historyChart.value?.dispose();
  historyChart.value = null;
  ensureChart();
}

function applyHistoryChartOption(option: echarts.EChartsCoreOption, reset = false) {
  if (!historyChart.value) return;

  try {
    historyChart.value.setOption(option, true);
  } catch (error) {
    if (reset) {
      console.error("History chart render failed after reset", error);
      pushToast("趋势图渲染失败，请稍后重试。", "warning", 2600);
      return;
    }

    recreateChart();
    if (!historyChart.value) return;
    historyChart.value.setOption(option, true);
  }
}

function renderHistoryChart() {
  ensureChart();
  if (!historyChart.value) return;

  const seriesPoints = historySeriesPoints.value;

  if (!seriesPoints.length || seriesPoints.every((item) => !Number.isFinite(item.raw))) {
    applyHistoryChartOption({
      animation: false,
      title: {
        text: "暂无历史数据",
        left: "center",
        top: "middle",
        textStyle: {
          color: "#64748B",
          fontSize: 14,
          fontWeight: 500,
        },
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: [],
    });
    return;
  }

  const metric = historyMetricMeta.value;

  applyHistoryChartOption({
    animationDuration: 300,
    grid: {
      left: 24,
      right: 18,
      top: 24,
      bottom: 28,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#0F172A",
      borderWidth: 0,
      textStyle: {
        color: "#F8FAFC",
      },
      formatter: (params: Array<{ axisValue: string; data: number }>) => {
        const first = params[0];
        if (!first) return "";
        return `${first.axisValue}<br/>${metric.label}：${formatDecimal(first.data, metric.digits)}`;
      },
    },
    xAxis: {
      type: "category",
      data: seriesPoints.map((item) => item.label),
      boundaryGap: false,
      axisLine: {
        lineStyle: { color: "#CBD5E1" },
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: "#64748B",
      },
    },
    yAxis: {
      type: "value",
      splitLine: {
        lineStyle: { color: "#E2E8F0" },
      },
      axisLabel: {
        color: "#64748B",
      },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        connectNulls: false,
        data: seriesPoints.map((item) => item.raw ?? null),
        itemStyle: { color: metric.color },
        lineStyle: { width: 3, color: metric.color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `${metric.color}55` },
            { offset: 1, color: `${metric.color}08` },
          ]),
        },
      },
    ],
  });
}

function resizeHistoryChart() {
  if (!historyChart.value) return;

  try {
    historyChart.value.resize();
  } catch {
    recreateChart();
    renderHistoryChart();
  }
}

function clearReconnectTimer() {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function clearHeartbeatTimer() {
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function disconnectRealtime() {
  clearReconnectTimer();
  clearHeartbeatTimer();
  if (realtimeSocket) {
    realtimeSocket.onopen = null;
    realtimeSocket.onclose = null;
    realtimeSocket.onmessage = null;
    realtimeSocket.onerror = null;
    realtimeSocket.close();
    realtimeSocket = null;
  }
}

function scheduleReconnect() {
  if (!selectedSourceId.value || analysisStatus.value !== "running" || reconnectTimer) return;
  const delay = Math.min(10000, 1000 * 2 ** Math.min(reconnectAttempts, 4));
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    reconnectAttempts += 1;
    connectRealtime();
  }, delay);
}

function connectRealtime() {
  if (!selectedSourceId.value || analysisStatus.value !== "running") return;

  disconnectRealtime();
  const currentSourceId = selectedSourceId.value;
  const socket = new WebSocket(buildWsUrl("/api/ws/realtime", { source_id: currentSourceId }));
  realtimeSocket = socket;

  socket.onopen = () => {
    reconnectAttempts = 0;
    clearReconnectTimer();
    clearHeartbeatTimer();
    heartbeatTimer = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 15000);
  };

  socket.onmessage = (event) => {
    if (event.data === "pong") return;

    try {
      const payload = JSON.parse(event.data) as SocketEnvelope;
      if (payload.type === "frame") {
        liveFrame.value = payload.data as RealtimeFrame;
      }

      if (payload.type === "alert") {
        recentAlerts.value = [
          {
            alert_id: payload.data.alert_id,
            alert_type: payload.data.alert_type,
            level: payload.data.level,
            region_id: payload.data.region_id,
            region_name: payload.data.region_name,
            current_value: payload.data.current_value,
            threshold: payload.data.threshold,
            timestamp: payload.data.timestamp,
            message: payload.data.message,
          },
          ...recentAlerts.value.filter((item) => item.alert_id !== payload.data.alert_id),
        ].slice(0, 8);

        pushToast(payload.data.message, payload.data.level === "critical" ? "error" : "warning", 4200);
      }
    } catch {
      pushToast("实时数据解析失败。", "warning");
    }
  };

  socket.onclose = () => {
    clearHeartbeatTimer();
    realtimeSocket = null;
    if (selectedSourceId.value === currentSourceId && analysisStatus.value === "running") {
      scheduleReconnect();
    }
  };

  socket.onerror = () => {
    socket.close();
  };
}

async function refreshDashboard() {
  await loadSystemStatus();
  if (selectedSourceId.value) {
    await loadSourceContext(selectedSourceId.value);
  }
}

async function activateSource(sourceId: string) {
  if (sourceId === selectedSourceId.value && regions.value.length) return;
  selectedSourceId.value = sourceId;
  await loadSourceContext(sourceId);
}

function openSourcePicker() {
  sourcePickerOpen.value = true;
}

function closeSourcePicker() {
  sourcePickerOpen.value = false;
}

function selectSourceFromPicker(sourceId: string) {
  closeSourcePicker();
  if (!sourceId) return;
  void activateSource(sourceId);
}

async function startAnalysis() {
  if (!selectedSourceId.value) {
    openSourceModal("stream");
    pushToast("请先添加一个数据源。", "warning");
    return;
  }

  busy.analysis = true;
  try {
    await apiPost("/analysis/start", { source_id: selectedSourceId.value });
    analysisStatus.value = "running";
    analysisStartedAt.value = new Date().toISOString();
    connectRealtime();
    pushToast("分析已开始。", "success");
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.analysis = false;
  }
}

async function stopAnalysis() {
  if (!selectedSourceId.value) return;

  busy.analysis = true;
  try {
    await apiPost("/analysis/stop", { source_id: selectedSourceId.value });
    analysisStatus.value = "stopped";
    disconnectRealtime();
    pushToast("分析已停止。", "info");
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.analysis = false;
  }
}

async function saveThresholds() {
  if (!selectedSourceId.value) {
    pushToast("请先选择数据源。", "warning");
    return;
  }

  busy.thresholds = true;
  try {
    await apiPost<AlertThresholdConfig>("/alerts/threshold", {
      source_id: selectedSourceId.value,
      total_warning_threshold: thresholdForm.totalWarning,
      total_critical_threshold: thresholdForm.totalCritical,
      default_region_warning: thresholdForm.regionWarning,
      default_region_critical: thresholdForm.regionCritical,
      cooldown_seconds: thresholdForm.cooldown,
    });
    pushToast("阈值已保存，重新开始分析后会立即看到完整效果。", "success", 3800);
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.thresholds = false;
  }
}

function openSourceModal(mode: SourceModalMode) {
  sourcePickerOpen.value = false;
  sourceModal.open = true;
  sourceModal.mode = mode;
  sourceModal.name = "";
  sourceModal.url = "";
  sourceModal.file = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function closeSourceModal() {
  sourceModal.open = false;
}

function handleSourceFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  sourceModal.file = target.files?.[0] || null;
}

async function submitSourceModal() {
  busy.sourceSubmit = true;
  try {
    let sourceId = "";

    if (sourceModal.mode === "stream") {
      if (!sourceModal.name.trim() || !sourceModal.url.trim()) {
        throw new Error("请填写数据源名称和流地址。");
      }
      const data = await apiPost<VideoSource>("/sources/stream", {
        name: sourceModal.name.trim(),
        url: sourceModal.url.trim(),
      });
      sourceId = data.source_id;
    } else {
      if (!sourceModal.file) {
        throw new Error("请先选择一个视频文件。");
      }
      const data = await apiUpload<VideoSource>("/sources/upload", sourceModal.file);
      sourceId = data.source_id;
    }

    closeSourceModal();
    pushToast("数据源已添加。", "success");
    await loadSources(sourceId);
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.sourceSubmit = false;
  }
}

function openRegionModal(region?: Region) {
  if (!selectedSourceId.value) {
    pushToast("请先选择数据源。", "warning");
    return;
  }

  regionModal.open = true;
  regionModal.regionId = region?.region_id || "";
  regionModal.name = region?.name || `区域 ${regions.value.length + 1}`;
  regionModal.color = region?.color || "#2563EB";
  regionModal.pointsText = serializeRegionPoints(region?.points || []);
  regionModal.countWarning = region?.count_warning != null ? String(region.count_warning) : "";
  regionModal.countCritical = region?.count_critical != null ? String(region.count_critical) : "";
  regionModal.densityWarning = region?.density_warning != null ? String(region.density_warning) : "";
  regionModal.densityCritical = region?.density_critical != null ? String(region.density_critical) : "";
  regionModal.showAdvanced = false;
  setRegionEditorTool("polygon");
  setRegionEditorPoints(region?.points || [], Boolean(region?.points?.length));
  nextTick(() => {
    regionStageRef.value?.focus?.();
  });
}

function closeRegionModal() {
  regionModal.open = false;
  regionModal.showAdvanced = false;
  resetRegionDrag();
  regionEditor.hoverPoint = null;
}

function applyRegionPreset(presetId: string) {
  const preset = regionPresets.find((item) => item.id === presetId);
  if (!preset) return;
  setRegionEditorPoints(preset.points, true);
}

function setRegionEditorTool(tool: RegionEditorTool) {
  regionEditor.tool = tool;
  regionEditor.hoverPoint = null;
}

function clampPercent(value: number) {
  return Number(Math.min(100, Math.max(0, value)).toFixed(2));
}

function normalizeRegionPoint(point: number[]) {
  return [clampPercent(Number(point[0])), clampPercent(Number(point[1]))] as RegionPoint;
}

function normalizeRegionPoints(points: number[][]) {
  return points.map((point) => normalizeRegionPoint(point));
}

function serializeRegionPoints(points: number[][]) {
  return JSON.stringify(
    normalizeRegionPoints(points).map(([x, y]) => [Number(x.toFixed(2)), Number(y.toFixed(2))]),
    null,
    2
  );
}

function setRegionEditorPoints(points: number[][], closed = points.length >= 3) {
  regionEditor.points = normalizeRegionPoints(points);
  regionEditor.isClosed = closed && regionEditor.points.length >= 3;
  regionModal.pointsText = serializeRegionPoints(regionEditor.points);
}

function syncRegionEditorText() {
  regionModal.pointsText = serializeRegionPoints(regionEditor.points);
}

function resetRegionDrag() {
  regionDrag.mode = "none";
  regionDrag.index = -1;
  regionDrag.start = null;
  regionDrag.startPoints = [];
  regionDrag.didMove = false;
}

function clearRegionEditor() {
  setRegionEditorPoints([], false);
  regionEditor.hoverPoint = null;
  resetRegionDrag();
}

function undoRegionPoint() {
  if (!regionEditor.points.length) return;
  if (regionEditor.isClosed) {
    regionEditor.isClosed = false;
    return;
  }
  regionEditor.points = regionEditor.points.slice(0, -1);
  syncRegionEditorText();
}

function finishPolygon() {
  if (regionEditor.points.length < 3) {
    pushToast("区域至少需要 3 个点。", "warning");
    return;
  }
  regionEditor.isClosed = true;
  syncRegionEditorText();
}

function applyRegionTextToCanvas() {
  try {
    const points = parseRegionPoints(regionModal.pointsText);
    setRegionEditorPoints(points, true);
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  }
}

function toSvgPoints(points: number[][]) {
  return points.map(([x, y]) => `${clampPercent(Number(x))},${clampPercent(Number(y))}`).join(" ");
}

function regionHandleStyle(point: number[]) {
  return {
    left: `${point[0]}%`,
    top: `${point[1]}%`,
    backgroundColor: regionModal.color,
  };
}

function getStagePointFromClient(clientX: number, clientY: number, clamp = true) {
  if (!regionStageRef.value) return null;

  const rect = regionStageRef.value.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;

  const rawX = ((clientX - rect.left) / rect.width) * 100;
  const rawY = ((clientY - rect.top) / rect.height) * 100;

  if (!clamp && (rawX < 0 || rawX > 100 || rawY < 0 || rawY > 100)) {
    return null;
  }

  return [clampPercent(rawX), clampPercent(rawY)] as RegionPoint;
}

function getStagePointFromPointer(event: PointerEvent | MouseEvent, clamp = true) {
  return getStagePointFromClient(event.clientX, event.clientY, clamp);
}

function distanceBetweenPoints(a: RegionPoint, b: RegionPoint) {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  return Math.sqrt(dx * dx + dy * dy);
}

function buildRectanglePoints(start: RegionPoint, end: RegionPoint) {
  const left = Math.min(start[0], end[0]);
  const right = Math.max(start[0], end[0]);
  const top = Math.min(start[1], end[1]);
  const bottom = Math.max(start[1], end[1]);
  return [
    [left, top],
    [right, top],
    [right, bottom],
    [left, bottom],
  ] as RegionPoint[];
}

function clampPolygonDelta(points: RegionPoint[], deltaX: number, deltaY: number) {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  let nextX = deltaX;
  let nextY = deltaY;

  if (minX + nextX < 0) nextX = -minX;
  if (maxX + nextX > 100) nextX = 100 - maxX;
  if (minY + nextY < 0) nextY = -minY;
  if (maxY + nextY > 100) nextY = 100 - maxY;

  return [nextX, nextY] as const;
}

function handleRegionStageClick(event: MouseEvent) {
  if (regionEditor.tool !== "polygon") return;
  if (regionDrag.ignoreNextClick) {
    regionDrag.ignoreNextClick = false;
    return;
  }
  if (regionEditor.isClosed || event.detail > 1) return;

  const point = getStagePointFromPointer(event, false);
  if (!point) return;

  const firstPoint = regionEditor.points[0];
  if (firstPoint && regionEditor.points.length >= 3 && distanceBetweenPoints(point, firstPoint) <= 3) {
    finishPolygon();
    return;
  }

  const lastPoint = regionEditor.points[regionEditor.points.length - 1];
  if (lastPoint && distanceBetweenPoints(point, lastPoint) < 0.6) return;

  regionEditor.points = [...regionEditor.points, point];
  syncRegionEditorText();
}

function handleRegionStageDoubleClick() {
  if (regionEditor.tool === "polygon" && regionEditor.points.length >= 3) {
    finishPolygon();
  }
}

function handleRegionStagePointerMove(event: PointerEvent) {
  if (regionDrag.mode !== "none") return;
  regionEditor.hoverPoint = regionEditor.tool === "polygon" ? getStagePointFromPointer(event, false) : null;
}

function handleRegionStagePointerLeave() {
  if (regionDrag.mode === "none") {
    regionEditor.hoverPoint = null;
  }
}

function handleRegionStagePointerDown(event: PointerEvent) {
  if (regionEditor.tool !== "rectangle") return;

  const point = getStagePointFromPointer(event);
  if (!point) return;

  regionDrag.mode = "rectangle";
  regionDrag.start = point;
  regionDrag.startPoints = [];
  regionDrag.didMove = false;
  regionEditor.hoverPoint = null;
  regionEditor.points = buildRectanglePoints(point, point);
  regionEditor.isClosed = false;
  syncRegionEditorText();
}

function startRegionHandleDrag(index: number, event: PointerEvent) {
  const point = getStagePointFromPointer(event);
  if (!point) return;

  regionDrag.mode = "vertex";
  regionDrag.index = index;
  regionDrag.start = point;
  regionDrag.startPoints = regionEditor.points.map(([x, y]) => [x, y] as RegionPoint);
  regionDrag.didMove = false;
}

function startRegionPolygonDrag(event: PointerEvent) {
  if (!regionEditor.isClosed || !regionEditor.points.length) return;

  const point = getStagePointFromPointer(event);
  if (!point) return;

  regionDrag.mode = "shape";
  regionDrag.index = -1;
  regionDrag.start = point;
  regionDrag.startPoints = regionEditor.points.map(([x, y]) => [x, y] as RegionPoint);
  regionDrag.didMove = false;
}

function handleRegionEditorPointerMove(event: PointerEvent) {
  if (!regionModal.open || regionDrag.mode === "none" || !regionDrag.start) return;

  const point = getStagePointFromPointer(event);
  if (!point) return;

  if (regionDrag.mode === "vertex") {
    regionDrag.didMove = true;
    regionEditor.points = regionDrag.startPoints.map((item, index) =>
      index === regionDrag.index ? point : item
    );
    syncRegionEditorText();
    return;
  }

  if (regionDrag.mode === "shape") {
    const [deltaX, deltaY] = clampPolygonDelta(
      regionDrag.startPoints,
      point[0] - regionDrag.start[0],
      point[1] - regionDrag.start[1]
    );
    if (Math.abs(deltaX) > 0 || Math.abs(deltaY) > 0) {
      regionDrag.didMove = true;
    }
    regionEditor.points = regionDrag.startPoints.map(([x, y]) => [
      clampPercent(x + deltaX),
      clampPercent(y + deltaY),
    ]);
    syncRegionEditorText();
    return;
  }

  if (regionDrag.mode === "rectangle") {
    if (distanceBetweenPoints(point, regionDrag.start) > 0.4) {
      regionDrag.didMove = true;
    }
    regionEditor.points = buildRectanglePoints(regionDrag.start, point);
    syncRegionEditorText();
  }
}

function handleRegionEditorPointerUp() {
  if (!regionModal.open || regionDrag.mode === "none") return;

  if (regionDrag.mode === "rectangle") {
    const [first, second, third] = regionEditor.points;
    const width = first && second ? Math.abs(second[0] - first[0]) : 0;
    const height = second && third ? Math.abs(third[1] - second[1]) : 0;
    if (width < 1 || height < 1) {
      clearRegionEditor();
    } else {
      regionEditor.isClosed = true;
      syncRegionEditorText();
    }
  }

  if (regionDrag.didMove) {
    regionDrag.ignoreNextClick = true;
    window.setTimeout(() => {
      regionDrag.ignoreNextClick = false;
    }, 0);
  }

  resetRegionDrag();
}

function parseNullableNumber(raw: string, digits = 0) {
  if (!raw.trim()) return null;
  const value = digits === 0 ? parseInt(raw, 10) : parseFloat(raw);
  if (!Number.isFinite(value)) {
    throw new Error("请输入有效数字。");
  }
  return digits === 0 ? Math.round(value) : Number(value.toFixed(digits));
}

function parseRegionPoints(text: string) {
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed) || parsed.length < 3) {
    throw new Error("区域坐标至少需要 3 个点。");
  }

  return parsed.map((item, index) => {
    if (!Array.isArray(item) || item.length !== 2) {
      throw new Error(`第 ${index + 1} 个坐标格式不正确。`);
    }

    const x = Number(item[0]);
    const y = Number(item[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      throw new Error(`第 ${index + 1} 个坐标必须是数字。`);
    }
    if (x < 0 || x > 100 || y < 0 || y > 100) {
      throw new Error(`第 ${index + 1} 个坐标必须在 0 到 100 之间。`);
    }
    return [Number(x.toFixed(2)), Number(y.toFixed(2))];
  });
}

async function submitRegionModal() {
  if (!selectedSourceId.value) return;

  busy.regionSubmit = true;
  try {
    if (!regionEditor.isClosed && regionEditor.points.length >= 3) {
      regionEditor.isClosed = true;
      syncRegionEditorText();
    }

    const canvasText = serializeRegionPoints(regionEditor.points);
    const points = parseRegionPoints(regionModal.pointsText.trim() === canvasText.trim() ? canvasText : regionModal.pointsText);

    const payload = {
      name: regionModal.name.trim(),
      color: regionModal.color,
      points,
      count_warning: parseNullableNumber(regionModal.countWarning),
      count_critical: parseNullableNumber(regionModal.countCritical),
      density_warning: parseNullableNumber(regionModal.densityWarning, 2),
      density_critical: parseNullableNumber(regionModal.densityCritical, 2),
    };

    if (!payload.name) {
      throw new Error("请填写区域名称。");
    }

    if (regionModal.regionId) {
      await apiPut(`/regions/${encodeURIComponent(regionModal.regionId)}`, payload);
    } else {
      await apiPost("/regions", {
        source_id: selectedSourceId.value,
        ...payload,
      });
    }

    closeRegionModal();
    await loadRegions(selectedSourceId.value);
    pushToast("区域已保存。", "success");
    if (analysisStatus.value === "running") {
      pushToast("区域修改后，建议重新开始分析以应用新区域。", "warning", 4200);
    }
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.regionSubmit = false;
  }
}

function openConfirmDialog(options: {
  title: string;
  message: string;
  actionLabel: string;
  tone: ToastTone;
  action: () => Promise<void> | void;
}) {
  confirmDialog.open = true;
  confirmDialog.title = options.title;
  confirmDialog.message = options.message;
  confirmDialog.actionLabel = options.actionLabel;
  confirmDialog.tone = options.tone;
  confirmDialog.pending = false;
  confirmAction = options.action;
}

function closeConfirmDialog() {
  confirmDialog.open = false;
  confirmDialog.pending = false;
  confirmAction = null;
}

async function runConfirmAction() {
  if (!confirmAction) return;
  confirmDialog.pending = true;
  try {
    await confirmAction();
    closeConfirmDialog();
  } catch (error) {
    confirmDialog.pending = false;
    pushToast(extractErrorMessage(error), "error");
  }
}

function requestDeleteSource(source: VideoSource) {
  openConfirmDialog({
    title: "删除数据源",
    message: `确定删除“${source.name}”吗？此操作不可恢复。`,
    actionLabel: "删除",
    tone: "error",
    action: async () => {
      if (selectedSourceId.value === source.source_id && analysisStatus.value === "running") {
        await apiPost("/analysis/stop", { source_id: source.source_id }).catch(() => undefined);
        disconnectRealtime();
      }
      await apiDelete(`/sources/${encodeURIComponent(source.source_id)}`);
      pushToast("数据源已删除。", "success");
      await loadSources();
    },
  });
}

function requestDeleteRegion(region: Region) {
  openConfirmDialog({
    title: "删除区域",
    message: `确定删除区域“${region.name}”吗？`,
    actionLabel: "删除",
    tone: "error",
    action: async () => {
      await apiDelete(`/regions/${encodeURIComponent(region.region_id)}`);
      await loadRegions(selectedSourceId.value);
      pushToast("区域已删除。", "success");
      if (analysisStatus.value === "running") {
        pushToast("区域已变更，建议重新开始分析。", "warning", 3600);
      }
    },
  });
}

function requestApplyLayout(layoutId: string) {
  const layout = regionLayouts.find((item) => item.id === layoutId);
  if (!layout || !selectedSourceId.value) return;

  openConfirmDialog({
    title: "应用布局模板",
    message: `将使用“${layout.label}”覆盖当前区域配置，是否继续？`,
    actionLabel: "覆盖应用",
    tone: "warning",
    action: async () => {
      busy.template = true;
      try {
        for (const region of regions.value) {
          await apiDelete(`/regions/${encodeURIComponent(region.region_id)}`);
        }
        for (const draft of layout.regions) {
          await apiPost("/regions", {
            source_id: selectedSourceId.value,
            ...draft,
          });
        }
        await loadRegions(selectedSourceId.value);
        pushToast(`已应用布局模板：${layout.label}。`, "success");
        if (analysisStatus.value === "running") {
          pushToast("模板已更新，建议重新开始分析。", "warning", 4200);
        }
      } finally {
        busy.template = false;
      }
    },
  });
}

function openExportModal(kind: ExportKind) {
  if (!selectedSourceId.value) {
    pushToast("请先选择数据源。", "warning");
    return;
  }
  exportModal.open = true;
  exportModal.kind = kind;
  exportModal.range = historyWindow.value;
  exportModal.format = "csv";
}

function closeExportModal() {
  exportModal.open = false;
}

async function submitExportModal() {
  if (!selectedSourceId.value) return;

  busy.exportSubmit = true;
  try {
    let url = "";
    if (exportModal.kind === "clip") {
      const data = await apiGet<{ url: string }>(
        `/sources/${encodeURIComponent(selectedSourceId.value)}/export-clip`
      );
      url = data.url;
    } else {
      const range = resolveRange(exportModal.range);
      const query = new URLSearchParams({
        source_id: selectedSourceId.value,
        from: range.from,
        to: range.to,
        format: exportModal.format,
      });
      if (exportModal.kind === "history") {
        const data = await apiGet<{ url: string }>(`/export?${query.toString()}`);
        url = data.url;
      } else {
        const data = await apiGet<{ url: string }>(`/alerts/export?${query.toString()}`);
        url = data.url;
      }
    }

    window.open(resolveAssetUrl(url), "_blank", "noopener,noreferrer");
    closeExportModal();
    pushToast("导出任务已生成。", "success");
  } catch (error) {
    pushToast(extractErrorMessage(error), "error");
  } finally {
    busy.exportSubmit = false;
  }
}

function scrollToSection(section: SectionKey) {
  activeSection.value = section;
  const targetMap: Record<SectionKey, HTMLElement | null> = {
    overview: overviewSection.value,
    history: historySection.value,
    alerts: alertsSection.value,
  };
  targetMap[section]?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function syncActiveSection() {
  const sections: Array<{ key: SectionKey; el: HTMLElement | null }> = [
    { key: "overview", el: overviewSection.value },
    { key: "history", el: historySection.value },
    { key: "alerts", el: alertsSection.value },
  ];

  const current = sections
    .filter((item) => item.el)
    .reverse()
    .find((item) => (item.el as HTMLElement).getBoundingClientRect().top <= 140);

  if (current) {
    activeSection.value = current.key;
  }
}

watch([historyWindow, historyInterval], () => {
  if (selectedSourceId.value) {
    void refreshHistory();
  }
});

watch([historyMetric, historyRegionId], async () => {
  await nextTick();
  renderHistoryChart();
});

watch(drawerOpen, async () => {
  await nextTick();
  resizeHistoryChart();
});

onMounted(async () => {
  nowLabel.value = new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  clockTimer = window.setInterval(() => {
    nowLabel.value = new Date().toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }, 1000);

  window.addEventListener("scroll", syncActiveSection, { passive: true });
  window.addEventListener("resize", resizeHistoryChart);
  window.addEventListener("pointermove", handleRegionEditorPointerMove);
  window.addEventListener("pointerup", handleRegionEditorPointerUp);

  await Promise.all([loadSystemStatus(), loadSources()]);
  await nextTick();
  renderHistoryChart();
  syncActiveSection();

  pollTimer = window.setInterval(() => {
    void loadSystemStatus();
    if (selectedSourceId.value) {
      void loadAnalysisState(selectedSourceId.value);
      void loadRecentAlerts(selectedSourceId.value);
    }
  }, 15000);
});

onBeforeUnmount(() => {
  if (clockTimer) {
    window.clearInterval(clockTimer);
  }
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  clearReconnectTimer();
  clearHeartbeatTimer();
  disconnectRealtime();
  historyChart.value?.dispose();
  window.removeEventListener("scroll", syncActiveSection);
  window.removeEventListener("resize", resizeHistoryChart);
  window.removeEventListener("pointermove", handleRegionEditorPointerMove);
  window.removeEventListener("pointerup", handleRegionEditorPointerUp);
});
</script>

<style scoped>
.console-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  position: relative;
  max-width: 1560px;
  margin: 0 auto;
}

.nav-rail,
.config-drawer,
.workspace-header,
.panel,
.metric-card,
.toast-card,
.modal-card {
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.nav-rail {
  position: sticky;
  top: 24px;
  align-self: start;
  border-radius: 28px;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 48px);
}

.brand-lockup {
  border: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text);
}

.brand-lockup__mark {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, var(--primary-soft), #ffffff);
  color: var(--primary);
}

.brand-lockup__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
}

.brand-lockup__text strong {
  font-size: 13px;
  font-weight: 700;
}

.brand-lockup__text small {
  color: var(--muted);
  font-size: 11px;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.nav-item {
  border: 0;
  background: transparent;
  border-radius: 18px;
  min-height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--muted);
  font-size: 11px;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.nav-item:hover,
.nav-item.is-active {
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary);
  transform: translateY(-1px);
}

.workspace {
  min-width: 0;
}

.workspace-header {
  position: static;
  border-radius: 24px;
  padding: 14px 18px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.workspace-header__copy {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.workspace-header__copy h1 {
  font-size: clamp(26px, 3vw, 32px);
  line-height: 1;
  margin: 0;
  font-family: var(--font-display);
}

.workspace-header__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}

.workspace-content {
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-caption__title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.section-caption h2 {
  font-size: clamp(28px, 2.3vw, 34px);
  line-height: 1;
  font-weight: 800;
  letter-spacing: -0.03em;
  font-family: var(--font-display);
}

.section-caption__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.section-eyebrow,
.eyebrow,
.panel-kicker {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
  color: var(--muted);
}

.hero-grid,
.overview-grid,
.history-grid,
.alerts-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(280px, 0.95fr);
  gap: 14px;
  align-items: start;
}

.hero-grid {
  align-items: stretch;
}

.history-grid {
  align-items: stretch;
}

.alerts-grid {
  align-items: stretch;
}

.panel {
  border-radius: 24px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.panel--hero {
  gap: 14px;
}

.panel--fill {
  align-self: stretch;
  height: 100%;
}

.panel--chart,
.panel--history-side {
  height: clamp(420px, 56vh, 560px);
  min-height: 0;
}

.panel--insight {
  min-height: 0;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.panel-head h3 {
  font-size: 17px;
  line-height: 1.15;
}

.panel-head__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.panel-head__actions--hero {
  margin-left: auto;
  align-items: center;
  flex-wrap: nowrap;
}

.panel-head__actions--hero > .button {
  flex: 0 0 auto;
}

.panel-head--compact {
  align-items: center;
}

.source-trigger {
  flex: 0 1 248px;
  min-width: 0;
  min-height: 46px;
  padding: 0 14px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.8);
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}

.source-trigger__main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-trigger__icon {
  width: 36px;
  height: 36px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary);
  flex: none;
}

.source-trigger__copy {
  min-width: 0;
  display: block;
}

.source-trigger__copy strong {
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  display: block;
}

.video-stage {
  position: relative;
  min-height: 0;
  aspect-ratio: 16 / 9;
  border-radius: 24px;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 12%, rgba(37, 99, 235, 0.28), transparent 35%),
    linear-gradient(140deg, #0f172a 0%, #12324c 48%, #164e63 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.video-stage__frame,
.video-stage__grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.video-stage__frame {
  object-fit: contain;
  object-position: center;
}

.video-stage__grid {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.09) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.09) 1px, transparent 1px);
  background-size: 36px 36px;
}

.video-stage__empty {
  position: absolute;
  inset: 0;
  z-index: 2;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  text-align: center;
  color: rgba(248, 250, 252, 0.92);
}

.video-stage__empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.14);
  flex: none;
}

.video-stage__empty h4 {
  font-size: 20px;
  margin: 0;
}

.video-stage__footer {
  position: absolute;
  right: 16px;
  top: 16px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  color: rgba(248, 250, 252, 0.84);
  font-size: 12px;
}

.video-stage__footer > :last-child {
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(12px);
}

.action-bar,
.system-grid,
.metric-grid,
.history-stat-grid,
.alert-summary-grid {
  display: grid;
  gap: 12px;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
}

.action-bar > .button {
  flex: 1 1 160px;
}

.system-grid,
.metric-grid,
.alert-summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.history-stat-grid {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.insight-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 4px;
}

.system-card,
.metric-card,
.history-stat-card {
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.system-card span,
.metric-card small,
.history-stat-card span {
  color: var(--muted);
  font-size: 12px;
}

.system-card strong,
.metric-card strong,
.history-stat-card strong {
  display: block;
  margin: 10px 0 0;
  font-size: 24px;
  line-height: 1;
  font-family: var(--font-mono);
}

.metric-card[data-tone="danger"] strong {
  color: var(--danger);
}

.metric-card[data-tone="warning"] strong {
  color: var(--accent);
}

.metric-card[data-tone="primary"] strong {
  color: var(--primary);
}

.metric-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
}

.panel--alerts-summary {
  padding: 0;
  min-height: 0;
  overflow: hidden;
}

.panel--alerts-records {
  min-height: 0;
}

.alerts-summary-stack {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: repeat(4, minmax(0, 1fr));
}

.alerts-summary-item {
  min-height: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.alerts-summary-item + .alerts-summary-item {
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.alerts-summary-item strong {
  display: block;
  margin: 10px 0 0;
  font-size: 24px;
  line-height: 1;
  font-family: var(--font-mono);
}

.alerts-summary-item small {
  display: block;
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.alerts-summary-item[data-tone="danger"] strong {
  color: var(--danger);
}

.alerts-summary-item[data-tone="warning"] strong {
  color: var(--accent);
}

.alerts-summary-item[data-tone="primary"] strong {
  color: var(--primary);
}

.metric-card__icon,
.status-chip,
.soft-chip,
.button,
.icon-button,
.source-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.metric-card__icon {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary);
}

.insight-list,
.alert-stack,
.region-stack,
.source-stack,
.template-stack,
.drawer-region-stack,
.risk-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.region-stack--hero {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.stack-scroll {
  max-height: 440px;
  overflow-y: auto;
  padding-right: 4px;
}

.insight-list {
  list-style: none;
}

.insight-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.84);
  color: var(--text);
}

.button {
  gap: 8px;
  border: 1px solid transparent;
  border-radius: 16px;
  min-height: 46px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.button:hover {
  transform: translateY(-1px);
}

.button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
  transform: none;
}

.button--primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-strong));
  color: #ffffff;
}

.button--soft {
  background: rgba(37, 99, 235, 0.08);
  color: var(--primary);
  border-color: rgba(37, 99, 235, 0.12);
}

.button--ghost {
  background: rgba(255, 255, 255, 0.74);
  color: var(--text);
  border-color: rgba(148, 163, 184, 0.22);
}

.button--danger {
  color: var(--danger);
  border-color: rgba(220, 38, 38, 0.2);
}

.button--tiny {
  min-height: 38px;
  padding: 0 12px;
  font-size: 13px;
}

.button--full {
  width: 100%;
}

.status-chip,
.soft-chip {
  gap: 8px;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.7);
  color: var(--text);
}

.status-chip[data-tone="success"],
.soft-chip[data-tone="success"] {
  color: var(--success);
  background: rgba(34, 197, 94, 0.08);
  border-color: rgba(34, 197, 94, 0.2);
}

.soft-chip[data-tone="warning"] {
  color: var(--accent);
  background: rgba(249, 115, 22, 0.08);
  border-color: rgba(249, 115, 22, 0.18);
}

.soft-chip[data-tone="danger"] {
  color: var(--danger);
  background: rgba(220, 38, 38, 0.08);
  border-color: rgba(220, 38, 38, 0.18);
}

.region-row,
.alert-row,
.risk-row,
.source-card,
.template-card,
.drawer-region-card,
.history-row {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.region-row,
.risk-row,
.source-card,
.drawer-region-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.region-row__meta,
.risk-row__main,
.drawer-region-card__main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.risk-row__rank {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.region-row__meta strong,
.risk-row__main strong,
.drawer-region-card__main strong,
.source-card__copy strong,
.history-row strong,
.alert-row__content strong {
  display: block;
  font-size: 15px;
}

.region-row__meta small,
.risk-row__main small,
.drawer-region-card__main small,
.source-card__copy small,
.history-row small,
.alert-row__content small,
.empty-box {
  color: var(--muted);
  font-size: 12px;
}

.region-row__stats,
.risk-row__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 13px;
}

.region-swatch {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  flex: none;
}

.alert-row {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 14px;
}

.alert-row__icon {
  width: 32px;
  height: 32px;
  border-radius: 12px;
  background: rgba(249, 115, 22, 0.08);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.alert-row[data-tone="danger"] .alert-row__icon {
  background: rgba(220, 38, 38, 0.1);
  color: var(--danger);
}

.alert-row__content p {
  margin: 4px 0;
  color: var(--text);
}

.alert-row__value {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  font-family: var(--font-mono);
  font-size: 12px;
}

.alert-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-preview__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 12px;
}

.history-toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.history-toolbar__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  min-width: 0;
}

.history-toolbar__filters .field--select {
  min-width: 0;
}

.toggle-group {
  display: inline-flex;
  gap: 8px;
  padding: 6px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.toggle-group__item {
  border: 0;
  background: transparent;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 12px;
  font-size: 13px;
  color: var(--muted);
}

.toggle-group__item.is-active {
  background: rgba(37, 99, 235, 0.12);
  color: var(--primary);
  font-weight: 700;
}

.field,
.field--select {
  width: 100%;
  min-height: 46px;
  padding: 0 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.82);
  color: var(--text);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}

.field--textarea {
  min-height: 140px;
  padding: 12px 14px;
  resize: vertical;
  font-family: var(--font-mono);
}

.field--color {
  padding: 6px;
}

.form-grid {
  display: grid;
  gap: 12px;
}

.form-grid--double {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-surface {
  flex: 1;
  min-height: 0;
  height: auto;
}

.panel--history-side {
  min-height: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.history-row {
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-family: var(--font-mono);
}

.config-drawer {
  width: min(460px, calc(100vw - 40px));
  height: min(86vh, 920px);
  border-radius: 24px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.config-drawer--modal {
  background: var(--surface-strong);
}

.config-drawer__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.config-drawer__header h2 {
  font-size: 24px;
  margin: 6px 0 8px;
}

.drawer-note,
.confirm-copy {
  color: var(--muted);
  font-size: 13px;
}

.config-drawer__tabs {
  width: fit-content;
}

.config-drawer__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 4px;
}

.drawer-section {
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
  border-radius: 22px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.drawer-section__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.drawer-section__head h3 {
  font-size: 18px;
}

.drawer-section__actions {
  display: flex;
  gap: 8px;
}

.source-card__main {
  flex: 1;
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
}

.source-card.is-active {
  border-color: rgba(37, 99, 235, 0.34);
  background: rgba(37, 99, 235, 0.08);
}

.source-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 14px;
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary);
}

.source-card__copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-stack--picker {
  max-height: min(56vh, 420px);
  overflow-y: auto;
  padding-right: 4px;
}

.source-card--picker {
  width: 100%;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.source-card--picker:hover {
  transform: translateY(-1px);
}

.soft-chip--selected {
  color: var(--primary);
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.18);
}

.template-card {
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.icon-button {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.82);
  color: var(--text);
  cursor: pointer;
}

.icon-button--danger {
  color: var(--danger);
}

.toast-stack {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 40;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toast-card {
  min-width: 260px;
  max-width: 360px;
  border-radius: 18px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.toast-card[data-tone="error"] {
  border-color: rgba(220, 38, 38, 0.22);
}

.toast-card[data-tone="warning"] {
  border-color: rgba(249, 115, 22, 0.22);
}

.toast-card__icon {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.08);
  color: var(--primary);
}

.empty-box {
  border-radius: 18px;
  padding: 16px;
  background: rgba(248, 250, 252, 0.8);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  display: flex;
  align-items: center;
  gap: 10px;
}

.empty-box--drawer {
  font-size: 12px;
}

.empty-box--fill {
  flex: 1;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(10px);
  display: grid;
  place-items: center;
  padding: 20px;
}

.modal-card {
  width: min(560px, 100%);
  border-radius: 28px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.modal-card--large {
  width: min(720px, 100%);
}

.modal-card--region {
  width: min(1120px, 100%);
  height: min(88vh, 860px);
  min-height: 0;
}

.modal-card--picker {
  width: min(620px, 100%);
}

.modal-card--confirm {
  width: min(460px, 100%);
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.modal-head h3 {
  font-size: 24px;
  margin-top: 6px;
}

.modal-actions,
.preset-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.region-editor {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.9fr);
  gap: 18px;
}

.region-editor__stage-panel,
.region-editor__sidebar {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.region-editor__toolbar,
.region-editor__quick-row,
.region-editor__summary,
.region-editor__advanced-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.region-editor__toolbar-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.region-editor__quick-row {
  justify-content: flex-start;
}

.region-editor__quick-label {
  color: var(--muted);
  font-size: 12px;
}

.region-editor__stage {
  position: relative;
  flex: 1;
  min-height: 460px;
  border-radius: 24px;
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 18%, rgba(37, 99, 235, 0.22), transparent 36%),
    linear-gradient(140deg, #0f172a 0%, #12324c 48%, #164e63 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  user-select: none;
}

.region-editor__frame,
.region-editor__grid,
.region-editor__overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.region-editor__frame {
  object-fit: contain;
  object-position: center;
}

.region-editor__overlay {
  pointer-events: none;
}

.region-editor__reference {
  fill-opacity: 0.08;
  stroke-opacity: 0.34;
  stroke-width: 0.4;
  stroke-dasharray: 1.4 1.2;
  vector-effect: non-scaling-stroke;
}

.region-editor__draft-fill {
  fill-opacity: 0.2;
  stroke-opacity: 0.9;
  stroke-width: 0.5;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}

.region-editor__draft-fill.is-closed {
  cursor: grab;
  pointer-events: auto;
}

.region-editor__draft-line {
  fill: none;
  stroke-width: 0.5;
  stroke-linejoin: round;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}

.region-editor__handle {
  position: absolute;
  z-index: 3;
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.24);
  transform: translate(-50%, -50%);
  cursor: grab;
}

.region-editor__handle.is-active {
  cursor: grabbing;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.34);
}

.region-editor__handle.is-first {
  width: 18px;
  height: 18px;
}

.region-editor__fallback {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: rgba(248, 250, 252, 0.92);
  text-align: center;
}

.region-editor__fallback strong {
  display: block;
  font-size: 18px;
}

.region-editor__fallback small,
.region-editor__stage-meta,
.region-editor__advanced small {
  color: var(--muted);
  font-size: 12px;
}

.region-editor__fallback small {
  color: rgba(248, 250, 252, 0.72);
}

.region-editor__stage-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.region-editor__sidebar {
  border-radius: 24px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.16);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.region-editor__advanced {
  border-radius: 20px;
  padding: 14px;
  background: rgba(248, 250, 252, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.region-editor__advanced strong {
  display: block;
  margin-bottom: 4px;
}

.region-editor__advanced-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toggle-group--modal {
  width: fit-content;
}

.confirm-copy {
  line-height: 1.7;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.toast-enter-active,
.toast-leave-active,
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: all 0.22s ease;
}

.toast-enter-from,
.toast-leave-to,
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 1200px) {
  .hero-grid,
  .overview-grid,
  .history-grid,
  .alerts-grid {
    grid-template-columns: 1fr;
  }

  .history-toolbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .system-grid,
  .metric-grid,
  .alert-summary-grid,
  .action-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-header {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .panel-head__actions--hero {
    width: 100%;
    margin-left: 0;
    flex-wrap: wrap;
  }

  .source-trigger {
    flex-basis: 100%;
  }

  .history-grid {
    align-items: start;
  }

  .alerts-grid {
    align-items: start;
  }

  .panel--chart,
  .panel--history-side {
    height: auto;
  }

  .chart-surface {
    height: 320px;
  }

  .history-list {
    overflow: visible;
  }

  .alerts-summary-stack {
    height: auto;
    grid-template-rows: none;
  }

  .panel--alerts-summary {
    padding: 16px;
  }

  .alerts-summary-item {
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(255, 255, 255, 0.72);
  }

  .alerts-summary-item + .alerts-summary-item {
    border-top: 1px solid rgba(148, 163, 184, 0.16);
  }

  .region-editor {
    grid-template-columns: 1fr;
  }

  .modal-card--region {
    width: min(1120px, 100%);
    height: min(92vh, 980px);
  }

  .region-editor__stage {
    min-height: 320px;
  }
}

@media (max-width: 820px) {
  .console-shell {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .nav-rail {
    position: static;
    height: auto;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }

  .nav-list {
    flex-direction: row;
    justify-content: center;
  }

  .nav-item {
    min-height: 56px;
    min-width: 72px;
  }

  .workspace-header,
  .panel,
  .config-drawer,
  .metric-card,
  .system-card,
  .history-stat-card,
  .modal-card {
    border-radius: 22px;
  }

  .system-grid,
  .metric-grid,
  .alert-summary-grid,
  .action-bar,
  .form-grid--double {
    grid-template-columns: 1fr;
  }

  .section-caption,
  .drawer-section__head,
  .workspace-header__actions,
  .panel-head {
    align-items: flex-start;
    justify-content: flex-start;
  }

  .workspace-header__actions {
    width: 100%;
  }

  .source-trigger {
    flex-basis: 100%;
    min-width: 0;
  }

  .button,
  .status-chip,
  .soft-chip,
  .field {
    min-height: 44px;
  }

  .config-drawer {
    width: min(100%, 520px);
    height: min(88vh, 920px);
  }

  .history-toolbar__filters {
    grid-template-columns: 1fr;
  }

  .stack-scroll {
    max-height: none;
  }

  .alerts-summary-stack {
    gap: 12px;
  }
}
</style>
