<script setup lang="ts">
defineProps<{
  pendingCount: number
}>()
</script>

<template>
  <nav class="chapter-subnav" aria-label="章节子页">
    <router-link
      to="/chapters/list"
      class="chapter-subnav__link"
      active-class="chapter-subnav__link--active"
    >
      章节列表
    </router-link>
    <router-link
      to="/chapters/maintenance"
      class="chapter-subnav__link"
      active-class="chapter-subnav__link--active"
    >
      章节维护
      <el-badge
        v-if="pendingCount > 0"
        :value="pendingCount"
        type="danger"
        class="chapter-subnav__badge"
      />
    </router-link>
  </nav>
</template>

<style scoped>
.chapter-subnav {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: center;
  gap: 8px;
  margin: 0 0 4px;
}

.chapter-subnav__link {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-surface);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chapter-subnav__link:hover {
  border-color: rgba(198, 111, 79, 0.45);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.chapter-subnav__link--active {
  border-color: rgba(198, 111, 79, 0.55);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: 700;
}

.chapter-subnav__badge :deep(.el-badge__content) {
  border: 0;
}
</style>