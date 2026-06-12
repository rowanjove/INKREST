import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/tokens.css'
import './styles/element-theme.css'
import './styles/global-surfaces.css'
import './styles/pipeline-panel.css'
import { initTheme } from './composables/useTheme'
import ThemeRoot from './ThemeRoot.vue'
import router from './router'
import { bootstrapLocalAccessToken } from './api'

initTheme()

async function bootstrapApp() {
  await bootstrapLocalAccessToken()

  const app = createApp(ThemeRoot)
  app.use(createPinia())
  app.use(router)
  app.mount('#app')
}

void bootstrapApp()
