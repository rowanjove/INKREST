<script setup lang="ts">
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { DUAL_AUDIT_HINT } from '../constants/repairWorkflow'
import {
  longFormVectorWarn,
  LONG_FORM_VECTOR_WARN_TEXT,
} from '../utils/projectReadiness'
import { computed } from 'vue'

const {
  dialogVisible,
  running,
  form,
  ctx,
  currentProject,
  maxAvailableChapters,
  isCircuitPaused,
  dialogTitle,
  tokenEstimate,
  submit,
  cancelBatchRun,
  busy,
  busyPhaseLabel,
  goMonitorAlerts,
  goChapterRepair,
  workScale,
} = useNovelBatchRun()

const showVectorAlert = computed(() =>
  longFormVectorWarn({
    workScale: workScale.value,
    vectorEnabled: ctx.value.vectorEnabled,
    semanticSearchEffective: ctx.value.semanticSearchEffective,
  }),
)
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="500px"
    destroy-on-close
    append-to-body
  >
    <div class="batch-run-body">
      <p class="batch-run-lead">
        按已有卷级队列续跑，不会重新生成全书大纲。队列不足时会按「规划窗口」自动补章目标，再执行单章流水线。
      </p>
      <el-alert
        v-if="showVectorAlert"
        type="warning"
        :closable="false"
        show-icon
        title="长篇向量建议"
      >
        {{ LONG_FORM_VECTOR_WARN_TEXT }}
      </el-alert>
      <el-alert
        v-if="ctx.externalPendingCount > 0 && ctx.blockContinueUntilExternal"
        type="warning"
        :closable="false"
        show-icon
        title="有待外审章节"
        class="external-alert"
      >
        {{ ctx.externalPendingCount }} 章待外审通过后再续跑。可在设置 → 流水线高级关闭「外审未过禁止续跑」，或到章节维护标记通过。
      </el-alert>
      <el-alert
        v-else-if="ctx.externalPendingCount > 0"
        type="info"
        :closable="false"
        show-icon
        title="有待外审章节"
        class="external-alert"
      >
        {{ ctx.externalPendingCount }} 章待平台试审；续跑不会自动跳过外审队列。
      </el-alert>
      <el-alert
        v-if="isCircuitPaused"
        type="warning"
        :closable="false"
        show-icon
        title="全书因质量熔断已暂停"
        class="circuit-alert"
      >
        <p>建议先处理第 {{ ctx.lastChapterId || '—' }} 章（改稿 → 重跑门禁），再续写。</p>
        <div class="circuit-actions">
          <el-button size="small" type="warning" @click="goChapterRepair">
            去改稿
          </el-button>
          <el-button size="small" text @click="goMonitorAlerts">
            看待处理列表
          </el-button>
        </div>
      </el-alert>
      <el-checkbox v-model="form.autopilot">
        后台自动续轮（多轮排空 + 补窗，直至达到下方章数上限或熔断暂停）
      </el-checkbox>
      <div class="batch-run-stats">
        <div>
          大纲目标体量：<strong>{{ ctx.outline?.target_chapters || currentProject?.target_chapters || 20 }}</strong> 章
        </div>
        <div>当前已生成：<strong>{{ ctx.chapterCountTotal }}</strong> 章</div>
        <div>
          剩余可生成：<strong class="emph">{{ maxAvailableChapters }}</strong> 章
        </div>
      </div>
      <label class="batch-run-field">
        <span class="field-label">
          {{ form.autopilot ? '自动续跑总章数上限' : '本次生成章数' }}
        </span>
        <el-input-number
          v-model="form.target_chapters"
          :min="1"
          :max="maxAvailableChapters || 1"
          style="width: 150px"
        />
      </label>
      <p v-if="tokenEstimate.chapters > 0" class="token-estimate-hint">
        费用粗估：{{ tokenEstimate.label }} · {{ tokenEstimate.priceLabel }}
        <span class="muted">（{{ tokenEstimate.chapters }} 章 × 约 1.2 万 tokens/章，含规划、写作与审校）</span>
      </p>
      <p v-if="ctx.arcProgress?.last_arc_id" class="arc-hint">
        卷级进度：卷 {{ ctx.arcProgress.last_arc_id }} / 章
        {{ ctx.arcProgress.last_chapter_id || '—' }}
        （{{ ctx.arcProgress.status }}）
      </p>
      <p class="audit-hint">{{ DUAL_AUDIT_HINT }}</p>
    </div>
    <template #footer>
      <p v-if="busy && busyPhaseLabel" class="busy-phase-hint">{{ busyPhaseLabel }}</p>
      <el-button v-if="busy" type="danger" plain @click="cancelBatchRun">取消连写</el-button>
      <el-button v-else @click="dialogVisible = false">关闭</el-button>
      <el-button type="primary" :loading="running" :disabled="running" @click="submit(false)">
        {{ running ? '同步卷队列 / 连写启动中…' : '确认连写' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.batch-run-body {
  display: grid;
  gap: 14px;
  padding: 10px 0;
}

.batch-run-lead {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.circuit-alert p {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.circuit-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.token-estimate-hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.token-estimate-hint .muted {
  opacity: 0.85;
}

.batch-run-stats {
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13.5px;
  color: var(--color-text-muted);
  display: grid;
  gap: 4px;
}

.batch-run-stats .emph {
  color: var(--el-color-primary);
}

.batch-run-field {
  display: grid;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.arc-hint {
  margin: 0;
  font-size: 13px;
  color: #b45309;
}

.audit-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-subtle);
  line-height: 1.45;
}

.busy-phase-hint {
  margin: 0 0 8px;
  width: 100%;
  font-size: 13px;
  color: var(--color-text-muted);
  text-align: left;
}
</style>