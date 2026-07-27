<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  apiErrorMessage,
  backupProject,
  resetProjectToV2,
  type ProjectBackupResult,
} from '../api'
import { useProjectStore } from '../stores/project'
import { useProjectSnapshotStore } from '../stores/projectSnapshot'

const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()
const backingUp = ref(false)
const resetting = ref(false)
const lastBackup = ref<ProjectBackupResult | null>(null)
const project = computed(() => projectStore.currentProject)
const resetPhrase = computed(() =>
  project.value?.id ? `RESET V2 ${project.value.id}` : '',
)

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

async function createBackup() {
  if (!project.value?.id) return
  try {
    await ElMessageBox.confirm(
      `为《${project.value.name}》创建一次项目数据备份？生成任务运行时不会执行备份。`,
      '备份当前项目',
      {
        confirmButtonText: '创建备份',
        cancelButtonText: '取消',
        type: 'info',
      },
    )
    backingUp.value = true
    const { data } = await backupProject(project.value.id)
    lastBackup.value = data.backup
    ElMessage.success(`备份已创建：${data.backup.name}`)
  } catch (error: any) {
    if (error !== 'cancel' && error?.action !== 'cancel') {
      ElMessage.error(apiErrorMessage(error, '项目备份失败'))
    }
  } finally {
    backingUp.value = false
  }
}

async function resetProject() {
  if (!project.value?.id) return
  try {
    const { value } = await ElMessageBox.prompt(
      `此操作会先备份 data、state、workspace，再清空生成结果、任务、日志和导出文件。配置、提示词、素材与插件不会被删除。\n\n请输入：${resetPhrase.value}`,
      `重置《${project.value.name}》到 V2`,
      {
        confirmButtonText: '备份并重置',
        cancelButtonText: '取消',
        type: 'warning',
        inputPlaceholder: resetPhrase.value,
      },
    )
    if (value !== resetPhrase.value) {
      ElMessage.error('确认语不匹配，未执行任何操作')
      return
    }
    resetting.value = true
    const projectId = project.value.id
    const { data } = await resetProjectToV2(projectId, value)
    lastBackup.value = data.backup
    snapshotStore.invalidate(projectId)
    await projectStore.hydrate({ force: true })
    await snapshotStore.refresh(projectId, { force: true })
    ElMessage.success(`项目已重置到 V2，备份：${data.backup.name}`)
  } catch (error: any) {
    if (error !== 'cancel' && error?.action !== 'cancel') {
      ElMessage.error(apiErrorMessage(error, '项目重置失败'))
    }
  } finally {
    resetting.value = false
  }
}
</script>

<template>
  <section class="maintenance-card">
    <div class="maintenance-heading">
      <div>
        <span class="eyebrow">PROJECT DATA</span>
        <h3>项目数据维护</h3>
        <p>操作只作用于当前打开的项目，不会影响其他书籍或全局模型密钥。</p>
      </div>
      <el-tag v-if="project" effect="plain">{{ project.name }} · {{ project.id }}</el-tag>
      <el-tag v-else type="info" effect="plain">未打开项目</el-tag>
    </div>

    <el-alert
      title="备份优先的安全重置"
      description="保留 config、assets、prompts 和 plugins；清理 data、state、workspace、logs、dashboard、exports、dist 与 build，并初始化全新的 V2 SQLite。"
      type="info"
      :closable="false"
      show-icon
    />

    <div class="maintenance-actions">
      <article>
        <strong>仅创建备份</strong>
        <p>把当前项目的正文、状态和工作区写入带 SHA-256 校验值的 ZIP，不修改现有数据。</p>
        <el-button
          :disabled="!project || resetting"
          :loading="backingUp"
          @click="createBackup"
        >
          创建项目备份
        </el-button>
      </article>
      <article class="reset-action">
        <strong>备份并重置到 V2</strong>
        <p>适用于旧格式迁移或彻底重新开始。运行中的生成任务会阻止重置。</p>
        <el-button
          type="danger"
          plain
          :disabled="!project || backingUp"
          :loading="resetting"
          @click="resetProject"
        >
          重置当前项目
        </el-button>
      </article>
    </div>

    <div v-if="lastBackup" class="backup-result">
      <strong>最近备份</strong>
      <span>{{ lastBackup.name }}</span>
      <span>{{ lastBackup.file_count }} 个文件 · {{ formatBytes(lastBackup.size_bytes) }}</span>
      <code :title="lastBackup.sha256">SHA-256 {{ lastBackup.sha256.slice(0, 16) }}…</code>
    </div>
  </section>
</template>

<style scoped>
.maintenance-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.maintenance-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.eyebrow {
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
}
.maintenance-heading h3 {
  margin: 3px 0 4px;
  color: var(--color-text-strong);
  font-size: 16px;
}
.maintenance-heading p,
.maintenance-actions p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.65;
}
.maintenance-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.maintenance-actions article {
  display: grid;
  align-content: start;
  gap: 9px;
  min-height: 142px;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.maintenance-actions .el-button {
  align-self: end;
  justify-self: start;
  margin-top: auto;
}
.reset-action {
  border-color: color-mix(in srgb, var(--el-color-danger) 35%, var(--color-border)) !important;
  background: color-mix(in srgb, var(--el-color-danger) 4%, transparent);
}
.backup-result {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  padding: 11px 13px;
  border-radius: var(--radius-md);
  background: var(--color-bg-subtle);
  color: var(--color-text-muted);
  font-size: 11px;
}
.backup-result strong { color: var(--color-text-strong); }
.backup-result code { overflow: hidden; max-width: 240px; text-overflow: ellipsis; }
@media (max-width: 720px) {
  .maintenance-heading { flex-direction: column; }
  .maintenance-actions { grid-template-columns: 1fr; }
}
</style>
