<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getChapter, listAssets, getAsset, createAsset } from '../api'
import { ElMessage, ElNotification } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

const props = defineProps<{
  chapterId: string
  chapterGoal: string
}>()

const activeTab = ref<'outline' | 'assets'>('outline')

// ---- Story / Outline Tab State ----
const prevSummary = ref('')
const nextSummary = ref('')
const loadingOutline = ref(false)

// ---- Assets Tab State ----
const assetsList = ref<any[]>([])
const searchQuery = ref('')
const loadingAssets = ref(false)
const selectedAsset = ref<any>(null)
const showAssetDetail = ref(false)

// Resolve previous/next chapter IDs (e.g. "002" -> "001" and "003")
const getAdjacentChapterIds = (cid: string) => {
  const num = parseInt(cid, 10)
  if (isNaN(num)) return { prevId: '', nextId: '' }
  const prevNum = num - 1
  const nextNum = num + 1
  
  // Keep same padding style (e.g. "001", "002", etc.)
  const pad = (n: number) => n.toString().padStart(cid.length, '0')
  return {
    prevId: prevNum > 0 ? pad(prevNum) : '',
    nextId: pad(nextNum)
  }
}

// Fetch summaries for adjacent chapters
const fetchAdjacentSummaries = async (cid: string) => {
  if (!cid) return
  loadingOutline.value = true
  prevSummary.value = '无前章摘要'
  nextSummary.value = '无后章摘要'
  
  const { prevId, nextId } = getAdjacentChapterIds(cid)
  
  try {
    if (prevId) {
      const { data } = await getChapter(prevId)
      prevSummary.value = data.chapter_summary || data.plan?.chapter_goal || '前章暂无摘要'
    }
  } catch (e) {
    prevSummary.value = '前章暂未生成内容'
  }

  try {
    if (nextId) {
      const { data } = await getChapter(nextId)
      nextSummary.value = data.chapter_summary || data.plan?.chapter_goal || '后章暂无摘要'
    }
  } catch (e) {
    nextSummary.value = '后章暂未生成内容'
  }
  
  loadingOutline.value = false
}

// Fetch Assets
const fetchAssetsList = async () => {
  loadingAssets.value = true
  try {
    const { data } = await listAssets()
    // Filter out style_guide, rules, and sensitive_words
    assetsList.value = (data || []).filter((a: any) => a.name !== 'style_guide' && a.name !== 'rules' && a.name !== 'sensitive_words')
  } catch (e: any) {
    ElMessage.error('获取资产列表失败: ' + e.message)
  } finally {
    loadingAssets.value = false
  }
}

// ---- Create Asset State ----
const showCreateDialog = ref(false)
const createForm = ref({
  name: '',
  label: '',
  content: ''
})
const creating = ref(false)

const handleOpenCreateDialog = () => {
  createForm.value = {
    name: '',
    label: '',
    content: ''
  }
  showCreateDialog.value = true
}

const handleCreateAsset = async () => {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请填写英文标识')
    return
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(createForm.value.name)) {
    ElMessage.warning('英文标识仅支持英文字母、数字和下划线/连字符')
    return
  }
  creating.value = true
  try {
    const initContent = createForm.value.content || `# ${createForm.value.label || createForm.value.name}\n\n* 类型：子设定\n* 标识：${createForm.value.name}\n\n## 设定描述\n（此处补充名词解释）\n`
    await createAsset({
      name: createForm.value.name.trim(),
      label: createForm.value.label.trim() || createForm.value.name.trim(),
      extension: 'md',
      content: initContent
    })
    showCreateDialog.value = false
    
    ElNotification({
      title: '资产新增成功',
      message: '新资产已保存！请点击右上角的 🔄 刷新按钮，同步更新至当前系统。',
      type: 'success',
      duration: 10000
    })
    
    await fetchAssetsList()
  } catch (e: any) {
    ElMessage.error('新增资产失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

// View asset details on demand
const handleViewAsset = async (assetName: string) => {
  try {
    const { data } = await getAsset(assetName)
    selectedAsset.value = data
    showAssetDetail.value = true
  } catch (e: any) {
    ElMessage.error('获取资产详情失败: ' + e.message)
  }
}

// Expose refresh function to parent
defineExpose({
  refreshAssets: fetchAssetsList
})

// Watch chapter ID change
watch(() => props.chapterId, (newId) => {
  if (newId) {
    fetchAdjacentSummaries(newId)
  }
}, { immediate: true })

onMounted(() => {
  fetchAssetsList()
})
</script>

<template>
  <aside class="asset-sidebar">
    <el-tabs v-model="activeTab" class="sidebar-tabs" stretch>
      <!-- 故事大纲 Tab -->
      <el-tab-pane label="📖 故事大纲" name="outline">
        <div class="outline-pane-content" v-loading="loadingOutline">
          <div class="card-section">
            <h4 class="section-title">✨ 本章生成目标</h4>
            <div class="card-body goal-text">
              {{ chapterGoal || '暂无本章写作目标，请先在章节规划中设置。' }}
            </div>
          </div>

          <div class="card-section">
            <h4 class="section-title">⬅️ 前一章摘要</h4>
            <div class="card-body summary-text">
              {{ prevSummary }}
            </div>
          </div>

          <div class="card-section">
            <h4 class="section-title">➡️ 后一章预设</h4>
            <div class="card-body summary-text">
              {{ nextSummary }}
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 设定资产 Tab -->
      <el-tab-pane label="🗃️ 设定资产" name="assets">
        <div class="assets-pane-content">
          <div class="search-bar">
            <el-input
              v-model="searchQuery"
              placeholder="搜索角色、道具、设定..."
              clearable
              size="small"
              style="flex: 1;"
            />
            <el-button :icon="Refresh" size="small" circle @click="fetchAssetsList" style="margin-left: 6px;" title="刷新资产" />
            <el-button type="primary" :icon="Plus" size="small" circle @click="handleOpenCreateDialog" style="margin-left: 4px;" title="新增资产" />
          </div>

          <div class="assets-scroll-area" v-loading="loadingAssets">
            <el-empty v-if="assetsList.length === 0" description="暂无设定资产，写作时保存会自动同步提取。" :image-size="60" />
            <div v-else class="assets-grid">
              <div
                v-for="asset in assetsList.filter(a => !searchQuery || a.label.includes(searchQuery) || a.name.includes(searchQuery))"
                :key="asset.name"
                class="asset-item-card"
                @click="handleViewAsset(asset.name)"
              >
                <div class="asset-header">
                  <span class="asset-label">{{ asset.label }}</span>
                  <el-tag size="small" :type="asset.name === 'character_cards' ? 'success' : (asset.custom ? 'info' : 'warning')">
                    {{ asset.name === 'character_cards' ? '人设卡' : (asset.custom ? '子设定' : '设定') }}
                  </el-tag>
                </div>
                <div class="asset-name-id">{{ asset.name }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 资产详情抽屉弹窗 -->
    <el-drawer
      v-model="showAssetDetail"
      :title="selectedAsset?.label || '资产设定详情'"
      direction="rtl"
      size="320px"
      :append-to-body="true"
    >
      <div v-if="selectedAsset" class="asset-detail-drawer">
        <div class="detail-meta">
          <p><strong>英文标识:</strong> <code>{{ selectedAsset.name }}</code></p>
          <p><strong>存储路径:</strong> <code>{{ selectedAsset.path }}</code></p>
        </div>
        <div class="detail-content-box">
          <strong>设定内容:</strong>
          <pre class="content-pre">{{ selectedAsset.content || '无内容描述。' }}</pre>
        </div>
      </div>
    <!-- 新增资产对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="➕ 手动新增子设定资产"
      width="340px"
      :append-to-body="true"
    >
      <el-form label-position="top" size="small">
        <el-form-item label="英文标识 (ID)" required>
          <el-input v-model="createForm.name" placeholder="仅限字母/数字/下划线，例如 ling_yao_shan" />
        </el-form-item>
        <el-form-item label="中文名称" required>
          <el-input v-model="createForm.label" placeholder="例如：灵药山" />
        </el-form-item>
        <el-form-item label="设定内容 (名词解释)">
          <el-input
            v-model="createForm.content"
            type="textarea"
            :rows="4"
            placeholder="（可选）补充关于该设定/名词的详细解释..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button size="small" @click="showCreateDialog = false">取消</el-button>
          <el-button size="small" type="primary" :loading="creating" @click="handleCreateAsset">新增</el-button>
        </div>
      </template>
    </el-dialog>
  </el-drawer>
  </aside>
</template>

<style scoped>
.asset-sidebar {
  width: 100%;
  height: 100%;
  border-left: 1px solid rgba(220, 227, 237, 0.45);
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.sidebar-tabs :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.outline-pane-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-title {
  margin: 0;
  font-size: 13px;
  color: #4a5568;
  font-weight: 700;
}

.card-body {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px;
  font-size: 12.5px;
  line-height: 1.5;
  color: #2d3748;
}

.goal-text {
  border-left: 3px solid #007aff;
  font-weight: 500;
}

.summary-text {
  color: #718096;
}

/* ---- Assets Tab CSS ---- */
.assets-pane-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
  overflow: hidden;
}

.search-bar {
  display: flex;
  align-items: center;
  flex: none;
}

.assets-scroll-area {
  flex: 1;
  overflow-y: auto;
}

.assets-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.asset-item-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.asset-item-card:hover {
  border-color: #007aff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.asset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.asset-label {
  font-weight: 700;
  color: #1a202c;
  font-size: 13px;
}

.asset-name-id {
  font-size: 11px;
  color: #a0aec0;
  font-family: monospace;
  margin-top: 4px;
}

/* ---- Detail Drawer ---- */
.asset-detail-drawer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-meta {
  font-size: 12px;
  color: #4a5568;
}

.detail-meta p {
  margin: 4px 0;
}

.detail-content-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.content-pre {
  background: #f7fafc;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  color: #2d3748;
}
</style>
