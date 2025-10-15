import { describe, it, expect } from 'vitest'
import { Overlap_pixel_shift, Overlap_x_millis, space_annotations } from '../ChartBuilder'

describe('annotations', () => {
    const timeline = [new Date('2025-09-21T00:00:00'), null, null, new Date('2025-09-22T00:00:00')]

    // all annotations arrays must be in date order

    describe('overlap handled with 2 syzygy values on timeline', () => {
        it('avoid overlap of points a and b near left margin', () => {
            const date1 = new Date(timeline[0])
            const date2 = new Date(date1)
            date2.setTime(date2.getTime() + Overlap_x_millis - 1)
            const annotations = [{ x: date1 }, { x: date2 }]
            const expected = [{ x: date1 }, { x: date2, xshift: Overlap_pixel_shift }]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })

        it('avoid overlap of points a and b near right margin', () => {
            const date1 = new Date(timeline.at(-1))
            const date2 = new Date(date1)
            date2.setTime(date2.getTime() - Overlap_x_millis + 1)
            const annotations = [{ x: date1 }, { x: date2 }]
            const expected = [{ x: date1, xshift: -Overlap_pixel_shift }, { x: date2 }]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })
    })

    describe('overlap handled with 3 syzygy values on timeline', () => {
        it('avoid overlap of points a and b near left margin', () => {
            const date1 = new Date(timeline[0])
            const date2 = new Date(date1)
            date2.setTime(date2.getTime() + Overlap_x_millis - 1)
            const date3 = new Date(date2)
            date3.setTime(date3.getTime() + Overlap_x_millis * 2)
            const annotations = [{ x: date1 }, { x: date2 }, { x: date3 }]
            const expected = [{ x: date1 }, { x: date2, xshift: Overlap_pixel_shift }, { x: date3 }]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })

        it('avoid overlap of points b and c near right margin', () => {
            const date3 = new Date(timeline.at(-1))
            const date2 = new Date(date3)
            date2.setTime(date2.getTime() - Overlap_x_millis + 1)
            const date1 = new Date(date2)
            date1.setTime(date1.getTime() - Overlap_x_millis * 2)
            const annotations = [{ x: date1 }, { x: date2 }, { x: date3 }]
            const expected = [
                { x: date1 },
                { x: date2, xshift: -Overlap_pixel_shift },
                { x: date3 },
            ]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })
        it('avoid overlap of points a, b and c near right margin', () => {
            const date3 = new Date(timeline.at(-1))
            const date2 = new Date(date3)
            date2.setTime(date2.getTime() - Overlap_x_millis + 1)
            const date1 = new Date(date2)
            date1.setTime(date1.getTime() - Overlap_x_millis + 1)
            const annotations = [{ x: date1 }, { x: date2 }, { x: date3 }]
            const expected = [
                { x: date1, xshift: -Overlap_pixel_shift * 2 },
                { x: date2, xshift: -Overlap_pixel_shift },
                { x: date3 },
            ]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })

        it('with 3 avoid overlap of points a, b and c not near any margin', () => {
            const date1 = new Date(timeline[0])
            date1.setTime(date1.getTime() + Overlap_x_millis)
            const date2 = new Date(date1)
            date2.setTime(date2.getTime() + Overlap_x_millis - 1)
            const date3 = new Date(date2)
            date3.setTime(date3.getTime() + Overlap_x_millis - 1)
            const annotations = [{ x: date1 }, { x: date2 }, { x: date3 }]
            const expected = [
                { x: date1 },
                { x: date2, xshift: Overlap_pixel_shift },
                { x: date3, xshift: Overlap_pixel_shift * 2 },
            ]
            space_annotations(annotations, timeline)
            expect(annotations).toEqual(expected)
        })
    })
})
