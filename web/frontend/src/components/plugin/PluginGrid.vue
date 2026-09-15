<script setup lang="ts">
import { Delete, Edit, InfoFilled, Lock } from '@element-plus/icons-vue'
import type { PluginInfo } from '../../utils/pluginManagerConfig'

withDefaults(
  defineProps<{
    plugins: PluginInfo[]
    loading: boolean
    viewMode?: 'list' | 'card'
    onShowDetail: (plugin: PluginInfo) => void
    onShowConfig: (plugin: PluginInfo) => void
    onDelete: (plugin: PluginInfo) => void
    onToggle: (plugin: PluginInfo) => void
    onTrust: (plugin: PluginInfo) => void
  }>(),
  {
    viewMode: 'list',
  }
)
</script>

<template>
  <div v-loading="loading" class="plugins-grid-container">
    <div v-if="plugins.length > 0" :class="['plugins-grid', viewMode === 'list' ? 'list-mode' : 'card-mode']">
      <!-- 窄行列表模式 (Narrow Row List Mode) -->
      <template v-if="viewMode === 'list'">
        <el-card
          v-for="plugin in plugins"
          :key="plugin.name"
          class="plugin-item-card plugin-row-card"
          shadow="hover"
        >
          <div class="plugin-row-body">
            <!-- 状态 + 标题 + 属性 + 简介 -->
            <div class="row-left">
              <span class="status-indicator" :class="{ enabled: plugin.enabled }">
                <span v-if="plugin.enabled" class="pulse-dot" />
                <span class="status-badge-text">
                  {{
                    plugin.enabled
                      ? '运行中'
                      : plugin.requires_reauthorization
                        ? '需重新授权'
                        : plugin.trusted === false
                          ? '待信任'
                          : '已禁用'
                  }}
                </span>
              </span>

              <div class="row-title-area">
                <div class="row-title-bar">
                  <h3 class="row-plugin-name" :title="plugin.display_name">{{ plugin.display_name }}</h3>
                  <small class="v-tag">v{{ plugin.version }}</small>
                  <el-tag
                    size="small"
                    :type="plugin.risk_level === 'high' ? 'danger' : plugin.risk_level === 'medium' ? 'warning' : 'info'"
                  >
                    {{ plugin.risk_level === 'high' ? '高风险' : plugin.risk_level === 'medium' ? '中风险' : '低风险' }}
                  </el-tag>
                  <el-tag size="small" type="info" class="plugin-type-tag">{{ plugin.plugin_type }}</el-tag>
                  <span class="source-tag" :class="plugin.source">{{ plugin.source }}</span>
                  <span v-if="plugin.author" class="row-author">by {{ plugin.author }}</span>
                </div>
                <p class="row-plugin-desc" :title="plugin.description">{{ plugin.description || '暂无详细说明。' }}</p>
              </div>
            </div>

            <!-- 权限标签预览 (中间紧凑区) -->
            <div class="row-caps" v-if="plugin.capability_details && plugin.capability_details.length > 0">
              <span
                v-for="permission in plugin.capability_details.slice(0, 2)"
                :key="permission.id"
                class="cap-pill"
                :title="permission.description || permission.label"
              >
                {{ permission.label }}
              </span>
              <span v-if="plugin.capability_details.length > 2" class="cap-pill more">
                +{{ plugin.capability_details.length - 2 }}
              </span>
            </div>

            <!-- 操作按钮与开关 (右侧) -->
            <div class="row-right">
              <div class="row-actions">
                <el-button
                  v-if="plugin.source === 'local' && !plugin.trusted"
                  size="small"
                  type="warning"
                  plain
                  :icon="Lock"
                  @click="onTrust(plugin)"
                >
                  {{ plugin.requires_reauthorization ? '重新授权' : '检查并信任' }}
                </el-button>
                <el-button size="small" :icon="InfoFilled" @click="onShowDetail(plugin)">
                  详情
                </el-button>
                <el-button size="small" :icon="Edit" @click="onShowConfig(plugin)">配置</el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :icon="Delete"
                  @click="onDelete(plugin)"
                >
                  删除
                </el-button>
              </div>

              <div class="row-divider" />

              <div class="row-switch">
                <span class="switch-label">{{ plugin.enabled ? '启用' : '关闭' }}</span>
                <el-switch
                  :model-value="plugin.enabled"
                  :disabled="plugin.source === 'local' && !plugin.trusted"
                  active-color="#c66f4f"
                  @change="onToggle(plugin)"
                />
              </div>
            </div>
          </div>
        </el-card>
      </template>

      <!-- 卡片网格模式 (Card Grid Mode - 分层布局消除溢出) -->
      <template v-else>
        <el-card v-for="plugin in plugins" :key="plugin.name" class="plugin-item-card" shadow="hover">
          <div class="plugin-card-body">
            <div class="card-top">
              <span class="status-indicator" :class="{ enabled: plugin.enabled }">
                <span v-if="plugin.enabled" class="pulse-dot" />
                {{
                  plugin.enabled
                    ? '运行中'
                    : plugin.requires_reauthorization
                      ? '需重新授权'
                      : plugin.trusted === false
                        ? '待信任'
                        : '已禁用'
                }}
              </span>
              <div class="risk-tags">
                <el-tag
                  size="small"
                  :type="plugin.risk_level === 'high' ? 'danger' : plugin.risk_level === 'medium' ? 'warning' : 'info'"
                >
                  {{ plugin.risk_level === 'high' ? '高风险' : plugin.risk_level === 'medium' ? '中风险' : '低风险' }}
                </el-tag>
                <el-tag size="small" type="info" class="plugin-type-tag">{{ plugin.plugin_type }}</el-tag>
              </div>
            </div>

            <div class="plugin-title-info">
              <div class="plugin-display-name">
                <h3>{{ plugin.display_name }}</h3>
                <small class="v-tag">v{{ plugin.version }}</small>
              </div>
              <p class="plugin-desc">{{ plugin.description || '暂无详细说明。' }}</p>
            </div>

            <div class="plugin-meta-bottom">
              <div class="author-info">
                <span>作者: {{ plugin.author || '未知' }}</span>
                <span class="source-tag" :class="plugin.source">{{ plugin.source }}</span>
              </div>
              <div class="permission-preview">
                <span
                  v-for="permission in plugin.capability_details.slice(0, 3)"
                  :key="permission.id"
                >
                  {{ permission.label }}
                </span>
                <span v-if="plugin.capability_details.length > 3">
                  +{{ plugin.capability_details.length - 3 }}
                </span>
              </div>
            </div>

            <div class="card-actions">
              <div class="action-top-row">
                <el-button size="small" :icon="InfoFilled" @click="onShowDetail(plugin)">
                  详情
                </el-button>
                <el-button size="small" :icon="Edit" @click="onShowConfig(plugin)">配置</el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :icon="Delete"
                  @click="onDelete(plugin)"
                >
                  删除
                </el-button>
              </div>
              <div class="action-bottom-row">
                <el-button
                  v-if="plugin.source === 'local' && !plugin.trusted"
                  size="small"
                  type="warning"
                  plain
                  :icon="Lock"
                  class="trust-btn"
                  @click="onTrust(plugin)"
                >
                  {{ plugin.requires_reauthorization ? '重新授权' : '检查并信任' }}
                </el-button>
                <div class="card-switch-box">
                  <span class="switch-label">{{ plugin.enabled ? '启用' : '关闭' }}</span>
                  <el-switch
                    :model-value="plugin.enabled"
                    :disabled="plugin.source === 'local' && !plugin.trusted"
                    active-color="#c66f4f"
                    @change="onToggle(plugin)"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </template>
    </div>
    <el-empty v-else description="没有找到匹配的插件" />
  </div>
</template>

<style scoped>
/* 网格容器模式 */
.plugins-grid.card-mode {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.plugins-grid.list-mode {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 窄行视图卡片 */
.plugin-row-card {
  border-radius: 10px !important;
  transition: all 0.2s ease;
  border-color: #f1f3f5 !important;
}

.plugin-row-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06) !important;
  border-color: rgba(198, 111, 79, 0.3) !important;
}

.plugin-row-card :deep(.el-card__body) {
  padding: 12px 18px !important;
}

.plugin-row-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.row-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.row-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.row-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  overflow: hidden;
}

.row-plugin-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
}

.row-author {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  white-space: nowrap;
}

.row-plugin-desc {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-muted, #6b7280);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 520px;
}

.row-caps {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.cap-pill {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--color-bg-surface-muted, #f3f4f6);
  color: var(--color-text-muted, #4b5563);
  font-size: 11px;
  white-space: nowrap;
}

.cap-pill.more {
  background: #e5e7eb;
  font-weight: 600;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.row-divider {
  width: 1px;
  height: 20px;
  background-color: var(--el-border-color-light, #e5e7eb);
}

.row-switch {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-badge-text {
  white-space: nowrap;
}

/* 卡片视图卡片 */
.plugin-item-card {
  border-radius: 12px !important;
  overflow: hidden;
  transition: all 0.2s ease;
}

.plugin-item-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08) !important;
  border-color: rgba(198, 111, 79, 0.25) !important;
}

.plugin-card-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 5px;
}

.status-indicator {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-danger);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-indicator.enabled {
  color: var(--color-success);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  background: var(--color-success);
  border-radius: 99px;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
}

.plugin-title-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.plugin-display-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-display-name h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #111827;
}

.v-tag {
  background: #eef2f7;
  color: #4b5563;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.plugin-desc {
  margin: 0;
  color: var(--text-muted);
  font-size: 13.5px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.plugin-meta-bottom {
  border-top: 1px solid #f3f4f6;
  padding-top: 12px;
}

.author-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.permission-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 9px;
}

.permission-preview span {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  font-size: 10px;
}

.source-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 1px 5px;
  border-radius: 3px;
  background: #e5e7eb;
}

.source-tag.local {
  background: #fef3c7;
  color: var(--color-warning);
}

.source-tag.entry_point {
  background: #d1fae5;
  color: var(--color-success);
}

/* 卡片操作区：2 行清晰布局，消除横向溢出 */
.card-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.action-top-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.action-bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.trust-btn {
  flex: 1;
  max-width: 140px;
}

.card-switch-box {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.switch-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

@media (max-width: 900px) {
  .plugin-row-body {
    flex-wrap: wrap;
    gap: 12px;
  }
  .row-caps {
    display: none;
  }
}
</style>
