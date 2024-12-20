import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import Inspect from 'vite-plugin-inspect'
import eslint from 'vite-plugin-eslint'

// https://vitejs.dev/config/

export default defineConfig({
    base: '/',
    plugins: [react(), Inspect(), eslint()],
    server: {
        port: 3001,
        strictPort: true,
        host: true,
        origin: 'http://0.0.0.0:3001',
    },
})
