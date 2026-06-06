<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import DataManager from '../components/DataManager.vue'
import PipelineRuntimeConfig from '../components/PipelineRuntimeConfig.vue'
import LLMConfig from '../components/LLMConfig.vue'
import ModelLibrary from '../components/ModelLibrary.vue'
import EmbeddingConfig from '../components/EmbeddingConfig.vue'
import PetAssistantConfig from '../components/PetAssistantConfig.vue'
import PromptManager from '../components/PromptManager.vue'
import WritingRulesConfig from '../components/WritingRulesConfig.vue'
import AppearanceConfig from '../components/AppearanceConfig.vue'
import DeveloperNovelApiPanel from '../components/DeveloperNovelApiPanel.vue'
import AgentBridgeConfig from '../components/AgentBridgeConfig.vue'
const route = useRoute()

const sections = [
  { id: 'appearance', label: '外观' },
  { id: 'models', label: '模型库' },
  { id: 'embedding-config', label: '向量嵌入' },
  { id: 'pipeline-runtime', label: '流水线' },
  { id: 'llm-routing', label: 'Agent 路由' },
  { id: 'writing-rules', label: '写作规范' },
  { id: 'agent-bridge', label: 'Agent 接入' },
]

const scrollTo = (id: string) => {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

const hashSection = () => {
  const raw = (route.hash || '').replace(/^#/, '')
  if (raw && sections.some((s) => s.id === raw)) {
    requestAnimationFrame(() => scrollTo(raw))
  }
}

onMounted(hashSection)
watch(() => route.hash, hashSection)
</script>

<template>
  <section class="config-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>设置</h1>
      </div>
      <nav class="config-nav" aria-label="设置分区">
        <button
          v-for="item in sections"
          :key="item.id"
          type="button"
          class="nav-chip"
          @click="scrollTo(item.id)"
        >
          {{ item.label }}
        </button>
      </nav>
    </header>

    <AppearanceConfig />

    <div id="models">
      <ModelLibrary />
    </div>
    <div id="embedding-config">
      <EmbeddingConfig />
    </div>
    <div id="pipeline-runtime">
      <PipelineRuntimeConfig />
    </div>
    <div id="llm-routing">
      <LLMConfig />
    </div>
    <PromptManager />
    <div id="writing-rules">
      <WritingRulesConfig />
    </div>
    <PetAssistantConfig />
    <AgentBridgeConfig />
    <DeveloperNovelApiPanel />
    <DataManager />
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



.config-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-chip {
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-surface);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-chip:hover {
  border-color: var(--primary, #c66f4f);
  color: var(--primary, #c66f4f);
  background: var(--color-primary-soft);
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