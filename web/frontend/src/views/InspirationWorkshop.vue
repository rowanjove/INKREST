<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  Check,
  CircleCheck,
  Collection,
  Cpu,
  DataLine,
  Document,
  DocumentCopy,
  MagicStick,
  Opportunity,
  Refresh,
  Share,
  Switch,
  TrendCharts,
  Warning,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useBlueprintStore, type WorkshopViewMode, type MutationVariant } from '../stores/blueprint'
import { useProjectStore } from '../stores/project'

const blueprintStore = useBlueprintStore()
const projectStore = useProjectStore()

const searchKeyword = ref('')
const activeCategoryTab = ref('mechanisms')

const showMutationDialog = ref(false)
const lockedMutationDimensions = ref<string[]>(['channel'])

const quickBrainstormIdeas = [
  '现代工程师穿越异界，以代码思维重构宗门大阵',
  '底层杂役靠因果天平交换寿元与情报，步步登仙',
  '精神病患者在规则怪谈里反客为主，打破试炼规则',
  '异界宗门引入第四天灾，降维对抗上古旧体制',
]

const viewTabs: Array<{ id: WorkshopViewMode; label: string; icon: any }> = [
  { id: 'builder', label: '核心设定', icon: Collection },
  { id: 'inspiration', label: '灵感推导', icon: Opportunity },
  { id: 'graph', label: '设定图谱', icon: Share },
  { id: 'pacing', label: '剧情节拍', icon: DataLine },
  { id: 'blueprint', label: '蓝图预览', icon: Document },
]

onMounted(() => {
  void blueprintStore.fetchCatalog()
})

function isSelected(id: string) {
  return blueprintStore.selectedAtomIds.includes(id)
}

function applyQuickIdea(idea: string) {
  blueprintStore.userInputs.one_sentence_hook = idea
  void blueprintStore.incubateIdea(idea)
}

function handleIncubate() {
  if (!blueprintStore.userInputs.one_sentence_hook.trim()) {
    ElMessage.warning('请先输入开书灵感或点击下方灵感参考')
    return
  }
  void blueprintStore.incubateIdea()
}

function openMutationDialog() {
  showMutationDialog.value = true
  if (!blueprintStore.mutationVariants.length) {
    void blueprintStore.mutateBlueprint(lockedMutationDimensions.value)
  }
}

function executeMutation() {
  void blueprintStore.mutateBlueprint(lockedMutationDimensions.value)
}

function handleAdoptMutation(variant: MutationVariant) {
  blueprintStore.adoptMutationVariant(variant)
  showMutationDialog.value = false
}

async function copyGuideText() {
  if (!blueprintStore.compiledBlueprint?.writing_guide_markdown) return
  try {
    await navigator.clipboard.writeText(blueprintStore.compiledBlueprint.writing_guide_markdown)
    ElMessage.success('已复制故事蓝图与写作指导书全文')
  } catch {
    ElMessage.error('复制失败，请手动选取复制')
  }
}

function updateMechanismParam(aid: string, key: string, val: unknown) {
  if (!blueprintStore.mechanismParams[aid]) {
    blueprintStore.mechanismParams[aid] = {}
  }
  blueprintStore.mechanismParams[aid][key] = val
}
</script>

<template>
  <div class="inspiration-workshop">
    <!-- 头部栏 -->
    <header class="workshop-header">
      <div class="header-left">
        <div class="title-with-badge">
          <el-icon class="brand-icon" :size="22"><Opportunity /></el-icon>
          <h2>灵感工坊</h2>
          <span class="sub-badge">Story Blueprint</span>
        </div>
        <p class="subtitle">
          将开书灵感、核心设定与经典套路，提炼为自洽可执行的故事蓝图与写作指南
        </p>
      </div>

      <div class="header-right">
        <el-tag v-if="projectStore.currentProject" type="success" effect="plain" class="project-tag">
          关联作品：{{ projectStore.currentProject.name }}
        </el-tag>
        <el-tag v-else type="info" effect="plain" class="project-tag">
          全局构思模式
        </el-tag>

        <!-- 模式切换 -->
        <el-radio-group v-model="blueprintStore.activeView" size="default">
          <el-radio-button
            v-for="tab in viewTabs"
            :key="tab.id"
            :value="tab.id"
          >
            <el-icon style="margin-right: 4px;"><component :is="tab.icon" /></el-icon>
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <!-- 工作台主体 -->
    <div class="workshop-body">
      <!-- 左侧：设定与套路库 -->
      <aside class="catalog-panel">
        <div class="panel-head">
          <h3>设定与套路库</h3>
          <el-button
            text
            size="small"
            :icon="Refresh"
            :loading="blueprintStore.loading"
            @click="blueprintStore.fetchCatalog"
          >
            刷新
          </el-button>
        </div>

        <el-input
          v-model="searchKeyword"
          placeholder="搜索设定、机制或爽点..."
          clearable
          size="small"
          class="catalog-search"
        />

        <!-- 成品配方快捷套用 -->
        <div v-if="blueprintStore.recipes.length" class="recipe-presets">
          <div class="section-sub-title">经典搭配推荐</div>
          <div class="recipe-chips">
            <button
              v-for="r in blueprintStore.recipes.slice(0, 8)"
              :key="r.id"
              type="button"
              class="recipe-chip"
              :class="{ active: blueprintStore.selectedRecipeId === r.id }"
              :title="r.description"
              @click="blueprintStore.selectRecipe(r)"
            >
              {{ r.name }}
            </button>
          </div>
        </div>

        <!-- 积木分类选项卡 -->
        <el-tabs v-model="activeCategoryTab" class="catalog-tabs">
          <el-tab-pane label="机制/金手指" name="mechanisms">
            <div class="atom-cards-scroll">
              <div
                v-for="m in blueprintStore.mechanisms"
                :key="m.id"
                class="atom-card"
                :class="{ selected: isSelected(m.id) }"
                @click="blueprintStore.toggleAtom(m.id)"
              >
                <div class="atom-card-title">
                  <span>{{ m.name }}</span>
                  <el-icon v-if="isSelected(m.id)" class="check-icon"><Check /></el-icon>
                </div>
                <p class="atom-card-desc">{{ m.description || '经典核心剧情推进机制' }}</p>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="核心爽点" name="cool_points">
            <div class="atom-cards-scroll">
              <div
                v-for="cp in blueprintStore.coolPoints"
                :key="cp.id"
                class="atom-card"
                :class="{ selected: isSelected(cp.id) }"
                @click="blueprintStore.toggleAtom(cp.id)"
              >
                <div class="atom-card-title">
                  <span>{{ cp.name }}</span>
                  <el-icon v-if="isSelected(cp.id)" class="check-icon"><Check /></el-icon>
                </div>
                <p class="atom-card-desc">{{ cp.description || '核心阅读快感与情绪引擎' }}</p>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="题材外壳" name="genres">
            <div class="atom-cards-scroll">
              <div
                v-for="g in blueprintStore.genres"
                :key="g.id"
                class="atom-card"
                :class="{ selected: isSelected(g.id) }"
                @click="blueprintStore.toggleAtom(g.id)"
              >
                <div class="atom-card-title">
                  <span>{{ g.name }}</span>
                  <el-icon v-if="isSelected(g.id)" class="check-icon"><Check /></el-icon>
                </div>
                <p class="atom-card-desc">{{ g.description || '故事背景与世界设定分类' }}</p>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="频道受众" name="channels">
            <div class="atom-cards-scroll">
              <div
                v-for="c in blueprintStore.channels"
                :key="c.id"
                class="atom-card"
                :class="{ selected: isSelected(c.id) }"
                @click="blueprintStore.toggleAtom(c.id)"
              >
                <div class="atom-card-title">
                  <span>{{ c.name }}</span>
                  <el-icon v-if="isSelected(c.id)" class="check-icon"><Check /></el-icon>
                </div>
                <p class="atom-card-desc">{{ c.description || '读者受众群' }}</p>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </aside>

      <!-- 中部：工作台主操作区 -->
      <main class="workbench-main">
        <!-- 1. 核心设定 -->
        <div v-if="blueprintStore.activeView === 'builder'" class="view-container">
          <div class="section-banner">
            <h3>故事核心设定（Story Blueprint）</h3>
            <p>在此设定主角人设、核心机制、世界规则与开篇看点，系统将实时检查设定自洽性与潜在冲突。</p>
          </div>

          <!-- 已选设定池 -->
          <div class="selected-pool">
            <div class="pool-header">
              <div class="pool-title-group">
                <span>已选设定元素 ({{ blueprintStore.selectedAtomIds.length }})</span>
                <small>点击标签可移除</small>
              </div>
              <el-button
                size="small"
                type="warning"
                plain
                :icon="Switch"
                @click="openMutationDialog"
              >
                灵感变异推演
              </el-button>
            </div>
            <div class="pool-chips">
              <el-tag
                v-for="id in blueprintStore.selectedAtomIds"
                :key="id"
                closable
                effect="light"
                class="atom-tag"
                @close="blueprintStore.toggleAtom(id)"
              >
                {{ blueprintStore.allAtomsMap.get(id)?.name || id }}
              </el-tag>
              <span v-if="!blueprintStore.selectedAtomIds.length" class="empty-hint">
                从左侧库挑选设定元素，或直接点击上方经典搭配
              </span>
            </div>
          </div>

          <!-- 搭配推荐 -->
          <div v-if="blueprintStore.recommendations.length" class="recommendations-bar">
            <div class="rec-header">
              <span class="rec-title">搭配建议：</span>
              <small>根据当前已选设定，推荐契合的常用机制与爽点：</small>
            </div>
            <div class="rec-chips">
              <button
                v-for="rec in blueprintStore.recommendations"
                :key="rec.atom_id"
                type="button"
                class="rec-btn"
                :title="rec.reason"
                @click="blueprintStore.addRecommendedAtom(rec.atom_id)"
              >
                <span class="rec-btn-name">+ {{ rec.name }}</span>
                <span class="rec-btn-score">{{ rec.score }}%</span>
              </button>
            </div>
          </div>

          <!-- 故事参数表单 -->
          <el-form label-position="top" class="story-form">
            <div class="form-row-2">
              <el-form-item label="故事书名">
                <el-input v-model="blueprintStore.userInputs.title" placeholder="如：凡人长生模拟器" />
              </el-form-item>
              <el-form-item label="主角姓名">
                <el-input v-model="blueprintStore.userInputs.protagonist_name" placeholder="主角姓名" />
              </el-form-item>
            </div>

            <div class="form-row-2">
              <el-form-item label="主角人设与起点">
                <el-input
                  v-model="blueprintStore.userInputs.protagonist_archetype"
                  placeholder="如：资质平平却心志坚毅的底层散修"
                />
              </el-form-item>
              <el-form-item label="核心动机与目标">
                <el-input
                  v-model="blueprintStore.userInputs.core_desire"
                  placeholder="如：打破寿元大限，步步求索真仙"
                />
              </el-form-item>
            </div>

            <el-form-item label="世界背景与核心法则">
              <el-input
                v-model="blueprintStore.userInputs.world_structure"
                placeholder="如：各大宗门垄断筑基丹与灵脉资源，底层修士晋升通道受阻"
              />
            </el-form-item>

            <el-form-item label="核心看点 / 一句话简介">
              <el-input
                v-model="blueprintStore.userInputs.one_sentence_hook"
                type="textarea"
                :rows="2"
                placeholder="如：资质平平的杂役弟子，在获得因果模拟推演后，在危机重重的魔道宗门步步破局。"
              />
            </el-form-item>

            <div class="form-row-2">
              <el-form-item label="规划篇幅（章）">
                <el-input-number
                  v-model="blueprintStore.userInputs.target_chapters"
                  :min="20"
                  :max="2000"
                  :step="50"
                />
              </el-form-item>
              <el-form-item label="基调风格">
                <el-input
                  v-model="blueprintStore.userInputs.style_tone"
                  placeholder="如：爽快利落、智斗稳健、高潮反打彻底"
                />
              </el-form-item>
            </div>

            <!-- 参数化机制专属配置 -->
            <template
              v-for="aid in blueprintStore.selectedAtomIds"
              :key="'param-group-' + aid"
            >
              <div
                v-if="blueprintStore.allAtomsMap.get(aid)?.parameters_schema?.fields?.length"
                class="param-card"
              >
                <div class="param-card-head">
                  <strong>{{ blueprintStore.allAtomsMap.get(aid)?.name }} 规则与参数设定</strong>
                  <small>{{ blueprintStore.allAtomsMap.get(aid)?.parameters_schema.description }}</small>
                </div>
                <div class="param-fields-grid">
                  <div
                    v-for="field in blueprintStore.allAtomsMap.get(aid)?.parameters_schema.fields"
                    :key="field.key"
                    class="param-field"
                  >
                    <div class="field-top">
                      <span class="field-label">{{ field.label }}</span>
                      <el-switch
                        v-if="field.type === 'boolean'"
                        :model-value="blueprintStore.mechanismParams[aid]?.[field.key] ?? field.default"
                        @update:model-value="(val: unknown) => updateMechanismParam(aid, field.key, val)"
                      />
                      <el-select
                        v-else-if="field.type === 'select'"
                        :model-value="blueprintStore.mechanismParams[aid]?.[field.key] ?? field.default"
                        size="small"
                        class="field-select"
                        @update:model-value="(val: unknown) => updateMechanismParam(aid, field.key, val)"
                      >
                        <el-option
                          v-for="opt in field.options"
                          :key="opt"
                          :label="opt"
                          :value="opt"
                        />
                      </el-select>
                    </div>
                    <small class="field-hint">{{ field.hint }}</small>
                  </div>
                </div>
              </div>
            </template>
          </el-form>

          <!-- 变异推演对话框 -->
          <el-dialog
            v-model="showMutationDialog"
            title="灵感变异与破局推演"
            width="680px"
            destroy-on-close
          >
            <div class="mutation-dialog-body">
              <div class="mutation-controls">
                <span class="control-label">保持不变的维度：</span>
                <el-checkbox-group v-model="lockedMutationDimensions" size="small">
                  <el-checkbox-button value="channel">锁定频道</el-checkbox-button>
                  <el-checkbox-button value="genre">锁定题材</el-checkbox-button>
                  <el-checkbox-button value="mechanisms">锁定核心机制</el-checkbox-button>
                </el-checkbox-group>
                <el-button
                  type="primary"
                  size="small"
                  :loading="blueprintStore.mutating"
                  :icon="Refresh"
                  @click="executeMutation"
                >
                  重新生成方案
                </el-button>
              </div>

              <div class="mutation-variants-list">
                <div
                  v-for="variant in blueprintStore.mutationVariants"
                  :key="variant.mutation_level"
                  class="mutation-variant-card"
                  :class="variant.mutation_level"
                >
                  <div class="variant-head">
                    <div class="variant-badge">{{ variant.level_label }}</div>
                    <strong class="variant-headline">{{ variant.headline }}</strong>
                  </div>
                  <p class="variant-desc">{{ variant.description }}</p>
                  <div class="variant-twist">
                    <span class="twist-tag">差异化切入点：</span>
                    <span>{{ variant.novelty_twist }}</span>
                  </div>
                  <div class="variant-atoms">
                    <span class="twist-tag">推荐组合：</span>
                    <el-tag
                      v-for="aid in variant.suggested_atoms"
                      :key="aid"
                      size="small"
                      effect="plain"
                    >
                      {{ blueprintStore.allAtomsMap.get(aid)?.name || aid }}
                    </el-tag>
                  </div>
                  <div class="variant-foot">
                    <el-button
                      type="primary"
                      size="small"
                      @click="handleAdoptMutation(variant)"
                    >
                      套用此变异设定
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-dialog>
        </div>

        <!-- 2. 灵感推导 -->
        <div v-else-if="blueprintStore.activeView === 'inspiration'" class="view-container">
          <div class="section-banner">
            <h3>灵感推导与开书脑洞</h3>
            <p>输入一句简单的开书灵感，系统将从不同视角梳理出 3 个故事方向、主角人设与核心看点。</p>
          </div>

          <div class="snowflake-card">
            <h4>开书构思 / 脑洞输入</h4>
            <el-input
              v-model="blueprintStore.userInputs.one_sentence_hook"
              type="textarea"
              :rows="3"
              placeholder="在此随手写下一句开书构想（例如：现代工程师穿越异界，以代码思维重构宗门大阵）..."
            />

            <!-- 灵感参考标签 -->
            <div class="quick-brainstorm-tags">
              <span class="quick-label">灵感参考：</span>
              <el-tag
                v-for="(spark, sidx) in quickBrainstormIdeas"
                :key="sidx"
                class="clickable-spark"
                effect="plain"
                size="small"
                @click="applyQuickIdea(spark)"
              >
                {{ spark }}
              </el-tag>
            </div>

            <div class="card-action-bar">
              <el-button
                type="primary"
                :icon="MagicStick"
                :loading="blueprintStore.incubating"
                @click="handleIncubate"
              >
                推导演化 3 个故事方向
              </el-button>
            </div>
          </div>

          <!-- 孵化出的 3 个故事种子卡片 -->
          <div v-if="blueprintStore.incubatedSeeds.length" class="incubated-seeds-container">
            <div class="section-sub-title">故事构思方向（点击可直接导入至故事工作台）</div>
            <div class="seeds-grid">
              <div
                v-for="seed in blueprintStore.incubatedSeeds"
                :key="seed.id"
                class="seed-card"
              >
                <div class="seed-card-head">
                  <div class="seed-title">{{ seed.direction_title }}</div>
                  <el-tag size="small" type="success">{{ seed.primary_genre }}</el-tag>
                </div>
                <p class="seed-summary">{{ seed.summary }}</p>
                <div class="seed-details">
                  <div class="detail-row">
                    <span class="detail-label">主角人设：</span>
                    <span class="detail-val"><strong>{{ seed.protagonist_name }}</strong> · {{ seed.protagonist_archetype }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">核心动机：</span>
                    <span class="detail-val">{{ seed.core_desire }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">世界背景：</span>
                    <span class="detail-val">{{ seed.world_structure }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">开篇看点：</span>
                    <span class="detail-val">{{ seed.hook }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">推荐设定：</span>
                    <div class="seed-atom-tags">
                      <el-tag
                        v-for="m in [...seed.mechanisms, ...seed.cool_points]"
                        :key="m"
                        size="small"
                        effect="light"
                      >
                        {{ blueprintStore.allAtomsMap.get(m)?.name || m }}
                      </el-tag>
                    </div>
                  </div>
                </div>
                <div class="seed-action">
                  <el-button
                    type="primary"
                    size="small"
                    :icon="Check"
                    @click="blueprintStore.adoptSeed(seed)"
                  >
                    采纳该构思并进入工作台
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. 设定图谱 (Graph) -->
        <div v-else-if="blueprintStore.activeView === 'graph'" class="view-container">
          <div class="section-banner">
            <h3>设定关联图谱</h3>
            <p>可视化展示核心机制与爽点之间的关联与张力关系。</p>
          </div>

          <div class="graph-placeholder">
            <div class="graph-nodes-mock">
              <div
                v-for="id in blueprintStore.selectedAtomIds"
                :key="id"
                class="graph-node-box"
              >
                <div class="node-title">{{ blueprintStore.allAtomsMap.get(id)?.name || id }}</div>
                <div class="node-type">{{ blueprintStore.allAtomsMap.get(id)?.type || '设定' }}</div>
              </div>
            </div>
            <div class="graph-hint">
              当前已关联 {{ blueprintStore.selectedAtomIds.length }} 项设定，逻辑自洽，未检测到剧情死锁或冲突。
            </div>
          </div>
        </div>

        <!-- 4. 剧情节拍 (Pacing) -->
        <div v-else-if="blueprintStore.activeView === 'pacing'" class="view-container">
          <div class="section-banner">
            <h3>剧情节拍与情绪节奏</h3>
            <p>规划各卷起承转合、读者期待兑现周期与高潮分布。</p>
          </div>

          <!-- 读者承诺 -->
          <div class="promises-box">
            <div class="promises-head">
              <strong>读者核心期待与兑现周期</strong>
              <small>系统将结合章节进度提醒高潮与回报节奏，防止剧情持续平淡</small>
            </div>
            <div class="promises-grid">
              <div class="promise-item">
                <div class="promise-badge">实力成长与阶段回报</div>
                <div class="promise-desc">主角实力、地位或信息差在关键剧情节点产生明确质变</div>
                <div class="promise-interval">预期兑现周期：约每 5-10 章</div>
              </div>
              <div class="promise-item">
                <div class="promise-badge">对抗反转与反击爆发</div>
                <div class="promise-desc">前置铺垫的敌对压迫必须在对应高潮完成彻底反转，情绪释放彻底</div>
                <div class="promise-interval">预期兑现周期：约每 3-6 章</div>
              </div>
            </div>
          </div>

          <div class="pacing-cards-list">
            <div class="pacing-card">
              <div class="pacing-card-head">
                <strong>第一卷：破局立足</strong>
                <div class="pacing-badges">
                  <el-tag size="small" type="success">开篇吸引力: 9/10</el-tag>
                  <el-tag size="small" type="warning">高潮目标: 9/10</el-tag>
                </div>
              </div>
              <p>黄金开篇抛出悬念与金手指机制，解决生存危机，首次结算核心收益。</p>
              <div class="intensity-bar"><div class="bar-fill" style="width: 90%;"></div></div>
            </div>
            <div class="pacing-card">
              <div class="pacing-card-head">
                <strong>第二卷：锋芒毕露</strong>
                <div class="pacing-badges">
                  <el-tag size="small" type="info">起步沉淀: 7/10</el-tag>
                  <el-tag size="small" type="danger">高潮目标: 10/10</el-tag>
                </div>
              </div>
              <p>进入更大地图或组织考核，实力爆发彻底击溃前置压迫势力，引出深层世界悬念。</p>
              <div class="intensity-bar"><div class="bar-fill bar-fill--high" style="width: 100%;"></div></div>
            </div>
          </div>
        </div>

        <!-- 5. 蓝图预览 (Blueprint) -->
        <div v-else-if="blueprintStore.activeView === 'blueprint'" class="view-container">
          <div class="section-banner-with-actions">
            <div>
              <h3>故事蓝图预览 (Story Blueprint)</h3>
              <p>已生成的故事蓝图与写作指导，包含可直接指导下游正文创作的情节契约与设定红线。</p>
            </div>
            <div v-if="blueprintStore.compiledBlueprint" class="banner-btns">
              <el-button
                size="small"
                :icon="DocumentCopy"
                @click="copyGuideText"
              >
                复制指导书全文
              </el-button>
            </div>
          </div>

          <div v-if="blueprintStore.compiledBlueprint" class="blueprint-preview-box">
            <pre class="markdown-preview">{{ blueprintStore.compiledBlueprint.writing_guide_markdown }}</pre>
          </div>
          <div v-else class="empty-state">
            <el-empty description="尚未生成蓝图，请先在工作台挑选设定并点击底部「生成故事蓝图」" />
          </div>
        </div>
      </main>

      <!-- 右侧：诊断与建议面板 -->
      <aside class="diagnostics-panel">
        <div class="panel-head">
          <h3>设定健康度与题材透视</h3>
        </div>

        <!-- 完整度进度 -->
        <div class="score-card">
          <div class="score-value">
            <span class="num">{{ blueprintStore.validationReport.completeness_score }}</span>
            <span class="unit">%</span>
          </div>
          <div class="score-label">设定完整度</div>
        </div>

        <!-- 市场独创性与赛道透视 -->
        <div v-if="blueprintStore.uniquenessReport" class="uniqueness-box">
          <div class="sub-label">市场辨识度与题材透视：</div>
          <div class="uniqueness-metrics">
            <div class="metric-item">
              <div class="metric-head">
                <span class="m-label">辨识度</span>
                <span class="m-score">{{ blueprintStore.uniquenessReport.uniqueness_score }}分</span>
              </div>
              <el-progress
                :percentage="blueprintStore.uniquenessReport.uniqueness_score"
                :show-text="false"
                :color="blueprintStore.uniquenessReport.uniqueness_score > 60 ? '#67c23a' : '#e6a23c'"
              />
            </div>
            <div class="metric-item">
              <div class="metric-head">
                <span class="m-label">题材拥挤度</span>
                <span class="m-score">{{ blueprintStore.uniquenessReport.crowdedness_score }}分</span>
              </div>
              <el-progress
                :percentage="blueprintStore.uniquenessReport.crowdedness_score"
                :show-text="false"
                :color="blueprintStore.uniquenessReport.crowdedness_score > 70 ? '#f56c6c' : '#409eff'"
              />
            </div>
          </div>

          <div class="market-verdict-card">
            <el-icon class="verdict-icon"><TrendCharts /></el-icon>
            <span class="verdict-text">{{ blueprintStore.uniquenessReport.market_verdict }}</span>
          </div>

          <!-- 4 类反套路破局建议 -->
          <div v-if="blueprintStore.uniquenessReport.suggestions.length" class="suggestions-section">
            <div class="sub-label-mini">题材破局建议：</div>
            <div class="diff-suggestions-list">
              <div
                v-for="(sug, sidx) in blueprintStore.uniquenessReport.suggestions"
                :key="sidx"
                class="diff-sug-item"
              >
                <div class="sug-head">
                  <span class="sug-cat-tag">{{ sug.category === 'protagonist' ? '人设反差' : sug.category === 'mechanism' ? '机制微调' : sug.category === 'narrative' ? '叙事视角' : '设定杂交' }}</span>
                  <strong class="sug-title">{{ sug.title }}</strong>
                </div>
                <p class="sug-advice">{{ sug.advice }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 缺失要素提示 -->
        <div v-if="blueprintStore.validationReport.missing_elements.length" class="missing-box">
          <div class="sub-label">缺少核心维度：</div>
          <div class="missing-tags">
            <el-tag
              v-for="item in blueprintStore.validationReport.missing_elements"
              :key="item"
              type="info"
              size="small"
            >
              {{ item }}
            </el-tag>
          </div>
        </div>

        <!-- 冲突与提示列表 -->
        <div class="issues-list">
          <div class="sub-label">设定自洽性检测：</div>
          <div
            v-for="(issue, idx) in blueprintStore.validationReport.issues"
            :key="idx"
            class="issue-item"
            :class="issue.level"
          >
            <div class="issue-header">
              <el-icon v-if="issue.level === 'error'"><Warning /></el-icon>
              <el-icon v-else-if="issue.level === 'warning'"><Warning /></el-icon>
              <el-icon v-else><CircleCheck /></el-icon>
              <span>{{ issue.message }}</span>
            </div>
            <p v-if="issue.suggestion" class="issue-suggestion">建议：{{ issue.suggestion }}</p>
          </div>

          <div v-if="!blueprintStore.validationReport.issues.length" class="all-good">
            <el-icon :size="20" color="#67c23a"><CircleCheck /></el-icon>
            <span>当前设定组合自洽，未发现冲突点。</span>
          </div>
        </div>
      </aside>
    </div>

    <!-- 底部常驻操作栏 -->
    <footer class="workshop-footer">
      <div class="footer-left">
        <span class="footer-summary">
          已选 {{ blueprintStore.selectedAtomIds.length }} 项设定 · 设定完整度 {{ blueprintStore.validationReport.completeness_score }}%
        </span>
      </div>

      <div class="footer-right">
        <el-button
          :icon="Refresh"
          @click="blueprintStore.validateSelection"
        >
          重新检查
        </el-button>
        <el-button
          type="primary"
          :icon="Cpu"
          :loading="blueprintStore.compiling"
          @click="blueprintStore.compileBlueprint"
        >
          生成故事蓝图
        </el-button>
        <el-button
          v-if="projectStore.currentProject"
          type="success"
          :icon="Check"
          @click="blueprintStore.applyToCurrentProject"
        >
          同步至当前作品
        </el-button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.inspiration-workshop {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: calc(100vh - 40px);
  background: var(--color-bg-base);
  color: var(--color-text-main);
}

.workshop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-with-badge h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.brand-icon {
  color: var(--color-primary);
}

.sub-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-primary-soft, rgba(64, 158, 255, 0.1));
  color: var(--color-primary);
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-tag {
  font-weight: 500;
}

/* 主体三栏布局 */
.workshop-body {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 300px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 左侧元件库 */
.catalog-panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  padding: 16px;
  gap: 12px;
  overflow-y: auto;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}

.catalog-search {
  margin-bottom: 4px;
}

.section-sub-title {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 6px;
  font-weight: 600;
}

.recipe-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.recipe-chip {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-base);
  color: var(--color-text-main);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.recipe-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.recipe-chip.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.atom-cards-scroll {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 450px;
  overflow-y: auto;
  padding-right: 4px;
}

.atom-card {
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-base);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.atom-card:hover {
  border-color: var(--color-primary-light);
}

.atom-card.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft, rgba(64, 158, 255, 0.08));
}

.atom-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.check-icon {
  color: var(--color-primary);
}

.atom-card-desc {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* 中间主工作台 */
.workbench-main {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 24px;
  background: var(--color-bg-base);
}

.section-banner {
  margin-bottom: 20px;
}

.section-banner h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 700;
}

.section-banner p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.selected-pool {
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  margin-bottom: 20px;
}

.pool-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-muted);
}

.pool-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.atom-tag {
  font-size: 12px;
}

.empty-hint {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.story-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.story-form :deep(.el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
  padding-bottom: 4px;
}

/* 灵感模式卡片 */
.snowflake-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.snowflake-card h4 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 650;
}

.card-action-bar {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

/* 图谱模式占位 */
.graph-placeholder {
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  background: var(--color-bg-surface);
}

.graph-nodes-mock {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  margin-bottom: 16px;
}

.graph-node-box {
  padding: 10px 16px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary-soft, rgba(64, 158, 255, 0.1));
  border-radius: 6px;
}

.node-title {
  font-size: 13px;
  font-weight: 600;
}

.node-type {
  font-size: 10px;
  color: var(--color-text-muted);
}

.graph-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 节奏模式卡片 */
.pacing-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pacing-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.pacing-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.pacing-card p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 推荐栏样式 */
.recommendations-bar {
  padding: 12px;
  border: 1px dashed var(--color-primary-light);
  border-radius: 8px;
  background: var(--color-primary-soft, rgba(64, 158, 255, 0.05));
  margin-bottom: 20px;
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-bottom: 8px;
}

.rec-title {
  font-weight: 650;
  color: var(--color-primary);
}

.rec-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rec-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--color-primary);
  border-radius: 14px;
  background: var(--color-bg-base);
  color: var(--color-text-main);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.rec-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.rec-btn-score {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 8px;
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
  font-weight: 700;
}

/* 参数化机制配置卡片 */
.param-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  margin-bottom: 16px;
}

.param-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.param-fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.param-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
}

.field-select {
  width: 140px;
}

.field-hint {
  font-size: 11px;
  color: var(--color-text-muted);
}

/* 读者承诺 */
.promises-box {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  margin-bottom: 16px;
}

.promises-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 12px;
}

.promises-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.promise-item {
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-base);
}

.promise-badge {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 4px;
}

.promise-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-bottom: 6px;
}

.promise-interval {
  font-size: 10px;
  color: #e6a23c;
  font-weight: 600;
}

/* 节奏波形 */
.pacing-badges {
  display: flex;
  gap: 6px;
}

.intensity-bar {
  margin-top: 8px;
  height: 6px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: #e6a23c;
  border-radius: 3px;
}

.bar-fill--high {
  background: #f56c6c;
}

.section-banner-with-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* 蓝图预览 */
.blueprint-preview-box {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.markdown-preview {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
}

/* 右侧诊断面板 */
.diagnostics-panel {
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  padding: 16px;
  gap: 16px;
  overflow-y: auto;
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-base);
}

.score-value {
  display: flex;
  align-items: baseline;
  color: var(--color-primary);
}

.score-value .num {
  font-size: 32px;
  font-weight: 800;
}

.score-value .unit {
  font-size: 14px;
  font-weight: 600;
  margin-left: 2px;
}

.score-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.missing-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.missing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sub-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  border: 1px solid transparent;
}

.issue-item.warning {
  background: rgba(230, 162, 60, 0.1);
  border-color: rgba(230, 162, 60, 0.2);
  color: #e6a23c;
}

.issue-item.error {
  background: rgba(245, 108, 108, 0.1);
  border-color: rgba(245, 108, 108, 0.2);
  color: #f56c6c;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.issue-suggestion {
  margin: 4px 0 0 20px;
  font-size: 11px;
  opacity: 0.9;
}

.all-good {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 6px;
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
  font-size: 12px;
  font-weight: 500;
}

/* 底部操作栏 */
.workshop-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.footer-summary {
  font-size: 12px;
  color: var(--color-text-muted);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Phase 2: 变异推演、渐进式种子与独创性透视样式 */
.pool-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-brainstorm-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.quick-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.clickable-spark {
  cursor: pointer;
  transition: all 0.2s;
}

.clickable-spark:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  transform: translateY(-1px);
}

.incubated-seeds-container {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.seeds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.seed-card {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 10px);
  padding: 16px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.seed-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.seed-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.seed-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--color-text-strong, #0f172a);
}

.seed-summary {
  font-size: 12px;
  color: var(--color-text, #334155);
  line-height: 1.55;
  margin-bottom: 12px;
  background: var(--color-bg-app, #f8fafc);
  border: 1px solid var(--color-border-subtle, #edf0f4);
  padding: 9px 12px;
  border-radius: 8px;
}

.seed-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  flex: 1;
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.detail-label {
  color: var(--color-text-muted, #64748b);
  white-space: nowrap;
  font-weight: 500;
}

.detail-val {
  color: var(--color-text, #334155);
  line-height: 1.45;
}

.seed-atom-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.seed-action {
  margin-top: auto;
}

.seed-action .el-button {
  width: 100%;
}

/* 变异推演对话框样式 */
.mutation-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mutation-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-app, #f8fafc);
  border: 1px solid var(--color-border-subtle, #edf0f4);
  padding: 10px 14px;
  border-radius: var(--radius-md, 10px);
}

.control-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
}

.mutation-variants-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mutation-variant-card {
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 10px);
  padding: 14px 16px;
  background: var(--color-bg-surface, #ffffff);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mutation-variant-card.conservative {
  border-left: 4px solid #16a34a;
}

.mutation-variant-card.moderate {
  border-left: 4px solid var(--color-primary, #c66f4f);
}

.mutation-variant-card.radical {
  border-left: 4px solid #d97706;
}

.variant-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.variant-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--color-bg-app, #f1f5f9);
  color: var(--color-text-muted, #64748b);
  font-weight: 600;
}

.variant-headline {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong, #0f172a);
}

.variant-desc {
  font-size: 12.5px;
  color: var(--color-text, #334155);
  line-height: 1.5;
  margin: 0;
}

.variant-twist, .variant-atoms {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.twist-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
}

.variant-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

/* 诊断面板中的独创性与赛道透视 */
.uniqueness-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 10px);
  background: var(--color-bg-app, #f8fafc);
}

.uniqueness-metrics {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
}

.m-label {
  color: var(--color-text-muted, #64748b);
}

.m-score {
  font-weight: 700;
  color: var(--color-text-strong, #0f172a);
}

.market-verdict-card {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11.5px;
  line-height: 1.45;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--color-primary-soft, #fff5f0);
  border: 1px solid rgba(198, 111, 79, 0.2);
  color: var(--color-primary, #c66f4f);
}

.verdict-icon {
  margin-top: 2px;
}

.suggestions-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.sub-label-mini {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
}

.diff-suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diff-sug-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm, 7px);
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sug-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sug-cat-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
  font-weight: 600;
}

.sug-title {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--color-text-strong, #0f172a);
}

.sug-advice {
  font-size: 11px;
  color: var(--color-text-muted, #64748b);
  line-height: 1.4;
  margin: 0;
}
</style>
