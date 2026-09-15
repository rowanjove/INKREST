<script setup lang="ts">
import ConfigPageNav from '../components/config/ConfigPageNav.vue'
import ConfigSectionsStack from '../components/config/ConfigSectionsStack.vue'
import { useConfigNavigation } from '../composables/useConfigNavigation'

const { sections, scrollTo } = useConfigNavigation()
</script>

<template>
  <section class="config-page">
    <header class="page-head">
      <div class="page-title-area">
        <div class="title-row">
          <div class="title-text">
            <h1>设置</h1>
            <p>按创作任务组织常用配置；高风险与内部选项集中收纳在高级区域。</p>
          </div>
        </div>
      </div>
      <ConfigPageNav :sections="sections" :on-scroll-to="scrollTo" />
    </header>

    <ConfigSectionsStack />
  </section>
</template>

<style scoped>
.config-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  padding-bottom: 36px;
}

.page-head {
  display: grid;
  gap: 8px;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.title-text h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.title-text p {
  margin: 3px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.config-page > * {
  margin-bottom: 0 !important;
  margin-top: 0 !important;
}

.config-page :deep(.fold-head) {
  min-height: 46px;
  padding: 8px 14px;
}

.config-page :deep(.head-left) {
  align-items: center;
  gap: 10px;
}

.config-page :deep(.collapse-arrow) {
  flex: 0 0 12px;
  margin-top: 0;
}

.config-page :deep(.fold-head h2) {
  font-size: 14px;
  font-weight: 750;
  line-height: 1.25;
}

.config-page :deep(.fold-head p) {
  margin: 2px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.35;
}

.config-page :deep(.fold-body) {
  gap: 8px;
  padding: 10px 14px 12px;
}
</style>
