<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { Search } from '@element-plus/icons-vue'
import type {
  ProductionActionKind,
  ProductionReviewFilter,
  ProductionReviewItem,
} from '../../entities/production/production'
import {
  filterProductionReviews,
  productionStepLabel,
  qualityBlockedByLabels,
  qualityRecoverySteps,
  resolveReviewActionTargets,
} from '../../entities/production/production'
import StatusBadge from '../../shared/ui/StatusBadge.vue'

const props = defineProps<{
  items: ProductionReviewItem[]
  selectedChapterId: string
}>()

const emit = defineEmits<{
  select: [chapterId: string]
  action: [
    kind: Exclude<ProductionActionKind, 'cancel_task'>,
    chapterIds: string[],
  ]
  openChapter: [chapterId: string]
  openQuality: [chapterId: string]
}>()

const query = ref('')
const filter = ref<ProductionReviewFilter>('error')
const selectedIds = ref<string[]>([])
const scrollElement = ref<HTMLElement | null>(null)
const filtered = computed(() =>
  filterProductionReviews(props.items, filter.value, query.value),
)
const selected = computed(
  () =>
    props.items.find((item) => item.chapter_id === props.selectedChapterId) ||
    props.items[0] ||
    null,
)
const selectedItems = computed(() =>
  props.items.filter((item) => selectedIds.value.includes(item.chapter_id)),
)
const recoverySteps = computed(() =>
  selected.value ? qualityRecoverySteps(selected.value) : [],
)
const blockedLabels = computed(() =>
  selected.value ? qualityBlockedByLabels(selected.value) : [],
)
const virtualizer = useVirtualizer(
  computed(() => ({
    count: filtered.value.length,
    getScrollElement: () => scrollElement.value,
    estimateSize: () => 82,
    overscan: 8,
    getItemKey: (index: number) => filtered.value[index]?.chapter_id ?? index,
  })),
)
const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalHeight = computed(() => virtualizer.value.getTotalSize())

watch(
  () => props.items,
  (items) => {
    const available = new Set(items.map((item) => item.chapter_id))
    selectedIds.value = selectedIds.value.filter((id) => available.has(id))
  },
  { deep: true },
)

function toggleSelected(chapterId: string, checked: boolean) {
  if (checked) {
    selectedIds.value = [...new Set([...selectedIds.value, chapterId])]
  } else {
    selectedIds.value = selectedIds.value.filter((id) => id !== chapterId)
  }
}

function compatibleCount(kind: Exclude<ProductionActionKind, 'cancel_task'>) {
  return resolveReviewActionTargets(kind, selectedItems.value).length
}

function emitBulk(kind: Exclude<ProductionActionKind, 'cancel_task'>) {
  const targets = resolveReviewActionTargets(kind, selectedItems.value)
  if (targets.length) emit('action', kind, targets)
}
</script>

<template>
  <section class="review-workspace">
    <aside class="review-list-pane" aria-label="审校修复队列">
      <header>
        <div><strong>审校与修复</strong><small>{{ filtered.length }} / {{ items.length }}</small></div>
        <el-input v-model="query" :prefix-icon="Search" placeholder="搜索章节或问题" clearable />
        <el-segmented
          v-model="filter"
          :options="[
            { label: '全部', value: 'all' },
            { label: '阻断', value: 'error' },
            { label: '提醒', value: 'warning' },
            { label: '外审', value: 'external' },
          ]"
          aria-label="筛选审校问题"
        />
      </header>

      <div v-if="selectedIds.length" class="bulk-actions" aria-label="批量修复动作">
        <span>已选 {{ selectedIds.length }} 章</span>
        <div>
          <el-button
            size="small"
            :disabled="!compatibleCount('resume_audit')"
            @click="emitBulk('resume_audit')"
          >
            重试审校 {{ compatibleCount('resume_audit') }}
          </el-button>
          <el-button
            size="small"
            :disabled="!compatibleCount('rerun_gate')"
            @click="emitBulk('rerun_gate')"
          >
            重跑门禁 {{ compatibleCount('rerun_gate') }}
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            :disabled="!compatibleCount('rewrite')"
            @click="emitBulk('rewrite')"
          >
            重新生产 {{ compatibleCount('rewrite') }}
          </el-button>
        </div>
      </div>

      <div ref="scrollElement" class="virtual-scroll">
        <div v-if="filtered.length" class="virtual-list" :style="{ height: `${totalHeight}px` }">
          <div
            v-for="row in virtualRows"
            :key="String(row.key)"
            class="review-row"
            :class="{ active: filtered[row.index]?.chapter_id === selected?.chapter_id }"
            :style="{ transform: `translateY(${row.start}px)`, height: `${row.size}px` }"
            role="button"
            tabindex="0"
            @click="emit('select', filtered[row.index]!.chapter_id)"
            @keydown.enter="emit('select', filtered[row.index]!.chapter_id)"
            @keydown.space.prevent="emit('select', filtered[row.index]!.chapter_id)"
          >
            <el-checkbox
              :model-value="selectedIds.includes(filtered[row.index]!.chapter_id)"
              :aria-label="`选择第 ${filtered[row.index]!.chapter_id} 章`"
              @click.stop
              @change="(value: boolean) => toggleSelected(filtered[row.index]!.chapter_id, value)"
            />
            <span class="review-copy">
              <strong>{{ filtered[row.index]!.chapter_title }}</strong>
              <small>{{ filtered[row.index]!.message }}</small>
            </span>
            <span class="review-status">
              <StatusBadge
                :label="filtered[row.index]!.stage_label"
                :tone="filtered[row.index]!.severity === 'error' ? 'danger' : 'warning'"
              />
              <small v-if="filtered[row.index]!.overall_score != null">
                {{ filtered[row.index]!.overall_score }} 分
              </small>
            </span>
          </div>
        </div>
        <el-empty v-else description="没有匹配的审校问题" :image-size="64" />
      </div>
    </aside>

    <article class="review-detail" aria-label="审校问题详情">
      <template v-if="selected">
        <header class="detail-head">
          <div>
            <small>第 {{ selected.chapter_id }} 章</small>
            <h2>{{ selected.chapter_title }}</h2>
            <p>{{ selected.message }}</p>
          </div>
          <div class="score-block">
            <StatusBadge
              :label="selected.stage_label"
              :tone="selected.severity === 'error' ? 'danger' : 'warning'"
              dot
            />
            <strong v-if="selected.chapter_score != null">{{ selected.chapter_score }}<small> / 10</small></strong>
            <strong v-else-if="selected.overall_score != null">{{ selected.overall_score }}<small> / 100</small></strong>
          </div>
        </header>

        <section v-if="recoverySteps.length" class="recovery-section">
          <div class="section-head"><h3>恢复三步</h3></div>
          <p v-if="blockedLabels.length" class="blocked-copy">拦截项：{{ blockedLabels.join('、') }}</p>
          <ol class="recovery-steps">
            <li v-for="step in recoverySteps" :key="step.id">
              <strong>{{ step.label }}</strong>
              <p>{{ step.description }}</p>
            </li>
          </ol>
          <div class="recovery-actions">
            <el-button type="primary" plain @click="emit('openQuality', selected.chapter_id)">
              去质量中心
            </el-button>
            <el-button type="warning" @click="emit('action', 'rerun_gate', [selected.chapter_id])">
              重跑门禁
            </el-button>
          </div>
        </section>

        <section class="issue-section">
          <div class="section-head"><h3>发现的问题</h3><span>{{ selected.issues.length }}</span></div>
          <div v-if="selected.issues.length" class="issue-list">
            <article v-for="issue in selected.issues" :key="issue.code" class="issue-card">
              <header>
                <strong>{{ issue.label }}</strong>
                <span v-if="issue.score != null">{{ issue.score }} 分</span>
              </header>
              <ul v-if="issue.details.length">
                <li v-for="detail in issue.details" :key="detail">{{ detail }}</li>
              </ul>
              <p v-else>该检查已阻断当前章节，请结合正文上下文修订后重新检查。</p>
            </article>
          </div>
          <p v-else class="empty-copy">流水线已记录阻断，但报告中没有更细的检查项。</p>
        </section>

        <section class="completed-section">
          <div class="section-head"><h3>已完成步骤</h3><span>{{ selected.completed_stages.length }}</span></div>
          <div class="stage-list">
            <span v-for="stage in selected.completed_stages" :key="stage">
              {{ productionStepLabel(stage) }}
            </span>
            <span v-if="!selected.completed_stages.length" class="muted">暂无步骤记录</span>
          </div>
        </section>

        <footer class="review-actions">
          <el-button @click="emit('openChapter', selected.chapter_id)">打开正文改稿</el-button>
          <el-button
            v-if="['quality_blocked', 'report_failed'].includes(selected.stage)"
            type="warning"
            @click="emit('action', 'rerun_gate', [selected.chapter_id])"
          >
            重跑门禁
          </el-button>
          <el-button
            v-if="['quality_blocked', 'approval_rejected', 'report_invalid'].includes(selected.stage)"
            type="primary"
            @click="emit('action', 'resume_audit', [selected.chapter_id])"
          >
            重试审校
          </el-button>
          <el-button
            v-if="['quality_blocked', 'approval_rejected', 'report_failed', 'report_invalid', 'batch_retry'].includes(selected.stage)"
            type="danger"
            plain
            @click="emit('action', 'rewrite', [selected.chapter_id])"
          >
            重新生产
          </el-button>
          <el-button
            v-if="selected.stage === 'external_review_pending'"
            type="primary"
            @click="emit('action', 'external_passed', [selected.chapter_id])"
          >
            标记外审通过
          </el-button>
          <el-button
            plain
            @click="emit('action', 'dismiss', [selected.chapter_id])"
          >
            忽略并移出队列
          </el-button>
        </footer>
      </template>
      <el-empty v-else description="当前没有待审校或修复的章节" />
    </article>
  </section>
</template>

<style scoped>
.review-workspace { display: grid; grid-template-columns: minmax(300px, 38%) minmax(0, 1fr); height: 100%; min-height: 0; }
.review-list-pane { display: flex; min-width: 0; min-height: 0; flex-direction: column; border-right: 1px solid var(--color-border); background: var(--color-bg-surface); }
.review-list-pane > header { display: grid; gap: 9px; padding: 13px; border-bottom: 1px solid var(--color-border-subtle); }
.review-list-pane > header > div { display: flex; justify-content: space-between; color: var(--color-text-strong); font-size: 13px; }
.review-list-pane > header small { color: var(--color-text-muted); font-size: 12px; }
.review-list-pane :deep(.el-segmented) { width: 100%; }
.bulk-actions { display: grid; gap: 7px; padding: 9px 12px; border-bottom: 1px solid var(--color-border); background: var(--color-primary-soft); color: var(--color-text-strong); font-size: 12px; }
.bulk-actions > div { display: flex; flex-wrap: wrap; gap: 6px; }
.virtual-scroll { position: relative; flex: 1; min-height: 0; overflow: auto; padding: 7px; }
.virtual-list { position: relative; width: 100%; }
.review-row {
  position: absolute; inset-inline: 0; top: 0; display: grid; width: 100%;
  grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 9px; padding: 9px 10px;
  border: 0; border-left: 3px solid transparent; border-radius: 8px; background: transparent;
  color: var(--color-text); text-align: left; cursor: pointer;
}
.review-row:hover { background: var(--color-bg-hover); }
.review-row.active { border-left-color: var(--color-primary); background: var(--color-primary-soft); }
.review-copy { display: grid; min-width: 0; gap: 4px; }
.review-copy strong { overflow: hidden; color: var(--color-text-strong); font-size: 13.5px; text-overflow: ellipsis; white-space: nowrap; }
.review-copy small { display: -webkit-box; overflow: hidden; color: var(--color-text-muted); font-size: 12px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.review-status { display: grid; justify-items: end; gap: 4px; }
.review-status > small { color: var(--color-text-muted); font-size: 11.5px; }
.review-detail { min-width: 0; min-height: 0; overflow: auto; padding: 20px 22px 28px; background: var(--color-bg-page); }
.detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.detail-head > div:first-child > small { color: var(--color-text-muted); font-size: 12px; }
.detail-head h2 { margin: 3px 0; color: var(--color-text-strong); font-size: 20px; font-weight: 750; }
.detail-head p { margin: 0; color: var(--color-text-muted); font-size: 13px; line-height: 1.6; }
.score-block { display: grid; justify-items: end; gap: 8px; }
.score-block > strong { color: var(--color-text-strong); font-size: 24px; }
.score-block > strong small { color: var(--color-text-muted); font-size: 12px; }
.issue-section, .completed-section, .recovery-section { margin-top: 22px; }
.blocked-copy { margin: 0 0 10px; color: var(--color-danger, #b42318); font-size: 13px; }
.recovery-steps { margin: 0; padding-left: 18px; display: grid; gap: 10px; }
.recovery-steps p { margin: 4px 0 0; color: var(--color-text-muted); font-size: 13px; line-height: 1.6; }
.recovery-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.section-head h3 { margin: 0; color: var(--color-text-strong); font-size: 14px; }
.section-head span { color: var(--color-text-muted); font-size: 12px; }
.issue-list { display: grid; gap: 8px; }
.issue-card { padding: 14px; border: 1px solid var(--color-border); border-radius: 9px; background: var(--color-bg-surface); }
.issue-card header { display: flex; justify-content: space-between; gap: 8px; }
.issue-card strong { color: var(--color-text-strong); font-size: 13.5px; }
.issue-card header span { color: var(--color-danger); font-size: 12px; font-weight: 650; }
.issue-card ul { display: grid; gap: 5px; margin: 9px 0 0; padding-left: 17px; color: var(--color-text); font-size: 12.5px; line-height: 1.55; }
.issue-card p, .empty-copy { margin: 9px 0 0; color: var(--color-text-muted); font-size: 12.5px; line-height: 1.6; }
.stage-list { display: flex; flex-wrap: wrap; gap: 6px; }
.stage-list > span { padding: 5px 9px; border: 1px solid var(--color-border); border-radius: 999px; background: var(--color-bg-surface); color: var(--color-text-muted); font-size: 11.5px; }
.stage-list > .muted { border-style: dashed; }
.review-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--color-border); }
@media (max-width: 900px) { .review-workspace { grid-template-columns: minmax(260px, 42%) minmax(0, 1fr); } .review-detail { padding: 16px; } }
</style>
