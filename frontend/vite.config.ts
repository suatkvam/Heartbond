import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// ABI and deployment JSON live in ../shared (read at build time).
export default defineConfig({
  plugins: [react()],
  server: { fs: { allow: ['..'] } },
})
