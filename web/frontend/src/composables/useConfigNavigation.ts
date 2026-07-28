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
    const target = CONFIG_SECTION_ALIASES[raw] || raw
    if (target && CONFIG_SECTIONS.some((s) => s.id === target)) {
      requestAnimationFrame(() => scrollTo(target))
    }
  }

  onMounted(hashSection)
  watch(() => route.hash, hashSection)

  return { sections: CONFIG_SECTIONS, scrollTo }
}
