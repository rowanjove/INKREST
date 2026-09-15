<script setup lang="ts">
import { computed, defineAsyncComponent, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Avatar,
  Collection,
  Cpu,
  DataAnalysis,
  DataLine,
  Document,
  Edit,
  Files,
  List,
  Monitor,
  Opportunity,
  Plus,
  Reading,
  Search,
  Setting,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  GLOBAL_NAV_ITEMS,
  PROJECT_NAV_ITEMS,
  activeNavigationId,
  type NavigationIcon,
} from '../router/navigation'
import { useProjectStore } from '../../stores/project'
import { usePetStore } from '../../stores/pet'
import {
  useSidebarQuickActionsStore,
  type SidebarActionId,
} from '../../stores/sidebarQuickActions'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'
import PluginSidebarGroup from './PluginSidebarGroup.vue'

const RuntimeStatusButton = defineAsyncComponent(() => import('./RuntimeStatusButton.vue'))
const ProjectSwitcherDialog = defineAsyncComponent(() => import('./ProjectSwitcherDialog.vue'))

defineProps<{
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()

const emit = defineEmits<{ openDiagnostics: [] }>()

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const petStore = usePetStore()
const quickActionsStore = useSidebarQuickActionsStore()
const showProjectSwitcher = ref(false)

const shanshanAvatar = new URL('../../assets/pet/shanshan/ui/bubble_avatar.png', import.meta.url).href

const inProject = computed(
  () => route.meta.scope === 'project' && Boolean(projectStore.currentProject?.id),
)
const primaryItems = computed(() =>
  inProject.value ? PROJECT_NAV_ITEMS : GLOBAL_NAV_ITEMS.slice(0, 2),
)
const settingsItem = computed(() =>
  GLOBAL_NAV_ITEMS.find((item) => item.id === 'settings'),
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

const actionIconMap: Record<SidebarActionId, Component> = {
  plugins: Cpu,
  inspiration: Opportunity,
  shanshan: Avatar,
  diagnostics: Monitor,
  command: Search,
}

const go = (path: string) => void router.push(path)

function isActionActive(id: SidebarActionId): boolean {
  if (id === 'plugins') {
    return route.path === '/plugins' || route.path.startsWith('/extensions')
  }
  if (id === 'inspiration') {
    return route.path.startsWith('/inspiration')
  }
  return false
}

async function handleActionClick(id: SidebarActionId) {
  if (id === 'plugins') {
    go('/plugins')
    return
  }
  if (id === 'inspiration') {
    go('/inspiration')
    return
  }
  if (id === 'shanshan') {
    try {
      if (!petStore.settings.enabled) {
        await petStore.updateSettings({ enabled: true })
      }
      if (window.electronAPI?.showPet) {
        await window.electronAPI.showPet()
        ElMessage.success('已唤出桌面助手山山')
      } else {
        window.dispatchEvent(new CustomEvent('open-shanshan'))
        ElMessage.success('已打开驻场助手山山')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '打开山山失败')
    }
    return
  }
  if (id === 'diagnostics') {
    emit('openDiagnostics')
    return
  }
  if (id === 'command') {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
  }
}

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

      <!-- 快捷操作栏（设置上方可配置行） -->
      <div
        v-if="quickActionsStore.enabledActions.length"
        class="quick-actions-bar"
        :class="{ 'quick-actions-bar--icon-only': !quickActionsStore.showLabels }"
        aria-label="快捷操作栏"
      >
        <button
          v-for="action in quickActionsStore.enabledActions"
          :key="action.id"
          type="button"
          class="quick-action-btn"
          :class="{
            active: isActionActive(action.id),
            'quick-action-btn--icon-only': !quickActionsStore.showLabels,
          }"
          :title="action.label + ' · ' + action.description"
          :aria-label="action.label"
          @click="handleActionClick(action.id)"
        >
          <img
            v-if="action.id === 'shanshan'"
            :src="shanshanAvatar"
            alt=""
            class="action-avatar"
          />
          <el-icon v-else>
            <component :is="actionIconMap[action.id] || Cpu" />
          </el-icon>
          <span v-if="quickActionsStore.showLabels">{{ action.label }}</span>
        </button>
      </div>

      <!-- 全局设置入口 -->
      <nav class="nav-group nav-group--utility" aria-label="全局设置">
        <button
          v-if="settingsItem"
          type="button"
          class="nav-item"
          :class="{ active: activeId === 'settings' }"
          :aria-current="activeId === 'settings' ? 'page' : undefined"
          @click="go(settingsItem.path)"
        >
          <el-icon><Setting /></el-icon>
          <span>{{ settingsItem.label }}</span>
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

.quick-actions-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.quick-actions-bar--icon-only {
  justify-content: space-between;
}

.quick-action-btn {
  flex: 1;
  min-width: 0;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--color-text-sidebar-muted);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  transition: all var(--motion-fast) var(--ease-standard);
}

.quick-action-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.16);
  color: var(--color-text-sidebar);
}

.quick-action-btn.active {
  background: rgba(198, 111, 79, 0.16);
  border-color: rgba(198, 111, 79, 0.45);
  color: var(--color-brand-ink);
}

.quick-action-btn .el-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.quick-action-btn span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-action-btn--icon-only {
  flex: 1;
  max-width: 38px;
  height: 36px;
  padding: 0;
  border-radius: 8px;
}

.quick-action-btn--icon-only .el-icon {
  font-size: 16px;
}

.action-avatar {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.nav-group--utility {
  padding-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
