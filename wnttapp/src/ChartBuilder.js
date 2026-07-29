import { getSyzygyUrl } from './Syzygy'
import { minutesBetween } from './utils'

// These constants drive optimal placement settings in the EChart.  Adjust as needed.
const LegendWidthPix = 220 // width of our legend
const GridLeftFactor = 0.08 // this is treated by echarts as a minimum; it's widened when labels don't fit on small screens
const ChartDisplayFactor = 0.833 // this is 10/12 -- the graph is in the middle of a bootstrap row of [col-1 + col-10 + col-1]
const PrevFactor = 0.083 // 1/12 of screen width, size of the Prev/Next columns

export const Dimension = Object.freeze({
    DateTime: 'dt',
    RecordTide: 'rec',
    CustomElevation: 'custom-elevation',
    HighestAnnualPredicted: 'high-annual',
    // These must match the data property name returned from the back end.
    HistTides: 'hist-tides',
    AstroTides: 'astro-tides',
    RecordedStormSurge: 'past-surge',
    WindSpeeds: 'wind-speeds',
    WindGusts: 'wind-gusts',
    ForecastWindSpeeds: 'forecast-wind-speeds',
    PastSurge: 'past-surge',
    ProjectedStormTide: 'future-tide',
    ProjectedStormSurge: 'future-surge',
    HistTidesLabels: 'hist-tides-labels',
    WindDir: 'wind-dir',
    AstroTidesLabels: 'astro-tides-labels',
    ForecastWindDir: 'forecast-wind-dir',
})

// For uniquely identifying traces in event handling. Values don't matter, so long as they are unique.
export const LegendId = Object.freeze({
    RecordTide: 1,
    HighestAnnualPredicted: 2,
    CustomElevation: 4,
    ObservedTide: 5,
    PredictedTide: 6,
    RecordedStormSurge: 7,
    ProjectedStormTide: 8,
    ProjectedStormSurge: 9,
    WindGust: 10,
    WindSpeed: 11,
    WindForecast: 12,
    XPastStormTideCheck: 13,
    XPastStormTideCheckBias1: 14,
    XPastStormTideCheckBias2: 15,
    XPastStormSurgeCheck: 16,
    XPastStormSurgeCheckBias1: 17,
    XPastStormSurgeCheckBias2: 18,
})

export const buildSyzygyData = (syzygyData, blob, gridWidth) => {
    const copy = [...syzygyData]
    const startDate = new Date(blob[0][0])
    const endDate = new Date(blob[blob.length - 1][0])
    const timelineMinutes = minutesBetween(startDate, endDate)

    // Calculate pixels to move symbol from its assigned time to its real location
    const getOffset = (dt, realDt) => {
        const actualOffet = (minutesBetween(startDate, new Date(dt)) / timelineMinutes) * gridWidth
        const expectedOffset =
            (minutesBetween(startDate, new Date(realDt)) / timelineMinutes) * gridWidth
        return expectedOffset - actualOffet
    }

    // Each element in the blob array is a column of data, always starting with datetime.
    // We'll assign the N syzygy events to the first N column[s] of data, and shift their positions
    // with symbolOffset. This frees us from mapping forcing the timelines to contain these event times, a
    // practice that causes problems with the connectNulls flags on series.
    return blob.map((rec) => {
        const dt = rec[0]
        if (copy.length > 0) {
            const event = copy.shift()
            return {
                value: [dt, 1],
                symbol: getSyzygyUrl(event.code),
                symbolSize: 25,
                symbolOffset: [getOffset(dt, event.real_dt), 0],
                code: event.code,
                realDt: event.real_dt,
            }
        } else {
            return { value: [dt, 0] }
        }
    })
}

export const buildLocalDataSet = (blob, station, highestAnnualPrediction, customElevationMllw) => {
    // Build a second dataset for data that's better built here than the backend.
    const localDims = [
        { name: Dimension.DateTime, type: 'time' },
        { name: Dimension.RecordTide, type: 'number' },
        { name: Dimension.HighestAnnualPredicted, type: 'number' },
        ...(customElevationMllw ? [Dimension.CustomElevation] : []),
    ]
    const localBlob = blob.map((rec) => {
        const dt = rec[0] // the 1st element of every column is the datetime string
        const col = [dt, station.recordTideMllw(), highestAnnualPrediction]
        if (customElevationMllw) {
            col.push(customElevationMllw)
        }
        return col
    })

    return { source: localBlob, dimensions: localDims }
}

// Based on current screen width, determine best placement of the grid and legend and grid width so it looks
// great on any screen size.  showingLegend should be false on small screens.
export const getResponsivePlacement = (showingLegend) => {
    const screenPix = document.body.clientWidth // window.innerWidth counts scrollbar space as usable
    const legendMarginPix = screenPix >= 1000 ? 20 : 10 // We can afford a wider margin on big screens
    const centerColWidthPix = Math.ceil(screenPix * ChartDisplayFactor)
    const gridLeftPix = Math.ceil(centerColWidthPix * GridLeftFactor)
    const leftColWidthPix = Math.ceil(screenPix * PrevFactor)

    const legendLeftPix = centerColWidthPix - LegendWidthPix - legendMarginPix
    const gridWidthPix =
        showingLegend ?
            centerColWidthPix - gridLeftPix - LegendWidthPix - legendMarginPix * 2
        :   centerColWidthPix - gridLeftPix * 2

    return { gridLeftPix, gridWidthPix, legendLeftPix, leftColWidthPix }
}

export const buildGridLayout = (showingWind, placement, bgColor) => {
    const syzygyTop = '17%'
    const syzygyHeight = '3%'
    const tideGridTop = '20%'
    const windGridTop = '54%'
    const windGridHeight = '25%'

    const tideGridHeight = showingWind ? '30%' : '57%'
    const grid = [
        // The top section of the grid is only for the moon/sun symbols
        {
            left: placement.gridLeftPix,
            top: syzygyTop,
            width: placement.gridWidthPix,
            height: syzygyHeight,
        },
        {
            show: true,
            backgroundColor: bgColor,
            left: placement.gridLeftPix,
            top: tideGridTop,
            width: placement.gridWidthPix,
            height: tideGridHeight,
        },
        ...(showingWind ?
            [
                {
                    show: true,
                    backgroundColor: bgColor,
                    left: placement.gridLeftPix,
                    top: windGridTop,
                    width: placement.gridWidthPix,
                    height: windGridHeight,
                },
            ]
        :   []),
    ]
    return grid
}
