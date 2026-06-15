import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listProjects,
  getCurrentProject,
  createProject as apiCreate,
  deleteProject as apiDelete,
  switchProject as apiSwitch,
} from '../api'

export interface Project {
  id: string
  name: string
  description?: string
  created_at?: string
  updated_at?: string
  activity_at?: string
  pinned?: boolean
  pinned_at?: string
  chapter_count?: number
  total_words?: number
  genre?: string
  author_label?: string
  channel?: string
  target_chapters?: number
  has_cover?: boolean
  pending_alert_count?: number
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    try {
      const { data } = await listProjects()
      projects.value = data
      if (currentProject.value?.id && !data.some((project: Project) => project.id === currentProject.value?.id)) {
        currentProject.value = null
      }
    } catch { /* backend warming up */ }
  }

  async function fetchCurrent() {
    try {
      const { data } = await getCurrentProject()
      if (data.id && data.name) {
        currentProject.value = data
      } else if (!currentProject.value?.id) {
        currentProject.value = null
      }
    } catch {
      // 网络抖动时保留当前项目，避免 App 层 v-if 卸载连写弹窗
      if (!currentProject.value?.id) {
        currentProject.value = null
      }
    }
  }

  async function createProject(
    name: string,
    description?: string,
    presetId?: string,
    extra?: {
      genre?: string
      channel?: string
      target_chapters?: number
      scale?: string
      scale_label?: string
      target_chars_per_chapter?: number[]
      scale_profile?: Record<string, unknown>
      outline?: Record<string, unknown>
      preset_channel?: string
      preset_theme?: string
      preset_mechanisms?: string[]
      preset_cool_points?: string[]
    },
  ): Promise<Project> {
    loading.value = true
    try {
      const { data } = await apiCreate({
        name,
        description,
        preset_id: presetId,
        ...extra,
      })
      await fetchProjects()
      return data
    } finally {
      loading.value = false
    }
  }

  async function switchProject(id: string) {
    loading.value = true
    try {
      await apiSwitch(id)
      await fetchCurrent()
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id: string) {
    loading.value = true
    try {
      await apiDelete(id)
      if (currentProject.value?.id === id) {
        currentProject.value = null
      }
      await fetchProjects()
    } finally {
      loading.value = false
    }
  }

  return {
    projects, currentProject, loading,
    fetchProjects, fetchCurrent, createProject, switchProject, deleteProject,
  }
})
