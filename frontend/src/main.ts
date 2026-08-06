import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.less'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import VueDOMPurifyHTML from 'vue-dompurify-html'

// LicenseGenerator stub for community edition (no xpack)
// Provides: sqlbotEncrypt (passthrough), getLicense (always valid), generate (random key)
;(window as any).LicenseGenerator = {
  sqlbotEncrypt: (text: string) => text,  // passthrough - encryption handled by backend proxy
  getLicense: () => ({ status: 'valid', type: 'community' }),
  generate: () => Math.random().toString(36).substring(2),
  generateRouters: () => {},
  init: () => Promise.resolve(),
}

// import 'element-plus/dist/index.css'
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(VueDOMPurifyHTML)
app.mount('#app')
