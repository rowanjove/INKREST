import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useProjectStore } from './project'
import { ElMessage } from 'element-plus'

export interface TropeAtomItem {
  id: string
  name: string
  type: string
  category: string
  tags: string[]
  channels: string[]
  description: string
  parameters_schema: Record<string, any>
  requires: string[]
  recommended_with: string[]
  conflicts_with: string[]
  built_in: boolean
}

export interface TropeRecipeItem {
  id: string
  name: string
  channel: string
  category: string
  subcategory: string
  description: string
  tags: string[]
  atoms: string[]
  writing_guide: string
  built_in: boolean
}

export interface ValidationIssue {
  level: 'error' | 'warning' | 'suggestion'
  code: string
  message: string
  affected_atoms: string[]
  suggestion: string
}

export interface ValidationReport {
  is_valid: boolean
  issues: ValidationIssue[]
  completeness_score: number
  missing_elements: string[]
}

export interface RecommendationItem {
  atom_id: string
  name: string
  type: string
  score: number
  reason: string
}

export interface IncubatedSeed {
  id: string
  direction_title: string
  summary: string
  channel: string
  primary_genre: string
  mechanisms: string[]
  cool_points: string[]
  protagonist_name: string
  protagonist_archetype: string
  core_desire: string
  world_structure: string
  hook: string
}

export interface MutationVariant {
  mutation_level: string
  level_label: string
  headline: string
  description: string
  suggested_atoms: string[]
  novelty_twist: string
}

export interface DifferentiationSuggestion {
  category: string
  title: string
  advice: string
}

export interface UniquenessAnalysisReport {
  commonality_score: number
  uniqueness_score: number
  novelty_score: number
  crowdedness_score: number
  market_verdict: string
  suggestions: DifferentiationSuggestion[]
}

export interface StoryBlueprintData {
  schema_version: number
  id: string
  project_id: string
  title: string
  revision: number
  created_at: string
  updated_at: string
  dna: {
    channel: { id: string; label: string }
    genres: { primary: string; secondary: string[] }
    protagonist: { name: string; archetype: string; identity: string; core_desire: string; flaw: string }
    world: { structure: string; scarcity: string; power_system: string; core_conflict: string }
    mechanisms: Array<{ id: string; name: string; category: string; parameters: Record<string, any> }>
    core_conflict: string
    emotional_engines: Array<{ id: string; name: string; frequency: string }>
    narrative: { structure: string; viewpoint: string; pacing: string; style_tone: string }
  }
  selected_atoms: string[]
  selected_recipe_id: string
  parameters: Record<string, any>
  usp: {
    one_sentence_hook: string
    core_fantasy: string[]
    novelty_points: string[]
    reader_promise_summary: string
  }
  reader_promises: Array<{
    id: string
    promise_type: string
    description: string
    expected_interval: string
    payoff_stage: string
  }>
  pacing: {
    target_chapters: number
    rhythm_pattern: string
    volumes: Array<{
      volume_index: number
      title: string
      opening_hook: number
      climax_target: number
      cool_points: string[]
    }>
  }
  writing_guide_markdown: string
  outline_contract: Record<string, any>
  review_rules: Array<{ rule_id: string; target: string; description: string }>
}

export type WorkshopViewMode = 'builder' | 'inspiration' | 'graph' | 'pacing' | 'blueprint'

export const useBlueprintStore = defineStore('blueprintStore', () => {
  const projectStore = useProjectStore()

  const activeView = ref<WorkshopViewMode>('builder')
  const loading = ref(false)
  const compiling = ref(false)

  const channels = ref<TropeAtomItem[]>([])
  const genres = ref<TropeAtomItem[]>([])
  const mechanisms = ref<TropeAtomItem[]>([])
  const coolPoints = ref<TropeAtomItem[]>([])
  const recipes = ref<TropeRecipeItem[]>([])

  const selectedAtomIds = ref<string[]>(['male', 'xianxia', 'xitong', 'dalian'])
  const selectedRecipeId = ref<string>('')

  const userInputs = ref({
    title: '',
    protagonist_name: '李牧',
    protagonist_archetype: '坚毅果决的底层求道者',
    core_desire: '在残酷修仙界稳健生存并登临仙道绝巅',
    world_structure: '宗门割据、弱肉强食的弱法时代修真界',
    one_sentence_hook: '',
    target_chapters: 120,
    style_tone: '爽快紧凑、智斗为主',
  })

  const validationReport = ref<ValidationReport>({
    is_valid: true,
    issues: [],
    completeness_score: 100,
    missing_elements: [],
  })

  const recommendations = ref<RecommendationItem[]>([])
  const mechanismParams = ref<Record<string, Record<string, any>>>({})
  const compiledBlueprint = ref<StoryBlueprintData | null>(null)

  // Phase 2: 渐进式孵化、变异与独特性分析状态
  const incubatedSeeds = ref<IncubatedSeed[]>([])
  const incubating = ref(false)
  const mutationVariants = ref<MutationVariant[]>([])
  const mutating = ref(false)
  const uniquenessReport = ref<UniquenessAnalysisReport | null>(null)
  const analyzingUniqueness = ref(false)

  const allAtomsMap = computed(() => {
    const map = new Map<string, TropeAtomItem>()
    const all = [...channels.value, ...genres.value, ...mechanisms.value, ...coolPoints.value]
    all.forEach((item) => map.set(item.id, item))
    return map
  })

  async function fetchCatalog() {
    loading.value = true
    try {
      const [compRes, recRes] = await Promise.all([
        fetch('/api/blueprint/components'),
        fetch('/api/blueprint/recipes'),
      ])

      if (compRes.ok) {
        const data = await compRes.json()
        channels.value = data.channels || []
        genres.value = data.genres || []
        mechanisms.value = data.mechanisms || []
        coolPoints.value = data.cool_points || []
      }

      if (recRes.ok) {
        recipes.value = await recRes.json()
      }

      await validateSelection()
    } catch (e: any) {
      ElMessage.error(e?.message || '获取套路元件库失败')
    } finally {
      loading.value = false
    }
  }

  function toggleAtom(atomId: string) {
    const idx = selectedAtomIds.value.indexOf(atomId)
    if (idx >= 0) {
      selectedAtomIds.value.splice(idx, 1)
    } else {
      selectedAtomIds.value.push(atomId)
    }
    void validateSelection()
  }

  function addRecommendedAtom(atomId: string) {
    if (!selectedAtomIds.value.includes(atomId)) {
      selectedAtomIds.value.push(atomId)
      void validateSelection()
      ElMessage.success(`已添加推荐套路「${allAtomsMap.value.get(atomId)?.name || atomId}」`)
    }
  }

  function selectRecipe(recipe: TropeRecipeItem) {
    selectedRecipeId.value = recipe.id
    const newAtoms = new Set(selectedAtomIds.value)
    recipe.atoms.forEach((a) => newAtoms.add(a))
    selectedAtomIds.value = Array.from(newAtoms)
    if (!userInputs.value.title) {
      userInputs.value.title = recipe.name
    }
    void validateSelection()
    ElMessage.success(`已套用「${recipe.name}」套路配方`)
  }

  async function fetchRecommendations() {
    try {
      const res = await fetch('/api/blueprint/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_atoms: selectedAtomIds.value, limit: 5 }),
      })
      if (res.ok) {
        recommendations.value = await res.json()
      }
    } catch {
      // 容错处理
    }
  }

  async function analyzeUniqueness() {
    analyzingUniqueness.value = true
    try {
      const res = await fetch('/api/blueprint/analyze-uniqueness', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_atoms: selectedAtomIds.value }),
      })
      if (res.ok) {
        uniquenessReport.value = await res.json()
      }
    } catch {
      // 容错处理
    } finally {
      analyzingUniqueness.value = false
    }
  }

  async function validateSelection() {
    try {
      const res = await fetch('/api/blueprint/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_atoms: selectedAtomIds.value }),
      })
      if (res.ok) {
        validationReport.value = await res.json()
      }
      void fetchRecommendations()
      void analyzeUniqueness()
    } catch {
      // 容错处理
    }
  }

  async function incubateIdea(ideaText?: string) {
    const text = ideaText || userInputs.value.one_sentence_hook || ''
    incubating.value = true
    try {
      const res = await fetch('/api/blueprint/incubate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea: text }),
      })
      if (res.ok) {
        const data = await res.json()
        incubatedSeeds.value = data.seeds || []
        ElMessage.success('已生成 3 个故事方向')
      } else {
        ElMessage.error('灵感生成失败，请稍后重试')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '生成请求失败')
    } finally {
      incubating.value = false
    }
  }

  function adoptSeed(seed: IncubatedSeed) {
    // 1. 合并元件
    const newAtoms = new Set(selectedAtomIds.value)
    if (seed.channel) newAtoms.add(seed.channel)
    if (seed.primary_genre) {
      // 查找对应 genre atom，优先全等匹配
      const matchedGenre = genres.value.find(
        (g) => g.name === seed.primary_genre || g.id === seed.primary_genre,
      )
      if (matchedGenre) newAtoms.add(matchedGenre.id)
    }
    seed.mechanisms.forEach((m) => newAtoms.add(m))
    seed.cool_points.forEach((c) => newAtoms.add(c))
    selectedAtomIds.value = Array.from(newAtoms)

    // 2. 注入故事表单
    userInputs.value.title = seed.direction_title.replace(/^方向\s*[A-Z]：\s*/, '')
    userInputs.value.protagonist_name = seed.protagonist_name
    userInputs.value.protagonist_archetype = seed.protagonist_archetype
    userInputs.value.core_desire = seed.core_desire
    userInputs.value.world_structure = seed.world_structure
    userInputs.value.one_sentence_hook = seed.hook

    // 3. 校验并切换到积木模式
    void validateSelection()
    activeView.value = 'builder'
    ElMessage.success(`已导入「${seed.direction_title}」到故事工作台`)
  }

  async function mutateBlueprint(lockedDimensions?: string[]) {
    mutating.value = true
    try {
      const res = await fetch('/api/blueprint/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_atoms: selectedAtomIds.value,
          locked_dimensions: lockedDimensions || ['channel'],
        }),
      })
      if (res.ok) {
        const data = await res.json()
        mutationVariants.value = data.variants || []
        ElMessage.success('灵感变异方案已更新')
      } else {
        ElMessage.error('变异方案推演失败')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '请求出错')
    } finally {
      mutating.value = false
    }
  }

  function adoptMutationVariant(variant: MutationVariant) {
    if (variant.suggested_atoms && variant.suggested_atoms.length) {
      selectedAtomIds.value = [...variant.suggested_atoms]
      void validateSelection()
      ElMessage.success(`已套用「${variant.level_label}」设定`)
    }
  }

  async function compileBlueprint() {
    compiling.value = true
    try {
      const currentProjectId = projectStore.currentProject?.id || ''
      const payloadInputs = {
        ...userInputs.value,
        mechanism_params: mechanismParams.value,
      }
      const res = await fetch('/api/blueprint/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selected_atoms: selectedAtomIds.value,
          recipe_id: selectedRecipeId.value || undefined,
          user_inputs: payloadInputs,
          project_id: currentProjectId,
        }),
      })

      if (res.ok) {
        compiledBlueprint.value = await res.json()
        ElMessage.success('故事蓝图已生成')
        activeView.value = 'blueprint'
      } else {
        const err = await res.json()
        ElMessage.error(err.detail || '蓝图生成失败')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '生成蓝图请求出错')
    } finally {
      compiling.value = false
    }
  }

  async function applyToCurrentProject() {
    if (!projectStore.currentProject?.id) {
      ElMessage.warning('当前未选择作品，请先打开或新建作品')
      return
    }
    if (!compiledBlueprint.value) {
      await compileBlueprint()
    }
    if (!compiledBlueprint.value) return

    try {
      const res = await fetch('/api/blueprint/apply-to-project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blueprint: compiledBlueprint.value,
          project_id: projectStore.currentProject.id,
        }),
      })
      const result = await res.json()
      if (result.success) {
        ElMessage.success('已同步故事蓝图与写作指导至当前作品')
      } else {
        ElMessage.error(result.message || '同步失败')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '同步请求失败')
    }
  }

  return {
    activeView,
    loading,
    compiling,
    channels,
    genres,
    mechanisms,
    coolPoints,
    recipes,
    selectedAtomIds,
    selectedRecipeId,
    userInputs,
    validationReport,
    compiledBlueprint,
    recommendations,
    mechanismParams,
    incubatedSeeds,
    incubating,
    mutationVariants,
    mutating,
    uniquenessReport,
    analyzingUniqueness,
    addRecommendedAtom,
    fetchRecommendations,
    allAtomsMap,
    fetchCatalog,
    toggleAtom,
    selectRecipe,
    validateSelection,
    compileBlueprint,
    applyToCurrentProject,
    incubateIdea,
    adoptSeed,
    mutateBlueprint,
    adoptMutationVariant,
    analyzeUniqueness,
  }
})
