import { describe, it, expect } from 'vitest'
import { isSyzygyCode } from '../Syzygy'

describe('syzygy', () => {
    describe('isSyzygyCode', () => {
        it('should return true for valid codes', () => {
            for (const code of ['NM', 'FQ', 'FM', 'LQ', 'PG', 'PH']) {
                const result = isSyzygyCode(code)
                expect(result).toBe(true)
            }
        })
        it('should return false for invalid codes', () => {
            for (const code of ['fq', 'NMM', 0, -3.7, null, undefined, {}, NaN]) {
                const result = isSyzygyCode(code)
                expect(result).toBe(false)
            }
        })
    })
})
