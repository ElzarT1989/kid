import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'KidsEdu — Родительский доступ',
        short_name: 'KidsEdu Parent',
        description: 'Контроль и мониторинг KidsEdu AI: статистика просмотров, каналы, модерация видео',
        theme_color: '#2a78d6',
        background_color: '#fcfcfb',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: 'icons.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    port: 5174,
  },
})
