//  This is a "flat config" format file
import globals from 'globals'
import js from '@eslint/js'
import reactPlugin from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
    js.configs.recommended,
    {
        name: 'lint-config-1',
        files: ['**/*.js', '**/*.jsx'],
        plugins: {
            react: reactPlugin,
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
        },
        languageOptions: {
            parserOptions: {
                ecmaVersion: 'latest',
                sourceType: 'module',
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
]
