import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import { handleQueryError } from '../queryError'
import { HttpNotAcceptableCode } from '../utils'

vi.mock('@sentry/react', () => ({
    captureException: vi.fn(),
}))

const mainStore = { uid: 'uid-1', session: 'sess-1', started: '2024-01-01' }

const makeAxiosError = (overrides = {}) => {
    const error = new axios.AxiosError('boom')
    return Object.assign(error, overrides)
}

beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
})

describe('handleQueryError', () => {
    it('silently rethrows a CanceledError without logging', () => {
        const error = makeAxiosError({ name: 'CanceledError' })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).not.toHaveBeenCalled()
        expect(Sentry.captureException).not.toHaveBeenCalled()
    })

    it('silently rethrows a 406 version-mismatch error without logging', () => {
        const error = makeAxiosError({ response: { status: HttpNotAcceptableCode } })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).not.toHaveBeenCalled()
        expect(Sentry.captureException).not.toHaveBeenCalled()
    })

    it('logs and reports a generic 400 error, then rethrows', () => {
        const error = makeAxiosError({ response: { status: 400, data: { detail: 'bad' } } })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).toHaveBeenCalledWith(error.message, 400, 'bad')
        expect(Sentry.captureException).toHaveBeenCalledWith(
            error,
            expect.objectContaining({
                tags: { operation: 'op' },
                user: mainStore,
            }),
        )
    })

    it('logs and reports a generic 500 error, then rethrows', () => {
        const error = makeAxiosError({ response: { status: 500 } })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).toHaveBeenCalledOnce()
        expect(Sentry.captureException).toHaveBeenCalledOnce()
    })

    it('logs and reports a network error with no response', () => {
        const error = makeAxiosError({ code: 'ERR_NETWORK' })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).toHaveBeenCalledWith(error.message, undefined, undefined)
        expect(Sentry.captureException).toHaveBeenCalledOnce()
    })

    it('logs and reports a timeout error with no response', () => {
        const error = makeAxiosError({ code: 'ECONNABORTED', message: 'timeout of 5000ms exceeded' })
        expect(() => handleQueryError(error, { operation: 'op', mainStore })).toThrow(error)
        expect(console.error).toHaveBeenCalledWith(error.message, undefined, undefined)
        expect(Sentry.captureException).toHaveBeenCalledOnce()
    })

    it('passes extra context through to Sentry when provided', () => {
        const error = makeAxiosError({ response: { status: 500 } })
        expect(() =>
            handleQueryError(error, { operation: 'op', mainStore, extra: { start: 'a', end: 'b' } }),
        ).toThrow(error)
        expect(Sentry.captureException).toHaveBeenCalledWith(
            error,
            expect.objectContaining({ extra: { start: 'a', end: 'b' } }),
        )
    })
})
