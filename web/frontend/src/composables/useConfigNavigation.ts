import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CONFIG_SECTION_ALIASES, CONFIG_SECTIONS } from '../utils/configSections'

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
    if (!raw) return
    const group = CONFIG_SECTION_ALIASES[raw] || raw
    requestAnimationFrame(() => {
      const el = document.getElementById(raw) || document.getElementById(group)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  onMounted(hashSection)
  watch(() => route.hash, hashSection)

  return { sections: CONFIG_SECTIONS, scrollTo }
}
