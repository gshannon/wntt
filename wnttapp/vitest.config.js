/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import Inspect from 'vite-plugin-inspect'
import eslint from 'vite-plugin-eslint'

// https://vitest.dev/config/

export default defineConfig({
    base: '/',
    plugins: [react(), Inspect(), eslint()],
    server: {
        port: 3001,
        strictPort: true,
        host: true,
        origin: 'http://0.0.0.0:3001',
    },
    test: {
        environment: 'jsdom',
    },
    // Set env variables for testing here, e.g.
    // 'process.env.VITE_MIN_DATE': JSON.stringify('5/1/2024'),
    define: {},
})
