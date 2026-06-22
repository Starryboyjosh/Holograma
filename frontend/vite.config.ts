import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Tauri's devUrl points at a fixed port; fail loudly instead of hopping ports.
  server: {
    port: 5173,
    strictPort: true,
  },
  // Don't wipe Tauri's terminal output during `tauri dev`.
  clearScreen: false,
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
})
