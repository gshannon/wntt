import * as Sentry from '@sentry/react'
import { HttpNotAcceptableCode } from './utils'

// Shared handling for axios errors raised inside react-query queryFn's. Cancellations (component
// unmounted / query key changed) and HTTP 406 (app version mismatch, handled separately by
// ErrorBlock's upgrade prompt) are expected, not real errors, so they're excluded from logging.
// All errors are rethrown so react-query surfaces them via the query's `error` state.
export const handleQueryError = (error, { operation, mainStore, extra } = {}) => {
    if (error.name !== 'CanceledError' && error.response?.status !== HttpNotAcceptableCode) {
        console.error(error.message, error.response?.status, error.response?.data?.detail)
        Sentry.captureException(error, {
            tags: { operation },
            user: {
                uid: mainStore?.uid,
                session: mainStore?.session,
                started: mainStore?.started,
            },
            extra,
        })
    }
    throw error
}
