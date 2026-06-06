<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'

defineProps<{ plan: any }>()
</script>

<template>
  <div class="plan-tab-content">
    <div class="plan-summary-header">
      <span class="plan-title-bold">章节创作大纲规划</span>
      <span class="plan-words-target" v-if="plan?.target_chars">
        目标总字数: {{ plan.target_chars[0] }} - {{ plan.target_chars[1] }}
      </span>
    </div>
    <div class="scenes-list" v-if="plan?.scenes?.length">
      <div v-for="scene in plan.scenes" :key="scene.scene_id" class="scene-item-card">
        <div class="scene-item-header">
          <span class="scene-number">场次 {{ scene.scene_id }}</span>
          <span class="scene-range" v-if="scene.target_chars">字数要求: {{ scene.target_chars[0] }}-{{ scene.target_chars[1] }}</span>
        </div>
        <div class="scene-item-body">
          <div class="scene-field">
            <span class="f-lbl">场次大纲目标</span>
            <p class="f-val">{{ scene.purpose }}</p>
          </div>
          <div class="scene-field-grid">
            <div class="scene-field">
              <span class="f-lbl">切入场景</span>
              <p class="f-val-light">{{ scene.entry }}</p>
            </div>
            <div class="scene-field">
              <span class="f-lbl">切出场景</span>
              <p class="f-val-light">{{ scene.exit }}</p>
            </div>
          </div>
          <div class="scene-field tags-group" v-if="scene.must_include?.length">
            <span class="f-lbl">本场必须引入的线索/道具/人物</span>
            <div class="tags-wrapper">
              <span v-for="t in scene.must_include" :key="t" class="tag-badge include">{{ t }}</span>
            </div>
          </div>
          <div class="scene-field tags-group" v-if="scene.must_not_include?.length">
            <span class="f-lbl">绝对不能透露/出现的设定</span>
            <div class="tags-wrapper">
              <span v-for="t in scene.must_not_include" :key="t" class="tag-badge exclude">{{ t }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-tab-state">
      <el-icon><InfoFilled /></el-icon>
      <p>暂无计划大纲数据</p>
    </div>

    <el-collapse class="raw-json-collapse">
      <el-collapse-item title="查看原始章节计划 JSON 数据" name="raw">
        <pre class="raw-json-pre">{{ JSON.stringify(plan, null, 2) }}</pre>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.plan-tab-content { display: flex; flex-direction: column; gap: 20px; }
.plan-summary-header {
  display: flex; justify-content: space-between; align-items: center;
  background: #fbf9f6; border: 1px solid var(--border-light);
  padding: 14px 20px; border-radius: 8px;
}
.plan-title-bold { font-weight: 700; color: #1a2129; }
.plan-words-target { font-size: 13px; color: var(--text-muted); }
.scenes-list { display: flex; flex-direction: column; gap: 16px; }
.scene-item-card {
  border: 1px solid var(--border-light); border-radius: 10px;
  background: var(--color-bg-surface); overflow: hidden; box-shadow: var(--shadow-sm);
}
.scene-item-header {
  display: flex; justify-content: space-between; align-items: center;
  background: #fafafa; padding: 12px 18px; border-bottom: 1px solid var(--border-light);
}
.scene-number { font-size: 13px; font-weight: 700; color: var(--primary); }
.scene-range { font-size: 12px; color: var(--text-muted); }
.scene-item-body { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.scene-field { display: flex; flex-direction: column; gap: 6px; }
.f-lbl { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
.f-val { font-size: 14px; line-height: 1.5; color: #1a2129; font-weight: 500; }
.f-val-light {
  font-size: 13px; line-height: 1.5; color: var(--text-main);
  background: #fcfcfc; padding: 8px 12px; border-radius: 6px; border: 1px solid #f0f0f0;
}
.scene-field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.tags-group { margin-top: 4px; }
.tags-wrapper { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 2px; }
.tag-badge { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
.tag-badge.include { background: #f0f9eb; color: #52c41a; border: 1px solid rgba(82, 196, 26, 0.2); }
.tag-badge.exclude { background: #fef0f0; color: #f56c6c; border: 1px solid rgba(245, 108, 108, 0.2); }

.raw-json-collapse { margin-top: 32px; border: 1px solid var(--border-light); border-radius: 8px; overflow: hidden; }
.raw-json-collapse :deep(.el-collapse-item__header) { padding: 0 16px; font-size: 12px; color: var(--text-muted); background-color: #fafafa; }
.raw-json-collapse :deep(.el-collapse-item__content) { padding: 16px; background-color: #f7f7f7; }
.raw-json-pre { font-family: var(--font-mono); font-size: 12px; color: #333333; white-space: pre-wrap; line-height: 1.5; }
.empty-tab-state {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 40px; border: 1px dashed var(--border-light); border-radius: 8px; color: var(--text-muted);
}
</style>
