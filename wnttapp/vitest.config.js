/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import Inspect from 'vite-plugin-inspect'
import eslint from 'vite-plugin-eslint2'

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
        setupFiles: ['./src/setupTests.js'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'html'],
            include: ['src/**/*.{js,jsx}'],
            exclude: ['src/__tests__/**', 'src/main.jsx'],
        },
    },
    // Set env variables for testing here, e.g.
    // 'process.env.VITE_MIN_DATE': JSON.stringify('5/1/2024'),
    define: {
        'import.meta.env.VITE_APP_VERSION': JSON.stringify('test'),
        'import.meta.env.VITE_API_STATIONS_URL': JSON.stringify('http://test/stations/'),
        'import.meta.env.VITE_API_GRAPH_URL': JSON.stringify('http://test/graph/'),
        'import.meta.env.VITE_API_LATEST_URL': JSON.stringify('http://test/latest/'),
        'import.meta.env.VITE_API_ADDRESS_URL': JSON.stringify('http://test/address/'),
    },
})
