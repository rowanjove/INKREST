import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getChapter, listChapters } from '../api'

export interface ChapterSummary {
  chapter_id: string
  title: string
  word_count: number
}

export interface ReaderSettings {
  fontSize: number
  lineHeight: number
  width: number
  indent: boolean
  theme: 'paper' | 'light' | 'dark' | 'green'
}

const SETTINGS_KEY = 'novel-agent-reader-settings'

export function useReaderView() {
  const router = useRouter()

  const chapters = ref<ChapterSummary[]>([])
  const selectedId = ref('')
  const loading = ref(false)
  const chapterLoading = ref(false)
  const chapter = ref<any>(null)
  const catalogSearch = ref('')
  const drawerVisible = ref(false)

  const settings = ref<ReaderSettings>({
    fontSize: 20,
    lineHeight: 1.8,
    width: 800,
    indent: true,
    theme: 'paper',
  })

  const selectedIndex = computed(() =>
    chapters.value.findIndex((item) => item.chapter_id === selectedId.value),
  )
  const currentTitle = computed(
    () => chapter.value?.title || chapters.value[selectedIndex.value]?.title || '未命名章节',
  )
  const paragraphs = computed(() => {
    const text = chapter.value?.final_text || ''
    return text
      .split(/\n+/)
      .map((part: string) => part.trim())
      .filter(Boolean)
  })
  const readerStyle = computed(() => ({
    maxWidth: `${settings.value.width}px`,
    fontSize: `${settings.value.fontSize}px`,
    lineHeight: settings.value.lineHeight,
  }))

  const filteredChapters = computed(() => {
    if (!catalogSearch.value.trim()) return chapters.value
    const query = catalogSearch.value.toLowerCase()
    return chapters.value.filter(
      (c) =>
        c.chapter_id.includes(query) ||
        (c.title || '').toLowerCase().includes(query),
    )
  })

  const loadSettings = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
      settings.value = { ...settings.value, ...saved }
    } catch {
      localStorage.removeItem(SETTINGS_KEY)
    }
  }

  const loadChapters = async () => {
    loading.value = true
    try {
      const { data } = await listChapters({ offset: 0, limit: 500, sync: true })
      chapters.value = data.items ?? data
      if (!selectedId.value && chapters.value.length) {
        selectedId.value = chapters.value[0].chapter_id
      }
    } finally {
      loading.value = false
    }
  }

  const goToWriter = () => {
    if (!selectedId.value) return
    router.push({ path: '/writer', query: { chapter: selectedId.value } })
  }

  const loadChapter = async (chapterId: string) => {
    if (!chapterId) {
      chapter.value = null
      return
    }
    chapterLoading.value = true
    try {
      const { data } = await getChapter(chapterId)
      chapter.value = data
      scrollToTop()
    } finally {
      chapterLoading.value = false
    }
  }

  const goChapter = (offset: number) => {
    const next = chapters.value[selectedIndex.value + offset]
    if (next) {
      selectedId.value = next.chapter_id
    }
  }

  const scrollToTop = () => {
    const mainEl = document.querySelector('.reader-content-scroll')
    if (mainEl) {
      mainEl.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const selectChapter = (chapterId: string) => {
    selectedId.value = chapterId
    drawerVisible.value = false
  }

  watch(selectedId, (id) => loadChapter(id), { immediate: false })
  watch(
    settings,
    (value) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(value)),
    { deep: true },
  )

  onMounted(async () => {
    loadSettings()
    await loadChapters()
  })

  return {
    chapters,
    selectedId,
    loading,
    chapterLoading,
    chapter,
    catalogSearch,
    drawerVisible,
    settings,
    selectedIndex,
    currentTitle,
    paragraphs,
    readerStyle,
    filteredChapters,
    loadChapters,
    goToWriter,
    goChapter,
    scrollToTop,
    selectChapter,
  }
}