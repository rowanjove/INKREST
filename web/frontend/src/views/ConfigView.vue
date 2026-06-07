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
        <h1>设置</h1>
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
  gap: 20px;
  max-width: 1080px;
  padding-bottom: 48px;
}

.config-page > * {
  margin-bottom: 0 !important;
  margin-top: 0 !important;
}

.config-page :deep(.fold-head) {
  min-height: 72px;
  padding: 15px 18px;
}

.config-page :deep(.head-left) {
  align-items: center;
  gap: 12px;
}

.config-page :deep(.collapse-arrow) {
  flex: 0 0 12px;
  margin-top: 0;
}

.config-page :deep(.fold-head h2) {
  font-size: 17px;
  font-weight: 800;
  line-height: 1.25;
}

.config-page :deep(.fold-head p) {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.config-page :deep(.fold-body) {
  gap: 14px;
  padding: 16px 18px 18px;
}

#system-readiness,
#appearance,
#models,
#embedding-config,
#pipeline-runtime,
#llm-routing,
#writing-rules,
#agent-bridge {
  scroll-margin-top: 16px;
}
</style>