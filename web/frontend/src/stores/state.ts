import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getState, getTimeline } from '../api'

export interface ContinuityState {
  characters: Record<string, any>
  events: any[]
  foreshadows: any[]
  hooks: any[]
  objects: any[]
  threads: any[]
}

export interface TimelineState {
  nodes: any[]
  edges: any[]
  foreshadows: any[]
  hooks: any[]
}

const emptyTimeline = (): TimelineState => ({
  nodes: [],
  edges: [],
  foreshadows: [],
  hooks: [],
})

export const useStateStore = defineStore('state', () => {
  const continuity = ref<ContinuityState>({
    characters: {},
    events: [],
    foreshadows: [],
    hooks: [],
    objects: [],
    threads: [],
  })
  const timeline = ref<TimelineState>(emptyTimeline())
  const loading = ref(false)

  async function fetchState() {
    loading.value = true
    try {
      const { data } = await getState()
      continuity.value = data
    } catch { /* backend warming up */ }
    finally { loading.value = false }
  }

  async function fetchTimeline() {
    try {
      const { data } = await getTimeline()
      timeline.value = { ...emptyTimeline(), ...(data || {}) }
    } catch { /* backend warming up */ }
  }

  async function refreshAll() {
    await Promise.all([fetchState(), fetchTimeline()])
  }

  return { continuity, timeline, loading, fetchState, fetchTimeline, refreshAll }
})
