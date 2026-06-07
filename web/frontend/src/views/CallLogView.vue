<script setup lang="ts">
import LLMLogViewer from '../components/LLMLogViewer.vue'
import CallLogPageHead from '../components/calllog/CallLogPageHead.vue'
</script>

<template>
  <section class="call-log-page">
    <CallLogPageHead />
    <LLMLogViewer />
  </section>
</template>

<style scoped>
.call-log-page {
  display: grid;
  gap: 18px;
}
</style>