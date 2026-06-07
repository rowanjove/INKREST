import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import { listChapters, getChapter, listTasks, runChapter } from '../api'

export interface Chapter {
  chapter_id: string
  title?: string
  word_count?: number
  risk_level?: string
  goal?: string
}

export interface Task {
  task_id: string
  chapter_id?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  goal?: string
  error?: string
  created_at?: string
  updated_at?: string
}

export const useChapterStore = defineStore('chapter', () => {
  const chapters = ref<Chapter[]>([])
  const tasks = ref<Task[]>([])
  const currentChapter = shallowRef<any>(null)
  const loading = ref(false)

  const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed').length)
  const runningTasks = computed(() => tasks.value.filter(t => ['pending', 'running'].includes(t.status)).length)
  const totalWords = computed(() => chapters.value.reduce((sum, c) => sum + (c.word_count || 0), 0))
  const latestChapter = computed(() => chapters.value[chapters.value.length - 1])

  async function fetchChapters(sync = false) {
    try {
      const { data } = await listChapters({ offset: 0, limit: 500, sync, include_gaps: true })
      chapters.value = data.items ?? data
    } catch { /* backend warming up */ }
  }

  async function fetchTasks() {
    try {
      const { data } = await listTasks()
      tasks.value = data.slice()
    } catch { /* backend warming up */ }
  }

  async function fetchChapter(id: string) {
    const { data } = await getChapter(id)
    currentChapter.value = { ...data }
    return data
  }

  async function submitChapter(form: { chapter_id: string; goal: string; dry_run?: boolean }) {
    loading.value = true
    try {
      await runChapter(form)
      await Promise.all([fetchChapters(true), fetchTasks()])
    } finally {
      loading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([fetchChapters(), fetchTasks()])
  }

  return {
    chapters, tasks, currentChapter, loading,
    completedTasks, runningTasks, totalWords, latestChapter,
    fetchChapters, fetchTasks, fetchChapter, submitChapter, refreshAll,
  }
})
