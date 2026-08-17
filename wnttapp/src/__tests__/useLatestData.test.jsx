import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import useLatestData from '../useLatestData'
import * as storage from '../storage'
import { HttpNotAcceptableCode } from '../utils'

vi.mock('axios')
vi.mock('@sentry/react', () => ({
    captureException: vi.fn(),
}))

const mainStore = { uid: 'uid-1', session: 'sess-1', started: '2024-01-01' }
const station = { id: 'welinwq' }

const makeAxiosError = (overrides = {}) => Object.assign(new Error('boom'), overrides)

const wrapper = ({ children }) => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(storage, 'getMainStorage').mockReturnValue(mainStore)
    vi.spyOn(console, 'error').mockImplementation(() => {})
})

describe('useLatestData', () => {
    it('sends the expected request shape and returns data on success', async () => {
        axios.post.mockResolvedValue({ data: { temp: 72 } })
        const { result } = renderHook(() => useLatestData(station), { wrapper })

        await waitFor(() => expect(result.current.isSuccess).toBe(true))

        expect(result.current.data).toEqual({ temp: 72 })
        expect(axios.post).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({
                station_id: 'welinwq',
                version: expect.any(String),
                uid: mainStore.uid,
                session: mainStore.session,
                started: mainStore.started,
            }),
        )
    })

    it('surfaces a 406 version-mismatch error without logging it', async () => {
        axios.post.mockRejectedValue(
            makeAxiosError({ response: { status: HttpNotAcceptableCode } }),
        )
        const { result } = renderHook(() => useLatestData(station), { wrapper })

        await waitFor(() => expect(result.current.isError).toBe(true))

        expect(result.current.error.response.status).toBe(HttpNotAcceptableCode)
        expect(console.error).not.toHaveBeenCalled()
        expect(Sentry.captureException).not.toHaveBeenCalled()
    })

    it('surfaces and logs a generic 500 error', async () => {
        axios.post.mockRejectedValue(makeAxiosError({ response: { status: 500 } }))
        const { result } = renderHook(() => useLatestData(station), { wrapper })

        await waitFor(() => expect(result.current.isError).toBe(true))

        expect(console.error).toHaveBeenCalledOnce()
        expect(Sentry.captureException).toHaveBeenCalledOnce()
    })

    it('surfaces and logs a network error with no response', async () => {
        axios.post.mockRejectedValue(makeAxiosError({ code: 'ERR_NETWORK' }))
        const { result } = renderHook(() => useLatestData(station), { wrapper })

        await waitFor(() => expect(result.current.isError).toBe(true))

        expect(console.error).toHaveBeenCalledOnce()
        expect(Sentry.captureException).toHaveBeenCalledOnce()
    })

    it('surfaces a cancellation without logging or retrying', async () => {
        axios.post.mockRejectedValue(makeAxiosError({ name: 'CanceledError' }))
        const { result } = renderHook(() => useLatestData(station), { wrapper })

        await waitFor(() => expect(result.current.isError).toBe(true))

        expect(console.error).not.toHaveBeenCalled()
        expect(Sentry.captureException).not.toHaveBeenCalled()
        expect(axios.post).toHaveBeenCalledOnce()
    })
})
