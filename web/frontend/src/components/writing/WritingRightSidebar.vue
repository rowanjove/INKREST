<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue'
import { Fold } from '@element-plus/icons-vue'
import AssetSidebar from '../AssetSidebar.vue'

const props = defineProps<{
  setAssetSidebarRef: (el: { refreshAssets?: () => void } | null) => void
  activeChapterId: string
  currentChapter: any | null
  chaptersList: any[]
  scrapbookList: any[]
  loadingScrapbook: boolean
  loadingFeedback: boolean
  loadingGolden: boolean
  feedbackList: any[]
  goldenCheckResult: any | null
  onFetchScrapbook: () => void
  onCopyScrapbookText: (text: string) => void
  onInsertScrapbookText: (text: string) => void
  onSubmitFeedback: () => void
  onRunGoldenCheck: () => void
  onGoldenRewrite: () => void
}>()

const collapsed = defineModel<boolean>('collapsed', { required: true })
const rightTab = defineModel<'assets' | 'scrapbook' | 'feedback' | 'golden'>('rightTab', { required: true })
const scrapbookQuery = defineModel<string>('scrapbookQuery', { required: true })
const feedbackForm = defineModel<{
  chapter_id: string
  bounce_rate: number
  retention_rate: number
  active_readers: number
}>('feedbackForm', { required: true })

function bindAssetSidebarRef(el: Element | ComponentPublicInstance | null) {
  props.setAssetSidebarRef(el as { refreshAssets?: () => void } | null)
}
</script>

<template>
  <div class="sidebar-workspace" :class="{ collapsed }">
    <div class="right-sidebar-tabs">
      <button class="tab-btn" :class="{ active: rightTab === 'assets' }" @click="rightTab = 'assets'">🏰 设定</button>
      <button class="tab-btn" :class="{ active: rightTab === 'scrapbook' }" @click="rightTab = 'scrapbook'">🗑️ 废稿</button>
      <button class="tab-btn" :class="{ active: rightTab === 'feedback' }" @click="rightTab = 'feedback'">📊 反馈</button>
      <button class="tab-btn" :class="{ active: rightTab === 'golden' }" @click="rightTab = 'golden'">✨ 黄金</button>
      <el-button class="right-sidebar-collapse" :icon="Fold" link title="隐藏辅助栏" @click="collapsed = true" />
    </div>

    <div class="right-sidebar-content" v-show="rightTab === 'assets'">
      <AssetSidebar
        :ref="bindAssetSidebarRef"
        :chapter-id="activeChapterId"
        :chapter-goal="currentChapter?.plan?.chapter_goal || ''"
      />
    </div>

    <div class="right-sidebar-content scrapbook-panel" v-show="rightTab === 'scrapbook'">
      <div class="scrapbook-header">
        <el-input
          v-model="scrapbookQuery"
          placeholder="搜索废稿段落..."
          prefix-icon="Search"
          clearable
          @input="onFetchScrapbook"
          size="small"
        />
      </div>
      <div class="scrapbook-list" v-loading="loadingScrapbook">
        <el-empty v-if="scrapbookList.length === 0" description="废稿库暂无此类检索内容" :image-size="60" />
        <div v-else class="scrapbook-card" v-for="(item, idx) in scrapbookList" :key="idx">
          <div class="scrapbook-card-header">
            <span class="sc-ch">CH {{ item.chapter_id }}</span>
            <span class="sc-ver">{{ item.version_name }}</span>
          </div>
          <div class="sc-note" v-if="item.note">走向: {{ item.note }}</div>
          <p class="sc-text">{{ item.text }}</p>
          <div class="sc-actions">
            <el-button size="small" type="primary" link @click="onCopyScrapbookText(item.text)">复制段落</el-button>
            <el-button size="small" type="success" link @click="onInsertScrapbookText(item.text)">插入编辑器</el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="right-sidebar-content feedback-panel" v-show="rightTab === 'feedback'" style="padding: 16px; display: flex; flex-direction: column; height: calc(100% - 40px); overflow-y: auto; box-sizing: border-box;">
      <div style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
        📊 追读与跳出率监控
      </div>

      <div v-loading="loadingFeedback" style="flex: 1; min-height: 200px;">
        <el-empty v-if="feedbackList.length === 0" description="暂无章节读者反馈数据" :image-size="60" />
        <div v-else style="display: flex; flex-direction: column; gap: 10px;">
          <div
            v-for="item in feedbackList"
            :key="item.id"
            class="feedback-metric-card"
            style="border: 1px solid var(--color-border); border-radius: 8px; padding: 10px; background: var(--color-bg-surface);"
          >
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-weight: 600; font-size: 13px;">第 {{ item.chapter_id }} 章</span>
              <span
                :style="{
                  color: item.bounce_rate > 0.35 ? 'var(--color-danger)' : (item.bounce_rate > 0.25 ? 'var(--color-warning)' : 'var(--color-success)'),
                  fontWeight: 600,
                  fontSize: '11px'
                }"
              >
                {{ item.bounce_rate > 0.35 ? '🚨 重度危机' : (item.bounce_rate > 0.25 ? '⚠️ 中度警戒' : '✅ 节奏健康') }}
              </span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; font-size: 11px; color: var(--color-text-muted);">
              <div>跳出率: <strong :style="{ color: item.bounce_rate > 0.25 ? 'var(--color-danger)' : 'var(--color-text-strong)' }">{{ (item.bounce_rate * 100).toFixed(1) }}%</strong></div>
              <div>追读率: <strong>{{ (item.retention_rate * 100).toFixed(1) }}%</strong></div>
              <div>读者数: <strong>{{ item.active_readers }}</strong></div>
            </div>
            <div v-if="item.bounce_rate > 0.25" style="margin-top:6px; font-size:10px; color:var(--color-danger); background:#fef2f2; padding:4px 6px; border-radius:4px;">
              💡 Agent 在本章后已自动调大剧情冲突密度与爆点权重！
            </div>
          </div>
        </div>
      </div>

      <div style="border-top: 1px dashed var(--color-border); margin-top: 16px; padding-top: 16px;">
        <div style="font-weight: 600; font-size: 13px; margin-bottom: 12px; color: var(--color-text-muted);">
          🧪 读者数据模拟录入
        </div>
        <el-form label-width="70px" size="small">
          <el-form-item label="对应章节">
            <el-select v-model="feedbackForm.chapter_id" placeholder="选择章节" style="width:100%;">
              <el-option
                v-for="ch in chaptersList"
                :key="ch.chapter_id"
                :label="ch.title || `第 ${ch.chapter_id} 章`"
                :value="ch.chapter_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="跳出率">
            <el-slider v-model="feedbackForm.bounce_rate" :min="0" :max="1" :step="0.01" show-input :input-size="'small'" />
          </el-form-item>
          <el-form-item label="追读率">
            <el-slider v-model="feedbackForm.retention_rate" :min="0" :max="1" :step="0.01" show-input :input-size="'small'" />
          </el-form-item>
          <el-form-item label="活跃读者">
            <el-input-number v-model="feedbackForm.active_readers" :min="100" :max="1000000" style="width:100%;" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" style="width:100%;" @click="onSubmitFeedback">提交模拟数据</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="right-sidebar-content golden-panel" v-show="rightTab === 'golden'" style="padding: 16px; display: flex; flex-direction: column; height: calc(100% - 40px); overflow-y: auto; box-sizing: border-box;">
      <div style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
        ✨ 黄金三章签约级诊断向导
      </div>

      <div style="margin-bottom: 16px;">
        <el-button
          type="warning"
          style="width: 100%; font-weight: 600;"
          :loading="loadingGolden"
          @click="onRunGoldenCheck"
        >
          🚀 开始黄金三章质检评估
        </el-button>
      </div>

      <div v-if="goldenCheckResult" style="display: flex; flex-direction: column; gap: 14px;">
        <div v-if="goldenCheckResult.status === 'pending'" style="font-size: 12px; color: #909399; text-align: center;">
          {{ goldenCheckResult.message }}
        </div>
        <div v-else-if="goldenCheckResult.status === 'success'">
          <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 12px; background: #fffdf5; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
            <span style="font-size: 11px; color: #854d0e;">前三章综合推荐分</span>
            <span style="font-size: 32px; font-weight: 800; color: var(--color-warning); margin: 4px 0;">{{ goldenCheckResult.overall_score }}</span>
            <span style="font-size: 12px; font-weight: 600; color: #3f3f46; text-align: center;">"{{ goldenCheckResult.summary }}"</span>
          </div>

          <div style="font-weight: 600; font-size: 12px; color: #4b5563; margin-bottom: 8px;">诊断拆解：</div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div
              v-for="(check, idx) in goldenCheckResult.checks"
              :key="idx"
              style="border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px; background: #fefefe;"
            >
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-weight: 600; font-size: 12px; color: #1f2937;">{{ check.indicator }}</span>
                <el-tag
                  size="small"
                  :type="check.status === 'pass' ? 'success' : (check.status === 'warning' ? 'warning' : 'danger')"
                >
                  {{ check.score }}分
                </el-tag>
              </div>
              <div style="font-size: 11px; color: #6b7280; line-height: 1.4;">{{ check.reason }}</div>
            </div>
          </div>

          <div style="font-weight: 600; font-size: 12px; color: #4b5563; margin-top: 14px; margin-bottom: 8px;">编辑部整改建议：</div>
          <ul style="margin: 0; padding-left: 18px; font-size: 11px; color: #4b5563; line-height: 1.5; display: flex; flex-direction: column; gap: 6px;">
            <li v-for="(sug, idx) in goldenCheckResult.suggestions" :key="idx">{{ sug }}</li>
          </ul>

          <div v-if="['001', '002', '003', '1', '2', '3'].includes(activeChapterId)" style="margin-top: 20px; border-top: 1px solid var(--color-border); padding-top: 14px;">
            <el-button
              type="danger"
              style="width: 100%; font-weight: 600;"
              @click="onGoldenRewrite"
            >
              🔄 针对本章建议一键优化重写
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar-workspace {
  width: 320px;
  height: 100%;
  overflow: hidden;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  transition: width 0.25s ease, border-left-width 0.25s ease;
}
.sidebar-workspace.collapsed {
  width: 0;
  border-left-width: 0;
}
.right-sidebar-collapse {
  flex: none;
  margin-left: 2px;
}

.right-sidebar-tabs {
  display: flex;
  background: var(--color-bg-surface-muted);
  border-bottom: 1px solid var(--color-border);
  padding: 4px;
}
.tab-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.tab-btn:hover {
  background: var(--color-border-subtle);
  color: var(--color-text-strong);
}
.tab-btn.active {
  background: var(--color-bg-surface);
  color: var(--primary, #c66f4f);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.right-sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100% - 37px);
}
.scrapbook-panel {
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
}
.scrapbook-header {
  padding: 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}
.scrapbook-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.scrapbook-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.scrapbook-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sc-ch {
  font-size: 11px;
  font-weight: 700;
  background: var(--color-border);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
}
.sc-ver {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary, #c66f4f);
}
.sc-note {
  font-size: 11px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 4px 8px;
  border-radius: 4px;
}
.sc-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
}
.sc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--color-bg-hover);
  padding-top: 8px;
}
</style>