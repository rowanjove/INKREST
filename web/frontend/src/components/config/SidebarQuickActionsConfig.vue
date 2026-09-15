<script setup lang="ts">
import { computed } from 'vue'
import {
  Avatar,
  Cpu,
  Monitor,
  Opportunity,
  Search,
  Top,
  Bottom,
  Delete,
  Plus,
  RefreshRight,
} from '@element-plus/icons-vue'
import {
  useSidebarQuickActionsStore,
  type SidebarActionId,
} from '../../stores/sidebarQuickActions'

defineProps<{ bare?: boolean }>()

const quickActions = useSidebarQuickActionsStore()

const shanshanAvatar = new URL('../../assets/pet/shanshan/ui/bubble_avatar.png', import.meta.url).href

const actionIconMap: Record<SidebarActionId, any> = {
  plugins: Cpu,
  inspiration: Opportunity,
  shanshan: Avatar,
  diagnostics: Monitor,
  command: Search,
}

const isAtMaxLimit = computed(
  () => quickActions.enabledIds.length >= quickActions.maxSlots,
)

function handleShowLabelsChange(val: string | number | boolean) {
  quickActions.setShowLabels(Boolean(val))
}
</script>

<template>
  <div class="sidebar-actions-config">
    <div class="section-header">
      <div class="header-intro">
        <h4>侧边栏底部快捷操作栏</h4>
        <p>自定义左侧栏设置上方的快捷按钮行，可按需配置排序、图标样式与数量。</p>
      </div>
      <el-button
        size="small"
        text
        :icon="RefreshRight"
        @click="quickActions.resetToDefault"
      >
        恢复默认
      </el-button>
    </div>

    <!-- 1. 显示模式切换 -->
    <div class="config-row">
      <span class="row-label">显示样式</span>
      <div class="row-control">
        <el-radio-group
          :model-value="quickActions.showLabels"
          size="default"
          @change="handleShowLabelsChange"
        >
          <el-radio-button :value="true">
            带文字（最多 3 个）
          </el-radio-button>
          <el-radio-button :value="false">
            纯图标（最多 5 个）
          </el-radio-button>
        </el-radio-group>
        <span class="row-hint">
          当前容量：{{ quickActions.enabledIds.length }} / {{ quickActions.maxSlots }} 个按钮
        </span>
      </div>
    </div>

    <!-- 2. 实时渲染预览 -->
    <div class="preview-box">
      <div class="preview-label">侧边栏实际效果预览</div>
      <div class="preview-sidebar-stub">
        <div
          class="preview-quick-bar"
          :class="{ 'preview-quick-bar--icon-only': !quickActions.showLabels }"
        >
          <div
            v-for="action in quickActions.enabledActions"
            :key="action.id"
            class="preview-action-btn"
            :class="{ 'preview-action-btn--icon-only': !quickActions.showLabels }"
          >
            <img
              v-if="action.id === 'shanshan'"
              :src="shanshanAvatar"
              alt=""
              class="preview-avatar"
            />
            <el-icon v-else :size="15">
              <component :is="actionIconMap[action.id] || Cpu" />
            </el-icon>
            <span v-if="quickActions.showLabels">{{ action.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 已启用按钮从左到右排序 -->
    <div class="slots-section">
      <div class="slots-header">
        <span class="slots-title">当前栏内按钮（从左到右）</span>
        <el-tag v-if="isAtMaxLimit" type="warning" size="small" effect="plain">
          已达当前上限 ({{ quickActions.maxSlots }}个)
        </el-tag>
      </div>

      <div class="action-items-list">
        <div
          v-for="(action, index) in quickActions.enabledActions"
          :key="action.id"
          class="action-item-card"
        >
          <div class="card-left">
            <span class="item-order">{{ index + 1 }}</span>
            <div class="item-icon-box">
              <img
                v-if="action.id === 'shanshan'"
                :src="shanshanAvatar"
                alt=""
                class="card-avatar"
              />
              <el-icon v-else :size="18">
                <component :is="actionIconMap[action.id] || Cpu" />
              </el-icon>
            </div>
            <div class="item-info">
              <span class="item-name">{{ action.label }}</span>
              <span class="item-desc">{{ action.description }}</span>
            </div>
          </div>

          <div class="card-actions">
            <el-button-group size="small">
              <el-button
                :disabled="index === 0"
                :icon="Top"
                title="向左移动"
                @click="quickActions.moveAction(index, index - 1)"
              >
                左移
              </el-button>
              <el-button
                :disabled="index === quickActions.enabledActions.length - 1"
                :icon="Bottom"
                title="向右移动"
                @click="quickActions.moveAction(index, index + 1)"
              >
                右移
              </el-button>
            </el-button-group>
            <el-button
              size="small"
              type="danger"
              plain
              :icon="Delete"
              title="从栏中移除"
              @click="quickActions.disableAction(action.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 4. 可选候选动作池（预留设计） -->
    <div v-if="quickActions.availableActions.length" class="available-section">
      <div class="slots-title">可添加的其他按钮</div>
      <div class="available-grid">
        <div
          v-for="action in quickActions.availableActions"
          :key="action.id"
          class="available-item"
        >
          <div class="item-icon-box">
            <img
              v-if="action.id === 'shanshan'"
              :src="shanshanAvatar"
              alt=""
              class="card-avatar"
            />
            <el-icon v-else :size="18">
              <component :is="actionIconMap[action.id] || Cpu" />
            </el-icon>
          </div>
          <div class="item-info">
            <span class="item-name">{{ action.label }}</span>
            <span class="item-desc">{{ action.description }}</span>
          </div>
          <el-button
            size="small"
            type="primary"
            plain
            :icon="Plus"
            :disabled="isAtMaxLimit"
            @click="quickActions.enableAction(action.id)"
          >
            添加
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar-actions-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-intro h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 750;
  color: var(--color-text-strong);
}

.header-intro p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.config-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px;
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface-muted, rgba(0, 0, 0, 0.02));
}

.row-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
  min-width: 70px;
}

.row-control {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.row-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.preview-box {
  padding: 12px 14px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
}

.preview-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-subtle);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preview-sidebar-stub {
  width: 204px;
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-sidebar, #1c1a19);
}

.preview-quick-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.preview-quick-bar--icon-only {
  justify-content: space-between;
}

.preview-action-btn {
  flex: 1;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.8);
  font-size: 11px;
  font-weight: 600;
}

.preview-action-btn--icon-only {
  flex: 1;
  max-width: 34px;
  height: 32px;
  padding: 0;
}

.preview-avatar {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  object-fit: cover;
}

.slots-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slots-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.slots-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.action-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-item-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
}

.card-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.item-order {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary-soft, rgba(198, 111, 79, 0.1));
  color: var(--color-primary, #c66f4f);
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.item-icon-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: var(--color-bg-surface-muted, rgba(0, 0, 0, 0.04));
  color: var(--color-text-strong);
  flex-shrink: 0;
}

.card-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.item-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.item-desc {
  font-size: 11px;
  color: var(--color-text-muted);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.available-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.06));
}

.available-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.available-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
}

.available-item .item-info {
  flex: 1;
}
</style>
