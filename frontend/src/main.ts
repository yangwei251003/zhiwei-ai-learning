import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@fontsource-variable/ibm-plex-sans/index.css'
import { createPinia } from 'pinia'
import './styles/main.scss'
import App from './App.vue'

createApp(App).use(createPinia()).use(ElementPlus).mount('#app')
