import { nextTick, ref } from 'vue'
import { usePetStore } from '../stores/pet'
import { abortTask } from '../api'
import { SHANSHAN_SUGGESTED_QUESTIONS } from '../constants/shanshanCopy'
import { renderPetMarkdown } from '../utils/petMarkdown'

export type PetBubbleTab = 'status' | 'chat'

export type PetAction = {
  type: string
  label: string
  payload?: Record<string, unknown>
}

export function usePetBubbleView() {
  const pet = usePetStore()
  const avatar = new URL('../assets/pet/shanshan/ui/bubble_avatar.png', import.meta.url).href

  const activeTab = ref<PetBubbleTab>('status')
  const inputMessage = ref('')
  const chatContainer = ref<HTMLElement | null>(null)
  const chatInputRef = ref<HTMLTextAreaElement | null>(null)
  const diagnoseCollapsed = ref(
    JSON.parse(localStorage.getItem('pet_diagnose_collapsed') || 'false') as boolean,
  )

  const suggestedQuestions = [...SHANSHAN_SUGGESTED_QUESTIONS]

  function toggleDiagnoseCollapsed() {
    diagnoseCollapsed.value = !diagnoseCollapsed.value
    localStorage.setItem('pet_diagnose_collapsed', JSON.stringify(diagnoseCollapsed.value))
  }

  function navigate(route: string) {
    window.electronAPI?.navigateMain?.(route)
  }

  function handleStatusCardClick() {
    const failed = pet.latestFailedTask
    if (failed?.chapter_id) {
      navigate(`/chapters/${failed.chapter_id}`)
      return
    }
    if (
      pet.novelBatchPaused ||
      failed ||
      pet.context?.running_tasks?.length ||
      (pet.context?.pipeline_pending?.pending_total ?? 0) > 0
    ) {
      navigate('/chapters/maintenance')
    }
  }

  function openMonitorForBatch() {
    navigate('/chapters/maintenance')
  }

  function scrollToBottom() {
    nextTick(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
    })
  }

  function setChatContainer(el: HTMLElement | null) {
    chatContainer.value = el
  }

  function setChatInputRef(el: HTMLTextAreaElement | null) {
    chatInputRef.value = el
  }

  function selectTab(tab: PetBubbleTab) {
    activeTab.value = tab
    if (tab === 'chat') {
      pet.initChatHistory()
      scrollToBottom()
      nextTick(() => chatInputRef.value?.focus())
    }
  }

  function handleInputKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter') return
    if (event.shiftKey) return
    event.preventDefault()
    void handleSend()
  }

  async function handleSend() {
    if (!inputMessage.value.trim() || pet.chatLoading) return
    const msg = inputMessage.value
    inputMessage.value = ''
    await pet.sendChatMessage(msg)
    scrollToBottom()
  }

  function handleSuggestQuestion(q: string) {
    if (pet.chatLoading) return
    inputMessage.value = q
    void handleSend()
  }

  async function handleActionClick(action: PetAction) {
    if (action.type === 'navigate') {
      navigate((action.payload?.route as string) || '/')
    } else {
      await pet.executeFix(action.type, action.payload || {})
      scrollToBottom()
    }
  }

  async function handleAbortRunningTask() {
    const task = pet.context?.running_tasks?.[0]
    if (!task?.id) return
    try {
      await abortTask(task.id)
      await pet.refreshContext()
    } catch (e) {
      console.error('Failed to abort task:', e)
    }
  }

  return {
    pet,
    avatar,
    activeTab,
    inputMessage,
    chatContainer,
    chatInputRef,
    diagnoseCollapsed,
    suggestedQuestions,
    toggleDiagnoseCollapsed,
    navigate,
    handleStatusCardClick,
    openMonitorForBatch,
    selectTab,
    handleInputKeydown,
    handleSend,
    handleSuggestQuestion,
    handleActionClick,
    handleAbortRunningTask,
    scrollToBottom,
    setChatContainer,
    setChatInputRef,
    renderMarkdown: renderPetMarkdown,
  }
}