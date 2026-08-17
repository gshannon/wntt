import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import ErrorBlock from '../ErrorBlock'
import { HttpNotAcceptableCode } from '../utils'

vi.mock('@sentry/react', () => ({
    logger: { error: vi.fn() },
}))

const make406Error = () => {
    const error = new axios.AxiosError('Not Acceptable')
    error.response = { status: HttpNotAcceptableCode }
    return error
}

const make500Error = () => {
    const error = new axios.AxiosError('Server Error')
    error.response = { status: 500 }
    return error
}

describe('ErrorBlock', () => {
    let reloadSpy

    beforeEach(() => {
        vi.useFakeTimers()
        reloadSpy = vi.fn()
        Object.defineProperty(window, 'location', {
            value: { reload: reloadSpy },
            writable: true,
        })
    })

    afterEach(() => {
        cleanup()
        vi.useRealTimers()
        vi.clearAllMocks()
    })

    it('renders nothing and logs to Sentry when error is null', () => {
        const { container } = render(<ErrorBlock error={null} />)
        expect(container).toBeEmptyDOMElement()
        expect(Sentry.logger.error).toHaveBeenCalledWith('Error is NULL!')
        expect(reloadSpy).not.toHaveBeenCalled()
    })

    it('renders a plain string error verbatim', () => {
        render(<ErrorBlock error='out of map bounds' />)
        expect(screen.getByText('out of map bounds')).toBeInTheDocument()
    })

    it('renders the generic message for a non-406 axios error', () => {
        render(<ErrorBlock error={make500Error()} />)
        expect(
            screen.getByText('There was a problem fetching the data. Please try again later.'),
        ).toBeInTheDocument()
        expect(screen.queryByText(/new version/i)).not.toBeInTheDocument()
    })

    it('renders the upgrade UI for a 406 axios error', () => {
        render(<ErrorBlock error={make406Error()} />)
        expect(screen.getByText(/a new version was detected/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /get new version/i })).toBeInTheDocument()
    })

    it('reloads immediately when the upgrade button is clicked', () => {
        render(<ErrorBlock error={make406Error()} />)
        fireEvent.click(screen.getByRole('button', { name: /get new version/i }))
        expect(reloadSpy).toHaveBeenCalledOnce()
    })

    it('auto-reloads after 10 seconds for a 406 error', () => {
        render(<ErrorBlock error={make406Error()} />)
        expect(reloadSpy).not.toHaveBeenCalled()
        vi.advanceTimersByTime(10_000)
        expect(reloadSpy).toHaveBeenCalledOnce()
    })

    it('reloads on unmount before the timer fires, and does not double-fire afterward', () => {
        const { unmount } = render(<ErrorBlock error={make406Error()} />)
        vi.advanceTimersByTime(5_000)
        expect(reloadSpy).not.toHaveBeenCalled()
        unmount()
        expect(reloadSpy).toHaveBeenCalledOnce()
        vi.advanceTimersByTime(10_000)
        expect(reloadSpy).toHaveBeenCalledOnce()
    })

    it('does not reload on unmount for a non-upgrade error', () => {
        const { unmount } = render(<ErrorBlock error={make500Error()} />)
        unmount()
        expect(reloadSpy).not.toHaveBeenCalled()
    })
})
