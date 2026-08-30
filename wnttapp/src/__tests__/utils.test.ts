import { describe, it, expect } from 'vitest'
import {
    defaultMinGraphDate,
    maxGraphDate,
    stringify,
    roundTo,
    degreesToDir,
    toEchartDegrees,
    calcWindspeedTickInterval,
    buildCacheKey,
} from '../utils'

describe('utils', () => {
    describe('defaultMinGraphDate', () => {
        it('should return Jan 1 two years before the current year', () => {
            const result = defaultMinGraphDate()
            expect(result).toEqual(new Date(`1/1/${new Date().getFullYear() - 2}`))
        })
    })

    describe('maxGraphDate', () => {
        it('should return Dec 31 two years after the current year', () => {
            const result = maxGraphDate()
            expect(result).toEqual(new Date(`12/31/${new Date().getFullYear() + 2}`))
        })
    })

    describe('stringify', () => {
        it('should stringify a date the same regardless of format', () => {
            const expected = '03/09/2051'
            expect(stringify(new Date(expected))).toBe(expected)
            expect(stringify(new Date('3/9/2051'))).toBe(expected)
            expect(stringify(new Date('3-9-2051'))).toBe(expected)
            expect(stringify(new Date('03-09-2051'))).toBe(expected)
        })
    })

    describe('roundTo', () => {
        it('should round a floating point value to n digits', () => {
            expect(roundTo(1.23456, 2)).toBe(1.23)
            expect(roundTo(1.235, 2)).toBe(1.24)
            expect(roundTo(1, 2)).toBe(1)
        })
    })

    describe('degreesToDir', () => {
        it('should map boundary degree values to compass directions', () => {
            expect(degreesToDir(0)).toBe('N')
            expect(degreesToDir(11)).toBe('N')
            expect(degreesToDir(12)).toBe('NNE')
            expect(degreesToDir(101)).toBe('E')
            expect(degreesToDir(191)).toBe('S')
            expect(degreesToDir(281)).toBe('W')
            expect(degreesToDir(348)).toBe('NNW')
            expect(degreesToDir(349)).toBe('N')
            expect(degreesToDir(360)).toBe('N')
        })
    })

    describe('toEchartDegrees', () => {
        it('should convert 0-180 to negative form', () => {
            expect(toEchartDegrees(0)).toBe(-0)
            expect(toEchartDegrees(90)).toBe(-90)
            expect(toEchartDegrees(180)).toBe(-180)
        })

        it('should convert 181-359 to 1-179', () => {
            expect(toEchartDegrees(181)).toBe(179)
            expect(toEchartDegrees(270)).toBe(90)
            expect(toEchartDegrees(359)).toBe(1)
        })
    })

    describe('calcWindspeedTickInterval', () => {
        it('should default to 10 when there is no data', () => {
            expect(calcWindspeedTickInterval(null, null)).toBe(10)
        })

        it('should use gusts range when gusts are provided', () => {
            expect(calcWindspeedTickInterval([5, 15], [100])).toBe(3)
        })

        it('should fall back to forecasts range when gusts are null', () => {
            expect(calcWindspeedTickInterval(null, [5, 25])).toBe(5)
        })

        it('should default to 10 when the range is large', () => {
            expect(calcWindspeedTickInterval([5, 35], null)).toBe(10)
        })
    })

    describe('buildCacheKey', () => {
        it('should build a cache key including hilo mode', () => {
            expect(buildCacheKey('welinwq', '01/01/2024', '01/07/2024', true)).toEqual([
                'graph',
                'welinwq',
                '01/01/2024:01/07/2024',
                'hilo',
            ])
        })

        it('should build a cache key for non-hilo mode', () => {
            expect(buildCacheKey('welinwq', '01/01/2024', '01/07/2024', false)).toEqual([
                'graph',
                'welinwq',
                '01/01/2024:01/07/2024',
                'all',
            ])
        })
    })
})
