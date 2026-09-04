<script setup lang="ts">
import { computed, ref } from 'vue'
import { Clock, MagicStick, Reading, Setting } from '@element-plus/icons-vue'
import type {
  AiEditIntent,
  AiEditSuggestion,
  ManuscriptContext,
  ManuscriptDocument,
  ManuscriptRevision,
} from '../../entities/manuscript/manuscript'
import { REVISION_SOURCE_LABELS } from '../../entities/manuscript/manuscript'

const props = defineProps<{
  document: ManuscriptDocument | null
  context: ManuscriptContext
  history: ManuscriptRevision[]
  aiIntent: AiEditIntent | null
  aiSuggestion: AiEditSuggestion | null
  aiLoading: boolean
  fontSize: number
  lineHeight: number
}>()

const emit = defineEmits<{
  confirmAi: []
  cancelAi: []
  acceptAi: []
  acceptQualityCandidate: []
  previewRevision: [revision: ManuscriptRevision]
  updateFontSize: [value: number]
  updateLineHeight: [value: number]
}>()

const activeTab = ref<'context' | 'ai' | 'review' | 'history' | 'settings'>('context')
const targetRange = computed(() => {
  const target = props.context.target_chars
  if (!Array.isArray(target) || target.length < 2) return '未设置'
  return `${target[0]}–${target[1]} 字`
})
const qualityCandidate = computed(() => props.context.quality_candidate)
const qualityCandidateStatus = computed(() => {
  const metadata = qualityCandidate.value?.metadata
  if (metadata?.adopted) return `已采纳${metadata.adopted_revision ? ` · 修订 ${metadata.adopted_revision}` : ''}`
  if (metadata?.accepted) return '已通过契约'
  if (metadata?.status === 'rejected') return '已拒绝，正文未变'
  return '待审阅'
})
const qualityCandidateCanAdopt = computed(() => {
  const metadata = qualityCandidate.value?.metadata
  return Boolean(qualityCandidate.value?.available && metadata?.accepted && !metadata.adopted)
})

function showAiTab() {
  activeTab.value = 'ai'
}

defineExpose({ showAiTab })
</script>

<template>
  <aside class="manuscript-inspector">
    <nav class="inspector-tabs" aria-label="正文辅助工具">
      <button :class="{ active: activeTab === 'context' }" @click="activeTab = 'context'">
        <Reading />上下文
      </button>
      <button :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">
        <MagicStick />AI
      </button>
      <button :class="{ active: activeTab === 'review' }" @click="activeTab = 'review'">
        <span>✓</span>审校
      </button>
      <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
        <Clock />历史
      </button>
      <button :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">
        <Setting />设置
      </button>
    </nav>

    <div class="inspector-body">
      <section v-if="activeTab === 'context'" class="inspector-section">
        <div class="section-heading">
          <span>本章目标</span>
          <small>{{ targetRange }}</small>
        </div>
        <p class="context-lead">{{ context.chapter_goal || '策划中心尚未设置本章目标。' }}</p>
        <div class="context-card">
          <strong>剧情摘要</strong>
          <p>{{ context.synopsis || '暂无章节摘要，可先完成正文再交由审校阶段补充。' }}</p>
        </div>
        <div class="context-card">
          <strong>当前正文</strong>
          <p>{{ document?.plain_text.length || 0 }} 字 · 修订 {{ document?.revision || 0 }}</p>
        </div>
      </section>

      <section v-else-if="activeTab === 'ai'" class="inspector-section">
        <div class="section-heading">
          <span>AI 建议</span>
          <small>采纳前不会修改正文</small>
        </div>
        <div v-if="aiSuggestion" class="suggestion-card">
          <div>
            <small>原文</small>
            <p>{{ aiSuggestion.selection.text || '光标位置' }}</p>
          </div>
          <div class="suggested">
            <small>{{ aiSuggestion.label }}建议</small>
            <p>{{ aiSuggestion.replacement }}</p>
          </div>
          <div class="suggestion-actions">
            <el-button @click="emit('cancelAi')">放弃</el-button>
            <el-button type="primary" @click="emit('acceptAi')">采纳建议</el-button>
          </div>
        </div>
        <div v-else-if="aiIntent" class="intent-card">
          <el-tag type="warning" effect="plain">{{ aiIntent.label }}</el-tag>
          <p>{{ aiIntent.instruction }}</p>
          <blockquote v-if="aiIntent.selection.text">{{ aiIntent.selection.text }}</blockquote>
          <p class="intent-note">确认后才会调用当前配置的文字模型，并先返回可审阅建议。</p>
          <div class="suggestion-actions">
            <el-button @click="emit('cancelAi')">取消</el-button>
            <el-button type="primary" :loading="aiLoading" @click="emit('confirmAi')">
              生成建议
            </el-button>
          </div>
        </div>
        <el-empty v-else description="选中正文后可改写、润色、精简或扩写" :image-size="70" />
      </section>

      <section v-else-if="activeTab === 'review'" class="inspector-section">
        <div class="section-heading"><span>审校摘要</span><small>只读</small></div>
        <div class="review-row">
          <span>流水线门禁</span>
          <el-tag size="small" effect="plain">{{ context.gate_status || '尚未审校' }}</el-tag>
        </div>
        <div class="review-row">
          <span>风险等级</span>
          <el-tag size="small" type="warning" effect="plain">
            {{ context.risk_level || '暂无风险' }}
          </el-tag>
        </div>
        <p class="muted">完整质量报告将在 Phase 5 审校中心集中处理，正文中心仅展示当前章结论。</p>
        <div v-if="qualityCandidate?.available" class="candidate-card">
          <div class="section-heading">
            <span>返工候选稿</span>
            <el-tag size="small" effect="plain" :type="qualityCandidate.metadata?.accepted ? 'success' : 'warning'">
              {{ qualityCandidateStatus }}
            </el-tag>
          </div>
          <p class="muted">{{ qualityCandidate.metadata?.adopted ? '候选稿已写入版本历史。' : '候选稿与正文隔离保存，尚未覆盖正文。' }}</p>
          <el-button
            v-if="qualityCandidateCanAdopt"
            type="primary"
            size="small"
            @click="emit('acceptQualityCandidate')"
          >
            采纳为新修订
          </el-button>
          <small v-if="qualityCandidateCanAdopt" class="candidate-note">采纳前会再次校验当前正文版本。</small>
          <div v-if="qualityCandidate.diff?.stats" class="candidate-stats">
            <span>改动 {{ qualityCandidate.diff.stats.changed_blocks }} 处</span>
            <span>+{{ qualityCandidate.diff.stats.added_lines }} / -{{ qualityCandidate.diff.stats.removed_lines }} 行</span>
          </div>
          <div v-if="qualityCandidate.diff?.segments?.length" class="diff-view" aria-label="候选稿差异">
            <span
              v-for="(segment, index) in qualityCandidate.diff.segments"
              :key="`${segment.op}-${index}`"
              :class="`diff-${segment.op}`"
            >{{ segment.text }}</span>
          </div>
          <pre>{{ qualityCandidate.preview }}<span v-if="qualityCandidate.preview_truncated">…</span></pre>
          <small v-if="qualityCandidate.metadata?.reasons?.length" class="candidate-reasons">
            {{ qualityCandidate.metadata.reasons.join('、') }}
          </small>
        </div>
      </section>

      <section v-else-if="activeTab === 'history'" class="inspector-section history-section">
        <div class="section-heading"><span>修订历史</span><small>{{ history.length }} 个节点</small></div>
        <button
          v-for="revision in history"
          :key="revision.revision_id"
          type="button"
          class="history-row"
          @click="emit('previewRevision', revision)"
        >
          <span class="history-dot" />
          <span>
            <strong>修订 {{ revision.revision }}</strong>
            <small>{{ REVISION_SOURCE_LABELS[revision.source] || revision.source }}</small>
          </span>
          <time>{{ revision.created_at }}</time>
        </button>
        <el-empty v-if="!history.length" description="尚无历史节点" :image-size="64" />
      </section>

      <section v-else class="inspector-section">
        <div class="section-heading"><span>阅读与排版</span><small>仅影响本机</small></div>
        <label>
          <span>字号 {{ fontSize }}px</span>
          <el-slider
            :model-value="fontSize"
            :min="15"
            :max="24"
            @update:model-value="emit('updateFontSize', Number($event))"
          />
        </label>
        <label>
          <span>行高 {{ lineHeight.toFixed(1) }}</span>
          <el-slider
            :model-value="lineHeight"
            :min="1.5"
            :max="2.6"
            :step="0.1"
            @update:model-value="emit('updateLineHeight', Number($event))"
          />
        </label>
        <p class="muted">标题、段落和正文内容保存在文档中；字号与行高属于本机阅读偏好。</p>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.manuscript-inspector {
  height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface);
}
.inspector-tabs {
  min-height: 48px;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border-bottom: 1px solid var(--color-border);
}
.inspector-tabs button {
  display: grid;
  place-items: center;
  gap: 3px;
  padding: 7px 3px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  cursor: pointer;
}
.inspector-tabs button :deep(svg),
.inspector-tabs button > svg {
  width: 16px;
  height: 16px;
}
.inspector-tabs button.active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 700;
}
.inspector-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.inspector-section {
  display: grid;
  gap: 14px;
  padding: 18px 15px;
}
.section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.section-heading span {
  color: var(--color-text-strong);
  font-size: 13.5px;
  font-weight: 800;
}
.section-heading small,
.history-row small {
  color: var(--color-text-muted);
  font-size: 12px;
}
.context-lead {
  margin: 0;
  padding: 12px;
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-text-strong);
  font-size: 13px;
  line-height: 1.7;
}
.context-card,
.intent-card,
.suggestion-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface-muted);
}
.context-card strong { font-size: 13px; }
.context-card p,
.intent-card p,
.suggestion-card p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12.5px;
  line-height: 1.65;
}
.intent-card blockquote {
  max-height: 130px;
  overflow: auto;
  margin: 0;
  padding: 8px;
  border-left: 2px solid var(--color-border);
  color: var(--color-text);
  font-size: 12px;
}
.intent-note { color: var(--color-warning) !important; }
.suggested {
  padding-top: 8px;
  border-top: 1px dashed var(--color-border);
}
.suggested p { color: var(--color-text-strong); }
.suggestion-actions { display: flex; justify-content: flex-end; gap: 7px; }
.review-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-subtle);
  font-size: 12.5px;
}
.muted { margin: 0; color: var(--color-text-muted); font-size: 12px; line-height: 1.6; }
.candidate-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-warning-soft, var(--color-border));
  border-radius: 10px;
  background: var(--color-warning-surface, var(--color-bg-surface-muted));
}
.candidate-card pre {
  max-height: 180px;
  overflow: auto;
  margin: 0;
  padding: 9px;
  border-radius: 7px;
  background: var(--color-bg-surface);
  color: var(--color-text);
  white-space: pre-wrap;
  font: inherit;
  font-size: 12px;
  line-height: 1.65;
}
.candidate-stats { display: flex; gap: 10px; color: var(--color-text-muted); font-size: 12px; }
.diff-view {
  max-height: 170px;
  overflow: auto;
  padding: 8px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 7px;
  background: var(--color-bg-surface);
  white-space: pre-wrap;
  font-size: 12.5px;
  line-height: 1.65;
}
.diff-delete { color: var(--color-danger); background: color-mix(in srgb, var(--color-danger) 12%, transparent); text-decoration: line-through; }
.diff-insert { color: var(--color-success); background: color-mix(in srgb, var(--color-success) 12%, transparent); }
.candidate-note { color: var(--color-text-muted); font-size: 12px; }
.candidate-reasons { color: var(--color-warning); font-size: 12px; }
.history-section { gap: 6px; }
.history-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 10px 7px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}
.history-row:hover { background: var(--color-bg-hover); }
.history-row > span:nth-child(2) { display: grid; gap: 3px; }
.history-row strong { font-size: 13px; font-weight: 700; }
.history-row time { color: var(--color-text-subtle); font-size: 11.5px; }
.history-dot {
  width: 7px;
  height: 7px;
  border: 2px solid var(--color-primary);
  border-radius: 50%;
}
.inspector-section label { display: grid; gap: 8px; color: var(--color-text); font-size: 12.5px; }
</style>
