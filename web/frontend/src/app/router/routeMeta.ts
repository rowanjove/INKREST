import 'vue-router'
import type { RouterScrollBehavior } from 'vue-router'

export type RouteScope = 'global' | 'project' | 'pet'

declare module 'vue-router' {
  interface RouteMeta {
    scope: RouteScope
    title: string
    navId?: string
    fullBleed?: boolean
  }
}

export function routeFallback(scope: RouteScope, hasProject: boolean) {
  if (scope === 'project' && !hasProject) return { name: 'library' as const }
  return true
}

export const appScrollBehavior: RouterScrollBehavior = (
  to,
  _from,
  savedPosition,
) => {
  if (savedPosition) return savedPosition
  if (to.hash) return { el: to.hash, behavior: 'smooth' }
  return { top: 0, left: 0 }
}
