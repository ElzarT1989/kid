import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'KidsEdu AI',
        short_name: 'KidsEdu',
        description: 'Детский образовательный киоск-плеер',
        theme_color: '#4f46e5',
        background_color: '#0f172a',
        display: 'fullscreen',
        orientation: 'landscape',
        icons: [
          { src: 'icons.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
  },
})
