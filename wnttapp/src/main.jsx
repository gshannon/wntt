import 'bootstrap/dist/css/bootstrap.min.css'
import * as Sentry from '@sentry/react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import App from './App'

import.meta.env.VITE_SENTRY_ENABLE === '1' &&
    Sentry.init({
        dsn: import.meta.env.VITE_SENTRY_DSN,
        environment: import.meta.env.MODE,
        release: import.meta.env.VITE_APP_VERSION,
        enableLogs: true,
        debug: false,
    })

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

const container = document.getElementById('root')
const root = createRoot(container, {
    // Callback called when an error is thrown and not caught by an ErrorBoundary.
    onUncaughtError: Sentry.reactErrorHandler((error, errorInfo) => {
        console.warn('Uncaught error', error, errorInfo.componentStack)
    }),
    // Callback called when React catches an error in an ErrorBoundary.
    onCaughtError: Sentry.reactErrorHandler(),
    // Callback called when React automatically recovers from errors.
    onRecoverableError: Sentry.reactErrorHandler(),
})

root.render(
    <>
        <QueryClientProvider client={queryClient}>
            <App />
            {/* <ReactQueryDevtools
                initialIsOpen={false}
                buttonPosition='top-right'
                position='bottom'
            /> */}
        </QueryClientProvider>
    </>,
)
