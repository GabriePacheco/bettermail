import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  base: "/static/",
  build: {
    rollupOptions: {
      input: {
        index: path.resolve(rootDir, "index.html"),
        pricing: path.resolve(rootDir, "pricing.html"),
      },
    },
  },
  plugins: [
   
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
