<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPrompt, listPrompts, resetPrompt, updatePrompt } from '../api'

interface PromptItem {
  role: string
  content: string
  has_default: boolean
}

const prompts = ref<PromptItem[]>([])
const loading = ref(false)
const expanded = ref(false)
const editDialogVisible = ref(false)
const editingRole = ref('')
const editingContent = ref('')
const saving = ref(false)

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

const loadPrompts = async () => {
  loading.value = true
  try {
    const { data } = await listPrompts()
    prompts.value = data
  } catch (error: any) {
    ElMessage.error(`加载提示词失败：${error.message || error}`)
  } finally {
    loading.value = false
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
    if (error !== 'cancel') ElMessage.error(error.message || '重置失败')
  }
}

const truncate = (text: string, len: number) => {
  if (!text) return '(空)'
  return text.length > len ? `${text.substring(0, len)}...` : text
}

onMounted(loadPrompts)
defineExpose({ loadPrompts })
</script>

<template>
  <section class="fold-card">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>提示词管理</h2>
          <p>管理多阶段 Agent 生产线提示词。已加载 {{ nonEmptyCount }}/{{ prompts.length }} 条。</p>
        </div>
      </div>
      <el-button class="fold-action" size="small" type="primary" @click.stop="expanded = !expanded">
        {{ expanded ? '收起' : '编辑配置' }}
      </el-button>
    </div>

    <div v-show="expanded" class="fold-body">
      <div class="toolbar">
        <p>空白提示词会自动从内置默认模板恢复。</p>
        <el-button :loading="loading" @click="loadPrompts">刷新</el-button>
      </div>
      <el-table :data="prompts" size="small" stripe v-loading="loading">
        <el-table-column label="角色" width="170">
          <template #default="{ row }">{{ roleLabels[row.role] || row.role }}</template>
        </el-table-column>
        <el-table-column prop="role" label="标识" width="180" />
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
      <div class="editor-meta">角色标识：{{ editingRole }} · 文件：prompts/{{ editingRole }}.md</div>
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
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar p,
.editor-meta,
.preview {
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
</style>
