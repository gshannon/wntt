import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Conditions from '../Conditions'

vi.mock('../ErrorBlock', () => ({
    default: ({ error }) => <div data-testid='error-block'>{String(error)}</div>,
}))

describe('Conditions', () => {
    it('renders ErrorBlock with the error prop when an error is present', () => {
        render(<Conditions data={null} error={new Error('fetch failed')} />)

        expect(screen.getByTestId('error-block')).toHaveTextContent('fetch failed')
    })
})
