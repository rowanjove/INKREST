<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, DocumentChecked, View, MagicStick, TrendCharts } from '@element-plus/icons-vue'
import {
  acceptHwePatch,
  generateHwePatch,
  getHweMemoryDiagnostics,
  getLatestHweEval,
  planHwePatches,
  previewHwePrompt,
  resolveHweIssue,
  runHweEval,
  runHweSemanticReview,
  scanHweText,
} from '../../api/quality'
import type { HWEReport, HWEIssue, HWEPatchCandidate } from '../../entities/quality'

const props = defineProps<{
  initialChapter?: string
  availableChapters?: Array<{ chapter_id: string; title?: string }>
}>()

const router = useRouter()
const scanning = ref(false)
const semanticReviewing = ref(false)
const previewingPrompt = ref(false)
const generatingPatch = ref(false)
const acceptingPatch = ref(false)
const diffDialogVisible = ref(false)
const promptPreviewDialogVisible = ref(false)
const memoryDrawerVisible = ref(false)
const evalDialogVisible = ref(false)
const runningEval = ref(false)
const evalReport = ref<any>(null)
const candidate = ref<HWEPatchCandidate | null>(null)
const promptPreviewData = ref<{ prompt_block: string; char_count: number; budget: number; within_budget: boolean } | null>(null)
const memoryDiagnostics = ref<{
  chapter_id: string
  total_extracted_entries: number
  sliding_windows: Array<{
    expression: string
    kind: string
    window_3_count: number
    window_10_count: number
    whole_book_count: number
    is_saturated: boolean
    evidence_chapters: string[]
  }>
  saturated_count: number
  ending_issues: HWEIssue[]
} | null>(null)
const selectedChapter = ref(props.initialChapter || '')
const report = ref<HWEReport | null>(null)
const selectedFamily = ref<string>('all')

const families = [
  { key: 'all', label: '全部问题' },
  { key: 'staging', label: '表演腔' },
  { key: 'narration', label: '解释腔' },
  { key: 'rhythm', label: '机械节奏' },
  { key: 'imagery', label: '修辞惯性' },
  { key: 'dialogue', label: '对话失真' },
  { key: 'language', label: '套话翻译腔' },
]

const filteredIssues = computed<HWEIssue[]>(() => {
  if (!report.value?.issues) return []
  if (selectedFamily.value === 'all') return report.value.issues
  return report.value.issues.filter((i) => i.hwe.family === selectedFamily.value)
})

async function generatePatchForIssue(issue: HWEIssue) {
  if (!selectedChapter.value) return
  generatingPatch.value = true
  try {
    const planRes = await planHwePatches({ chapter_id: selectedChapter.value })
    const plans = planRes.data
    const matchingPatch =
      plans.find(
        (p) =>
          (p.start <= issue.hwe.start && p.end >= issue.hwe.end) ||
          p.rule_ids.includes(issue.hwe.rule_id),
      ) || plans[0]

    if (!matchingPatch) {
      ElMessage.warning('未能为该问题构建局部修复方案')
      return
    }

    const genRes = await generateHwePatch({ patch: matchingPatch })
    candidate.value = genRes.data
    diffDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成修复候选失败')
  } finally {
    generatingPatch.value = false
  }
}

async function applyCandidatePatch() {
  if (!candidate.value || !selectedChapter.value) return
  acceptingPatch.value = true
  try {
    const res = await acceptHwePatch({
      chapter_id: selectedChapter.value,
      patch_id: candidate.value.patch_id,
      start: candidate.value.start,
      end: candidate.value.end,
      candidate_text: candidate.value.candidate_text,
      rule_ids: candidate.value.rule_ids,
    })
    report.value = res.data
    diffDialogVisible.value = false
    ElMessage.success('已采纳局部修复，并已自动保存为新的正文修订版本！')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '采纳补丁失败')
  } finally {
    acceptingPatch.value = false
  }
}

async function runScan() {
  if (!selectedChapter.value) {
    ElMessage.warning('请先选择要扫描的章节')
    return
  }
  scanning.value = true
  try {
    const res = await scanHweText({ chapter_id: selectedChapter.value, mode: 'assist' })
    report.value = res.data
    ElMessage.success(`活人文风扫描完成，发现 ${report.value.issues.length} 处建议项`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '活人文风扫描失败')
  } finally {
    scanning.value = false
  }
}

async function runSemanticReviewAction() {
  if (!selectedChapter.value) {
    ElMessage.warning('请先选择章节')
    return
  }
  semanticReviewing.value = true
  try {
    const res = await runHweSemanticReview({
      chapter_id: selectedChapter.value,
      template_risk: report.value?.scores?.template_risk || 40,
      user_requested: true,
    })
    const semanticIssues = res.data
    if (semanticIssues.length === 0) {
      ElMessage.success('深度语义审校完成，未发现明显语义层 AI 腔！')
    } else {
      ElMessage.warning(`深度语义审校发现 ${semanticIssues.length} 处潜在作者越位或假深刻问题`)
      if (report.value) {
        const existingIds = new Set(report.value.issues.map((i) => i.hwe.rule_id + i.hwe.start))
        for (const si of semanticIssues) {
          const key = si.hwe.rule_id + si.hwe.start
          if (!existingIds.has(key)) {
            report.value.issues.unshift(si)
            existingIds.add(key)
          }
        }
      }
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '深度语义审校失败')
  } finally {
    semanticReviewing.value = false
  }
}

async function openLongformMemory() {
  if (!selectedChapter.value) {
    ElMessage.warning('请先选择章节')
    return
  }
  try {
    const res = await getHweMemoryDiagnostics(selectedChapter.value)
    memoryDiagnostics.value = res.data
    memoryDrawerVisible.value = true
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '读取长篇记忆诊断失败')
  }
}

async function openPromptPreview() {
  if (!selectedChapter.value) {
    ElMessage.warning('请先选择章节')
    return
  }
  previewingPrompt.value = true
  try {
    const res = await previewHwePrompt({
      chapter_id: selectedChapter.value,
      max_budget: 1200,
    })
    promptPreviewData.value = res.data
    promptPreviewDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成前约束预览失败')
  } finally {
    previewingPrompt.value = false
  }
}

async function openEvalLab() {
  evalDialogVisible.value = true
  try {
    const res = await getLatestHweEval()
    if (res.data) {
      evalReport.value = res.data
    }
  } catch {
    // optional initial load
  }
}

async function triggerEvalLab() {
  runningEval.value = true
  try {
    const res = await runHweEval()
    evalReport.value = res.data
    ElMessage.success('Eval Lab 基准评测执行完成！')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '评测运行失败')
  } finally {
    runningEval.value = false
  }
}

async function handleIssueAction(issue: HWEIssue, action: string) {
  try {
    const issueId = (issue as any).id || `${issue.hwe.rule_id}_${issue.hwe.start}`
    await resolveHweIssue(issueId, {
      action,
      rule_id: issue.hwe.rule_id,
      note:
        action === 'false_positive'
          ? '用户标记为误报'
          : action === 'allow_rule'
            ? '用户永久允许该规则'
            : '用户手动忽略',
    })
    if (report.value?.issues) {
      report.value.issues = report.value.issues.filter((i) => i !== issue)
    }
    if (action === 'allow_rule') {
      ElMessage.success(`已将规则 [${issue.hwe.rule_id}] 加入本项目豁免偏好`)
    } else if (action === 'false_positive') {
      ElMessage.success('已记录误报反馈，系统将自适应降低该规则判定权重')
    } else {
      ElMessage.info('已忽略该项')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '操作失败')
  }
}

function openInWriter(issue?: HWEIssue) {
  if (!selectedChapter.value) return
  void router.push({
    path: '/writer',
    query: {
      chapter: selectedChapter.value,
      highlight_line: issue?.hwe?.line,
    },
  })
}

watch(
  () => props.initialChapter,
  (newVal) => {
    if (newVal && newVal !== selectedChapter.value) {
      selectedChapter.value = newVal
      void runScan()
    }
  },
)

onMounted(() => {
  if (selectedChapter.value) {
    void runScan()
  } else if (props.availableChapters && props.availableChapters.length > 0) {
    selectedChapter.value = props.availableChapters[0].chapter_id
    void runScan()
  }
})
</script>

<template>
  <div class="hwe-panel">
    <!-- Top toolbar & Chapter Selector -->
    <header class="hwe-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedChapter"
          placeholder="选择章节"
          style="width: 180px"
          @change="runScan"
        >
          <el-option
            v-for="ch in availableChapters || []"
            :key="ch.chapter_id"
            :label="`第 ${ch.chapter_id} 章 ${ch.title ? '- ' + ch.title : ''}`"
            :value="ch.chapter_id"
          />
        </el-select>
        <el-button type="primary" :icon="Search" :loading="scanning" @click="runScan">
          扫描活人文风
        </el-button>
        <el-button :icon="MagicStick" :loading="semanticReviewing" @click="runSemanticReviewAction">
          深度语义审校
        </el-button>
        <el-button :icon="View" :loading="previewingPrompt" @click="openPromptPreview">
          写前约束预览
        </el-button>
        <el-button :icon="DocumentChecked" @click="openLongformMemory">
          长篇记忆透视
        </el-button>
        <el-button :icon="TrendCharts" @click="openEvalLab">
          Eval Lab 评测
        </el-button>
      </div>

      <div class="toolbar-right">
        <el-tag v-if="report" effect="plain" type="info">
          规则版本: {{ report.ruleset_version }}
        </el-tag>
        <el-tag v-if="report" effect="plain" type="info">
          正文字数: {{ report.char_count }} 字
        </el-tag>
      </div>
    </header>

    <!-- Score Overview Cards -->
    <section v-if="report" class="hwe-score-grid">
      <div class="score-card main-score" :class="{ high: report.scores.template_risk > 35 }">
        <span class="score-label">模板风险值</span>
        <div class="score-value">
          <strong>{{ report.scores.template_risk }}</strong>
          <small>/ 100</small>
        </div>
        <div class="score-desc">
          {{ report.scores.template_risk > 35 ? '风险偏高，建议局部精修' : '风险较低，行文自然' }}
        </div>
      </div>

      <div class="score-card">
        <span class="score-label">自然表达</span>
        <div class="metric-val">{{ report.scores.naturalness }}</div>
        <el-progress :percentage="report.scores.naturalness" :show-text="false" color="#409EFF" />
      </div>

      <div class="score-card">
        <span class="score-label">节奏多样</span>
        <div class="metric-val">{{ report.scores.rhythm }}</div>
        <el-progress :percentage="report.scores.rhythm" :show-text="false" color="#67C23A" />
      </div>

      <div class="score-card">
        <span class="score-label">叙事克制</span>
        <div class="metric-val">{{ report.scores.narrative_trust }}</div>
        <el-progress :percentage="report.scores.narrative_trust" :show-text="false" color="#E6A23C" />
      </div>

      <div class="score-card">
        <span class="score-label">人物声线</span>
        <div class="metric-val">{{ report.scores.voice }}</div>
        <el-progress :percentage="report.scores.voice" :show-text="false" color="#909399" />
      </div>

      <div class="score-card">
        <span class="score-label">表达新鲜度</span>
        <div class="metric-val">{{ report.scores.freshness }}</div>
        <el-progress :percentage="report.scores.freshness" :show-text="false" color="#F56C6C" />
      </div>
    </section>

    <!-- Diagnosis Summary Box -->
    <div v-if="report" class="hwe-summary-banner">
      <el-icon :size="18"><DocumentChecked /></el-icon>
      <div class="summary-text">{{ report.summary }}</div>
    </div>

    <!-- Issue Classification Filter & List -->
    <section v-if="report" class="hwe-issues-container">
      <div class="filter-bar">
        <el-radio-group v-model="selectedFamily" size="small">
          <el-radio-button
            v-for="fam in families"
            :key="fam.key"
            :value="fam.key"
          >
            {{ fam.label }}
            <span v-if="fam.key !== 'all' && report.issue_counts_by_family[fam.key]">
              ({{ report.issue_counts_by_family[fam.key] }})
            </span>
          </el-radio-button>
        </el-radio-group>
        <span class="issue-count">共 {{ filteredIssues.length }} 项瑕疵</span>
      </div>

      <!-- Empty State -->
      <el-empty
        v-if="filteredIssues.length === 0"
        description="该分类下未检出明显套路瑕疵，行文自然！"
        :image-size="80"
      />

      <!-- Issues List -->
      <div v-else class="issues-list">
        <article
          v-for="(issue, idx) in filteredIssues"
          :key="idx"
          class="issue-card"
          :class="`sev-${issue.severity}`"
        >
          <div class="issue-header">
            <div class="header-left">
              <el-tag
                size="small"
                :type="issue.severity === 'high' ? 'danger' : issue.severity === 'medium' ? 'warning' : 'info'"
              >
                {{ issue.severity === 'high' ? '高风险' : issue.severity === 'medium' ? '中等' : '轻微' }}
              </el-tag>
              <span class="rule-title">{{ issue.text }}</span>
              <span class="location-badge">第 {{ issue.hwe.line }} 行 · 第 {{ issue.hwe.paragraph }} 段</span>
            </div>
            <div class="header-actions">
              <el-button
                size="small"
                type="primary"
                link
                :icon="MagicStick"
                :loading="generatingPatch"
                @click="generatePatchForIssue(issue)"
              >
                生成修复候选
              </el-button>
              <el-button size="small" :icon="View" link @click="openInWriter(issue)">
                正文定位
              </el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => handleIssueAction(issue, cmd)">
                <el-button size="small" link type="info">反馈与偏好 ▾</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="ignore">仅忽略此项</el-dropdown-item>
                    <el-dropdown-item command="false_positive">标记为误报 (自动校准)</el-dropdown-item>
                    <el-dropdown-item command="allow_rule" divided>本项目允许该规则 (豁免)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- Matched Quote Snippet -->
          <div class="matched-snippet">
            <span class="ctx-before">{{ issue.hwe.context_before }}</span>
            <mark class="highlight-matched">{{ issue.hwe.matched_text }}</mark>
            <span class="ctx-after">{{ issue.hwe.context_after }}</span>
          </div>

          <!-- Why & Fix Advice -->
          <div class="issue-body">
            <div class="reason-row">
              <span class="label">瑕疵剖析：</span>
              <span class="text">{{ issue.why }}</span>
            </div>
            <div class="fix-row">
              <span class="label">修改建议：</span>
              <span class="text">{{ issue.fix }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- Diff and Candidate Dialog -->
    <el-dialog
      v-model="diffDialogVisible"
      title="活人文风 · 局部保真修复候选"
      width="680px"
      destroy-on-close
    >
      <div v-if="candidate" class="candidate-dialog-content">
        <div class="dialog-banner">
          <div class="banner-stat">
            <span class="label">健康分预期提升</span>
            <strong class="stat-gain">+{{ candidate.quality_gain }} 分</strong>
          </div>
          <div class="banner-stat">
            <span class="label">改写差异率</span>
            <strong>{{ (candidate.fidelity.edit_ratio * 100).toFixed(1) }}%</strong>
          </div>
          <div class="banner-stat">
            <span class="label">保真状态</span>
            <el-tag :type="candidate.fidelity.passed ? 'success' : 'danger'" size="small">
              {{ candidate.fidelity.passed ? '保真通过' : '存在风险' }}
            </el-tag>
          </div>
        </div>

        <div v-if="candidate.fidelity.violations.length > 0" class="fidelity-alert">
          <el-alert
            v-for="(v, i) in candidate.fidelity.violations"
            :key="i"
            :title="v"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>

        <div class="diff-block">
          <div class="diff-col original-col">
            <div class="col-head">修复前原文</div>
            <div class="col-body original-text">{{ candidate.original_text }}</div>
          </div>
          <div class="diff-col candidate-col">
            <div class="col-head">修复候选稿</div>
            <div class="col-body candidate-text">{{ candidate.candidate_text }}</div>
          </div>
        </div>

        <div v-if="candidate.fidelity.preserved_spans.length > 0" class="preserved-tags">
          <span class="label">已锁定保护要素：</span>
          <el-tag
            v-for="(ps, idx) in candidate.fidelity.preserved_spans"
            :key="idx"
            size="small"
            type="info"
            effect="plain"
          >
            {{ ps.kind === 'character' ? '人名' : ps.kind === 'number' ? '数字' : ps.kind === 'time' ? '时间' : ps.kind }}: {{ ps.value }}
          </el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="diffDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="candidate && !candidate.fidelity.passed"
          :loading="acceptingPatch"
          @click="applyCandidatePatch"
        >
          采纳修复并创建新修订
        </el-button>
      </template>
    </el-dialog>

    <!-- Prompt Constraints Preview Dialog -->
    <el-dialog
      v-model="promptPreviewDialogVisible"
      title="活人文风 · 写前约束提示词编译预览 (PRD §7, §41)"
      width="640px"
    >
      <div v-if="promptPreviewData" class="prompt-preview-container">
        <div class="preview-meta">
          <el-tag :type="promptPreviewData.within_budget ? 'success' : 'danger'" size="small">
            字数预算: {{ promptPreviewData.char_count }} / {{ promptPreviewData.budget }} 字 ({{ promptPreviewData.within_budget ? '合规' : '超标' }})
          </el-tag>
          <span class="preview-tip">依据场景类型、角色人设与近期记忆动态选优注入</span>
        </div>
        <pre class="prompt-block-text">{{ promptPreviewData.prompt_block }}</pre>
      </div>
      <template #footer>
        <el-button type="primary" @click="promptPreviewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Longform Memory Diagnostics Drawer -->
    <el-drawer
      v-model="memoryDrawerVisible"
      title="长篇记忆 2.0 · 跨章表达与结尾复读透视 (PRD §19, §58)"
      size="540px"
    >
      <div v-if="memoryDiagnostics" class="memory-drawer-content">
        <div class="memory-summary">
          <el-statistic title="本章提取特征数" :value="memoryDiagnostics.total_extracted_entries" />
          <el-statistic title="近期高频饱和词" :value="memoryDiagnostics.saturated_count" />
          <el-statistic title="结尾雷同问题" :value="memoryDiagnostics.ending_issues.length" />
        </div>

        <el-divider>近期 3 / 10 章高频复读监控</el-divider>
        <div v-if="memoryDiagnostics.sliding_windows.length === 0" class="empty-hint">
          暂未发现跨章高频复读特征
        </div>
        <div v-else class="memory-list">
          <div
            v-for="(w, idx) in memoryDiagnostics.sliding_windows.slice(0, 15)"
            :key="idx"
            class="memory-item"
            :class="{ saturated: w.is_saturated }"
          >
            <div class="memory-item-header">
              <span class="expr-text">{{ w.expression }}</span>
              <el-tag :type="w.is_saturated ? 'danger' : 'info'" size="small">
                {{ w.is_saturated ? '高频饱和' : '正常复用' }}
              </el-tag>
            </div>
            <div class="memory-stats">
              <span>近 3 章: <strong>{{ w.window_3_count }}</strong> 次</span>
              <span>近 10 章: <strong>{{ w.window_10_count }}</strong> 次</span>
              <span>全书累计: <strong>{{ w.whole_book_count }}</strong> 次</span>
            </div>
          </div>
        </div>

        <div v-if="memoryDiagnostics.ending_issues.length > 0">
          <el-divider>跨章章尾模板雷同警示</el-divider>
          <el-alert
            v-for="(ei, idx) in memoryDiagnostics.ending_issues"
            :key="idx"
            :title="ei.text"
            type="warning"
            :description="ei.why"
            show-icon
            :closable="false"
            style="margin-bottom: 8px"
          />
        </div>
      </div>
    </el-drawer>

    <!-- Eval Lab Benchmark Dialog -->
    <el-dialog
      v-model="evalDialogVisible"
      title="HWE Eval Lab · 文风评测实验室"
      width="780px"
      destroy-on-close
    >
      <div class="eval-dialog-content">
        <div class="eval-banner">
          <div class="eval-stat">
            <span class="label">基准准确率 (F1)</span>
            <strong class="stat-green">
              {{ evalReport?.metrics ? (evalReport.metrics.f1_score * 100).toFixed(1) + '%' : '-' }}
            </strong>
          </div>
          <div class="eval-stat">
            <span class="label">误报率 (FPR)</span>
            <strong :class="evalReport?.fpr_target_met ? 'stat-green' : 'stat-red'">
              {{ evalReport?.metrics ? (evalReport.metrics.false_positive_rate * 100).toFixed(2) + '%' : '-' }}
            </strong>
            <small class="target-tip">目标 &lt; 5.0%</small>
          </div>
          <div class="eval-stat">
            <span class="label">平均扫描耗时</span>
            <strong>{{ evalReport?.metrics ? evalReport.metrics.avg_latency_ms + ' ms' : '-' }}</strong>
          </div>
          <div class="eval-stat">
            <span class="label">测试用例规模</span>
            <strong>{{ evalReport?.metrics ? evalReport.metrics.total_cases + ' 条' : '-' }}</strong>
          </div>
        </div>

        <div style="margin: 16px 0; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 13px; color: #909399;">
            {{ evalReport ? `规则库版本: ${evalReport.ruleset_version} · 上次评测: ${evalReport.timestamp}` : '尚未执行评测' }}
          </span>
          <el-button type="primary" :loading="runningEval" @click="triggerEvalLab">
            立即运行全量基准评测
          </el-button>
        </div>

        <el-table v-if="evalReport?.results" :data="evalReport.results" size="small" style="width: 100%" max-height="360">
          <el-table-column prop="case_id" label="用例 ID" width="180" />
          <el-table-column prop="category" label="分类" width="90" />
          <el-table-column label="判定结果" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.is_true_positive" type="success" size="small">TP 正确命中</el-tag>
              <el-tag v-else-if="row.is_true_negative" type="success" size="small">TN 正常放行</el-tag>
              <el-tag v-else-if="row.is_false_positive" type="danger" size="small">FP 误报</el-tag>
              <el-tag v-else type="warning" size="small">FN 漏报</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detected_rules" label="检出规则">
            <template #default="{ row }">
              {{ row.detected_rules ? row.detected_rules.join(', ') || '（无）' : '（无）' }}
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时" width="90">
            <template #default="{ row }">
              {{ row.duration_ms }} ms
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.eval-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.eval-banner {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 14px;
  border-radius: 8px;
}

.eval-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.eval-stat .label {
  font-size: 12px;
  color: #909399;
}

.eval-stat strong {
  font-size: 20px;
  font-weight: 700;
}

.stat-green {
  color: #67c23a;
}

.stat-red {
  color: #f56c6c;
}

.target-tip {
  font-size: 11px;
  color: #a8abb2;
}

.hwe-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

.hwe-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-bg-color-overlay, #ffffff);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 8px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.hwe-score-grid {
  display: grid;
  grid-template-columns: 1.4fr repeat(5, 1fr);
  gap: 12px;
}

.score-card {
  padding: 14px;
  border-radius: 8px;
  background: var(--el-bg-color-overlay, #ffffff);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.score-card.main-score {
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f1fc 100%);
  border-color: #b3d8ff;
}

.score-card.main-score.high {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
  border-color: #fbc4c4;
}

.score-label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}

.score-value strong {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary, #303133);
}

.score-value small {
  font-size: 13px;
  color: var(--el-text-color-secondary, #909399);
}

.score-desc {
  font-size: 12px;
  color: var(--el-text-color-regular, #606266);
  margin-top: 4px;
}

.metric-val {
  font-size: 20px;
  font-weight: 600;
  margin: 6px 0;
  color: var(--el-text-color-primary, #303133);
}

.hwe-summary-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f4f4f5;
  border-left: 4px solid var(--el-color-primary, #409eff);
  border-radius: 4px;
  font-size: 13px;
  color: var(--el-text-color-primary, #303133);
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.issue-count {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-card {
  padding: 14px 16px;
  background: var(--el-bg-color-overlay, #ffffff);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 8px;
  transition: all 0.2s ease;
}

.issue-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.issue-card.sev-high {
  border-left: 4px solid #f56c6c;
}

.issue-card.sev-medium {
  border-left: 4px solid #e6a23c;
}

.issue-card.sev-low {
  border-left: 4px solid #909399;
}

.issue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary, #303133);
}

.location-badge {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}

.matched-snippet {
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
  font-family: monospace, sans-serif;
  font-size: 13px;
  color: #555;
  margin-bottom: 10px;
  line-height: 1.6;
}

.highlight-matched {
  background: #ffe58f;
  color: #d4380d;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 2px;
}

.issue-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}

.reason-row, .fix-row {
  display: flex;
  gap: 6px;
}

.reason-row .label {
  color: var(--el-color-danger, #f56c6c);
  flex-shrink: 0;
}

.fix-row .label {
  color: var(--el-color-success, #67c23a);
  flex-shrink: 0;
}

.reason-row .text, .fix-row .text {
  color: var(--el-text-color-regular, #606266);
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.candidate-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-banner {
  display: flex;
  gap: 24px;
  background: var(--el-fill-color-light, #f8f9fa);
  padding: 12px 18px;
  border-radius: 6px;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-stat .label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}

.stat-gain {
  color: #67c23a;
  font-size: 16px;
  font-weight: 700;
}

.diff-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.diff-col {
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 6px;
  overflow: hidden;
}

.col-head {
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  background: var(--el-fill-color-light, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
}

.col-body {
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  font-family: monospace, sans-serif;
  min-height: 90px;
  white-space: pre-wrap;
  word-break: break-word;
}

.original-col .col-body {
  background: #fff1f0;
  color: #cf1322;
}

.candidate-col .col-body {
  background: #f6ffed;
  color: #389e0d;
}

.preserved-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 12px;
}

.preserved-tags .label {
  color: var(--el-text-color-secondary, #909399);
}

.prompt-preview-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}

.prompt-block-text {
  padding: 12px 14px;
  background: #f8f9fa;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 6px;
  font-family: monospace, sans-serif;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 420px;
  overflow-y: auto;
  color: #333;
}

.memory-drawer-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.memory-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px;
  background: var(--el-fill-color-light, #f5f7fa);
  border-radius: 8px;
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 6px;
  background: var(--el-bg-color-overlay, #ffffff);
}

.memory-item.saturated {
  border-left: 4px solid #f56c6c;
  background: #fef0f0;
}

.memory-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.expr-text {
  font-weight: 600;
  font-size: 13px;
}

.memory-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}
</style>
