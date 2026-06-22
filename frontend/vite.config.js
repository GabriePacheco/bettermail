import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

const cleanRouteTargets = {
  "/install": "/install.html",
  "/pricing": "/pricing.html",
  "/internal-admin": "/admin.html",
  "/support": "/support.html",
  "/privacy": "/privacy.html",
  "/terms": "/terms.html",
  "/security": "/security.html",
  "/contact": "/contact.html",
  "/appsource-test": "/appsource-test.html",
}

function cleanRoutes() {
  return {
    name: "bettermail-clean-routes",
    configureServer(server) {
      server.middlewares.use((request, _response, next) => {
        const url = new URL(request.url || "/", "http://localhost")
        const target = cleanRouteTargets[url.pathname]
        if (target) request.url = `${target}${url.search}`
        next()
      })
    },
  }
}

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
    cleanRoutes(),
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
