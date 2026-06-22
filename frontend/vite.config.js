import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  base: process.env.FRONTEND_BASE || "/",
  build: {
    rollupOptions: {
      input: {
        index: path.resolve(rootDir, "index.html"),
        landing: path.resolve(rootDir, "landing.html"),
        taskpane: path.resolve(rootDir, "taskpane.html"),
        pricing: path.resolve(rootDir, "pricing.html"),
        admin: path.resolve(rootDir, "admin.html"),
      },
    },
  },
  plugins: [
   
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
