<script setup lang="ts">
import DataManager from '../DataManager.vue'
import PipelineRuntimeConfig from '../PipelineRuntimeConfig.vue'
import LLMConfig from '../LLMConfig.vue'
import ModelLibrary from '../ModelLibrary.vue'
import EmbeddingConfig from '../EmbeddingConfig.vue'
import PetAssistantConfig from '../PetAssistantConfig.vue'
import PromptManager from '../PromptManager.vue'
import WritingRulesConfig from '../WritingRulesConfig.vue'
import AppearanceConfig from '../AppearanceConfig.vue'
import DeveloperNovelApiPanel from '../DeveloperNovelApiPanel.vue'
import AgentBridgeConfig from '../AgentBridgeConfig.vue'
</script>

<template>
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
</template>