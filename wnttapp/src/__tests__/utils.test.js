import { describe, it, expect } from 'vitest'
import { addDays, limitDate, stringify, setLocalStorage, getLocalStorage } from '../utils'

describe('utils', () => {
    describe('limitDate', () => {
        it('should return the same date if within min/max settings', () => {
            const date = new Date('2024-05-05')
            const result = limitDate(date)
            expect(result).toEqual(date)
        })

        it('should return the min date if the input date is before the min date', () => {
            const date = new Date('2024-01-01')
            const minDate = new Date(import.meta.env.VITE_MIN_DATE)
            const result = limitDate(date)
            expect(result).toEqual(minDate)
        })

        it('should return the max date if the input date is after the max date', () => {
            const date = new Date('2025-01-01')
            const maxDate = new Date(import.meta.env.VITE_MAX_DATE)
            const result = limitDate(date)
            expect(result).toEqual(maxDate)
        })
    })

    describe('stringify', () => {
        it('should stringify a date the same regardless of format', () => {
            const expected = '03/09/2051'
            expect(stringify(new Date(expected))).toBe(expected)
            expect(stringify(new Date('3/9/2051'))).toBe(expected)
            expect(stringify(new Date('3-9-2051'))).toBe(expected)
            expect(stringify(new Date('03-09-2051'))).toBe(expected)
            expect(stringify(new Date('2051-03-09'))).toBe(expected)
            expect(stringify(new Date('2051-3-9'))).toBe(expected)
        })
    })

    describe('addDays', () => {
        it('should add the specified number of days to the date', () => {
            const date = new Date('2024-05-05')
            const result = addDays(date, 5)
            expect(result).toEqual(new Date('2024-05-10'))
        })

        it('should subtract if specified', () => {
            const date = new Date('2024-05-01')
            const result = addDays(date, -3)
            expect(result).toEqual(new Date('2024-04-28'))
        })
    })

    describe('limitDate', () => {
        // These tests depend on the VITE_MIN_DATE and VITE_MAX_DATE environment variables, set in vitest.config.js
        it('should return the same date if within min/max settings', () => {
            const date = new Date('2024-05-05')
            const result = limitDate(date)
            expect(result).toEqual(date)
        })

        it('should return the min date if the input date is before the min date', () => {
            const date = new Date('2024-01-01')
            const minDate = new Date(import.meta.env.VITE_MIN_DATE)
            const result = limitDate(date)
            expect(result).toEqual(minDate)
        })

        it('should return the max date if the input date is after the max date', () => {
            const date = new Date('2025-01-01')
            const maxDate = new Date(import.meta.env.VITE_MAX_DATE)
            const result = limitDate(date)
            expect(result).toEqual(maxDate)
        })
    })

    describe('localStorage', () => {
        it('should store a scalar value in localStorage', () => {
            setLocalStorage('test', 'value')
            expect(getLocalStorage('test')).toEqual('value')
        })

        it('should store an object in localStorage', () => {
            const obj = { name: 'Alice', age: 42 }
            setLocalStorage('test', obj)
            expect(getLocalStorage('test', false)).toEqual(obj)
        })

        it('should return a value from daily localStorage if day has not changed', () => {
            const obj = { name: 'Alice', age: 42 }
            const date = new Date()
            setLocalStorage('test', obj, true, date)
            expect(getLocalStorage('test', true, date)).toEqual(obj)
        })

        it('should return undefined from daily localStorage if day has changed', () => {
            const obj = { name: 'Alice', age: 42 }
            const date1 = new Date()
            const date2 = addDays(date1, 1)
            setLocalStorage('test', obj, true, date1)
            expect(getLocalStorage('test', true, date2)).toBeUndefined
        })
    })
})
