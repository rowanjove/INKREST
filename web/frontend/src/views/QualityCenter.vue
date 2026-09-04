<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import PageShell from '../shared/ui/PageShell.vue'
import ErrorState from '../shared/ui/ErrorState.vue'
import { useProjectStore } from '../stores/project'
import {
  adoptCandidateSetCandidate,
  createQualityBaseline,
  getQualityCalibration,
  getQualityMetrics,
  getQualityReview,
  getVoiceLab,
  recordCalibrationFeedback,
  recordVoiceFeedback,
  rollbackCandidateSet,
  runQualityCalibration,
  restoreProseProfile,
  setVoiceLabFrozen,
  getLongformReadiness,
} from '../api'
import { l0BlockBanner, type CalibrationReport, type QualityMetrics, type QualityReview, type VoiceLabState } from '../entities/quality'

const route = useRoute()
const projectStore = useProjectStore()
const loading = ref(false)
const loadError = ref('')
const calibration = ref<CalibrationReport | null>(null)
const voiceLab = ref<VoiceLabState | null>(null)
const metrics = ref<QualityMetrics | null>(null)
const review = ref<QualityReview | null>(null)
const selectedChapter = ref('')
const longformReadiness = ref<Record<string, any> | null>(null)
const loadGeneration = ref(0)

const chapterRows = computed(() => metrics.value?.rows || [])
const selectedRow = computed(() => chapterRows.value.find((row) => row.chapter_id === selectedChapter.value))
const l0Banner = computed(() => l0BlockBanner(review.value))

function chapterFromQuery(): string {
  return typeof route.query.chapter === 'string' ? route.query.chapter : ''
}
const calibrationLabel = computed(() => {
  if (!calibration.value || calibration.value.status !== 'calibrated') return '未校准'
  return `已校准 · ${calibration.value.sample_count} 个样本`
})
const passRateLabel = computed(() => {
  const rate = metrics.value?.aggregate.quality_pass_rate
  return rate == null ? '—' : `${Math.round(rate * 100)}%`
})

async function loadMetrics(generation = loadGeneration.value) {
  const { data } = await getQualityMetrics()
  if (generation !== loadGeneration.value) return
  metrics.value = data
  const queryChapter = chapterFromQuery()
  const queryExists = Boolean(
    queryChapter && data.rows.some((row) => row.chapter_id === queryChapter),
  )
  if (queryExists && queryChapter) {
    selectedChapter.value = queryChapter
  } else if (!selectedChapter.value && data.rows.length) {
    selectedChapter.value = data.rows[0].chapter_id
  }
}

async function loadAll() {
  const generation = ++loadGeneration.value
  loading.value = true
  loadError.value = ''
  try {
    const [calibrationResult, voiceResult, readinessResult] = await Promise.all([getQualityCalibration(), getVoiceLab(), getLongformReadiness()])
    if (generation !== loadGeneration.value) return
    calibration.value = calibrationResult.data
    voiceLab.value = voiceResult.data
    longformReadiness.value = readinessResult.data?.detail || null
    await loadMetrics(generation)
    if (generation !== loadGeneration.value) return
    if (selectedChapter.value) await loadReview(selectedChapter.value)
  } catch (error: any) {
    if (generation !== loadGeneration.value) return
    loadError.value = error?.message || String(error)
    ElMessage.error(`质量中心加载失败：${loadError.value}`)
  } finally {
    if (generation === loadGeneration.value) loading.value = false
  }
}

async function loadReview(chapterId: string) {
  selectedChapter.value = chapterId
  try {
    const { data } = await getQualityReview(chapterId)
    if (chapterId !== selectedChapter.value) return
    review.value = data
  } catch (error: any) {
    if (chapterId !== selectedChapter.value) return
    review.value = null
    ElMessage.error(`章节证据加载失败：${error?.message || error}`)
  }
}

async function toggleFreeze() {
  if (!voiceLab.value) return
  try {
    const { data } = await setVoiceLabFrozen(!voiceLab.value.frozen, !voiceLab.value.frozen ? '质量中心人工冻结' : '')
    voiceLab.value = data.voice_lab
    ElMessage.success(data.voice_lab.frozen ? '声线档案已冻结' : '声线档案已恢复可更新')
  } catch (error: any) {
    ElMessage.error(error?.message || '声线状态更新失败')
  }
}

async function flagVoiceFalsePositive() {
  try {
    const { data } = await recordVoiceFeedback({ kind: 'false_positive', chapter_id: selectedChapter.value, note: '人工标记为有意偏离' })
    voiceLab.value = data.voice_lab
    ElMessage.success('已记录声线误报反馈')
  } catch (error: any) {
    ElMessage.error(error?.message || '反馈记录失败')
  }
}

async function flagCalibrationFeedback() {
  try {
    const { data } = await recordCalibrationFeedback({ kind: 'false_positive', chapter_id: selectedChapter.value, note: '人工标记为误报' })
    calibration.value = data.calibration
    ElMessage.success('已记录校准反馈')
  } catch (error: any) {
    ElMessage.error(error?.message || '反馈记录失败')
  }
}

async function rerunCalibration() {
  try {
    calibration.value = (await runQualityCalibration()).data
    ElMessage.success('校准已重新运行')
  } catch (error: any) {
    ElMessage.error(error?.message || '校准运行失败')
  }
}

async function saveBaseline() {
  try {
    metrics.value = (await createQualityBaseline()).data
    ElMessage.success('本地基线已保存')
  } catch (error: any) {
    ElMessage.error(error?.message || '基线保存失败')
  }
}

async function restoreVoiceVersion(revision: number) {
  try {
    await ElMessageBox.confirm(
      `恢复声线档案 r${revision}？这会创建一个新的活动修订。`,
      '恢复声线档案',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await restoreProseProfile(revision)
    voiceLab.value = (await getVoiceLab()).data
    ElMessage.success(`已恢复声线档案 r${revision}`)
  } catch (error: any) {
    ElMessage.error(error?.message || '声线档案恢复失败')
  }
}

async function adoptCandidate(candidate: Record<string, any>) {
  const chapterId = selectedChapter.value
  const setId = String(review.value?.candidate_set?.candidate_set_id || '')
  const revision = Number(review.value?.document?.revision || 0)
  if (!chapterId || !setId || !revision) {
    ElMessage.warning('当前章节缺少可校验的 revision 或候选集')
    return
  }
  try {
    try {
      await ElMessageBox.confirm(
        '采纳后会创建新的正文 revision，原正文仍可从修订历史回退。继续？',
        '采纳候选',
        { type: 'warning', confirmButtonText: '采纳', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
    await adoptCandidateSetCandidate(chapterId, String(candidate.candidate_id), revision, setId)
    ElMessage.success('候选已采纳为新正文修订')
    await loadAll()
  } catch (error: any) {
    ElMessage.error(error?.message || '候选采纳失败，请刷新后重试')
  }
}

async function rollbackCandidate(snapshot: Record<string, any>) {
  const chapterId = selectedChapter.value
  const setId = String(review.value?.candidate_set?.candidate_set_id || '')
  const timelineId = String(snapshot.timeline_id || '')
  if (!chapterId || !setId || !timelineId) return
  try {
    try {
      await ElMessageBox.confirm(
        '只回滚候选集快照，不会改写正文。继续？',
        '回滚候选集',
        { type: 'info', confirmButtonText: '回滚', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
    await rollbackCandidateSet(chapterId, timelineId, setId)
    ElMessage.success('候选集已回滚，正文未变更')
    await loadReview(chapterId)
  } catch (error: any) {
    ElMessage.error(error?.message || '候选回滚失败，请刷新后重试')
  }
}

watch(
  () => route.query.chapter,
  (value) => {
    const chapterId = typeof value === 'string' ? value : ''
    if (!chapterId || chapterId === selectedChapter.value) return
    if (!chapterRows.value.some((row) => row.chapter_id === chapterId)) return
    void loadReview(chapterId)
  },
)

watch(
  () => projectStore.currentProject?.id,
  () => {
    loadGeneration.value += 1
    selectedChapter.value = ''
    calibration.value = null
    voiceLab.value = null
    metrics.value = null
    review.value = null
    longformReadiness.value = null
    void loadAll()
  },
)

onMounted(loadAll)
</script>

<template>
  <PageShell
    title="质量中心"
    description="把声线、审校证据、候选反馈和基线指标放在同一条可回溯链路上。"
    eyebrow="文本质量与证据链"
  >
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
    </template>

    <ErrorState
      v-if="loadError && !metrics && !calibration"
      title="质量中心加载失败"
      :description="loadError"
      action-label="重试"
      @action="loadAll"
    />

    <div v-else class="quality-center" v-loading="loading">

    <section class="summary-grid">
      <article class="summary-card">
        <span>校准状态</span>
        <strong :class="{ warning: calibrationLabel === '未校准' }">{{ calibrationLabel }}</strong>
        <small>{{ calibration?.mutation_count || 0 }} 个 mutation cases · 命中率 {{ Math.round((calibration?.mutation_match_rate || 0) * 100) }}%</small>
      </article>
      <article class="summary-card">
        <span>章节基线</span>
        <strong :class="{ warning: metrics?.status !== 'calibrated' }">{{ metrics?.sample_count || 0 }} / {{ metrics?.minimum_samples || 20 }}</strong>
        <small>质量通过率 {{ passRateLabel }} · {{ metrics?.aggregate.quality_report_count || 0 }} 份报告</small>
      </article>
      <article class="summary-card">
        <span>声线档案</span>
        <strong>{{ voiceLab?.frozen ? '已冻结' : '可更新' }}</strong>
        <small>{{ voiceLab?.profile?.sample_count || 0 }} 个样本 · {{ voiceLab?.feedback_count || 0 }} 条反馈</small>
      </article>
      <article class="summary-card">
        <span>候选偏好</span>
        <strong>{{ metrics?.aggregate.candidate_feedback_count || 0 }} 条</strong>
        <small>盲选 {{ metrics?.aggregate.pairwise_count || 0 }} 次 · 返工 {{ metrics?.aggregate.rewrite_rounds || 0 }} 轮</small>
      </article>
    </section>

    <section v-if="longformReadiness" class="panel readiness-panel">
      <div class="panel-head"><div><h2>长篇能力与降级</h2><p>{{ longformReadiness.scale }} · 目标 {{ longformReadiness.target_chapters || 0 }} 章</p></div><el-tag :type="(longformReadiness.retrieval?.degraded || []).length ? 'warning' : 'success'">{{ (longformReadiness.retrieval?.degraded || []).length ? '有降级' : '可用' }}</el-tag></div>
      <div class="readiness-grid">
        <div><span>FTS</span><strong>{{ longformReadiness.retrieval?.fts?.status || '—' }}</strong></div>
        <div><span>Embedding / Chroma</span><strong>{{ longformReadiness.retrieval?.embedding?.status || '—' }}</strong></div>
        <div><span>Reranker</span><strong>{{ longformReadiness.retrieval?.reranker?.status || '—' }}</strong></div>
        <div><span>required fact coverage</span><strong>{{ longformReadiness.retrieval?.required_fact_coverage?.value == null ? '未知' : longformReadiness.retrieval.required_fact_coverage.value }}</strong></div>
        <div><span>弧合同</span><strong>{{ longformReadiness.arc_contract?.status || '—' }}</strong></div>
        <div><span>能力徽标</span><strong>{{ longformReadiness.badges?.real_run_verified ? '真实长跑' : longformReadiness.badges?.stress_verified ? '压力验证' : '设计支持' }}</strong></div>
        <div><span>长跑 / 导出 / 备份任务</span><strong>{{ longformReadiness.tasks?.active || 0 }} 个进行中</strong></div>
      </div>
      <p v-if="longformReadiness.retrieval?.degraded?.length" class="muted">降级：{{ longformReadiness.retrieval.degraded.join('、') }}</p>
    </section>

    <section class="workspace-grid">
      <article class="panel voice-panel">
        <div class="panel-head">
          <div><h2>声线实验室</h2><p>样本证据与章节偏离趋势</p></div>
          <el-button size="small" :type="voiceLab?.frozen ? 'success' : 'warning'" @click="toggleFreeze">
            {{ voiceLab?.frozen ? '解除冻结' : '冻结档案' }}
          </el-button>
        </div>
        <el-alert v-if="voiceLab?.status !== 'calibrated'" title="文风档案尚未校准，偏离趋势只做诊断" type="info" :closable="false" />
        <div class="evidence-list">
          <div v-for="evidence in voiceLab?.evidence || []" :key="String(evidence.id)" class="evidence-row">
            <span class="evidence-kind">{{ evidence.kind || 'sample' }}</span>
            <div><strong>{{ evidence.path || evidence.id }}</strong><p>{{ evidence.preview || `sha256 ${evidence.sha256 || '—'}` }}</p></div>
          </div>
          <el-empty v-if="!voiceLab?.evidence?.length" description="暂无显式样本证据" :image-size="56" />
        </div>
        <div v-if="voiceLab?.versions?.length" class="version-list">
          <div v-for="version in voiceLab.versions.slice(0, 8)" :key="String(version.revision)" class="version-row">
            <span>r{{ version.revision }} · {{ version.sample_count || 0 }} 样本</span>
            <el-button v-if="!version.is_active" text size="small" @click="restoreVoiceVersion(Number(version.revision))">恢复</el-button>
            <el-tag v-else size="small" type="success">活动</el-tag>
          </div>
        </div>
        <el-button text type="warning" @click="flagVoiceFalsePositive">记录当前章节为声线误报</el-button>
      </article>

      <article class="panel calibration-panel">
        <div class="panel-head"><div><h2>校准与 mutation</h2><p>样本不足时保持未校准</p></div><div class="panel-actions"><el-button size="small" @click="rerunCalibration">运行校准</el-button><el-button size="small" @click="saveBaseline">保存基线</el-button><el-button text type="warning" @click="flagCalibrationFeedback">标记误报</el-button></div></div>
        <div class="calibration-lines">
          <div><span>Golden 样本</span><strong>{{ calibration?.golden_count || 0 }}</strong></div>
          <div><span>Mutation 命中率</span><strong>{{ Math.round((calibration?.mutation_match_rate || 0) * 100) }}%</strong></div>
          <div><span>错误</span><strong>{{ calibration?.errors?.length || 0 }}</strong></div>
        </div>
        <div v-if="calibration?.layer_summary" class="layer-summary">
          <div v-for="(layer, name) in calibration.layer_summary" :key="String(name)"><span>{{ name }}</span><small>通过 {{ layer.pass || 0 }} · 复核 {{ layer.review || 0 }} · 错误 {{ layer.error || 0 }}</small></div>
        </div>
        <p class="muted">校准只验证规则与人工偏好，不以 AI 检测器通过率作为 KPI。</p>
      </article>
    </section>

    <section class="panel review-panel">
      <div class="panel-head">
        <div><h2>审校中心</h2><p>L0 / L1 / L2 证据、候选与回溯状态</p></div>
        <el-select v-model="selectedChapter" placeholder="选择章节" size="small" @change="loadReview">
          <el-option v-for="row in chapterRows" :key="row.chapter_id" :label="`第 ${row.chapter_id} 章`" :value="row.chapter_id" />
        </el-select>
      </div>
      <el-alert
        v-if="l0Banner"
        class="l0-block-banner"
        type="error"
        show-icon
        :closable="false"
        :title="l0Banner.title"
      >
        <p>拦截项：{{ l0Banner.items.join('、') }}</p>
        <p v-if="l0Banner.score != null">章节分 {{ l0Banner.score }} / 10 · 自动化生产仅在 L0 硬门未过时阻断</p>
      </el-alert>
      <div v-if="selectedRow" class="level-strip">
        <div><span>L0 事实/格式</span><strong>{{ review?.levels?.l0?.status || '—' }} · {{ review?.levels?.l0?.finding_count || 0 }} 证据</strong></div>
        <div><span>L1 表达/声线</span><strong>{{ review?.levels?.l1?.status || '—' }} · {{ review?.levels?.l1?.finding_count || 0 }} 证据</strong></div>
        <div><span>L2 人工偏好</span><strong>{{ review?.levels?.l2?.status || '—' }} · {{ review?.levels?.l2?.finding_count || 0 }} 证据</strong></div>
      </div>
      <el-alert v-if="review?.candidate_policy?.recommend" class="candidate-policy-alert" title="建议人工评估多候选" type="warning" :closable="false">
        {{ (review?.candidate_policy?.reason_codes || []).join('、') }}；当前为 {{ review?.candidate_policy?.mode || 'manual_only' }}，不会自动生成。
      </el-alert>
      <div v-if="review?.ranked_candidates?.length" class="candidate-table">
        <div v-for="candidate in review.ranked_candidates" :key="String(candidate.candidate_id)" class="candidate-row">
          <div><strong>{{ candidate.candidate_id }}</strong><span>{{ candidate.status || 'pending' }} · L0 {{ candidate.l0_validation?.pass === false ? '未通过' : '通过' }}</span></div>
          <p>{{ candidate.text }}</p>
          <div class="candidate-actions"><small>反馈分 {{ candidate.feedback_score }} · {{ candidate.content_lock_id || '无锁摘要' }}</small><el-button v-if="candidate.l0_validation?.pass !== false" size="small" type="primary" @click="adoptCandidate(candidate)">采纳为新修订</el-button></div>
        </div>
      </div>
      <el-empty v-else description="当前章节暂无候选集，单候选流程保持不变" :image-size="64" />
      <div v-if="review?.evidence?.length" class="evidence-chain">
        <div class="subhead">证据链</div>
        <div v-for="item in review.evidence.slice(0, 12)" :key="`${item.kind}-${item.index}-${item.summary}`" class="evidence-chain-row"><span>{{ item.layer }} · {{ item.kind }}</span><p>{{ item.summary }}<small v-if="item.source"> · {{ item.source }}</small></p></div>
      </div>
      <div v-if="review?.timeline?.length" class="timeline-list">
        <div class="timeline-note">候选时间线 {{ review.timeline.length }} 个快照 · 反馈 {{ review.feedback?.length || 0 }} 条</div>
        <div v-for="item in review.timeline.slice(0, 8)" :key="String(item.timeline_id)" class="timeline-row"><span>{{ item.event }} · {{ item.recorded_at }}</span><el-button text size="small" @click="rollbackCandidate(item)">回滚到此快照</el-button></div>
      </div>
    </section>

    <section class="panel metrics-panel">
      <div class="panel-head"><div><h2>指标面板</h2><p>仅作本地诊断与基线比较</p></div></div>
      <div class="metric-grid">
        <div><span>事实冲突</span><strong>{{ metrics?.aggregate.fact_conflict_count || 0 }}</strong></div>
        <div><span>知识越权</span><strong>{{ metrics?.aggregate.knowledge_boundary_count || 0 }}</strong></div>
        <div><span>表达复读</span><strong>{{ metrics?.aggregate.expression_repetition_count || 0 }}</strong></div>
        <div><span>审校 error</span><strong>{{ metrics?.aggregate.quality_error_count || 0 }}</strong></div>
        <div><span>接受率</span><strong>{{ metrics?.aggregate.candidate_accept_rate == null ? '—' : `${Math.round(metrics.aggregate.candidate_accept_rate * 100)}%` }}</strong></div>
        <div><span>手改比例</span><strong>{{ metrics?.aggregate.candidate_edit_ratio == null ? '—' : metrics.aggregate.candidate_edit_ratio }}</strong></div>
        <div><span>误报率</span><strong>{{ metrics?.aggregate.false_positive_rate == null ? '—' : `${Math.round(metrics.aggregate.false_positive_rate * 100)}%` }}</strong></div>
        <div><span>候选成本</span><strong>{{ metrics?.aggregate.candidate_cost_units || 0 }} units</strong></div>
      </div>
    </section>
    </div>
  </PageShell>
</template>

<style scoped>
.quality-center { display: grid; gap: 16px; min-width: 0; }
.panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.panel-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.panel-head p { margin: 0; color: var(--color-text-muted); font-size: 13.5px; line-height: 1.6; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.summary-card, .panel { border: 1px solid var(--color-border); border-radius: 14px; background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.summary-card { display: grid; gap: 7px; padding: 18px; }
.summary-card span, .metric-grid span, .level-strip span { color: var(--color-text-muted); font-size: 12.5px; }
.summary-card strong { color: var(--color-text-strong); font-size: 22px; }
.summary-card strong.warning { color: var(--color-warning); }
.summary-card small { color: var(--color-text-muted); font-size: 12px; line-height: 1.5; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(300px, .85fr); gap: 16px; margin-bottom: 16px; }
.readiness-panel { margin-bottom: 16px; }
.readiness-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
.readiness-grid > div { display: grid; gap: 6px; padding: 10px 12px; border-radius: 9px; background: var(--color-bg-surface-muted); }
.readiness-grid span { color: var(--color-text-muted); font-size: 12px; }
.readiness-grid strong { color: var(--color-text-strong); font-size: 13.5px; }
.panel { padding: 20px; }
.panel h2 { margin: 0 0 3px; color: var(--color-text-strong); font-size: 16px; font-weight: 750; }
.evidence-list { display: grid; gap: 8px; margin: 16px 0; }
.evidence-row { display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: 10px; padding: 12px; border-radius: 10px; background: var(--color-bg-surface-muted); }
.evidence-kind { color: var(--color-primary); font-size: 12px; font-weight: 750; }
.evidence-row strong { color: var(--color-text-strong); font-size: 13px; }
.evidence-row p, .candidate-row p { margin: 4px 0 0; color: var(--color-text-muted); font-size: 12.5px; line-height: 1.6; }
.version-list, .layer-summary, .timeline-list, .evidence-chain { display: grid; gap: 8px; margin: 12px 0; }
.version-row, .timeline-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; color: var(--color-text-muted); font-size: 12px; }
.layer-summary > div, .evidence-chain-row { display: flex; justify-content: space-between; gap: 10px; padding: 10px 12px; border-radius: 8px; background: var(--color-bg-surface-muted); color: var(--color-text-muted); font-size: 12px; }
.layer-summary small { color: var(--color-text-muted); font-size: 12px; }
.evidence-chain-row { display: grid; grid-template-columns: 140px minmax(0, 1fr); }
.evidence-chain-row p { margin: 0; line-height: 1.5; font-size: 12.5px; }
.evidence-chain-row small { color: var(--color-text-muted); font-size: 11.5px; }
.subhead { color: var(--color-text-strong); font-size: 13px; font-weight: 700; }
.calibration-lines, .metric-grid, .level-strip { display: grid; gap: 8px; }
.calibration-lines { margin: 20px 0; }
.calibration-lines > div, .level-strip > div, .metric-grid > div { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border-radius: 9px; background: var(--color-bg-surface-muted); }
.calibration-lines strong, .level-strip strong, .metric-grid strong { color: var(--color-text-strong); font-size: 13.5px; }
.muted { color: var(--color-text-muted); font-size: 12.5px; line-height: 1.6; }
.review-panel, .metrics-panel { margin-bottom: 16px; }
.level-strip { grid-template-columns: repeat(3, 1fr); margin: 16px 0; }
.level-strip > div { display: grid; gap: 5px; }
.candidate-table { display: grid; gap: 10px; }
.candidate-policy-alert, .l0-block-banner { margin: 12px 0; }
.l0-block-banner p { margin: 4px 0 0; line-height: 1.6; }
.candidate-row { padding: 14px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-surface-muted); }
.candidate-row > div { display: flex; justify-content: space-between; gap: 12px; }
.candidate-row > div span { color: var(--color-text-muted); font-size: 12px; }
.candidate-actions { align-items: center; }
.candidate-row small, .timeline-note { color: var(--color-text-muted); font-size: 12px; }
.timeline-note { margin-top: 12px; }
.metric-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); margin-top: 16px; }
.metric-grid > div { display: grid; gap: 6px; }
@media (max-width: 1000px) { .summary-grid { grid-template-columns: repeat(2, 1fr); } .workspace-grid { grid-template-columns: 1fr; } .metric-grid, .readiness-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 620px) { .summary-grid, .level-strip, .metric-grid, .readiness-grid { grid-template-columns: 1fr; } }
</style>
