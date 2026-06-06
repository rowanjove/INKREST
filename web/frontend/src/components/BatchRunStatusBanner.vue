<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Warning } from '@element-plus/icons-vue'
import { useNovelProgress } from '../composables/useNovelProgress'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'

const router = useRouter()
const { snapshot } = useNovelProgress({ pollMs: 5000 })
const { openDialog } = useNovelBatchRun()

const status = computed(() => snapshot.value)

const isCircuit = () =>
  status.value?.batch_paused &&
  (status.value?.pause_reason || 'circuit_breaker') === 'circuit_breaker'

const goMaintenance = () => {
  router.push('/chapters/maintenance')
}

const goTaskLogs = () => {
  router.push({ path: '/monitor', query: { tab: 'task_logs' } })
}

const goFixChapter = () => {
  const ch = status.value?.last_chapter_id
  if (ch) {
    router.push(`/chapters/${ch}`)
    return
  }
  goMaintenance()
}
</script>

<template>
  <section v-if="status?.batch_paused" class="batch-status-banner">
    <el-icon class="icon"><Warning /></el-icon>
    <div class="body">
      <strong>全书批量已暂停</strong>
      <span>
        原因：{{ status.pause_reason || 'circuit_breaker' }}；
        卷 {{ status.last_arc_id || '—' }} / 章 {{ status.last_chapter_id || '—' }}
        <template v-if="status.fail_streak">（连续失败 {{ status.fail_streak }} 次）</template>
      </span>
    </div>
    <div class="banner-actions">
      <el-button size="small" type="warning" plain @click="goMaintenance">
        去章节维护
      </el-button>
      <el-button size="small" plain @click="goTaskLogs">
        看任务日志
      </el-button>
      <el-button
        v-if="isCircuit()"
        size="small"
        type="info"
        plain
        @click="goFixChapter"
      >
        改问题章
      </el-button>
      <el-button size="small" type="primary" @click="openDialog">
        继续写书
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.batch-status-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1px solid var(--color-alert-warn-border);
  background: var(--color-alert-warn-bg);
  flex-wrap: wrap;
}

.icon {
  font-size: 22px;
  color: var(--color-warning);
}

.body {
  flex: 1;
  min-width: 220px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.body strong {
  color: var(--color-text);
  font-size: 14px;
}

.banner-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}
</style>