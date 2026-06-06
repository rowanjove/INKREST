<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAsset, updateAsset } from '../api'
import RulesAssetEditor from './RulesAssetEditor.vue'
import MarkdownAssetEditor from './MarkdownAssetEditor.vue'
import SensitiveWordsConfig from './SensitiveWordsConfig.vue'

const expanded = ref(false)
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('style')

const styleGuideContent = ref('')
const rulesContent = ref('')
const sensitiveWordsContent = ref('')

const loadData = async () => {
  loading.value = true
  try {
    const [styleRes, rulesRes, wordsRes] = await Promise.all([
      getAsset('style_guide'),
      getAsset('rules'),
      getAsset('sensitive_words'),
    ])
    styleGuideContent.value = styleRes.data.content || ''
    rulesContent.value = rulesRes.data.content || ''
    sensitiveWordsContent.value = wordsRes.data.content || ''
  } catch (error: any) {
    ElMessage.error('获取写作规范失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await Promise.all([
      updateAsset('style_guide', styleGuideContent.value),
      updateAsset('rules', rulesContent.value),
      updateAsset('sensitive_words', sensitiveWordsContent.value),
    ])
    ElMessage.success('写作规范已保存，下一章生成/审校将使用新配置')
  } catch (error: any) {
    ElMessage.error('保存写作规范失败: ' + (error.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <section id="writing-rules" class="fold-card writing-rules-config">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>写作规范</h2>
          <p>风格指南、结构化规则与敏感词库。保存后对当前项目的写作与审校生效。</p>
        </div>
      </div>
      <el-button
        v-show="expanded"
        class="fold-action"
        type="primary"
        size="small"
        :loading="saving"
        @click.stop="handleSave"
      >
        保存规范
      </el-button>
    </div>

    <div v-show="expanded" class="fold-body writing-rules-body" v-loading="loading">
      <el-alert type="info" :closable="false" class="rules-overview">
        <template #title>三块分工（避免填错位置）</template>
        <ul class="overview-list">
          <li><strong>风格指南</strong>：整体文风、视角、节奏、对话习惯 → 进入 Agent 上下文。</li>
          <li><strong>写作规则</strong>：禁用词/句式、常用表达、手法与<strong>对标作者</strong> → 拼进写作提示词。</li>
          <li><strong>敏感词库</strong>：审校阶段<strong>硬扫描</strong>，命中会记入敏感词报告（与禁用词互补，不重复填同一批词即可）。</li>
        </ul>
        <p class="overview-foot">剧情设定库里的资产编辑也能改这些文件；以本页保存为准。修改后建议新开一章或重跑审校验证效果。</p>
      </el-alert>

      <el-tabs v-model="activeTab" type="border-card" class="rules-tabs">
        <el-tab-pane label="风格指南" name="style">
          <p class="tab-lead">
            对应 <code>assets/style_guide.md</code>。描述「怎么写」，适合长文说明与 Markdown 结构。
          </p>
          <MarkdownAssetEditor
            v-model="styleGuideContent"
            title="风格指南"
            path="assets/style_guide.md"
            @save="handleSave"
          />
        </el-tab-pane>
        <el-tab-pane label="写作规则" name="rules">
          <p class="tab-lead">
            对应 <code>assets/rules.yaml</code>。禁用词/句式会约束模型措辞；对标作者会写入提示词（借鉴气质，非照抄剧情）。
          </p>
          <RulesAssetEditor v-model="rulesContent" />
        </el-tab-pane>
        <el-tab-pane label="敏感词库" name="sensitive">
          <SensitiveWordsConfig v-model="sensitiveWordsContent" />
        </el-tab-pane>
      </el-tabs>

      <div class="save-bar">
        <span class="save-hint">三处修改需点击保存后才会写入项目资产</span>
        <el-button type="primary" :loading="saving" @click="handleSave">保存全部修改</el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.writing-rules-config {
  margin-bottom: 12px;
}

.writing-rules-body {
  padding: 12px 18px 18px;
}

.rules-overview {
  margin-bottom: 14px;
}

.overview-list {
  margin: 8px 0 0;
  padding-left: 1.2em;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.overview-list li {
  margin-bottom: 4px;
}

.overview-foot {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--color-text-subtle);
  line-height: 1.45;
}

.rules-tabs {
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
}

.tab-lead {
  margin: 0 0 12px;
  padding: 0 4px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.tab-lead code {
  font-size: 12px;
}

.save-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-subtle);
}

.save-hint {
  font-size: 12px;
  color: var(--color-text-subtle);
}
</style>