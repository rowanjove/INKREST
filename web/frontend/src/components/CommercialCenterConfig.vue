<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  fetchCommercialStatus,
  startTrialLicense,
  activateLicenseKey,
  checkSystemHealth,
  repairSystemHealth,
  createCommercialBackup,
  generateDiagnostics,
  estimateTaskCost,
  type CommercialStatus,
  type CostEstimateResult,
} from '../api/commercial'

const props = withDefaults(
  defineProps<{
    bare?: boolean
  }>(),
  {
    bare: false,
  },
)

const loading = ref(true)
const status = ref<CommercialStatus | null>(null)

// License activation dialog
const licenseDialogVisible = ref(false)
const licenseInput = ref('')
const activating = ref(false)
const startingTrial = ref(false)

// Recovery actions
const checkingHealth = ref(false)
const repairing = ref(false)
const backingUp = ref(false)
const generatingDiag = ref(false)

// Cost estimator
const estChapters = ref(10)
const estModel = ref('deepseek-chat')
const estimating = ref(false)
const estimateResult = ref<CostEstimateResult | null>(null)

const modelOptions = [
  { label: 'DeepSeek Chat (标准)', value: 'deepseek-chat' },
  { label: 'DeepSeek Reasoner (推理强化)', value: 'deepseek-reasoner' },
  { label: 'Claude 3.5 Sonnet (高画质)', value: 'claude-3-5-sonnet' },
  { label: 'GPT-4o (旗舰创作)', value: 'gpt-4o' },
]

async function loadStatus() {
  loading.value = true
  try {
    status.value = await fetchCommercialStatus()
  } catch (err: any) {
    console.error('Failed to load commercial status:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadStatus()
})

async function onStartTrial() {
  startingTrial.value = true
  try {
    const res = await startTrialLicense()
    ElMessage.success(res.message || '14 天 Pro 体验版已成功激活！')
    await loadStatus()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '试用开启失败')
  } finally {
    startingTrial.value = false
  }
}

async function onActivateLicense() {
  if (!licenseInput.value.trim()) {
    ElMessage.warning('请输入有效的许可证密钥或 JSON 内容')
    return
  }
  activating.value = true
  try {
    const res = await activateLicenseKey(licenseInput.value.trim())
    ElMessage.success(res.message || '许可证激活成功！')
    licenseDialogVisible.value = false
    licenseInput.value = ''
    await loadStatus()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '许可证激活失败，请检查签名或有效期')
  } finally {
    activating.value = false
  }
}

async function onCheckHealth() {
  checkingHealth.value = true
  try {
    const res = await checkSystemHealth()
    if (res.status === 'healthy') {
      ElNotification({
        title: '健康体检通过',
        message: '数据保险箱 SQLite PRAGMA 校验通过，架构版本匹配，未发现损坏异常。',
        type: 'success',
      })
    } else {
      ElNotification({
        title: '体检发现异常',
        message: res.issues.join('\n'),
        type: 'warning',
      })
    }
    await loadStatus()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '体检失败')
  } finally {
    checkingHealth.value = false
  }
}

async function onRepair() {
  repairing.value = true
  try {
    const res = await repairSystemHealth()
    ElNotification({
      title: '自愈修复完成',
      message: res.repaired?.length ? `已修复: ${res.repaired.join(', ')}` : '未发现需要修复的损坏项，系统处于健康状态。',
      type: 'success',
    })
    await loadStatus()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '自愈修复失败')
  } finally {
    repairing.value = false
  }
}

async function onBackup() {
  backingUp.value = true
  try {
    const res = await createCommercialBackup()
    ElNotification({
      title: '保险箱灾备归档成功',
      message: `已创建 ${res.backup_file} (SHA-256: ${res.sha256.slice(0, 12)}…)`,
      type: 'success',
      duration: 6000,
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '灾备导出失败')
  } finally {
    backingUp.value = false
  }
}

async function onDiagnostics() {
  generatingDiag.value = true
  try {
    const res = await generateDiagnostics()
    ElNotification({
      title: '脱敏诊断报告已生成',
      message: `报告已保存至: ${res.report_file} (所有密钥、Token及私密正文已脱敏)`,
      type: 'info',
      duration: 6000,
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '诊断报告生成失败')
  } finally {
    generatingDiag.value = false
  }
}

async function onEstimate() {
  estimating.value = true
  try {
    estimateResult.value = await estimateTaskCost({
      num_chapters: estChapters.value,
      model: estModel.value,
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '试算失败')
  } finally {
    estimating.value = false
  }
}

const tierMeta = computed(() => {
  const t = status.value?.license?.tier || 'free'
  if (t === 'pro') {
    return { name: 'PRO 专业版', color: '#6366f1', bg: '#eef2ff', icon: '👑' }
  }
  if (t === 'trial') {
    return { name: 'PRO 14天体验', color: '#f59e0b', bg: '#fef3c7', icon: '⚡' }
  }
  if (t === 'enterprise') {
    return { name: 'ENTERPRISE 企业版', color: '#0ea5e9', bg: '#e0f2fe', icon: '🏛' }
  }
  return { name: 'FREE 基础版', color: '#64748b', bg: '#f1f5f9', icon: '🌱' }
})
</script>

<template>
  <section id="commercial-center" class="commercial-card" :class="{ 'is-bare': bare }">
    <!-- 头部 -->
    <div class="commercial-heading">
      <div class="heading-left">
        <span class="eyebrow">COMMERCIAL READINESS</span>
        <div class="title-with-badge">
          <h3>商业授权与数据安全</h3>
          <span
            class="tier-badge"
            :style="{ color: tierMeta.color, backgroundColor: tierMeta.bg, borderColor: tierMeta.color }"
          >
            {{ tierMeta.icon }} {{ tierMeta.name }}
          </span>
          <span v-if="status?.license?.is_valid" class="verify-badge">
            ✓ Ed25519 签名验证通过
          </span>
        </div>
        <p class="sub-hint">
          提供端到端数据保险箱隔离、SQLite 完整性自动体检与自愈、AI 成本预算守卫与商业授权特权。
        </p>
      </div>
      <div class="heading-action">
        <el-button
          v-if="status?.license?.tier === 'free'"
          type="primary"
          :loading="startingTrial"
          @click="onStartTrial"
        >
          免费开启 14 天 Pro 体验
        </el-button>
        <el-button
          plain
          @click="licenseDialogVisible = true"
        >
          {{ status?.license?.tier === 'free' ? '输入许可证激活' : '更新许可证' }}
        </el-button>
      </div>
    </div>

    <!-- 1. 商业授权特权看板 -->
    <div class="section-block">
      <div class="block-title">
        <span class="section-icon">👑</span>
        <span>商业授权与生效特权</span>
        <span class="title-subhint">离线无网环境下亦可通过密码学数字签名安全验签</span>
      </div>

      <div class="entitlements-grid">
        <div
          class="entitlement-item"
          :class="{ active: status?.license?.entitlements?.includes('advanced_agent') }"
        >
          <div class="ent-header">
            <strong>高级写作 Agent</strong>
            <span class="ent-badge">PRO</span>
          </div>
          <p>多智能体闭环推演、剧情网状推导与大纲深度扩写</p>
        </div>

        <div
          class="entitlement-item"
          :class="{ active: status?.license?.entitlements?.includes('conflict_diagnostics') }"
        >
          <div class="ent-header">
            <strong>剧情冲突自动诊断</strong>
            <span class="ent-badge">PRO</span>
          </div>
          <p>时间线、战力设定与人设矛盾智能检测与修复建议</p>
        </div>

        <div
          class="entitlement-item"
          :class="{ active: status?.license?.entitlements?.includes('batch_export') }"
        >
          <div class="ent-header">
            <strong>多卷工程批量排版导出</strong>
            <span class="ent-badge">PRO</span>
          </div>
          <p>出版级 EPUB、PDF 自动化排版与精校分卷打包</p>
        </div>

        <div
          class="entitlement-item"
          :class="{ active: status?.license?.entitlements?.includes('diff_review') }"
        >
          <div class="ent-header">
            <strong>差量审查与事务回滚</strong>
            <span class="ent-badge">CORE</span>
          </div>
          <p>精细到段落的 Diff 对比、逐块合并与跨会话 Undo/Redo</p>
        </div>
      </div>
    </div>

    <!-- 2. 数据安全与健康自愈中心 -->
    <div class="section-block">
      <div class="block-title">
        <span class="section-icon">🛡️</span>
        <span>数据保险箱与自愈恢复中心</span>
        <span class="title-subhint">保护创作者长篇数百万字手稿免受崩溃损坏或意外覆写</span>
      </div>

      <div class="recovery-dashboard">
        <div class="vault-info-card">
          <div class="info-row">
            <span class="label">保险箱容器：</span>
            <code class="path-code">{{ status?.vault?.storage_path || 'accounts/default/' }}</code>
            <el-tag size="small" type="success" effect="plain">安全隔离</el-tag>
          </div>
          <div class="info-row">
            <span class="label">数据库健康：</span>
            <span class="health-status">
              <i class="dot" :class="{ 'is-ok': status?.recovery?.integrity_ok }"></i>
              {{ status?.recovery?.sqlite_health || 'PRAGMA integrity_check: ok' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">崩溃守护：</span>
            <span>已启用原子事务保护 · 活动恢复会话: {{ status?.recovery?.crash_recovery?.active_session_count ?? 0 }}</span>
          </div>
        </div>

        <div class="recovery-actions">
          <div class="action-card">
            <strong>完整性体检</strong>
            <p>对 SQLite 数据表、外键依赖与 Schema 执行只读体检</p>
            <el-button
              size="small"
              :loading="checkingHealth"
              @click="onCheckHealth"
            >
              健康体检
            </el-button>
          </div>

          <div class="action-card">
            <strong>一键自愈修复</strong>
            <p>自动修复损坏的索引用量、重置悬空任务与脏状态</p>
            <el-button
              size="small"
              type="primary"
              plain
              :loading="repairing"
              @click="onRepair"
            >
              自愈修复
            </el-button>
          </div>

          <div class="action-card">
            <strong>导出 .inkrest-vault</strong>
            <p>生成带 SHA-256 签名清单的便携式加密灾备归档包</p>
            <el-button
              size="small"
              :loading="backingUp"
              @click="onBackup"
            >
              创建归档
            </el-button>
          </div>

          <div class="action-card">
            <strong>生成脱敏诊断包</strong>
            <p>自动剥离敏感密钥与正文，生成可安全提交的错误日志</p>
            <el-button
              size="small"
              :loading="generatingDiag"
              @click="onDiagnostics"
            >
              生成报告
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. AI 成本与预算守卫 -->
    <div class="section-block">
      <div class="block-title">
        <span class="section-icon">💰</span>
        <span>AI 成本与预算守卫</span>
        <span class="title-subhint">防止突发大批量生成导致 API 欠费，设置任务级与单日预算熔断</span>
      </div>

      <div class="budget-dashboard">
        <div class="budget-stat-card">
          <div class="stat-item">
            <span class="stat-label">今日已消耗</span>
            <div class="stat-value cny">¥{{ (status?.budget?.today_spent_cny ?? 0).toFixed(2) }}</div>
            <span class="stat-sub">今日预算: ¥{{ (status?.budget?.daily_budget_cny ?? 50).toFixed(2) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">今日 Token 用量</span>
            <div class="stat-value">{{ (status?.budget?.today_tokens_used ?? 0).toLocaleString() }}</div>
            <span class="stat-sub">任务熔断线: ¥{{ (status?.budget?.task_budget_cny ?? 15).toFixed(2) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">预算守卫状态</span>
            <div class="stat-value safe">
              <span class="safe-pill">● 活跃防御</span>
            </div>
            <span class="stat-sub">超额请求自动阻断</span>
          </div>
        </div>

        <!-- 成本预估测算器 -->
        <div class="calculator-card">
          <div class="calc-header">
            <strong>批量任务成本预估计算器</strong>
            <span>在批量生成前测算预计消耗的 Token 与费用</span>
          </div>
          <div class="calc-controls">
            <div class="field-item">
              <label>计划生成章节：</label>
              <el-input-number
                v-model="estChapters"
                :min="1"
                :max="100"
                size="default"
              />
            </div>
            <div class="field-item">
              <label>目标模型：</label>
              <el-select v-model="estModel" size="default" style="width: 220px">
                <el-option
                  v-for="m in modelOptions"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                />
              </el-select>
            </div>
            <el-button
              type="primary"
              :loading="estimating"
              @click="onEstimate"
            >
              测算成本
            </el-button>
          </div>

          <div v-if="estimateResult" class="calc-result-box">
            <div class="res-item">
              <span>预估总 Token：</span>
              <strong>{{ estimateResult.total_tokens.toLocaleString() }}</strong>
            </div>
            <div class="res-item">
              <span>预估总费用：</span>
              <strong class="highlight-cny">¥{{ estimateResult.estimated_cost_cny.toFixed(2) }}</strong>
            </div>
            <div class="res-item">
              <span>今日剩余预算：</span>
              <span>¥{{ estimateResult.daily_budget_remaining_cny.toFixed(2) }}</span>
            </div>
            <div class="res-item">
              <span>预算安全：</span>
              <el-tag :type="estimateResult.fits_daily_budget ? 'success' : 'danger'" size="small">
                {{ estimateResult.fits_daily_budget ? '在安全预算内' : '超出单日限额' }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 许可证激活弹窗 -->
    <el-dialog
      v-model="licenseDialogVisible"
      title="激活商业许可证"
      width="540px"
      append-to-body
    >
      <div class="license-dialog-content">
        <p class="dialog-desc">
          请粘贴您购买或获赠的许可证 JSON 授权文件内容（包含 Ed25519 签名及用户特权）：
        </p>
        <el-input
          v-model="licenseInput"
          type="textarea"
          :rows="7"
          placeholder='{"license_id": "...", "licensee": "...", "tier": "pro", "signature": "..."}'
        />
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="licenseDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="activating"
            @click="onActivateLicense"
          >
            校验并激活
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.commercial-card {
  scroll-margin-top: 72px;
  display: grid;
  gap: 20px;
  padding: 20px 22px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}

.commercial-card.is-bare {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 4px 0 !important;
  border-radius: 0 !important;
}

.commercial-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--color-border);
}

.heading-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.eyebrow {
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-with-badge h3 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 750;
  line-height: 1.3;
}

.tier-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid transparent;
}

.verify-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.sub-hint {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.heading-action {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.block-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-strong, #222);
  font-size: 13px;
  font-weight: 650;
}

.section-icon {
  font-size: 15px;
}

.title-subhint {
  color: var(--color-text-muted, #888);
  font-size: 11px;
  font-weight: normal;
  margin-left: 6px;
}

/* 1. Entitlements Grid */
.entitlements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.entitlement-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.entitlement-item.active {
  border-color: #6366f1;
  background: color-mix(in srgb, #6366f1 4%, var(--color-bg-surface));
}

.ent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ent-header strong {
  font-size: 12px;
  color: var(--color-text-strong);
}

.ent-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f0ede9);
  color: var(--color-text-muted);
  font-weight: 700;
}

.entitlement-item.active .ent-badge {
  background: #6366f1;
  color: #fff;
}

.entitlement-item p {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

/* 2. Recovery Center */
.recovery-dashboard {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.vault-info-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-subtle, #faf8f5);
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-strong);
  flex-wrap: wrap;
}

.info-row .label {
  color: var(--color-text-muted);
  font-weight: 500;
}

.path-code {
  background: var(--color-bg-surface);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  font-family: ui-monospace, monospace;
  font-size: 11px;
}

.health-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #16a34a;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}

.dot.is-ok {
  background: #16a34a;
}

.recovery-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}

.action-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
}

.action-card strong {
  font-size: 12px;
  color: var(--color-text-strong);
}

.action-card p {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.45;
  flex: 1;
}

.action-card .el-button {
  margin-top: 6px;
  align-self: flex-start;
}

/* 3. Budget Dashboard */
.budget-dashboard {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.budget-stat-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-surface);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-muted);
}

.stat-value {
  font-size: 20px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.stat-value.cny {
  color: var(--color-primary);
}

.stat-sub {
  font-size: 10px;
  color: var(--color-text-subtle, #999);
}

.stat-divider {
  width: 1px;
  height: 38px;
  background: var(--color-border);
}

.safe-pill {
  font-size: 12px;
  font-weight: 600;
  color: #16a34a;
  background: #f0fdf4;
  padding: 2px 8px;
  border-radius: 12px;
}

.calculator-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-subtle, #faf8f5);
}

.calc-header strong {
  display: block;
  font-size: 12px;
  color: var(--color-text-strong);
}

.calc-header span {
  font-size: 11px;
  color: var(--color-text-muted);
}

.calc-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-strong);
}

.calc-result-box {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-radius: 6px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  font-size: 12px;
}

.res-item strong {
  color: var(--color-text-strong);
}

.highlight-cny {
  color: #ef4444;
  font-weight: 700;
}

.license-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dialog-desc {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

@media (max-width: 720px) {
  .commercial-heading {
    flex-direction: column;
  }
  .heading-action {
    width: 100%;
  }
  .budget-stat-card {
    flex-direction: column;
    gap: 14px;
  }
  .stat-divider {
    display: none;
  }
}
</style>
