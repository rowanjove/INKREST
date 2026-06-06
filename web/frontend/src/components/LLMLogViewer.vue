<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getLLMLogs } from '../api'
import { ElMessage } from 'element-plus'

const logs = ref<any[]>([])
const summary = ref({ call_count: 0, total_tokens: 0, total_latency_ms: 0, avg_latency_ms: 0 })
const loading = ref(false)
const roleFilter = ref('')
const chapterFilter = ref('')
const page = ref(1)
const pageSize = ref(100)

const loadLogs = async () => {
  loading.value = true
  try {
    const { data } = await getLLMLogs()
    logs.value = data.logs || []
    summary.value = data.summary || { call_count: 0, total_tokens: 0, total_latency_ms: 0, avg_latency_ms: 0 }
  } catch {
    ElMessage.error('加载 LLM 日志失败')
  } finally {
    loading.value = false
  }
}

const formatTime = (ts: number) => {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

const roleBreakdown = computed(() => {
  const map: Record<string, { count: number; tokens: number; latency: number }> = {}
  for (const entry of logs.value) {
    const role = entry.role || 'unknown'
    if (!map[role]) map[role] = { count: 0, tokens: 0, latency: 0 }
    map[role].count += 1
    map[role].tokens += entry.total_tokens || 0
    map[role].latency += entry.latency_ms || 0
  }
  return Object.entries(map).map(([role, stats]) => ({ role, ...stats }))
})

const roleOptions = computed(() => Array.from(new Set(logs.value.map((entry) => entry.role || 'unknown'))).sort())
const filteredLogs = computed(() => {
  return logs.value.filter((entry) => {
    if (roleFilter.value && (entry.role || 'unknown') !== roleFilter.value) return false
    if (chapterFilter.value && !String(entry.chapter_id || '').includes(chapterFilter.value.trim())) return false
    return true
  })
})
const pagedLogs = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredLogs.value.slice(start, start + pageSize.value)
})

onMounted(loadLogs)
defineExpose({ loadLogs })
</script>

<template>
  <el-card class="llm-log-card">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <strong>LLM 调用日志</strong>
        <el-button size="small" :loading="loading" @click="loadLogs">刷新</el-button>
      </div>
    </template>

    <p class="intro">每次章节生成完成后，记录 Token 用量、延迟、模型和 Agent 角色。为上千章项目预留分页筛选。</p>

    <!-- Summary cards -->
    <div class="summary-grid">
      <el-card shadow="never" style="flex: 1; text-align: center">
        <div style="font-size: 24px; font-weight: 700; color: #409eff">{{ summary.call_count }}</div>
        <div style="font-size: 12px; color: #909399">总调用次数</div>
      </el-card>
      <el-card shadow="never" style="flex: 1; text-align: center">
        <div style="font-size: 24px; font-weight: 700; color: #67c23a">{{ summary.total_tokens.toLocaleString() }}</div>
        <div style="font-size: 12px; color: #909399">总 Token 数</div>
      </el-card>
      <el-card shadow="never" style="flex: 1; text-align: center">
        <div style="font-size: 24px; font-weight: 700; color: #e6a23c">{{ (summary.total_latency_ms / 1000).toFixed(1) }}s</div>
        <div style="font-size: 12px; color: #909399">总耗时</div>
      </el-card>
      <el-card shadow="never" style="flex: 1; text-align: center">
        <div style="font-size: 24px; font-weight: 700; color: #f56c6c">{{ summary.avg_latency_ms }}ms</div>
        <div style="font-size: 12px; color: #909399">平均延迟</div>
      </el-card>
    </div>

    <!-- Role breakdown -->
    <div v-if="roleBreakdown.length" style="margin-bottom: 16px">
      <h4 style="margin: 0 0 8px; font-size: 13px; color: #606266">按角色汇总</h4>
      <el-table :data="roleBreakdown" size="small" border>
        <el-table-column prop="role" label="角色" width="160" />
        <el-table-column prop="count" label="调用次数" width="100" />
        <el-table-column prop="tokens" label="总 Token">
          <template #default="{ row }">{{ row.tokens.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="总延迟">
          <template #default="{ row }">{{ (row.latency / 1000).toFixed(1) }}s</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Detailed log table -->
    <div class="log-toolbar">
      <h4>详细调用记录</h4>
      <div class="filters">
        <el-input v-model="chapterFilter" clearable placeholder="筛章节号" style="width: 130px" @input="page = 1" />
        <el-select v-model="roleFilter" clearable placeholder="筛角色" style="width: 180px" @change="page = 1">
          <el-option v-for="role in roleOptions" :key="role" :label="role" :value="role" />
        </el-select>
      </div>
    </div>
    <el-table :data="pagedLogs" size="small" border max-height="520" v-loading="loading">
      <el-table-column prop="chapter_id" label="章节" width="80" />
      <el-table-column prop="role" label="角色" width="140" />
      <el-table-column prop="model" label="模型" width="180" />
      <el-table-column label="Prompt Tokens" width="120">
        <template #default="{ row }">{{ (row.prompt_tokens || 0).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="Completion Tokens" width="130">
        <template #default="{ row }">{{ (row.completion_tokens || 0).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="总 Tokens" width="100">
        <template #default="{ row }">{{ (row.total_tokens || 0).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="延迟" width="100">
        <template #default="{ row }">{{ row.latency_ms || 0 }}ms</template>
      </el-table-column>
      <el-table-column label="时间">
        <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <span>共 {{ filteredLogs.length }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[50, 100, 200, 500]"
        layout="sizes, prev, pager, next"
        :total="filteredLogs.length"
      />
    </div>

    <el-empty v-if="!loading && logs.length === 0" description="暂无调用记录，请先运行一次章节生成" />
  </el-card>
</template>

<style scoped>
.llm-log-card {
  margin-bottom: 0;
}

.intro {
  margin: 0 0 12px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.summary-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.log-toolbar,
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.log-toolbar {
  margin-bottom: 8px;
}

.log-toolbar h4 {
  margin: 0;
  color: #606266;
  font-size: 13px;
}

.filters {
  display: flex;
  gap: 8px;
}

.pager {
  padding-top: 12px;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>
