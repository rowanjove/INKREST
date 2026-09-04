<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Cpu } from '@element-plus/icons-vue'

import PageShell from '../shared/ui/PageShell.vue'
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
  <PageShell
    :title="pageTitle"
    :description="`所属插件: ${pluginDisplayName} · 区域: ${isProjectScope ? '作品级' : '书库级'}`"
    :eyebrow="`扩展 · ${pluginDisplayName}`"
  >
    <template #actions>
      <el-button text :icon="ArrowLeft" @click="handleBack">
        {{ isProjectScope ? '返回概览' : '返回书库' }}
      </el-button>
    </template>

    <div v-if="!currentNav" class="plugin-missing-card">
      <el-icon class="missing-icon"><Cpu /></el-icon>
      <h3>插件或视图暂不可用</h3>
      <p>该插件可能未启用、未通过安全信任，或未声明当前区域的视图贡献。</p>
      <div class="actions">
        <el-button type="primary" @click="router.push('/plugins')">前往扩展中心</el-button>
        <el-button @click="handleBack">返回</el-button>
      </div>
    </div>

    <div v-else class="plugin-host-container">
      <PluginViewHost
        :plugin-id="pluginId"
        :view-id="viewId"
        :surface="isProjectScope ? 'project_sidebar' : 'library_sidebar'"
        :project-id="projectStore.currentProject?.id"
      />
    </div>
  </PageShell>
</template>

<style scoped>
.plugin-missing-card {
  margin: 40px auto;
  max-width: 480px;
  text-align: center;
  padding: 36px 24px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
}

.missing-icon {
  font-size: 48px;
  color: var(--color-text-dim);
  margin-bottom: 16px;
}

.plugin-missing-card h3 {
  margin: 0 0 8px;
  color: var(--color-text-primary);
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

.plugin-host-container {
  width: 100%;
  min-height: 480px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.plugin-host-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 480px;
  padding: 40px 20px;
  text-align: center;
}

.placeholder-content {
  max-width: 520px;
}

.host-icon {
  font-size: 44px;
  color: var(--color-primary);
  margin-bottom: 16px;
}

.placeholder-content h3 {
  margin: 0 0 12px;
  font-size: 20px;
  color: var(--color-text-primary);
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.meta code {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  font-family: monospace;
}

.tip {
  color: var(--color-text-dim);
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}
</style>
