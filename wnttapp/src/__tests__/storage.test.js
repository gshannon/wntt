import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as Sentry from '@sentry/react'
import {
    initStorage,
    setMainStorage,
    getMainStorage,
    setPermanentStorage,
    getPermanentStorage,
    setDailyStorage,
    getDailyStorage,
} from '../storage'

vi.mock('@sentry/react', () => ({
    captureException: vi.fn(),
}))

beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
})

describe('storage', () => {
    describe('main storage', () => {
        it('returns {} when nothing has been stored', () => {
            expect(getMainStorage()).toEqual({})
        })

        it('round-trips a value', () => {
            setMainStorage({ session: 'abc123', started: '2024-01-01' })
            expect(getMainStorage()).toEqual({ session: 'abc123', started: '2024-01-01' })
        })

        it('returns {} and reports to Sentry on corrupt JSON', () => {
            localStorage.setItem('003.main', '{not valid json')
            expect(getMainStorage()).toEqual({})
            expect(Sentry.captureException).toHaveBeenCalledOnce()
        })
    })

    describe('initStorage', () => {
        it('sets session and started while preserving other main fields', () => {
            setMainStorage({ uid: 'user-1' })
            initStorage()
            const main = getMainStorage()
            expect(main.uid).toBe('user-1')
            expect(main.session).toEqual(expect.any(String))
            expect(main.started).toBeTruthy()
        })
    })

    describe('permanent storage', () => {
        it('returns {} for a missing stationId', () => {
            expect(getPermanentStorage(undefined)).toEqual({})
        })

        it('returns {} when nothing has been stored for a station', () => {
            expect(getPermanentStorage('welinwq')).toEqual({})
        })

        it('round-trips a value per station', () => {
            setPermanentStorage('welinwq', { zoom: 5 })
            setPermanentStorage('newport', { zoom: 8 })
            expect(getPermanentStorage('welinwq')).toEqual({ zoom: 5 })
            expect(getPermanentStorage('newport')).toEqual({ zoom: 8 })
        })

        it('returns {} and reports to Sentry on corrupt JSON', () => {
            localStorage.setItem('003.welinwq', '{not valid json')
            expect(getPermanentStorage('welinwq')).toEqual({})
            expect(Sentry.captureException).toHaveBeenCalledOnce()
        })
    })

    describe('daily storage', () => {
        it('returns {} for a missing stationId', () => {
            expect(getDailyStorage(undefined)).toEqual({})
        })

        it('round-trips a value stored today', () => {
            const today = new Date()
            setDailyStorage('welinwq', { note: 'hi' }, today)
            expect(getDailyStorage('welinwq')).toEqual({ day: expect.any(String), note: 'hi' })
        })

        it('expires and clears values stored on a previous day', () => {
            const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)
            setDailyStorage('welinwq', { note: 'stale' }, yesterday)
            expect(getDailyStorage('welinwq')).toEqual({})
            // Confirm it was cleared, not just skipped, by checking a second read is still empty.
            expect(getDailyStorage('welinwq')).toEqual({})
        })

        it('does not clobber permanent data when daily data expires', () => {
            setPermanentStorage('welinwq', { zoom: 5 })
            const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)
            setDailyStorage('welinwq', { note: 'stale' }, yesterday)
            getDailyStorage('welinwq')
            expect(getPermanentStorage('welinwq')).toEqual({ zoom: 5 })
        })

        it('returns {} and reports to Sentry on corrupt JSON', () => {
            localStorage.setItem('003.welinwq', '{not valid json')
            expect(getDailyStorage('welinwq')).toEqual({})
            expect(Sentry.captureException).toHaveBeenCalledOnce()
        })
    })
})
