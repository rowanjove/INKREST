<script setup lang="ts">
import { Connection, Lock, Setting } from '@element-plus/icons-vue'

import AgentBridgeConfig from '../AgentBridgeConfig.vue'
import AppearanceConfig from '../AppearanceConfig.vue'
import DataManager from '../DataManager.vue'
import EmbeddingConfig from '../EmbeddingConfig.vue'
import LLMConfig from '../LLMConfig.vue'
import ModelLibrary from '../ModelLibrary.vue'
import PetAssistantConfig from '../PetAssistantConfig.vue'
import PipelineRuntimeConfig from '../PipelineRuntimeConfig.vue'
import PromptManager from '../PromptManager.vue'
import WritingRulesConfig from '../WritingRulesConfig.vue'
import ConfigTaskGroup from './ConfigTaskGroup.vue'
</script>

<template>
  <ConfigTaskGroup
    id="models-providers"
    eyebrow="01 / AI"
    title="模型与提供方"
    description="先维护可用模型，再按任务选择日常档、逻辑档与 Agent 路由。"
  >
    <div id="models"><ModelLibrary /></div>
    <details class="advanced-zone">
      <summary><el-icon><Setting /></el-icon>高级：Agent 模型路由</summary>
      <p>仅在不同 Agent 确实需要不同模型时调整；常规写作使用模型库中的全局档位即可。</p>
      <div id="llm-routing"><LLMConfig /></div>
    </details>
  </ConfigTaskGroup>

  <ConfigTaskGroup
    id="memory"
    eyebrow="02 / Memory"
    title="记忆"
    description="管理跨章召回、语义去重与状态检索所依赖的向量嵌入能力。"
  >
    <EmbeddingConfig />
  </ConfigTaskGroup>

  <ConfigTaskGroup
    id="generation-quality"
    eyebrow="03 / Quality"
    title="生成与质量"
    description="控制生成流水线、质量门禁与失败处理；页面加载不会触发任何模型任务。"
  >
    <div id="pipeline-runtime"><PipelineRuntimeConfig /></div>
    <details class="advanced-zone">
      <summary><el-icon><Lock /></el-icon>高级：提示词源内容</summary>
      <p>直接修改提示词会影响后续生成结果。仅在理解各阶段输入输出契约后使用。</p>
      <PromptManager />
    </details>
  </ConfigTaskGroup>

  <ConfigTaskGroup
    id="writing-layout"
    eyebrow="04 / Writing"
    title="写作与排版"
    description="集中维护风格、结构规则与敏感词；阅读版心和字号在发布预览中调整。"
  >
    <WritingRulesConfig />
  </ConfigTaskGroup>

  <ConfigTaskGroup
    id="extensions"
    eyebrow="05 / Extend"
    title="扩展"
    description="这里只展示扩展入口与本机 Agent 接入；插件清单、信任和权限统一在扩展中心管理。"
  >
    <article class="extension-entry">
      <div class="extension-entry-icon"><el-icon><Connection /></el-icon></div>
      <div>
        <strong>插件与权限</strong>
        <p>安装的 Python 插件会在本机进程中运行。启用前请检查来源、权限与内容摘要。</p>
      </div>
      <router-link class="extension-entry-link" to="/plugins">打开扩展中心</router-link>
    </article>
    <PetAssistantConfig />
    <details class="advanced-zone">
      <summary><el-icon><Lock /></el-icon>高级：AI Agent 接入</summary>
      <p>面向本机 CLI、Cursor 等只读诊断集成，普通创作流程无需配置。</p>
      <AgentBridgeConfig />
    </details>
  </ConfigTaskGroup>

  <ConfigTaskGroup
    id="system-data"
    eyebrow="06 / System"
    title="系统与数据"
    description="管理界面外观和当前项目数据。清理操作不可逆，执行前会要求二次确认。"
  >
    <AppearanceConfig />
    <DataManager />
  </ConfigTaskGroup>
</template>

<style scoped>
.advanced-zone {
  overflow: hidden;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.advanced-zone > summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 15px;
  color: var(--color-text-strong);
  cursor: pointer;
  font-size: 12px;
  font-weight: 750;
  list-style: none;
}
.advanced-zone > summary::-webkit-details-marker { display: none; }
.advanced-zone > summary::after {
  margin-left: auto;
  color: var(--color-text-subtle);
  content: '展开';
  font-size: 10px;
  font-weight: 600;
}
.advanced-zone[open] > summary::after { content: '收起'; }
.advanced-zone > p {
  margin: -2px 15px 12px;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.6;
}
.advanced-zone > :deep(div:last-child),
.advanced-zone > :deep(section:last-child) { margin: 0 10px 10px !important; }
.extension-entry {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.extension-entry-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.extension-entry strong { color: var(--color-text-strong); font-size: 13px; }
.extension-entry p { margin: 3px 0 0; color: var(--color-text-muted); font-size: 11px; line-height: 1.55; }
.extension-entry-link {
  padding: 7px 11px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 750;
  text-decoration: none;
}
.extension-entry-link:hover { background: var(--color-primary-soft); }
@media (max-width: 720px) {
  .extension-entry { grid-template-columns: auto minmax(0, 1fr); }
  .extension-entry-link { grid-column: 1 / -1; text-align: center; }
}
</style>
