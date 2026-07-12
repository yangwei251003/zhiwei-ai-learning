import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@fontsource-variable/ibm-plex-sans/index.css'
import { createPinia } from 'pinia'
import './styles/main.scss'
import App from './App.vue'
import { bootstrap } from './bootstrap'
import { createAppRouter, installAuthGuard } from './router'
import { useUserStore } from './stores/user'

const app = createApp(App)
const pinia = createPinia()
const router = createAppRouter()

app.use(pinia).use(router).use(ElementPlus)
installAuthGuard(router, pinia)

const userStore = useUserStore(pinia)
void bootstrap({
  restoreSession: () => userStore.restoreSession(),
  isReady: () => router.isReady(),
  mount: () => app.mount('#app'),
})
