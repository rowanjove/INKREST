import type { Router } from 'vue-router'

/** Navigate to a settings section and scroll it into view. */
export function goConfigSection(router: Router, sectionId: string) {
  const hash = `#${sectionId}`
  return router.push({ path: '/config', hash }).then(() => {
    requestAnimationFrame(() => {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  })
}

export function isConfigSectionActive(route: { path: string; hash?: string }, sectionId: string) {
  return route.path.startsWith('/config') && (route.hash === `#${sectionId}` || route.hash === sectionId)
}