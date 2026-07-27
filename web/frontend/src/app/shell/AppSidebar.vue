<script setup lang="ts">
import { computed, defineAsyncComponent, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Collection,
  Cpu,
  DataLine,
  Document,
  Edit,
  Files,
  List,
  Plus,
  Reading,
  Setting,
} from '@element-plus/icons-vue'

import {
  GLOBAL_NAV_ITEMS,
  PROJECT_NAV_ITEMS,
  activeNavigationId,
  type NavigationIcon,
} from '../router/navigation'
import { useProjectStore } from '../../stores/project'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'

const RuntimeStatusButton = defineAsyncComponent(() => import('./RuntimeStatusButton.vue'))

defineProps<{
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()

defineEmits<{ openDiagnostics: [] }>()

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const inProject = computed(() => Boolean(projectStore.currentProject?.id))
const primaryItems = computed(() =>
  inProject.value ? PROJECT_NAV_ITEMS : GLOBAL_NAV_ITEMS.slice(0, 2),
)
const utilityItems = computed(() =>
  inProject.value
    ? GLOBAL_NAV_ITEMS.filter((item) => ['library', 'settings', 'extensions'].includes(item.id))
    : GLOBAL_NAV_ITEMS.slice(2),
)
const activeId = computed(() => activeNavigationId(route.path, inProject.value))

const iconMap: Record<NavigationIcon, Component> = {
  library: Collection,
  create: Plus,
  overview: DataLine,
  planning: List,
  manuscript: Edit,
  production: Files,
  publishing: Reading,
  settings: Setting,
  extensions: Cpu,
}

const go = (path: string) => void router.push(path)
</script>

<template>
  <aside class="app-sidebar">
    <button class="brand" type="button" aria-label="返回书库" @click="go('/')">
      <img src="/favicon.svg" alt="" class="brand__logo" />
      <span class="brand__copy">
        <span><strong>栖墨</strong><em>INKREST</em></span>
        <small>本地长篇创作空间</small>
      </span>
    </button>

    <button
      v-if="inProject"
      type="button"
      class="project-switcher"
      title="返回书库切换作品"
      @click="go('/')"
    >
      <Document aria-hidden="true" />
      <span>{{ projectStore.currentProject?.name }}</span>
    </button>

    <nav class="nav-group" :aria-label="inProject ? '项目导航' : '全局导航'">
      <button
        v-for="item in primaryItems"
        :key="item.id"
        type="button"
        class="nav-item"
        :class="{ active: activeId === item.id }"
        :aria-current="activeId === item.id ? 'page' : undefined"
        @click="go(item.path)"
      >
        <el-icon><component :is="iconMap[item.icon]" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-utility">
      <RuntimeStatusButton
        v-if="inProject"
        :backend-status="backendStatus"
        :backend-unreachable="backendUnreachable"
        @open="$emit('openDiagnostics')"
      />
      <nav class="nav-group nav-group--utility" aria-label="全局入口">
        <button
          v-for="item in utilityItems"
          :key="item.id"
          type="button"
          class="nav-item"
          :class="{ active: activeId === item.id }"
          :aria-current="activeId === item.id ? 'page' : undefined"
          @click="go(item.path)"
        >
          <el-icon><component :is="iconMap[item.icon]" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px 16px 16px;
  background: var(--color-bg-sidebar);
  color: var(--color-text-sidebar);
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 4px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.brand__logo {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  box-shadow: var(--shadow-brand);
}

.brand__copy > span {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.brand__copy strong {
  color: var(--color-brand-ink);
  font-size: 19px;
  letter-spacing: 2px;
}

.brand__copy em {
  color: var(--color-brand-gold);
  font-family: Georgia, serif;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
  letter-spacing: 1.4px;
}

.brand__copy small {
  display: block;
  margin-top: 4px;
  color: var(--color-text-sidebar-dim);
  font-size: 11px;
}

.project-switcher {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 11px;
  border: 1px solid rgba(198, 111, 79, 0.25);
  border-radius: var(--radius-md);
  background: rgba(198, 111, 79, 0.12);
  color: var(--color-brand-ink);
  cursor: pointer;
  font-weight: 700;
}

.project-switcher svg {
  width: 16px;
}

.project-switcher span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-group {
  display: grid;
  gap: 5px;
}

.nav-item {
  width: 100%;
  height: 43px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 13px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: var(--color-text-sidebar-muted);
  cursor: pointer;
  font-size: 14px;
  font-weight: 650;
  text-align: left;
}

.nav-item:hover,
.nav-item.active {
  background: rgba(255, 255, 255, 0.065);
  color: var(--color-text-sidebar);
}

.nav-item.active {
  border-color: rgba(198, 111, 79, 0.34);
  box-shadow: inset 3px 0 0 var(--color-primary);
}

.sidebar-utility {
  margin-top: auto;
  display: grid;
  gap: 8px;
}

.nav-group--utility {
  padding-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
