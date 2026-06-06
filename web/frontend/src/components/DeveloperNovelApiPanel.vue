<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { continueNovel, runNovel, runNovelArc } from '../api'

const devApiEnabled =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEV_NOVEL_RUN === 'true'

const expanded = ref(false)
const dryRunLoading = ref(false)

/** 仅开发排障：冷启动全书规划（普通用户请用工作台 + ensure-queue + continue） */
const probeRunNovel = async () => {
  try {
    const { data } = await runNovel({
      theme: '调试',
      target_chapters: 3,
      dry_run: true,
    })
    ElMessage.success(`novel/run 已提交（dry_run）task=${data.task_id || '—'}`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '请求失败')
  }
}

const probeRunArc = async () => {
  try {
    const { data } = await runNovelArc({ dry_run: true, max_chapters: 1 })
    ElMessage.success(`novel/run-arc 已提交 task=${data.task_id || '—'}`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '请求失败')
  }
}

const probeContinue = async () => {
  dryRunLoading.value = true
  try {
    const { data } = await continueNovel({ dry_run: true, max_chapters: 0, autopilot: true })
    ElMessage.success(`continue 校验通过 task=${data.task_id || '—'}`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || 'continue 被拒绝')
  } finally {
    dryRunLoading.value = false
  }
}
</script>

<template>
  <details
    v-if="devApiEnabled"
    id="developer-novel-api"
    class="dev-api panel"
    :open="expanded"
    @toggle="expanded = ($event.target as HTMLDetailsElement).open"
  >
    <summary>开发者 · 全书 API（高级）</summary>
    <div class="body">
      <el-alert type="warning" :closable="false" show-icon title="请勿替代主路径">
        用户连写请用：<strong>工作台「连写启动」</strong> → <strong>章节维护「继续写书」</strong>（同一弹窗）。
        下列接口需服务端 <code>NOVEL_AGENT_DEBUG_RUN=1</code> 或开发模式。
      </el-alert>
      <table class="api-table">
        <thead>
          <tr>
            <th>接口</th>
            <th>用途</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>POST /api/novel/ensure-queue</code></td>
            <td>同步卷队列（主路径会自动调用）</td>
          </tr>
          <tr>
            <td><code>POST /api/novel/continue</code></td>
            <td>全书续跑（服务端 readiness + 熔断校验）</td>
          </tr>
          <tr class="deprecated">
            <td><code>POST /api/novel/run</code></td>
            <td>冷启动总编+拆卷（调试）</td>
          </tr>
          <tr class="deprecated">
            <td><code>POST /api/novel/run-arc</code></td>
            <td>单卷/多卷裸跑（调试）</td>
          </tr>
        </tbody>
      </table>
      <div class="actions">
        <el-button size="small" :loading="dryRunLoading" @click="probeContinue">
          探测 continue（dry_run）
        </el-button>
        <el-button size="small" plain @click="probeRunArc">探测 run-arc（dry_run）</el-button>
        <el-button size="small" plain type="danger" @click="probeRunNovel">探测 run（dry_run）</el-button>
      </div>
    </div>
  </details>
</template>

<style scoped>
.dev-api {
  margin-top: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px dashed var(--color-border, #dcdfe6);
  background: var(--color-bg-muted, #fafafa);
}

.dev-api summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted, #606266);
}

.body {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.api-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.api-table th,
.api-table td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-border, #ebeef5);
}

.api-table tr.deprecated td {
  color: var(--color-text-muted, #909399);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>