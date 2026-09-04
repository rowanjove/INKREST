<script setup lang="ts">
import { computed, onMounted, type Component } from 'vue'
import {
  Collection,
  Cpu,
  DataAnalysis,
  DataLine,
  Document,
  Edit,
  Files,
  Folder,
  List,
  MoreFilled,
  Plus,
  Reading,
  Setting,
  Tools,
} from '@element-plus/icons-vue'

import { usePluginNavigationStore } from '../../stores/pluginNavigation'
import type { PluginNavigationContribution } from '../../entities/plugin/pluginNavigation'

const props = defineProps<{
  inProject: boolean
  activePath: string
}>()

const emit = defineEmits<{
  navigate: [path: string]
}>()

const pluginNav = usePluginNavigationStore()

onMounted(() => {
  if (pluginNav.status === 'idle') {
    void pluginNav.fetchNavigation()
  }
})

const displayItems = computed<PluginNavigationContribution[]>(() =>
  props.inProject ? pluginNav.activeProjectItems : pluginNav.activeLibraryItems,
)

const overflowItems = computed<PluginNavigationContribution[]>(() =>
  props.inProject ? pluginNav.overflowProjectItems : pluginNav.overflowLibraryItems,
)

const iconMap: Record<string, Component> = {
  collection: Collection,
  library: Collection,
  document: Document,
  inspection: DataAnalysis,
  radar: DataAnalysis,
  chart: DataLine,
  tools: Tools,
  cpu: Cpu,
  edit: Edit,
  list: List,
  folder: Folder,
  reading: Reading,
  create: Plus,
  settings: Setting,
  files: Files,
}

function resolveIcon(iconName?: string): Component {
  if (!iconName) return Cpu
  return iconMap[iconName.toLowerCase()] || Cpu
}

function handleGo(path: string) {
  emit('navigate', path)
}
</script>

<template>
  <div v-if="displayItems.length > 0" class="plugin-sidebar-group">
    <div class="plugin-group-header">
      <small>{{ inProject ? '作品插件' : '书库插件' }}</small>
    </div>

    <div class="plugin-items-scroll">
      <button
        v-for="item in displayItems"
        :key="item.id"
        type="button"
        class="nav-item plugin-nav-item"
        :class="{ active: activePath === item.path }"
        :title="item.title"
        :aria-label="item.title"
        @click="handleGo(item.path)"
      >
        <el-icon class="plugin-icon"><component :is="resolveIcon(item.icon)" /></el-icon>
        <span class="plugin-title">{{ item.title }}</span>
      </button>

      <el-dropdown
        v-if="overflowItems.length > 0"
        trigger="click"
        placement="right-start"
        @command="handleGo"
      >
        <button type="button" class="nav-item plugin-more-btn" title="查看更多插件">
          <el-icon><MoreFilled /></el-icon>
          <span>更多插件…</span>
        </button>
        <template #dropdown>
          <el-dropdown-menu class="plugin-overflow-menu">
            <el-dropdown-item
              v-for="item in overflowItems"
              :key="item.id"
              :command="item.path"
            >
              <el-icon><component :is="resolveIcon(item.icon)" /></el-icon>
              <span>{{ item.title }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style scoped>
.plugin-sidebar-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.plugin-group-header {
  padding: 2px 14px;
  color: var(--color-text-sidebar-dim);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.plugin-items-scroll {
  max-height: 220px;
  overflow-y: auto;
  display: grid;
  gap: 4px;
  padding-right: 2px;
}

.plugin-items-scroll::-webkit-scrollbar {
  width: 4px;
}

.plugin-items-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 4px;
}

.nav-item {
  width: 100%;
  height: 38px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: var(--color-text-sidebar-muted);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  text-align: left;
  transition: all var(--motion-fast) var(--ease-standard);
}

.nav-item .el-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}

.plugin-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--color-text-sidebar);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(198, 111, 79, 0.38);
  box-shadow: inset 3px 0 0 var(--color-primary);
  color: var(--color-text-sidebar);
}

.plugin-more-btn {
  color: var(--color-text-sidebar-dim);
  font-size: 12.5px;
}
</style>
