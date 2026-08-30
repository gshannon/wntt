import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import Inspect from 'vite-plugin-inspect'
import eslint from 'vite-plugin-eslint2'

// https://vitejs.dev/config/

export default defineConfig({
    plugins: [react(), Inspect(), eslint()],
    server: {
        port: 3001,
        strictPort: true,
        host: true,
        origin: 'http://0.0.0.0:3001',
    },
    preview: {
        port: 4173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000', // host port -> api-c:8001
                changeOrigin: true,
                rewrite: (p) => p.replace(/^\/api/, ''), // /api/stations/ -> /stations/
            },
        },
    },
})
