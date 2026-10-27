import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  // Public assets keep runtime URLs instead of becoming server-side test imports.
  plugins: [vue({ template: { transformAssetUrls: { includeAbsolute: false } } })],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path === '/api/health' ? '/health' : path,
      },
    },
  },
})
