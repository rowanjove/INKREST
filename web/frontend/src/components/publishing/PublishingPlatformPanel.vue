<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Check, DataAnalysis, Guide, Warning } from '@element-plus/icons-vue'

import type { PublishingWorkspace } from '../../entities/publishing/publishing'

const props = defineProps<{
  workspace: PublishingWorkspace
  selectedChapterId: string
  saving: boolean
}>()
const emit = defineEmits<{
  platform: [platform: string]
  feedback: [payload: { bounce_rate: number; retention_rate: number; active_readers: number }]
}>()

const platforms = [
  { value: 'qidian', label: '起点中文网' },
  { value: 'fanqie', label: '番茄小说' },
  { value: 'feilu', label: '飞卢小说网' },
  { value: 'jinjiang', label: '晋江文学城' },
]
const feedback = reactive({
  bounce_rate: 0,
  retention_rate: 0,
  active_readers: 0,
})
const current = computed(() =>
  props.workspace.feedback.find((item) => item.chapter_id === props.selectedChapterId),
)
watch(
  current,
  (value) => {
    feedback.bounce_rate = value?.bounce_rate || 0
    feedback.retention_rate = value?.retention_rate || 0
    feedback.active_readers = value?.active_readers || 0
  },
  { immediate: true },
)
</script>

<template>
  <section class="platform-grid">
    <div class="platform-column">
      <article class="panel platform-card">
        <header>
          <el-icon><Guide /></el-icon>
          <div><h2>目标平台</h2><p>选择会影响后续创作提示与发布检查。</p></div>
        </header>
        <el-select
          :model-value="workspace.platform.id"
          :loading="saving"
          size="large"
          @change="emit('platform', String($event))"
        >
          <el-option
            v-for="item in platforms"
            :key="item.value"
            :value="item.value"
            :label="item.label"
          />
        </el-select>
        <div class="rule-metrics">
          <div><span>节奏密度</span><strong>{{ workspace.platform.pacing_density }}/5</strong></div>
          <div><span>设定权重</span><strong>{{ workspace.platform.setting_detail_weight }}/5</strong></div>
          <div>
            <span>建议对话占比</span>
            <strong>
              {{ Math.round(workspace.platform.dialogue_ratio_range[0] * 100) }}–{{
                Math.round(workspace.platform.dialogue_ratio_range[1] * 100)
              }}%
            </strong>
          </div>
        </div>
        <p class="style-summary">{{ workspace.platform.style_summary }}</p>
        <div class="avoid-list">
          <strong>发布前避坑</strong>
          <span v-for="item in workspace.platform.avoid" :key="item">
            <el-icon><Warning /></el-icon>{{ item }}
          </span>
        </div>
      </article>

      <article class="panel">
        <header>
          <el-icon><DataAnalysis /></el-icon>
          <div><h2>外站读者反馈</h2><p>手动录入测试数据，不会连接或投稿到外部平台。</p></div>
        </header>
        <div class="feedback-form">
          <label>
            当前章节
            <el-input :model-value="`第 ${selectedChapterId || '—'} 章`" disabled />
          </label>
          <label>
            跳出率
            <el-input-number
              v-model="feedback.bounce_rate"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="2"
              controls-position="right"
            />
          </label>
          <label>
            留存率
            <el-input-number
              v-model="feedback.retention_rate"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="2"
              controls-position="right"
            />
          </label>
          <label>
            活跃读者
            <el-input-number
              v-model="feedback.active_readers"
              :min="0"
              :step="10"
              controls-position="right"
            />
          </label>
        </div>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!selectedChapterId"
          @click="emit('feedback', { ...feedback })"
        >
          保存反馈
        </el-button>
      </article>
    </div>

    <div class="platform-column">
      <article class="panel golden-card">
        <header>
          <el-icon><Check /></el-icon>
          <div>
            <h2>黄金三章</h2>
            <p>{{ workspace.golden_check.ready_count }}/3 章已有可检查正文。</p>
          </div>
        </header>
        <div class="golden-list">
          <div
            v-for="item in workspace.golden_check.checks"
            :key="item.chapter_id"
            :class="{ ready: item.status === 'ready' }"
          >
            <span>{{ item.chapter_id }}</span>
            <div><strong>{{ item.label }}</strong><small>{{ item.word_count }} 字</small></div>
            <em>{{ item.status === 'ready' ? '已有正文' : '待补齐' }}</em>
          </div>
        </div>
        <div class="golden-rules">
          <strong>{{ workspace.platform.label }}检查提示</strong>
          <p>{{ workspace.platform.golden_three_rules }}</p>
        </div>
      </article>

      <article class="panel check-card">
        <header><div><h2>平台规则检查</h2><p>页面打开时仅执行确定性检查，不调用模型。</p></div></header>
        <div class="check-list">
          <div v-for="item in workspace.platform_check.items" :key="item.code">
            <span :class="item.status">{{ item.status === 'ready' ? '通过' : item.status === 'review' ? '复核' : '待处理' }}</span>
            <div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.platform-grid { display: grid; min-height: 100%; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; padding: 10px; overflow: auto; background: var(--color-bg-surface-muted); }
.platform-column { display: grid; align-content: start; gap: 10px; }
.panel { padding: 16px; border: 1px solid var(--color-border); border-radius: 11px; background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.panel > header { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 14px; }
.panel > header > .el-icon { width: 30px; height: 30px; flex: 0 0 30px; border-radius: 8px; background: var(--color-primary-soft); color: var(--color-primary); }
.panel h2 { margin: 0; color: var(--color-text-strong); font-size: 14px; }
.panel header p { margin: 3px 0 0; color: var(--color-text-muted); font-size: 10px; }
.platform-card > .el-select { width: 100%; }
.rule-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin: 12px 0; }
.rule-metrics div { display: grid; gap: 2px; padding: 9px; border-radius: 8px; background: var(--color-bg-surface-muted); }
.rule-metrics span { color: var(--color-text-muted); font-size: 9px; }
.rule-metrics strong { color: var(--color-text-strong); font-size: 12px; }
.style-summary { margin: 0; padding: 10px; border-left: 3px solid var(--color-primary); background: var(--color-primary-soft); color: var(--color-text); font-size: 10px; line-height: 1.7; }
.avoid-list { display: grid; gap: 6px; margin-top: 12px; }
.avoid-list > strong { color: var(--color-text-strong); font-size: 10px; }
.avoid-list span { display: flex; align-items: center; gap: 6px; color: var(--color-text-muted); font-size: 10px; }
.avoid-list .el-icon { color: var(--color-warning); }
.feedback-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.feedback-form label { display: grid; gap: 5px; color: var(--color-text-muted); font-size: 10px; }
.feedback-form .el-input-number { width: 100%; }
.golden-list { display: grid; gap: 7px; }
.golden-list > div { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 9px; border: 1px solid var(--color-border); border-radius: 8px; }
.golden-list > div > span { display: grid; width: 30px; height: 30px; place-items: center; border-radius: 8px; background: var(--color-bg-surface-muted); color: var(--color-text-muted); font-size: 9px; font-weight: 800; }
.golden-list > div.ready > span { background: var(--color-success-soft); color: var(--color-success); }
.golden-list div div { display: grid; min-width: 0; gap: 2px; }
.golden-list strong { overflow: hidden; color: var(--color-text-strong); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.golden-list small { color: var(--color-text-muted); font-size: 9px; }
.golden-list em { color: var(--color-warning); font-size: 9px; font-style: normal; }
.golden-list .ready em { color: var(--color-success); }
.golden-rules { margin-top: 12px; padding: 11px; border-radius: 8px; background: var(--color-bg-surface-muted); }
.golden-rules strong { color: var(--color-text-strong); font-size: 10px; }
.golden-rules p { margin: 6px 0 0; color: var(--color-text-muted); font-size: 10px; line-height: 1.7; }
.check-list { display: grid; gap: 9px; }
.check-list > div { display: flex; align-items: flex-start; gap: 9px; }
.check-list > div > span { flex: 0 0 38px; padding: 3px 5px; border-radius: 999px; background: var(--color-warning-soft); color: var(--color-warning); font-size: 8px; font-weight: 800; text-align: center; }
.check-list > div > span.ready { background: var(--color-success-soft); color: var(--color-success); }
.check-list div div { display: grid; gap: 2px; }
.check-list strong { color: var(--color-text-strong); font-size: 10px; }
.check-list p { margin: 0; color: var(--color-text-muted); font-size: 9px; line-height: 1.5; }
@media (max-width: 900px) {
  .platform-grid { grid-template-columns: 1fr; }
}
</style>
