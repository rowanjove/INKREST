import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useCommandPalette() {
  const isOpen = ref(false)

  const open = () => {
    isOpen.value = true
  }
  const close = () => {
    isOpen.value = false
  }
  const onKeydown = (event: KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      open()
    }
  }
  const onExternalOpen = () => open()

  onMounted(() => {
    window.addEventListener('keydown', onKeydown)
    window.addEventListener('inkrest-open-command-palette', onExternalOpen)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown)
    window.removeEventListener('inkrest-open-command-palette', onExternalOpen)
  })

  return { isOpen, open, close }
}
