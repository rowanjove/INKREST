<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getAutopilotRounds } from '../api'

const loading = ref(false)
const rounds = ref<Array<Record<string, unknown>>>([])
const total = ref(0)

const load = async () => {
  loading.value = true
  try {
    const { data } = await getAutopilotRounds(30, 0)
    rounds.value = data?.rounds || []
    total.value = data?.total || 0
  } catch {
    rounds.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="autopilot-rounds panel" v-loading="loading">
    <div class="head">
      <h3>连写轮次</h3>
      <span class="muted">共 {{ total }} 轮（workspace/autopilot_rounds.jsonl）</span>
      <el-button size="small" text @click="load">刷新</el-button>
    </div>
    <el-empty v-if="!rounds.length" description="尚无连写轮次记录" :image-size="56" />
    <ul v-else class="round-list">
      <li v-for="(row, idx) in rounds" :key="idx">
        <strong>{{ row.ts || '—' }}</strong>
        <span>
          轮次 {{ row.round ?? '—' }} · 完成 {{ row.chapters_completed ?? row.completed ?? 0 }} 章
          <template v-if="row.stopped_reason"> · {{ row.stopped_reason }}</template>
        </span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.autopilot-rounds {
  margin-bottom: 12px;
  padding: 12px 14px;
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.head h3 {
  margin: 0;
  font-size: 14px;
}

.muted {
  font-size: 12px;
  color: var(--color-text-subtle);
  flex: 1;
}

.round-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.round-list li {
  font-size: 12px;
  color: var(--color-text-muted);
  display: grid;
  gap: 2px;
}

.round-list strong {
  color: var(--color-text-strong);
  font-size: 12px;
}
</style>