<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOutline } from '../../api'
import { isLongFormScale } from '../../utils/projectReadiness'

const PENDING_KEY = 'inkrest_pending_guide'

const props = defineProps<{
  projectId: string
}>()

const router = useRouter()
const route = useRoute()
const dialogVisible = ref(false)

const storageKey = computed(() => `first_book_guide_${props.projectId}`)

const dismissed = () => {
  try {
    return localStorage.getItem(storageKey.value) === '1'
  } catch {
    return false
  }
}

const shouldOpen = () => {
  if (!props.projectId || dismissed()) return false
  try {
    if (sessionStorage.getItem(PENDING_KEY) === props.projectId) return true
  } catch {
    /* ignore */
  }
  return route.query.welcome === '1'
}

const clearPendingFlags = () => {
  try {
    sessionStorage.removeItem(PENDING_KEY)
  } catch {
    /* ignore */
  }
  if (route.query.welcome === '1') {
    const { welcome: _w, ...rest } = route.query
    router.replace({ path: route.path, query: rest })
  }
}

const tryOpen = () => {
  if (!shouldOpen()) return
  dialogVisible.value = true
  clearPendingFlags()
}

onMounted(() => {
  void loadScale()
  tryOpen()
})

watch(
  () => [props.projectId, route.query.welcome],
  () => tryOpen(),
)

const closeDialog = () => {
  dialogVisible.value = false
}

const dismissForever = () => {
  closeDialog()
  try {
    localStorage.setItem(storageKey.value, '1')
  } catch {
    /* ignore */
  }
}

const workScale = ref('medium')

const loadScale = async () => {
  try {
    const { data } = await getOutline()
    workScale.value = String(data?.scale_profile?.scale || 'medium')
  } catch {
    workScale.value = 'medium'
  }
}

const steps = computed(() => {
  const micro = workScale.value === 'micro'
  const longForm = isLongFormScale(workScale.value)
  const base = [
    { label: '设置模型', route: '/config' },
    { label: micro ? '大纲与场景' : '大纲与卷纲', route: '/outline' },
  ]
  if (longForm) {
    base.push({ label: '配置 Embedding', route: '/config' })
  }
  base.push(
    { label: '工作台连写', route: '/workspace' },
    { label: '章节维护', route: '/chapters/maintenance' },
  )
  return base
})

const stepCountLabel = computed(() => {
  const n = steps.value.length
  if (workScale.value === 'micro') return `微型作品 · ${n} 步`
  if (isLongFormScale(workScale.value)) return `长篇作品 · ${n} 步`
  return `标准流程 · ${n} 步`
})

const goStep = (path: string) => {
  dialogVisible.value = false
  router.push(path)
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    class="first-book-guide-dialog"
    width="520px"
    align-center
    :close-on-click-modal="false"
    @close="closeDialog"
  >
    <template #header>
      <span class="dialog-title">首次创作向导</span>
    </template>
    <p class="guide-desc">
      新书已创建（{{ stepCountLabel }}）。建议按下面顺序完成配置后再点工作台「连写启动」；系统暂停后可在章节维护处理待改章节。
    </p>
    <ul class="guide-bullets">
      <li>配置模型 → 完善大纲与卷纲 → 开书清单全绿 → 连写启动</li>
      <li>门禁或外审未过时，在章节维护「待处理章节」改稿并复制试审</li>
    </ul>
    <div class="guide-steps">
      <el-button
        v-for="(s, i) in steps"
        :key="s.route"
        size="small"
        @click="goStep(s.route)"
      >
        {{ i + 1 }}. {{ s.label }}
      </el-button>
    </div>
    <template #footer>
      <el-button @click="dismissForever">不再提示</el-button>
      <el-button type="primary" @click="goStep('/workspace')">进入工作台</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.guide-desc {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.guide-bullets {
  margin: 0 0 16px;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.guide-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>