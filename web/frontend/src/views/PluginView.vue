<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Cpu } from '@element-plus/icons-vue'

import { usePluginNavigationStore } from '../stores/pluginNavigation'
import { useProjectStore } from '../stores/project'
import PluginViewHost from '../app/plugins/PluginViewHost.vue'

const route = useRoute()
const router = useRouter()
const pluginNav = usePluginNavigationStore()
const projectStore = useProjectStore()

const pluginId = computed(() => String(route.params.pluginId || ''))
const viewId = computed(() => String(route.params.viewId || ''))
const isProjectScope = computed(() => route.path.startsWith('/extensions/project/'))

const currentNav = computed(() => {
  const all = [...pluginNav.libraryItems, ...pluginNav.projectItems]
  return all.find(
    (item) => item.plugin_id === pluginId.value && item.view === viewId.value,
  )
})

const pageTitle = computed(() => currentNav.value?.title || '插件页面')
const pluginDisplayName = computed(() => currentNav.value?.plugin_name || pluginId.value)

function handleBack() {
  if (isProjectScope.value && projectStore.currentProject?.id) {
    void router.push('/workspace')
  } else {
    void router.push('/')
  }
}
</script>

<template>
  <div class="plugin-fullscreen-view">
    <!-- 沉浸式插件顶栏 -->
    <header class="plugin-compact-bar">
      <div class="bar-left">
        <el-button
          text
          size="small"
          :icon="ArrowLeft"
          class="back-btn"
          @click="handleBack"
        >
          {{ isProjectScope ? '返回概览' : '返回书库' }}
        </el-button>
        <span class="bar-divider">/</span>
        <span class="plugin-badge">插件</span>
        <strong class="plugin-title">{{ pluginDisplayName }}</strong>
        <span class="view-title">· {{ pageTitle }}</span>
      </div>

      <div class="bar-right">
        <el-tag size="small" type="info" effect="plain" class="scope-tag">
          {{ isProjectScope ? '作品级作用域' : '书库级作用域' }}
        </el-tag>
        <router-link to="/plugins" class="manage-link">
          插件管理
        </router-link>
      </div>
    </header>

    <!-- 插件错误或未命中 -->
    <div v-if="!currentNav" class="plugin-missing-card">
      <el-icon class="missing-icon"><Cpu /></el-icon>
      <h3>插件或视图暂不可用</h3>
      <p>该插件可能未启用、未通过安全信任，或未声明当前区域的视图贡献。</p>
      <div class="actions">
        <el-button type="primary" @click="router.push('/plugins')">前往插件中心</el-button>
        <el-button @click="handleBack">返回</el-button>
      </div>
    </div>

    <!-- 铺满的插件宿主容器 -->
    <div v-else class="plugin-host-fullscreen">
      <PluginViewHost
        :plugin-id="pluginId"
        :view-id="viewId"
        :surface="isProjectScope ? 'project_sidebar' : 'library_sidebar'"
        :project-id="isProjectScope ? projectStore.currentProject?.id : undefined"
      />
    </div>
  </div>
</template>

<style scoped>
.plugin-fullscreen-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-app);
  color: var(--color-text-primary);
  overflow: hidden;
}

.plugin-compact-bar {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 20px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
  flex-shrink: 0;
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.back-btn {
  font-weight: 600;
  padding: 4px 8px;
}

.bar-divider {
  color: var(--color-text-subtle);
  font-size: 13px;
}

.plugin-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-primary-soft, rgba(198, 111, 79, 0.1));
  color: var(--color-primary, #c66f4f);
}

.plugin-title {
  font-size: 13.5px;
  font-weight: 750;
  color: var(--color-text-strong);
}

.view-title {
  font-size: 13px;
  color: var(--color-text-muted);
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.manage-link {
  font-size: 12px;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color var(--motion-fast);
}

.manage-link:hover {
  color: var(--color-primary);
}

.plugin-host-fullscreen {
  flex: 1;
  width: 100%;
  height: calc(100% - 44px);
  background: var(--color-bg-app);
  display: flex;
  overflow: hidden;
}

.plugin-missing-card {
  margin: 60px auto;
  max-width: 480px;
  text-align: center;
  padding: 36px 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
}

.missing-icon {
  font-size: 48px;
  color: var(--color-text-subtle);
  margin-bottom: 16px;
}

.plugin-missing-card h3 {
  margin: 0 0 8px;
  color: var(--color-text-strong);
  font-size: 18px;
}

.plugin-missing-card p {
  margin: 0 0 24px;
  color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1.6;
}

.plugin-missing-card .actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
