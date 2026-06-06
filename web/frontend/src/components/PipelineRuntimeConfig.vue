<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, getEmbeddingStatus, updateConfig } from '../api'

const expanded = ref(false)
const loading = ref(false)
const saving = ref(false)

const qualityMode = ref<'report_only' | 'block_on_fail'>('report_only')
const qualityAutoRewrite = ref(true)
const personaEvaluations = ref<'auto' | 'full' | 'on_fail_only' | 'off'>('auto')
const semanticEffective = ref(true)
const hookFailFast = ref(false)
const hookTimeoutSeconds = ref(30)
const batchSkipPauseMax = ref(3)
const blockContinueUntilExternal = ref(false)
const workScale = ref('medium')
const pipelineTier = ref('standard')
const auditProfile = ref('standard')
const chapterConfig = ref<Record<string, unknown>>({})
const runtimeConfig = ref<Record<string, unknown>>({})

const load = async () => {
  loading.value = true
  try {
    const { data } = await getConfig()
    chapterConfig.value = { ...(data.chapter || {}) }
    runtimeConfig.value = { ...(data.runtime || {}) }
    const mode = data.chapter?.quality_mode
    qualityMode.value = mode === 'block_on_fail' ? 'block_on_fail' : 'report_only'
    qualityAutoRewrite.value = data.chapter?.quality_auto_rewrite !== false
    const persona = data.chapter?.persona_evaluations
    if (persona === 'off' || persona === 'full' || persona === 'on_fail_only') {
      personaEvaluations.value = persona
    } else {
      personaEvaluations.value = 'auto'
    }
    try {
      const emb = await getEmbeddingStatus()
      semanticEffective.value = Boolean(emb.data?.semantic_search_effective)
      workScale.value = String(emb.data?.work_scale || 'medium')
      pipelineTier.value = String(emb.data?.pipeline_tier || 'standard')
      auditProfile.value = String(emb.data?.audit_profile || 'standard')
    } catch {
      semanticEffective.value = false
    }
    hookFailFast.value = Boolean(data.runtime?.hook_fail_fast)
    const timeout = Number(data.runtime?.hook_timeout_seconds)
    hookTimeoutSeconds.value = Number.isFinite(timeout) && timeout > 0 ? timeout : 30
    const skipMax = Number(data.runtime?.batch_skip_pause_max)
    batchSkipPauseMax.value = Number.isFinite(skipMax) && skipMax >= 0 ? skipMax : 3
    blockContinueUntilExternal.value = Boolean(
      data.runtime?.block_continue_until_external_pass,
    )
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    await updateConfig({
      chapter: {
        ...chapterConfig.value,
        quality_mode: qualityMode.value,
        quality_auto_rewrite: qualityAutoRewrite.value,
        persona_evaluations: personaEvaluations.value,
      },
      runtime: {
        ...runtimeConfig.value,
        hook_fail_fast: hookFailFast.value,
        hook_timeout_seconds: hookTimeoutSeconds.value,
        batch_skip_pause_max: batchSkipPauseMax.value,
        block_continue_until_external_pass: blockContinueUntilExternal.value,
      },
    })
    ElMessage.success('流水线高级设置已保存')
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const embeddingDegraded = computed(() => !semanticEffective.value)

onMounted(load)
</script>

<template>
  <section class="fold-card" v-loading="loading">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>流水线高级设置</h2>
          <p>质量门禁与插件钩子行为（写入当前项目的 pipeline.yaml）。</p>
        </div>
      </div>
    </div>

    <div v-show="expanded" class="fold-body">
      <el-alert type="info" :closable="false" show-icon class="mode-preset-alert" title="推荐组合">
        <p><strong>连写优先</strong>：失败阻断 + 自动修正开 — 少熔断、机器先修一版。</p>
        <p><strong>外站严审 / 半自动</strong>：失败阻断 + 自动修正关 — 宁可暂停，改稿后重试审校再「继续写书」。</p>
      </el-alert>
      <p class="hint scale-hint">
        长篇/超长篇的体量请在工作台「体量架构」修改；保存后会自动补全此处空缺的批量保护、persona 自动等项。手改本页后以 pipeline.yaml 为准。
        当前体量 <strong>{{ workScale }}</strong> · 流水线档位 <strong>{{ pipelineTier }}</strong> · 审校配置 <strong>{{ auditProfile }}</strong>
        （economy 可跳过连续性检查，premium 全审；可在 pipeline.yaml 的 <code>runtime.audit_profile</code> 覆盖）。
      </p>

      <el-alert
        v-if="embeddingDegraded"
        type="warning"
        :closable="false"
        show-icon
        title="语义向量未生效"
        class="embedding-alert"
      >
        当前 Embedding 为 stub 或未配置密钥，跨章去重与向量伏笔召回不会执行。
        请在本页上方「向量嵌入」区块配置本地 BGE 或云端 API。
      </el-alert>

      <div class="field-block">
        <label>质量门禁模式</label>
        <el-radio-group v-model="qualityMode">
          <el-radio value="report_only">仅报告（默认，不阻断落库）</el-radio>
          <el-radio value="block_on_fail">失败阻断（正文为空等严重问题暂停 post_audit 落库）</el-radio>
        </el-radio-group>
        <p class="hint">
          阻断模式下会回滚检查点到审校阶段，可在任务日志中看到 quality_guard / blocked。
        </p>
      </div>

      <div class="field-block">
        <label>读者人设评测</label>
        <el-radio-group v-model="personaEvaluations">
          <el-radio value="auto">按体量自动（长篇/超长篇关，中短篇仅门禁告警时评测）</el-radio>
          <el-radio value="on_fail_only">仅门禁未通过或 WARN 时三连评</el-radio>
          <el-radio value="full">每章三连评（费 Token）</el-radio>
          <el-radio value="off">关闭</el-radio>
        </el-radio-group>
        <p class="hint">
          「自动」在 long/epic 档位默认关闭；short/medium 默认仅在质量未通过时跑 3 次 LLM 人设评测。
        </p>
      </div>

      <div class="field-block">
        <label>质量门禁自动修正</label>
        <el-switch
          v-model="qualityAutoRewrite"
          active-text="阻断前尝试一次风格编辑修正"
          inactive-text="关闭（仅阻断/报告）"
        />
        <p class="hint">
          在「失败阻断」模式下，若物理门禁未通过，会先用 style_editor 按报告提示改一版正文并重新检测；仍失败则保持 quality_blocked 状态。
        </p>
      </div>

      <div class="field-block">
        <label>插件钩子超时（秒）</label>
        <el-input-number
          v-model="hookTimeoutSeconds"
          :min="5"
          :max="300"
          :step="5"
        />
        <p class="hint">单个 hook 超过该时间将中止并记 plugin_hook 告警；默认 30 秒。</p>
      </div>

      <div class="field-block">
        <label>连续跳过暂停阈值</label>
        <el-input-number v-model="batchSkipPauseMax" :min="0" :max="20" />
        <p class="hint">
          全书批量中连续「跳过并进入待重试」达到该次数即暂停（0=关闭）。与质量熔断
          <code>batch_fail_streak_max</code> 独立。
        </p>
      </div>

      <div class="field-block">
        <label>外审未通过时禁止续跑</label>
        <el-switch
          v-model="blockContinueUntilExternal"
          active-text="有待外审章时拒绝 continue"
          inactive-text="关闭（仅提示）"
        />
      </div>

      <div class="field-block">
        <label>长篇批量保护</label>
        <p class="hint">
          连续 <code>batch_fail_streak_max</code>（默认 5）章质量阻断/异常将熔断暂停。向量默认回看
          <code>vector_search_window</code> 章。epic/infinite 可能抽检门禁（generation_policy）。
        </p>
      </div>

      <div class="field-block">
        <label>插件钩子失败</label>
        <el-switch
          v-model="hookFailFast"
          active-text="立即中断章节流水线"
          inactive-text="记录告警并继续（推荐）"
        />
        <p class="hint">
          关闭时 hook 异常会通过 plugin_hook 进度事件提示，不中断生成。
        </p>
      </div>

      <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
    </div>
  </section>
</template>

<style scoped>
.scale-hint {
  margin: 0;
  padding: 10px 12px;
  background: var(--color-bg-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.field-block label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.embedding-alert {
  margin-bottom: 4px;
}
</style>
