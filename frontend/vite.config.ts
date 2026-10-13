import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// ABI and deployment JSON live in ../shared (read at build time).
export default defineConfig({
  plugins: [react()],
  server: { fs: { allow: ['..'] } },
  build: {
    rollupOptions: {
      output: {
        // Keep the app chunk small: libraries go into their own long-cached chunks.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react'
          if (/node_modules\/(viem|ox|abitype|@noble|@scure|isows)\//.test(id)) return 'viem'
          return 'wallet'
        },
      },
    },
  },
})
