//  This is a "flat config" format file
import globals from 'globals'
import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import reactPlugin from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default tseslint.config(
    { ignores: ['dist/**', 'coverage/**'] },
    js.configs.recommended,
    // Non-type-checked TS rules (fast; no `parserOptions.project` needed).
    // Upgrade to `recommendedTypeChecked` once the codebase is on `strict: true`.
    tseslint.configs.recommended,
    {
        name: 'lint-config-1',
        files: ['**/*.{js,jsx,ts,tsx}'],
        plugins: {
            react: reactPlugin,
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
        },
        languageOptions: {
            parserOptions: {
                ecmaFeatures: {
                    jsx: true,
                },
            },
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
        rules: {
            ...reactPlugin.configs.recommended.rules,
            ...reactHooks.configs.recommended.rules,
            ...reactRefresh.configs.recommended.rules,
            'react/react-in-jsx-scope': 'off', // Not needed with React 17+
            'react/prop-types': 'off',
            'react/jsx-no-target-blank': 'off',
        },
        settings: {
            react: {
                version: 'detect',
            },
        },
    },
    {
        // Test files: allow the throwaway typing shortcuts that mocking needs.
        // EChart.tsx: echarts' own formatter/event callback params are typed `any`
        // upstream; mirroring that is clearer than hand-rolling partial interfaces.
        files: ['src/__tests__/**', 'src/EChart.tsx'],
        rules: {
            '@typescript-eslint/no-explicit-any': 'off',
        },
    },
)
