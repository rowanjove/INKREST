<script setup lang="ts">
import { Delete, Edit, InfoFilled, Lock } from '@element-plus/icons-vue'
import type { PluginInfo } from '../../utils/pluginManagerConfig'

defineProps<{
  plugins: PluginInfo[]
  loading: boolean
  onShowDetail: (plugin: PluginInfo) => void
  onShowConfig: (plugin: PluginInfo) => void
  onDelete: (plugin: PluginInfo) => void
  onToggle: (plugin: PluginInfo) => void
  onTrust: (plugin: PluginInfo) => void
}>()
</script>

<template>
  <div v-loading="loading" class="plugins-grid-container">
    <div v-if="plugins.length > 0" class="plugins-grid">
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
            <div class="action-left">
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
            <div class="action-right">
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
    </div>
    <el-empty v-else description="没有找到匹配的插件" />
  </div>
</template>

<style scoped>
.plugins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

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

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-left {
  display: flex;
  gap: 6px;
}

.action-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.switch-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 8px;
}
</style>
