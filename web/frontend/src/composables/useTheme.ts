import { computed, ref } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'inkrest-theme-mode'

const themeMode = ref<ThemeMode>('light')
const resolvedTheme = ref<'light' | 'dark'>('light')

let mediaQuery: MediaQueryList | null = null
let mediaListener: ((e: MediaQueryListEvent) => void) | null = null

function readStoredMode(): ThemeMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw
  } catch {
    /* ignore */
  }
  return 'light'
}

function resolveMode(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return mode
}

/** 写入 DOM：data-theme + Element Plus .dark */
export function applyTheme(mode: ThemeMode) {
  const resolved = resolveMode(mode)
  resolvedTheme.value = resolved
  themeMode.value = mode

  const root = document.documentElement
  root.dataset.theme = resolved
  root.classList.toggle('dark', resolved === 'dark')
}

function bindSystemListener() {
  if (typeof window === 'undefined') return
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaListener = () => {
    if (themeMode.value === 'system') applyTheme('system')
  }
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', mediaListener)
  } else {
    mediaQuery.addListener(mediaListener)
  }
}

export function initTheme() {
  if (typeof document === 'undefined') return
  const stored = readStoredMode()
  applyTheme(stored)
  bindSystemListener()
}

export function setThemeMode(mode: ThemeMode) {
  try {
    localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    /* ignore */
  }
  applyTheme(mode)
}

export function useTheme() {
  const isDark = computed(() => resolvedTheme.value === 'dark')

  return {
    themeMode,
    resolvedTheme,
    isDark,
    setThemeMode,
  }
}