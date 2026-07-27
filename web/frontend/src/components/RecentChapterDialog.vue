<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { ArrowRight, Document } from '@element-plus/icons-vue'
import { useChapterStore } from '../stores/chapter'

const visible = defineModel<boolean>('visible', { default: false })

const router = useRouter()
const store = useChapterStore()
const { latestChapter } = storeToRefs(store)

function goChapter(chapterId: string) {
  visible.value = false
  router.push({ path: '/writer', query: { chapter: chapterId } })
}

function goChapterList() {
  visible.value = false
  router.push('/writer')
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="最近产出章节"
    width="520px"
    class="recent-chapter-dialog"
    destroy-on-close
    append-to-body
  >
    <div v-if="latestChapter" class="chapter-focus">
      <div class="chapter-header-row">
        <span class="chapter-id">CHAPTER {{ latestChapter.chapter_id }}</span>
        <div class="chapter-meta">
          <span class="word-count">
            <el-icon><Document /></el-icon>
            {{ latestChapter.word_count || 0 }} 字
          </span>
          <span
            class="risk-badge"
            :class="latestChapter.risk_level === '低' ? 'risk-low' : 'risk-high'"
          >
            {{ latestChapter.risk_level || '未审校' }} 风险
          </span>
        </div>
      </div>
      <h3 class="chapter-title">{{ latestChapter.title || '未命名章节' }}</h3>
      <p class="chapter-goal-preview">{{ latestChapter.goal || '没有指定章节目标' }}</p>
      <el-button type="primary" @click="goChapter(latestChapter.chapter_id)">
        进入章节工作区
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </div>
    <div v-else class="empty-state">
      <el-icon class="empty-icon"><Document /></el-icon>
      <p>还没有章节产物，请先运行一章或启动连写。</p>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" link @click="goChapterList">
        查看全部章节
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.chapter-focus {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.chapter-id {
  font-size: 12px;
  font-weight: 800;
  color: var(--primary, #409eff);
  background: var(--primary-light, #ecf5ff);
  padding: 4px 10px;
  border-radius: 6px;
  letter-spacing: 0.5px;
}

.chapter-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.word-count {
  font-size: 13px;
  color: var(--text-muted, #909399);
  display: flex;
  align-items: center;
  gap: 4px;
}

.risk-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}

.risk-low {
  background: #f0f9eb;
  color: #52c41a;
}

.risk-high {
  background: #fef0f0;
  color: #f56c6c;
}

.chapter-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1a2129;
}

.chapter-goal-preview {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted, #909399);
  line-height: 1.6;
  background: #fbfbfb;
  border: 1px dashed var(--border-light, #e4e7ed);
  padding: 14px;
  border-radius: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 8px;
  color: var(--text-muted, #909399);
  text-align: center;
}

.empty-icon {
  font-size: 36px;
  color: #c4cbd2;
}
</style>
