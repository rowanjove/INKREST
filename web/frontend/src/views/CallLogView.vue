<script setup lang="ts">
import LLMLogViewer from '../components/LLMLogViewer.vue'
</script>

<template>
  <section class="call-log-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>调用日志</h1>
        <p>按章节、Agent 角色和模型追踪 LLM 调用；长篇项目可用分页筛选查看历史记录。</p>
      </div>
    </header>

    <LLMLogViewer />
  </section>
</template>

<style scoped>
.call-log-page {
  display: grid;
  gap: 18px;
}


</style>
