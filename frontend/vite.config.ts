import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Do not emit source maps in production (prevents exposing source in F12)
    sourcemap: false,
  },
  server: {
    host: true, // expose to network
    port: 5173,
    strictPort: true,
    // Allow ngrok hostnames
    allowedHosts: ['.ngrok-free.app'], 
  },
})