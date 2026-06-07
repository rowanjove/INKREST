<script setup lang="ts">
import { onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import TropeComponentLibrary from '../components/trope/TropeComponentLibrary.vue'
import TropeBlueprintPanel from '../components/trope/TropeBlueprintPanel.vue'
import { useTropeWorkshop } from '../composables/useTropeWorkshop'

const {
  channels,
  themes,
  mechanisms,
  coolPoints,
  loading,
  activeTab,
  selectedChannel,
  selectedTheme,
  selectedMechanisms,
  selectedCoolPoints,
  guideLoading,
  currentProjectId,
  isValidBlueprint,
  parsedGuideHtml,
  loadAllComponents,
  addToBlueprint,
  removeFromBlueprint,
  handleApplyToActiveProject,
  openCreateDialog,
  handleDragStart,
  handleDrop,
} = useTropeWorkshop()

onMounted(loadAllComponents)
</script>

<template>
  <section class="trope-workshop">
    <header class="page-head">
      <div class="page-title-area">
        <h1>网文套路设计工坊</h1>
        <p>通过拖拽或选择题材主题、主角设定、情节机制与节奏爽点卡，自由组装定制专属的小说写作蓝图，一键输出项目级指南规则书。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="Refresh" @click="loadAllComponents">刷新元件</el-button>
      </div>
    </header>

    <div class="workshop-layout">
      <TropeComponentLibrary
        v-model:active-tab="activeTab"
        :channels="channels"
        :themes="themes"
        :mechanisms="mechanisms"
        :cool-points="coolPoints"
        :loading="loading"
        :on-add-to-blueprint="addToBlueprint"
        :on-drag-start="handleDragStart"
      />

      <TropeBlueprintPanel
        :selected-channel="selectedChannel"
        :selected-theme="selectedTheme"
        :selected-mechanisms="selectedMechanisms"
        :selected-cool-points="selectedCoolPoints"
        :is-valid-blueprint="isValidBlueprint"
        :guide-loading="guideLoading"
        :parsed-guide-html="parsedGuideHtml"
        :current-project-id="currentProjectId"
        :on-remove-from-blueprint="removeFromBlueprint"
        :on-drop="handleDrop"
        :on-open-create-dialog="openCreateDialog"
        :on-apply-to-active-project="handleApplyToActiveProject"
      />
    </div>
  </section>
</template>

<style scoped>
.trope-workshop {
  display: grid;
  gap: 20px;
}

.workshop-layout {
  display: grid;
  grid-template-columns: 460px minmax(0, 1fr);
  gap: 20px;
  min-height: calc(100vh - 190px);
}
</style>