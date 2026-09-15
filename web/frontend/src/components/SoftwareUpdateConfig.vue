<script setup lang="ts">
import { computed } from 'vue'
import { useUpdater } from '../composables/useUpdater'

const props = withDefaults(
  defineProps<{
    bare?: boolean
  }>(),
  {
    bare: false,
  },
)

const isDesktop = computed(
  () => typeof window !== 'undefined' && Boolean(window.electronAPI),
)

const {
  settings,
  status,
  isSaving,
  isChecking,
  hasUpdate,
  isNotAvailable,
  hasError,
  settingsError,
  updateSettings,
  checkForUpdates,
  openReleasePage,
} = useUpdater()

const lastCheckedText = computed(() => {
  if (!settings.value.lastCheckedAt) return '未检查过'
  const date = new Date(settings.value.lastCheckedAt)
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
})

const onToggleAutoCheck = (val: boolean) => {
  void updateSettings({ autoCheck: val })
}

const onToggleCheckPrerelease = (val: boolean) => {
  void updateSettings({ checkPrerelease: val })
}
</script>

<template>
  <section v-if="isDesktop" id="software-update" class="update-card" :class="{ 'is-bare': bare }">
    <!-- 头部工具栏与版本信息 -->
    <div class="update-heading">
      <div class="heading-left">
        <span class="eyebrow">ONLINE UPDATE</span>
        <div class="title-with-badge">
          <h3>在线更新</h3>
          <span class="version-badge">v{{ status.currentVersion }}</span>
          <span v-if="hasUpdate" class="status-pill update-available">
            发现新版本 v{{ status.updateInfo?.version }}
          </span>
        </div>
        <p class="sub-hint">
          仅从 GitHub 官方发布源检查更新；安装包请前往官方发布页手动下载。
          <span class="sub-meta">当前源：<strong>GitHub 官方源</strong> · 上次检查：{{ lastCheckedText }}</span>
        </p>
      </div>
      <div class="heading-action">
        <el-button
          type="primary"
          :plain="!hasUpdate"
          :loading="isChecking"
          @click="checkForUpdates"
        >
          {{ isChecking ? '正在检查...' : '检查更新' }}
        </el-button>
      </div>
    </div>

    <!-- 1. 自动获取更新开关区域 -->
    <div class="config-block">
      <div class="block-title">
        <span class="section-icon">⚙</span>
        <span>更新获取策略</span>
      </div>
      <div class="toggles-grid">
        <div class="toggle-card">
          <div class="toggle-text">
            <strong>自动检查更新</strong>
            <p>应用启动后静默查询新版本（延迟 15 秒）；关闭后仅在手动点击时检测。</p>
          </div>
          <el-switch
            :model-value="settings.autoCheck"
            :disabled="isSaving"
            @update:model-value="onToggleAutoCheck"
          />
        </div>

        <div class="toggle-card">
          <div class="toggle-text">
            <strong>接收体验预览版本</strong>
            <p>包含内测与 Beta 尝鲜构建，适合希望提前体验新特性的创作者。</p>
          </div>
          <el-switch
            :model-value="settings.checkPrerelease"
            :disabled="isSaving"
            @update:model-value="onToggleCheckPrerelease"
          />
        </div>
      </div>
    </div>

    <!-- 2. 官方更新源区域 -->
    <div class="config-block">
      <div class="block-title">
        <span class="section-icon">↻</span>
        <span>更新源</span>
        <span class="title-subhint">为保证发布者可信边界，不支持第三方代理或自定义 Generic feed</span>
      </div>

      <div class="sources-grid">
        <div class="source-card active">
          <div class="source-top">
            <span class="source-name">GitHub 官方源</span>
            <span class="source-badge">官方通道</span>
          </div>
          <p class="source-desc">仅从项目 GitHub Releases 官方通道校验版本与数字签名</p>
          <span class="source-hint">安装包请前往官方发布页手动下载</span>
        </div>
      </div>

      <p v-if="settingsError" class="custom-error" role="alert">{{ settingsError }}</p>
    </div>

    <!-- 3. 更新状态与操作交互看板 -->
    <div class="status-panel">
      <!-- 检查中 -->
      <div v-if="isChecking" class="status-row checking-state">
        <span class="is-loading">↻</span>
        <span>正在连接更新源查询最新版本信息，请稍候...</span>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="hasError" class="alert-box error-alert">
        <div class="alert-content">
          <span class="alert-icon">!</span>
          <div class="alert-texts">
            <strong>更新检测未完成</strong>
            <p>{{ status.error }}</p>
          </div>
        </div>
      </div>

      <!-- 发现新版本 -->
      <div v-else-if="hasUpdate" class="alert-box update-available-box">
        <div class="update-header-info">
          <div class="update-meta">
            <span class="new-tag">NEW</span>
            <strong class="new-version">栖墨 v{{ status.updateInfo?.version }} 现已发布</strong>
            <span v-if="status.updateInfo?.releaseDate" class="release-date">
              发布时间：{{ new Date(status.updateInfo.releaseDate).toLocaleDateString() }}
            </span>
          </div>
          <div class="update-actions">
            <el-button
              type="primary"
              size="default"
              @click="openReleasePage()"
            >
              前往官方发布页
            </el-button>
          </div>
        </div>

        <!-- 更新日志 -->
        <div v-if="status.updateInfo?.releaseNotes" class="release-notes-box">
          <div class="notes-head">更新日志：</div>
          <div class="notes-content">{{ status.updateInfo.releaseNotes }}</div>
        </div>
      </div>

      <!-- 当前已是最新版 -->
      <div v-else-if="isNotAvailable" class="up-to-date-box">
        <span class="up-icon">✓</span>
        <span>已是最新版本（v{{ status.currentVersion }}），暂无可用更新。</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.update-card {
  scroll-margin-top: 72px;
  display: grid;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}

.update-card.is-bare {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 4px 0 !important;
  border-radius: 0 !important;
}

.update-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--color-border);
}

.heading-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.eyebrow {
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.title-with-badge h3 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 16px;
  font-weight: 750;
  line-height: 1.3;
}

.version-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f0ede9);
  color: var(--color-text-muted, #736b63);
  font-size: 11px;
  font-weight: 600;
  font-family: ui-monospace, monospace;
}

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.status-pill.update-available {
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
}

.sub-hint {
  margin: 3px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.sub-meta {
  display: inline-block;
  margin-left: 6px;
  color: var(--color-text-subtle, #888);
}

.heading-action {
  flex-shrink: 0;
}

.config-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-strong, #222);
  font-size: 13px;
  font-weight: 650;
}

.section-icon {
  font-size: 14px;
  color: var(--color-primary);
}

.title-subhint {
  color: var(--color-text-muted, #888);
  font-size: 11px;
  font-weight: normal;
  margin-left: 6px;
}

.toggles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.toggle-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e5e0da);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface, #fff);
  box-sizing: border-box;
}

.toggle-text strong {
  display: block;
  color: var(--color-text-strong, #222);
  font-size: 12px;
  margin-bottom: 3px;
}

.toggle-text p {
  margin: 0;
  color: var(--color-text-muted, #888);
  font-size: 11px;
  line-height: 1.4;
}

.sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.source-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e5e0da);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface, #fff);
  box-sizing: border-box;
}

.source-card.active {
  border-color: var(--color-primary, #409eff);
  background: var(--color-primary-soft, #f0f7ff);
  box-shadow: 0 0 0 1px var(--color-primary, #409eff);
}

.source-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.source-name {
  color: var(--color-text-strong, #222);
  font-size: 12px;
  font-weight: 650;
}

.source-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-primary, #409eff);
  color: #fff;
}

.source-desc {
  margin: 0;
  color: var(--color-text-muted, #777);
  font-size: 11px;
  line-height: 1.45;
}

.source-hint {
  font-size: 10px;
  color: var(--color-text-subtle, #999);
}

.custom-error {
  color: #f56c6c;
  font-size: 11px;
  margin: 4px 0 0;
}

.status-panel {
  margin-top: 4px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted, #777);
  padding: 8px 0;
}

.is-loading {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.alert-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-md, 8px);
}

.error-alert {
  background: #fef0f0;
  border: 1px solid #fde2e2;
}

.error-alert .alert-icon {
  color: #f56c6c;
  font-size: 18px;
  font-weight: bold;
}

.alert-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.alert-texts strong {
  display: block;
  font-size: 12px;
  color: #303133;
  margin-bottom: 3px;
}

.alert-texts p {
  margin: 0;
  font-size: 11px;
  color: #606266;
  line-height: 1.5;
}

.update-available-box {
  background: #fdf6ec;
  border: 1px solid #faecd8;
}

.update-header-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.update-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.new-tag {
  background: #e6a23c;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.new-version {
  color: #303133;
  font-size: 13px;
}

.release-date {
  color: #909399;
  font-size: 11px;
}

.update-actions {
  display: flex;
  gap: 8px;
}

.release-notes-box {
  background: #fff;
  border: 1px solid #faecd8;
  border-radius: 6px;
  padding: 10px 12px;
  max-height: 160px;
  overflow-y: auto;
}

.notes-head {
  font-size: 11px;
  font-weight: 650;
  color: #606266;
  margin-bottom: 4px;
}

.notes-content {
  font-size: 11px;
  color: #606266;
  line-height: 1.55;
  white-space: pre-wrap;
}

.up-to-date-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--color-bg-subtle, #faf8f5);
  border: 1px solid var(--color-border, #e5e0da);
  border-radius: 6px;
  font-size: 11px;
  color: var(--color-text-muted, #777);
}

.up-icon {
  color: #67c23a;
  font-size: 14px;
}

@media (max-width: 720px) {
  .update-heading {
    flex-direction: column;
  }
  .heading-action {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
