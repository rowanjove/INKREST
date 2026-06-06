<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheck, CircleClose, Refresh } from '@element-plus/icons-vue'
import { getSystemReadiness } from '../api'

type ReadinessCheck = {
  ok?: boolean
  label?: string
  hint?: string
  pending?: string[]
  error?: string
  configured?: boolean
  enabled_count?: number
  untrusted_enabled?: string[]
  active?: boolean
  skipped?: boolean
}

const router = useRouter()
const loading = ref(false)
const overallOk = ref(false)
const checks = ref<Record<string, ReadinessCheck>>({})
const activeProjectId = ref<string | null>(null)
const loadError = ref('')

const items = computed(() =>
  Object.entries(checks.value).map(([id, check]) => ({
    id,
    label: check.label || id,
    ok: check.ok !== false,
    detail: formatDetail(check),
    action: actionFor(id, check),
  })),
)

function formatDetail(check: ReadinessCheck): string {
  if (check.error) return check.error
  if (check.pending?.length) return `待办：${check.pending.join('、')}`
  if (check.untrusted_enabled?.length) {
    return `未信任已启用：${check.untrusted_enabled.join('、')}`
  }
  if (check.hint) return check.hint
  if (check.configured === false) return '未配置远程访问令牌（仅本机可免）'
  if (check.configured === true) return '已配置 NOVEL_AGENT_ACCESS_TOKEN'
  if (check.active === true) return '有任务正在运行'
  if (check.active === false) return '无运行中任务'
  if (check.enabled_count != null) return `已启用 ${check.enabled_count} 个插件`
  return check.ok ? '正常' : '需处理'
}

function actionFor(id: string, _check: ReadinessCheck): string | null {
  if (id === 'llm' || id === 'book') return '/workspace'
  if (id === 'plugins') return '/plugins'
  if (id === 'remote_token') return '/config'
  return null
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await getSystemReadiness()
    overallOk.value = !!data.ok
    checks.value = data.checks || {}
    activeProjectId.value = data.active_project_id || null
  } catch (e: any) {
    loadError.value = e?.message || '无法加载系统自检'
    overallOk.value = false
    checks.value = {}
  } finally {
    loading.value = false
  }
}

const go = (path: string | null) => {
  if (path) router.push(path)
}

onMounted(load)

defineExpose({ reload: load })
</script>

<template>
  <section id="system-readiness" class="readiness-card panel">
    <div class="readiness-head">
      <h2>系统自检</h2>
      <span :class="['readiness-badge', overallOk ? 'ok' : 'pending']">
        {{ overallOk ? '全部通过' : '有待处理' }}
      </span>
      <el-button text size="small" :loading="loading" @click="load">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    <p class="readiness-desc">
      汇总 API、单进程模式、日常模型、开书清单与插件信任状态；与侧栏「运行状态」同源，便于远程部署前自查。
      <span v-if="activeProjectId" class="project-tag">当前书：{{ activeProjectId }}</span>
      <span v-else class="project-tag muted">未打开书籍时「开书清单」仅作提示</span>
    </p>
    <el-alert v-if="loadError" type="error" :title="loadError" show-icon :closable="false" />
    <ul v-else class="readiness-list">
      <li v-for="item in items" :key="item.id" class="readiness-item">
        <el-icon class="status-icon" :class="item.ok ? 'ok' : 'bad'">
          <CircleCheck v-if="item.ok" />
          <CircleClose v-else />
        </el-icon>
        <div class="item-body">
          <strong>{{ item.label }}</strong>
          <small>{{ item.detail }}</small>
        </div>
        <el-button v-if="item.action && !item.ok" text type="primary" size="small" @click="go(item.action)">
          去处理
        </el-button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.readiness-card {
  padding: 18px 20px;
}

.readiness-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.readiness-head h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
}

.readiness-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
}

.readiness-badge.ok {
  color: #2d7a52;
  background: #eaf8f0;
}

.readiness-badge.pending {
  color: #9a5b20;
  background: #fff8df;
}

.readiness-desc {
  margin: 10px 0 14px;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.project-tag {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--color-bg-muted, #f4f4f4);
  font-size: 12px;
}

.project-tag.muted {
  opacity: 0.85;
}

.readiness-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.readiness-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface);
}

.status-icon.ok {
  color: #3ea66d;
}

.status-icon.bad {
  color: #c66f4f;
}

.item-body {
  flex: 1;
  min-width: 0;
}

.item-body strong {
  display: block;
  font-size: 14px;
}

.item-body small {
  display: block;
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
}
</style>