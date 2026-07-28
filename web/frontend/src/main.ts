import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/notification/style/css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/tokens.css'
import './styles/element-theme.css'
import './styles/global-surfaces.css'
import './styles/pipeline-panel.css'
import { initTheme } from './composables/useTheme'
import ThemeRoot from './ThemeRoot.vue'
import router from './router'
import { bootstrapLocalAccessToken } from './api'

function isPetEntryPath() {
  if (typeof window === 'undefined') return false
  const path = window.location.pathname || ''
  return path === '/pet' || path === '/pet-bubble'
}

async function startApp() {
  initTheme()
  if (isPetEntryPath()) {
    void bootstrapLocalAccessToken()
  } else {
    await bootstrapLocalAccessToken()
  }

  const app = createApp(ThemeRoot)
  app.use(createPinia())
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void startApp()
