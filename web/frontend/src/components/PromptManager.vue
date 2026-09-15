<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { isMessageBoxDismissal } from '../utils/elementPlusServices'
import {
  getPrompt,
  getPromptManifest,
  getProseProfile,
  listPrompts,
  resetPrompt,
  restoreProseProfile,
  updatePrompt,
} from '../api'

interface PromptItem {
  role: string
  content: string
  has_default: boolean
}

interface PromptManifestRole {
  role: string
  selected_source?: string | null
  selected_sha256?: string | null
  has_drift?: boolean
  drift?: Array<{ type?: string; severity?: string }>
}

interface ProseProfileVersion {
  revision: number
  profile_id?: string
  sample_count?: number
  char_count?: number
  status?: string
  is_active?: boolean
}

interface ProseProfile {
  status?: string
  revision?: number
  profile_id?: string
  sample_count?: number
}

const prompts = ref<PromptItem[]>([])
const loading = ref(false)
const expanded = ref(false)
const editDialogVisible = ref(false)
const editingRole = ref('')
const editingContent = ref('')
const saving = ref(false)
const manifest = ref<Record<string, PromptManifestRole>>({})
const proseProfile = ref<ProseProfile | null>(null)
const profileVersions = ref<ProseProfileVersion[]>([])
const versionDialogVisible = ref(false)
const restoringRevision = ref<number | null>(null)

const roleLabels: Record<string, string> = {
  chief_editor: '总编 Agent',
  managing_editor: '主编 Agent',
  chapter_planner: '大纲编剧 Agent',
  planner: '章节规划 Agent',
  writer: '子 Agent 写手',
  stitch_editor: '拼接润色 Agent',
  style_editor: '文风润色 Agent',
  auditor: '审核 QA Agent',
  continuity_checker: '连续性检查 Agent',
  chapter_summary: '章节总结 Agent',
  expander: '扩写 Agent',
  compressor: '压缩 Agent',
  asset_compressor: '素材压缩 Agent',
}

const nonEmptyCount = computed(() => prompts.value.filter((item) => item.content?.trim()).length)
const manifestDriftCount = computed(() => Object.values(manifest.value).filter((item) => item.has_drift).length)
const profileStatusLabel = computed(() => {
  if (!proseProfile.value || proseProfile.value.status !== 'calibrated') return '文风档案未校准'
  const revision = proseProfile.value.revision ? ` · r${proseProfile.value.revision}` : ''
  return `文风档案已校准${revision}`
})

const sourceLabel = (source?: string | null) => ({
  project: '项目覆盖',
  environment: '模板环境',
  package: 'canonical',
}[source || ''] || '未解析')

const digestLabel = (digest?: string | null) => digest ? digest.slice(0, 12) : '—'

const loadPrompts = async () => {
  loading.value = true
  try {
    const { data } = await listPrompts()
    prompts.value = data
    const [manifestResult, profileResult] = await Promise.all([getPromptManifest(), getProseProfile()])
    const manifestRows = manifestResult.data?.roles || []
    manifest.value = Object.fromEntries(manifestRows.map((item: PromptManifestRole) => [item.role, item]))
    proseProfile.value = profileResult.data?.profile || null
    profileVersions.value = profileResult.data?.versions || []
  } catch (error: any) {
    ElMessage.error(`加载提示词失败：${error.message || error}`)
  } finally {
    loading.value = false
  }
}

const handleRestoreProfile = async (revision: number) => {
  try {
    await ElMessageBox.confirm(
      `确定恢复文风档案修订 r${revision} 吗？当前档案会保留为新的历史修订。`,
      '恢复文风档案',
      { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'warning' },
    )
    restoringRevision.value = revision
    await restoreProseProfile(revision)
    ElMessage.success(`已恢复文风档案 r${revision}`)
    await loadPrompts()
  } catch (error: any) {
    if (!isMessageBoxDismissal(error)) ElMessage.error(error.message || '恢复失败')
  } finally {
    restoringRevision.value = null
  }
}

const openEditor = async (item: PromptItem) => {
  editingRole.value = item.role
  const { data } = await getPrompt(item.role)
  editingContent.value = data.content || item.content || ''
  editDialogVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    await updatePrompt(editingRole.value, editingContent.value)
    ElMessage.success('提示词已保存')
    editDialogVisible.value = false
    await loadPrompts()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = async (role: string) => {
  try {
    await ElMessageBox.confirm(
      `确定将「${roleLabels[role] || role}」重置为系统默认提示词吗？当前修改会丢失。`,
      '重置提示词',
      { confirmButtonText: '重置', cancelButtonText: '取消', type: 'warning' },
    )
    await resetPrompt(role)
    ElMessage.success('已重置为系统默认')
    if (editDialogVisible.value && editingRole.value === role) {
      const { data } = await getPrompt(role)
      editingContent.value = data.content
    }
    await loadPrompts()
  } catch (error: any) {
    if (!isMessageBoxDismissal(error)) ElMessage.error(error.message || '重置失败')
  }
}

const truncate = (text: string, len: number) => {
  if (!text) return '(空)'
  return text.length > len ? `${text.substring(0, len)}...` : text
}

const props = withDefaults(
  defineProps<{
    bare?: boolean
  }>(),
  {
    bare: false,
  },
)

onMounted(loadPrompts)
defineExpose({ loadPrompts })
</script>

<template>
  <section class="fold-card" :class="{ 'is-bare': bare }">
    <div v-if="!bare" class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>提示词管理</h2>
          <p>管理多阶段 Agent 生产线提示词。已加载 {{ nonEmptyCount }}/{{ prompts.length }} 条。</p>
        </div>
      </div>
    </div>

    <div v-show="bare || expanded" class="fold-body">
      <div class="toolbar">
        <div class="prompt-status">
          <p>空白提示词会自动从内置默认模板恢复。</p>
          <div class="status-tags">
            <el-tag size="small" :type="manifestDriftCount ? 'warning' : 'success'">
              {{ manifestDriftCount ? `${manifestDriftCount} 个默认快照有漂移` : '默认快照一致' }}
            </el-tag>
            <el-tag size="small" :type="proseProfile?.status === 'calibrated' ? 'success' : 'info'">
              {{ profileStatusLabel }}
            </el-tag>
            <el-button text type="primary" size="small" @click="versionDialogVisible = true">
              查看档案历史
            </el-button>
          </div>
        </div>
        <el-button :loading="loading" @click="loadPrompts">刷新</el-button>
      </div>
      <el-table :data="prompts" size="small" stripe v-loading="loading">
        <el-table-column label="角色" width="170">
          <template #default="{ row }">{{ roleLabels[row.role] || row.role }}</template>
        </el-table-column>
        <el-table-column prop="role" label="标识" width="180" />
        <el-table-column label="生效来源" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ sourceLabel(manifest[row.role]?.selected_source) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="摘要" width="130">
          <template #default="{ row }">
            <span class="digest">{{ digestLabel(manifest[row.role]?.selected_sha256) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="漂移" width="90">
          <template #default="{ row }">
            <el-tag v-if="manifest[row.role]?.has_drift" size="small" type="warning">需查看</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="内容预览">
          <template #default="{ row }">
            <span class="preview">{{ truncate(row.content, 120) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEditor(row)">编辑</el-button>
            <el-button v-if="row.has_default" text type="warning" size="small" @click="handleReset(row.role)">重置</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="editDialogVisible" :title="`编辑提示词 · ${roleLabels[editingRole] || editingRole}`" width="900px" top="5vh">
      <div class="editor-meta">
        角色标识：{{ editingRole }} · 文件：prompts/{{ editingRole }}.md · 来源：{{ sourceLabel(manifest[editingRole]?.selected_source) }}
      </div>
      <el-input
        v-model="editingContent"
        type="textarea"
        :autosize="{ minRows: 18, maxRows: 32 }"
        placeholder="输入提示词内容..."
        spellcheck="false"
        class="prompt-textarea"
      />
      <template #footer>
        <el-button type="warning" @click="handleReset(editingRole)">重置为默认</el-button>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionDialogVisible" title="文风档案历史" width="720px">
      <p class="version-note">
        档案只保存统计特征与样本哈希，不保存样本文本。恢复会生成新的修订，不会删除旧版本。
      </p>
      <el-empty v-if="!profileVersions.length" description="尚未生成文风档案，可使用 calibrate-prose 命令校准" />
      <el-table v-else :data="profileVersions" size="small" stripe>
        <el-table-column label="修订" width="90">
          <template #default="{ row }">r{{ row.revision }}<el-tag v-if="row.is_active" size="small" type="success" class="active-tag">当前</el-tag></template>
        </el-table-column>
        <el-table-column prop="profile_id" label="Profile ID" min-width="170" />
        <el-table-column prop="sample_count" label="样本数" width="90" />
        <el-table-column prop="char_count" label="字符数" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              text
              type="warning"
              size="small"
              :disabled="row.is_active"
              :loading="restoringRevision === row.revision"
              @click="handleRestoreProfile(row.revision)"
            >恢复</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.prompt-status {
  min-width: 0;
}

.status-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar p,
.editor-meta,
.preview,
.version-note,
.digest,
.muted {
  color: var(--color-text-muted);
  font-size: 13px;
}

.toolbar p {
  margin: 0;
}

.editor-meta {
  margin-bottom: 8px;
}

.prompt-textarea {
  font-family: "Cascadia Mono", Consolas, monospace;
}

.active-tag {
  margin-left: 6px;
}
</style>
