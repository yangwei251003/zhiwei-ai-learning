import { createApp } from 'vue'
import { ElButton, ElIcon } from 'element-plus'
import 'element-plus/es/components/base/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/icon/style/css'
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

app.use(pinia).use(router).component('ElButton', ElButton).component('ElIcon', ElIcon)
installAuthGuard(router, pinia)

const userStore = useUserStore(pinia)
void bootstrap({
  restoreSession: () => userStore.restoreSession(),
  isReady: () => router.isReady(),
  mount: () => app.mount('#app'),
})
