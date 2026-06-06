<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Cpu, Edit } from '@element-plus/icons-vue'
import { updateOutline } from '../../api'
import ScaleModeBar from './ScaleModeBar.vue'
import { SCALE_OPTIONS, scalePlanningModeLabel } from '../../constants/scaleOptions'

const props = defineProps<{
  outline: Record<string, any> | null
  scaleProfile?: Record<string, any>
  chaptersWritten?: number
}>()

const emit = defineEmits<{
  saved: []
}>()

const router = useRouter()
const saving = ref(false)
const editScaleVisible = ref(false)
const expanded = ref(false)
const editScaleForm = ref({
  scale: 'long',
  target_chapters: 200,
  chars_min: 2000,
  chars_max: 3000,
})

const profile = computed(
  () => props.scaleProfile?.profile || props.outline?.scale_profile || {},
)

const scaleKey = computed(() => String(profile.value?.scale || ''))
const scaleLabel = computed(() => String(profile.value?.label || ''))
const targetChapters = computed(
  () => Number(profile.value?.target_chapters || props.outline?.target_chapters || 0),
)
const chaptersWritten = computed(
  () => props.scaleProfile?.current_chapter_count ?? props.chaptersWritten ?? 0,
)

const specSummary = computed(() => {
  if (!props.outline) return '尚未生成大纲'
  const label = scaleLabel.value || scaleKey.value || '未设定'
  const chars = profile.value?.target_chars
  const charsText = chars ? ` · ${chars[0]}–${chars[1]} 字/章` : ''
  return `${label} · 目标 ${targetChapters.value} 章${charsText}`
})

const displayPlanningMode = computed(() => {
  const raw = profile.value?.planning_mode || ''
  return scalePlanningModeLabel(String(raw))
})

const openEditScale = () => {
  if (!props.outline) {
    ElMessage.warning('请先生成或打开作品大纲')
    return
  }
  const p = profile.value
  const targetChars = p?.target_chars || [2000, 3000]
  editScaleForm.value = {
    scale: p?.scale || 'long',
    target_chapters: Number(p?.target_chapters || props.outline?.target_chapters || 200),
    chars_min: targetChars[0] || 2000,
    chars_max: targetChars[1] || 3000,
  }
  editScaleVisible.value = true
}

const handleSaveScale = async () => {
  const chosenOption = SCALE_OPTIONS.find((opt) => opt.scale === editScaleForm.value.scale)
  if (!chosenOption || !props.outline) return

  saving.value = true
  try {
    const scale_profile = {
      scale: chosenOption.scale,
      label: chosenOption.label,
      max_chapters: chosenOption.max_chapters,
      planning_mode: chosenOption.planning_mode,
      target_chars: [editScaleForm.value.chars_min, editScaleForm.value.chars_max],
      vector_enabled: ['medium', 'long', 'epic', 'infinite'].includes(chosenOption.scale),
      calibration_interval: ['medium', 'long', 'epic', 'infinite'].includes(chosenOption.scale) ? 20 : 0,
    }

    await updateOutline({
      ...props.outline,
      target_chapters: editScaleForm.value.target_chapters,
      scale_profile,
    })
    ElMessage.success('体量配置已保存，长篇流水线将同步更新')
    editScaleVisible.value = false
    emit('saved')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '体量配置保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section v-if="outline" class="scale-architecture-panel" :class="{ 'is-collapsed': !expanded }">
    <div class="panel-head">
      <button type="button" class="head-toggle" @click="expanded = !expanded">
        <el-icon class="panel-icon scale-color"><Cpu /></el-icon>
        <h2>体量架构</h2>
        <span class="spec-summary">{{ specSummary }}</span>
        <el-icon class="collapse-chevron" :class="{ open: expanded }"><ArrowDown /></el-icon>
      </button>
      <el-button text type="primary" :icon="Edit" size="small" @click.stop="openEditScale">编辑</el-button>
    </div>
    <div v-show="expanded" class="panel-body">
      <p class="panel-hint">体量唯一入口；保存后同步长篇流水线。下方长篇指标为只读参考。</p>
      <ScaleModeBar
        :scale="scaleKey"
        :scale-label="scaleLabel"
        :target-chapters="targetChapters"
        :chapters-written="chaptersWritten"
      />
      <dl class="config-kv">
        <div>
          <dt>当前规格</dt>
          <dd>{{ scaleLabel || scaleKey || '未设定' }}</dd>
        </div>
        <div>
          <dt>规划模式</dt>
          <dd class="ellipsis">{{ displayPlanningMode }}</dd>
        </div>
        <div>
          <dt>校准间隔</dt>
          <dd>
            {{
              profile?.calibration_interval
                ? `${profile.calibration_interval}章`
                : '关闭'
            }}
          </dd>
        </div>
        <div>
          <dt>创作进度</dt>
          <dd>{{ chaptersWritten }} / {{ profile?.max_chapters || '∞' }}</dd>
        </div>
        <div v-if="profile?.target_chars" class="kv-span-2">
          <dt>每章字数</dt>
          <dd>{{ profile.target_chars[0] }}–{{ profile.target_chars[1] }} 字</dd>
        </div>
      </dl>
      <p v-if="scaleProfile?.upgrade_pressure?.should_prompt" class="config-warn">
        已接近体量上限，建议升档。
      </p>
    </div>
  </section>

  <section v-else class="scale-architecture-panel scale-architecture-empty">
    <div class="panel-head">
      <div class="panel-title">
        <el-icon class="panel-icon scale-color"><Cpu /></el-icon>
        <h2>体量架构</h2>
        <span class="spec-summary muted">尚未生成大纲</span>
      </div>
    </div>
    <p class="panel-hint">尚未生成大纲，无法设定体量。</p>
    <el-button type="primary" link @click="router.push('/outline')">前往大纲页生成</el-button>
  </section>

  <el-dialog v-model="editScaleVisible" title="编辑体量配置" width="500px" top="10vh" append-to-body>
    <el-form label-width="110px">
      <el-form-item label="规格">
        <el-select v-model="editScaleForm.scale" placeholder="选择体量规格">
          <el-option
            v-for="opt in SCALE_OPTIONS"
            :key="opt.scale"
            :label="opt.label"
            :value="opt.scale"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="目标章数">
        <el-input-number v-model="editScaleForm.target_chapters" :min="1" />
      </el-form-item>
      <el-form-item label="每章最小字数">
        <el-input-number v-model="editScaleForm.chars_min" :min="500" :step="500" />
      </el-form-item>
      <el-form-item label="每章最大字数">
        <el-input-number v-model="editScaleForm.chars_max" :min="500" :step="500" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editScaleVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSaveScale">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.scale-architecture-panel {
  margin-bottom: 14px;
  border-radius: 12px;
  border: 1px solid var(--color-border, #e4e7ed);
  background: var(--color-bg-surface, #fff);
  box-shadow: var(--shadow-card, 0 4px 12px rgba(15, 23, 42, 0.06));
  overflow: hidden;
}

.scale-architecture-empty {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid transparent;
}

.scale-architecture-panel.is-collapsed .panel-head {
  border-bottom: 0;
}

.head-toggle {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.head-toggle:hover h2 {
  color: var(--color-primary);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.panel-title h2,
.head-toggle h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  flex-shrink: 0;
}

.panel-icon.scale-color {
  color: #409eff;
  font-size: 16px;
  flex-shrink: 0;
}

.spec-summary {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text-muted, #606266);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spec-summary.muted {
  font-weight: 500;
}

.collapse-chevron {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--color-text-subtle);
  transition: transform 0.2s ease;
}

.collapse-chevron.open {
  transform: rotate(180deg);
}

.panel-body {
  padding: 0 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-text-muted, #909399);
  line-height: 1.4;
}

.config-kv {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px 10px;
  margin: 0;
}

.config-kv dt {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-subtle, #a8abb2);
  font-weight: 600;
}

.config-kv dd {
  margin: 2px 0 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong, #303133);
}

.config-kv .kv-span-2 {
  grid-column: span 2;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.config-warn {
  margin: 0;
  font-size: 12.5px;
  color: #e6a23c;
  font-weight: 600;
}

.scale-architecture-panel :deep(.scale-mode-bar) {
  margin-bottom: 0;
}

@media (max-width: 900px) {
  .config-kv {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>