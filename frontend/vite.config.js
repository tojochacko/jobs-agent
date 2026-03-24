import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '^/(preferences|resume|jobs|applications|outreach|auth|webhook|health)': {
        target: process.env.BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        bypass: (req) => {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
