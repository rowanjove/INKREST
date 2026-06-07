<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ChapterSubnav from '../components/chapter/ChapterSubnav.vue'
import { DUAL_AUDIT_HINT } from '../constants/repairWorkflow'
import { usePipelineAlerts } from '../composables/usePipelineAlerts'

const route = useRoute()
const { pipelineAlerts } = usePipelineAlerts(4000)

const isMaintenance = computed(() => route.name === 'chapters-maintenance')
const isList = computed(() => route.name === 'chapters-list')
const pendingCount = computed(() => pipelineAlerts.value.length)
</script>

<template>
  <section class="chapters-layout">
    <header class="page-head align-start">
      <div class="page-title-area">
        <h1>章节</h1>
        <p v-if="isMaintenance" class="page-kicker">{{ DUAL_AUDIT_HINT }}</p>
        <p v-else-if="isList">检索、编辑全书章节；全书连写见工作台。</p>
      </div>
    </header>

    <ChapterSubnav :pending-count="pendingCount" />

    <router-view />
  </section>
</template>

<style scoped>
.chapters-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapters-layout .page-head {
  margin-bottom: 0;
  padding-bottom: 12px;
}
</style>