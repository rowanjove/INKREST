import { ref, watch, type Ref } from 'vue'
import type { PipelineAlert } from '../stores/pipelineAlerts'

const focusedChapterId = ref<string | null>(null)
const pickerVisible = ref(false)

export function useRepairChapterFocus(alerts?: Ref<PipelineAlert[]>) {
  if (alerts) {
    watch(
      alerts,
      (list) => {
        const ids = list.map((a) => a.chapter_id)
        if (focusedChapterId.value && ids.includes(focusedChapterId.value)) return
        focusedChapterId.value = ids[0] || null
      },
      { immediate: true, deep: true },
    )
  }

  function setFocusedChapter(chapterId: string | null) {
    focusedChapterId.value = chapterId
  }

  function openPicker() {
    pickerVisible.value = true
  }

  function closePicker() {
    pickerVisible.value = false
  }

  return {
    focusedChapterId,
    pickerVisible,
    setFocusedChapter,
    openPicker,
    closePicker,
  }
}