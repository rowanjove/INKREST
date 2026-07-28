import type { JSONContent } from '@tiptap/core'
import { computed, onBeforeUnmount, ref } from 'vue'
import {
  getManuscriptWorkspace,
  listManuscriptRevisions,
  restoreManuscriptRevision as restoreRevisionRequest,
  saveManuscriptDocument,
} from '../api/manuscript'
import type {
  ManuscriptDocument,
  ManuscriptRevision,
  ManuscriptSaveStatus,
  ManuscriptWorkspace,
} from '../entities/manuscript/manuscript'
import { EMPTY_TIPTAP_DOCUMENT } from '../entities/manuscript/manuscript'

const EMPTY_WORKSPACE: ManuscriptWorkspace = {
  schema_version: 1,
  chapters: [],
  selected_chapter_id: '',
  document: null,
  history: [],
  context: {},
}

function isConflict(error: unknown): error is {
  response: { status: number; data: { current: ManuscriptDocument } }
} {
  const candidate = error as {
    response?: { status?: number; data?: { current?: ManuscriptDocument } }
  }
  return candidate.response?.status === 409 && Boolean(candidate.response.data?.current)
}

export function useManuscriptWorkspace() {
  const workspace = ref<ManuscriptWorkspace>({ ...EMPTY_WORKSPACE })
  const content = ref<JSONContent>(EMPTY_TIPTAP_DOCUMENT)
  const title = ref('')
  const loading = ref(false)
  const loadError = ref('')
  const saveStatus = ref<ManuscriptSaveStatus>('idle')
  const saveError = ref('')
  const conflictDocument = ref<ManuscriptDocument | null>(null)
  const dirty = ref(false)
  const pendingSource = ref<'autosave' | 'manual' | 'ai_accept'>('autosave')
  let saveTimer: number | null = null

  const document = computed(() => workspace.value.document)
  const activeChapterId = computed(() => workspace.value.selected_chapter_id)

  function cancelSaveTimer() {
    if (saveTimer !== null) {
      window.clearTimeout(saveTimer)
      saveTimer = null
    }
  }

  function applyDocument(next: ManuscriptDocument) {
    workspace.value.document = next
    workspace.value.selected_chapter_id = next.chapter_id
    title.value = next.title
    content.value = next.content_json
  }

  async function load(chapterId = '') {
    loading.value = true
    loadError.value = ''
    try {
      const { data } = await getManuscriptWorkspace({
        chapter_id: chapterId || undefined,
      })
      workspace.value = data
      title.value = data.document?.title || ''
      content.value = data.document?.content_json || EMPTY_TIPTAP_DOCUMENT
      dirty.value = false
      conflictDocument.value = null
      saveStatus.value = data.document ? 'saved' : 'idle'
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : '正文工作区加载失败'
    } finally {
      loading.value = false
    }
  }

  function scheduleSave(source: 'autosave' | 'manual' | 'ai_accept' = 'autosave') {
    if (!document.value) return
    dirty.value = true
    pendingSource.value = source
    saveStatus.value = 'dirty'
    cancelSaveTimer()
    saveTimer = window.setTimeout(() => {
      void saveNow()
    }, 1200)
  }

  function updateContent(next: JSONContent, source: 'autosave' | 'ai_accept' = 'autosave') {
    content.value = next
    scheduleSave(source)
  }

  function updateTitle(next: string) {
    title.value = next
    scheduleSave('autosave')
  }

  async function saveNow(force = false): Promise<boolean> {
    cancelSaveTimer()
    const current = document.value
    if (!current || (!dirty.value && !force)) return true
    const snapshot = JSON.stringify(content.value)
    const source = pendingSource.value
    saveStatus.value = 'saving'
    saveError.value = ''
    try {
      const { data } = await saveManuscriptDocument(current.chapter_id, {
        title: title.value.trim() || current.title,
        content_json: content.value,
        expected_revision: current.revision,
        source,
      })
      workspace.value.document = data
      title.value = data.title
      try {
        workspace.value.history = (await listManuscriptRevisions(data.chapter_id)).data
      } catch {
        // Saving succeeded; a stale history panel is preferable to reporting a false save failure.
      }
      if (snapshot === JSON.stringify(content.value)) {
        dirty.value = false
        saveStatus.value = 'saved'
      } else {
        dirty.value = true
        saveStatus.value = 'dirty'
        scheduleSave(pendingSource.value)
      }
      conflictDocument.value = null
      return true
    } catch (error) {
      if (isConflict(error)) {
        conflictDocument.value = error.response.data.current
        saveStatus.value = 'conflict'
        return false
      }
      saveError.value = error instanceof Error ? error.message : '保存失败'
      saveStatus.value = 'error'
      return false
    }
  }

  async function selectChapter(chapterId: string): Promise<boolean> {
    if (chapterId === activeChapterId.value) return true
    if (dirty.value && !(await saveNow())) return false
    await load(chapterId)
    return !loadError.value
  }

  function useServerVersion() {
    if (!conflictDocument.value) return
    applyDocument(conflictDocument.value)
    conflictDocument.value = null
    dirty.value = false
    saveStatus.value = 'saved'
  }

  async function keepLocalAsNewRevision() {
    if (!conflictDocument.value) return false
    workspace.value.document = conflictDocument.value
    conflictDocument.value = null
    dirty.value = true
    pendingSource.value = 'manual'
    return saveNow(true)
  }

  async function restoreRevision(revision: ManuscriptRevision) {
    const current = document.value
    if (!current) return false
    saveStatus.value = 'saving'
    try {
      const { data } = await restoreRevisionRequest(
        current.chapter_id,
        revision.revision_id,
        current.revision,
      )
      applyDocument(data)
      dirty.value = false
      saveStatus.value = 'saved'
      await load(current.chapter_id)
      return true
    } catch (error) {
      if (isConflict(error)) {
        conflictDocument.value = error.response.data.current
        saveStatus.value = 'conflict'
      } else {
        saveError.value = error instanceof Error ? error.message : '恢复历史失败'
        saveStatus.value = 'error'
      }
      return false
    }
  }

  onBeforeUnmount(() => {
    cancelSaveTimer()
    if (dirty.value) void saveNow()
  })

  return {
    workspace,
    document,
    content,
    title,
    loading,
    loadError,
    saveStatus,
    saveError,
    conflictDocument,
    dirty,
    activeChapterId,
    load,
    selectChapter,
    updateContent,
    updateTitle,
    saveNow,
    useServerVersion,
    keepLocalAsNewRevision,
    restoreRevision,
  }
}
