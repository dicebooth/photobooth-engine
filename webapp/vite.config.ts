import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development the API is served by the python engine (python3 photobooth/main.py --web)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
