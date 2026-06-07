import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CONFIG_SECTIONS } from '../utils/configSections'

export function useConfigNavigation() {
  const route = useRoute()

  const scrollTo = (id: string) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const hashSection = () => {
    const raw = (route.hash || '').replace(/^#/, '')
    if (raw && CONFIG_SECTIONS.some((s) => s.id === raw)) {
      requestAnimationFrame(() => scrollTo(raw))
    }
  }

  onMounted(hashSection)
  watch(() => route.hash, hashSection)

  return { sections: CONFIG_SECTIONS, scrollTo }
}