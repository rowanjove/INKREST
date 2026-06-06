import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
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
void bootstrapLocalAccessToken()

const app = createApp(ThemeRoot)
app.use(createPinia())
app.use(ElementPlus)
app.use(router)
app.mount('#app')