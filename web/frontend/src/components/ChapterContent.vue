<script setup lang="ts">
defineProps<{ title?: string; chapterId: string; finalText: string }>()
</script>

<template>
  <div class="reading-container">
    <div class="reading-meta">
      <h3>{{ title || '无标题章节' }}</h3>
      <p>第 {{ chapterId }} 章</p>
    </div>
    <div class="reading-body">{{ finalText }}</div>
  </div>
</template>

<style scoped>
.reading-container {
  max-width: 740px; margin: 0 auto; padding: 20px 40px 60px;
  background: #faf8f5; border-radius: 12px;
  border: 1px solid rgba(195, 112, 80, 0.08);
  box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.01);
}
.reading-meta {
  text-align: center; margin-bottom: 40px;
  border-bottom: 1px dashed var(--border); padding-bottom: 24px;
}
.reading-meta h3 { font-family: var(--font-serif); font-size: 26px; font-weight: 700; color: #1a2129; }
.reading-meta p { font-size: 13px; color: var(--text-muted); margin-top: 8px; letter-spacing: 1px; text-transform: uppercase; }
.reading-body {
  font-family: var(--font-serif); font-size: 18px; line-height: 2.0;
  color: #2b2b2b; white-space: pre-wrap; text-align: justify;
}
</style>
