<script setup lang="ts">
import { computed, defineAsyncComponent, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Collection,
  Cpu,
  DataAnalysis,
  DataLine,
  Document,
  Edit,
  Files,
  List,
  Plus,
  Reading,
  Setting,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

import {
  GLOBAL_NAV_ITEMS,
  PROJECT_NAV_ITEMS,
  activeNavigationId,
  type NavigationIcon,
} from '../router/navigation'
import { useProjectStore } from '../../stores/project'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'
import PluginSidebarGroup from './PluginSidebarGroup.vue'

const RuntimeStatusButton = defineAsyncComponent(() => import('./RuntimeStatusButton.vue'))
const ProjectSwitcherDialog = defineAsyncComponent(() => import('./ProjectSwitcherDialog.vue'))

defineProps<{
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()

defineEmits<{ openDiagnostics: [] }>()

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const showProjectSwitcher = ref(false)

const inProject = computed(
  () => route.meta.scope === 'project' && Boolean(projectStore.currentProject?.id),
)
const primaryItems = computed(() =>
  inProject.value ? PROJECT_NAV_ITEMS : GLOBAL_NAV_ITEMS.slice(0, 2),
)
const utilityItems = computed(() =>
  inProject.value
    ? GLOBAL_NAV_ITEMS.filter((item) => ['settings', 'extensions'].includes(item.id))
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
  quality: DataAnalysis,
  publishing: Reading,
  settings: Setting,
  extensions: Cpu,
}

const go = (path: string) => void router.push(path)

async function handleBrandClick() {
  if (inProject.value) {
    try {
      await ElMessageBox.confirm(
        '当前作品修改已自动保存。确认返回书库主页吗？',
        '返回书库主页',
        {
          confirmButtonText: '返回主页',
          cancelButtonText: '继续创作',
          type: 'info',
        },
      )
      void router.push('/')
    } catch {
      /* 用户取消，继续停留在创作界面 */
    }
    return
  }
  void router.push('/')
}
</script>

<template>
  <aside class="app-sidebar">
    <button
      class="brand"
      type="button"
      :aria-label="inProject ? '返回书库主页（需确认）' : '栖墨书库主页'"
      :title="inProject ? '返回书库主页（当前作品已自动保存）' : '栖墨创作空间'"
      @click="handleBrandClick"
    >
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
      title="点击快速切换作品"
      @click="showProjectSwitcher = true"
    >
      <Document aria-hidden="true" />
      <span>{{ projectStore.currentProject?.name }}</span>
      <el-icon class="project-switcher__arrow"><ArrowDown /></el-icon>
    </button>

    <nav
      class="nav-group"
      :aria-label="inProject ? '项目导航' : '全局导航'"
      :data-tour="inProject ? 'project-journey' : undefined"
    >
      <button
        v-for="item in primaryItems"
        :key="item.id"
        type="button"
        class="nav-item"
        :class="{ active: activeId === item.id }"
        :aria-current="activeId === item.id ? 'page' : undefined"
        :data-tour="`nav-${item.id}`"
        @click="go(item.path)"
      >
        <el-icon><component :is="iconMap[item.icon]" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <PluginSidebarGroup
      :in-project="inProject"
      :active-path="route.path"
      @navigate="go"
    />

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

    <ProjectSwitcherDialog
      v-if="inProject"
      v-model="showProjectSwitcher"
    />
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
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
  letter-spacing: 1.4px;
}

.brand__copy small {
  display: block;
  margin-top: 4px;
  color: var(--color-text-sidebar-dim);
  font-size: 12px;
}

.project-switcher {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 12px;
  border: 1px solid rgba(198, 111, 79, 0.32);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, rgba(198, 111, 79, 0.16) 0%, rgba(198, 111, 79, 0.08) 100%);
  color: var(--color-brand-ink);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: all var(--motion-fast) var(--ease-standard);
}

.project-switcher:hover {
  border-color: rgba(198, 111, 79, 0.5);
  background: linear-gradient(180deg, rgba(198, 111, 79, 0.22) 0%, rgba(198, 111, 79, 0.12) 100%);
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

.project-switcher__arrow {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-sidebar-dim);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.project-switcher:hover .project-switcher__arrow {
  color: var(--color-brand-ink);
}

.nav-group {
  display: grid;
  gap: 5px;
}

.nav-item {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: var(--color-text-sidebar-muted);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  transition: all var(--motion-fast) var(--ease-standard);
}

.nav-item .el-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.nav-item span {
  display: inline-block;
  line-height: 1;
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
