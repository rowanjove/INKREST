<script setup lang="ts">
import { ArrowLeft, CopyDocument, Document, Edit, InfoFilled, RefreshRight, Warning } from '@element-plus/icons-vue'

defineProps<{
  chapter: any
  externalStatus: 'none' | 'pending_external' | 'external_passed'
  hasFinalText: boolean
  wordStatusLabel: string
  copying: boolean
  rewriting: boolean
}>()

const emit = defineEmits<{
  goBack: []
  saveExternalStatus: [status: 'none' | 'pending_external' | 'external_passed']
  handleCopyFullText: []
  startEdit: []
  handleRewrite: []
}>()
</script>

<template>
  <div class="page-header-nav">
    <el-button class="back-btn" size="small" @click="emit('goBack')">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>
    <div class="breadcrumbs">
      <span>章节列表</span> / <span class="active">章节详情</span>
    </div>
  </div>

  <div class="chapter-top-header">
    <div class="header-title-area">
      <span class="chapter-badge-id">CH {{ chapter.chapter_id }}</span>
      <h2 class="chapter-title-main" :title="chapter.title">{{ chapter.title || '无标题章节' }}</h2>
    </div>
    <div class="header-actions-area">
      <el-select
        :model-value="externalStatus"
        size="default"
        class="external-select"
        placeholder="外审状态"
        @update:model-value="emit('saveExternalStatus', $event)"
      >
        <el-option label="未标记" value="none" />
        <el-option label="待外审" value="pending_external" />
        <el-option label="外审已通过" value="external_passed" />
      </el-select>
      <el-button type="primary" plain :icon="CopyDocument" :loading="copying" @click="emit('handleCopyFullText')">
        复制全文
      </el-button>
      <el-button v-if="hasFinalText" class="edit-btn" type="warning" :icon="Edit" @click="emit('startEdit')">
        编辑本章
      </el-button>
      <el-tooltip
        v-if="hasFinalText"
        content="从规划阶段完整重跑流水线；质量阻断请用章节维护「重试审校」或本章「统一门禁」页。"
        placement="bottom"
      >
        <el-button
          class="rewrite-btn"
          type="primary"
          :icon="RefreshRight"
          :loading="rewriting"
          @click="emit('handleRewrite')"
        >
          整章重写
        </el-button>
      </el-tooltip>
    </div>
  </div>

  <el-row :gutter="16" class="meta-row">
    <el-col :span="8">
      <div class="meta-card">
        <div class="m-card-icon m-blue"><el-icon><Document /></el-icon></div>
        <div>
          <div class="m-val">{{ chapter.wordcount?.count || 0 }}</div>
          <div class="m-lbl">汉字字数</div>
        </div>
      </div>
    </el-col>
    <el-col :span="8">
      <div class="meta-card">
        <div class="m-card-icon m-orange"><el-icon><InfoFilled /></el-icon></div>
        <div>
          <div class="m-val">{{ wordStatusLabel }}</div>
          <div class="m-lbl">字数状态</div>
        </div>
      </div>
    </el-col>
    <el-col :span="8">
      <div class="meta-card">
        <div
          class="m-card-icon"
          :class="chapter.audit?.risk_level === '低' ? 'm-green' : 'm-red'"
        >
          <el-icon><Warning /></el-icon>
        </div>
        <div>
          <div class="m-val">{{ chapter.audit?.risk_level || '未审校' }}</div>
          <div class="m-lbl">安全风险等级</div>
        </div>
      </div>
    </el-col>
  </el-row>
</template>

<style scoped>
.back-btn {
  border-radius: 6px !important;
}

.page-header-nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chapter-top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 8px 0;
}

.header-title-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1 1 auto;
  min-width: 0;
}

.chapter-badge-id {
  background: var(--primary);
  color: var(--color-bg-surface);
  font-weight: 800;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  flex-shrink: 0;
}

.chapter-title-main {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--color-text-strong, #0f172a);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions-area {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}

.external-select {
  width: 120px;
}

.meta-row {
  margin-bottom: 8px;
}

.meta-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
}

.m-card-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  font-size: 18px;
}

.m-blue {
  background: #eaf6fc;
  color: #2e5f75;
}

.m-orange {
  background: #fdf2eb;
  color: var(--primary);
}

.m-green {
  background: #f0f9eb;
  color: #52c41a;
}

.m-red {
  background: #fef0f0;
  color: #f56c6c;
}

.m-val {
  font-size: 20px;
  font-weight: 800;
  color: #1a2129;
}

.m-lbl {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>