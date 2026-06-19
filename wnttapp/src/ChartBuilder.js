import { getSyzygyUrl } from './Syzygy'

// These constants drive optimal placement settings in the EChar.  Adjust if needed.
const LegendWidthPix = 220 // width of our legend currently
const GridLeftFactor = 0.08 // this is treated by echarts as a minimum; it's widened when labels don't fit on small screens
const ChartDisplayFactor = 0.833 // this is 10/12 -- the graph is in the middle of a bootstrap row of [col-1 + col-10 + col-1]

export const Dimension = Object.freeze({
    DateTime: 'dt',
    RecordTide: 'rec',
    Syzygy: 'syzygy',
    SyzygyUrl: 'syurl',
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

export const buildLocalDataSet = (
    timeline,
    syzygyData,
    station,
    highestAnnualPrediction,
    customElevationMllw,
) => {
    // Build a second dataset for data that's better built here than the backend.
    const localDims = [
        { name: Dimension.DateTime, type: 'time' },
        { name: Dimension.RecordTide, type: 'number' },
        { name: Dimension.HighestAnnualPredicted, type: 'number' },
        ...(customElevationMllw ? [Dimension.CustomElevation] : []),
        ...(syzygyData ? [Dimension.Syzygy, Dimension.SyzygyUrl] : []),
    ]
    const localBlob = timeline.map((dt) => {
        const row = [dt, station.recordTideMllw(), highestAnnualPrediction]
        if (customElevationMllw) {
            row.push(customElevationMllw)
        }
        if (syzygyData) {
            if (dt in syzygyData) {
                const code = syzygyData[dt]
                row.push(...[1, getSyzygyUrl(code)])
            } else {
                row.push(...[null, null])
            }
        }
        return row
    })

    return { source: localBlob, dimensions: localDims }
}

// Based on current screen width, determine best placement of the grid and legend and grid width so it looks
// great on any screen size.  showingLegend should be false on small screens.
export const getOptimalPlacement = (showingLegend) => {
    const screenPix = window.innerWidth
    const legendMarginPix = screenPix >= 1000 ? 20 : 10 // We can afford a wider margin on big screens
    const colWidthPix = Math.ceil(screenPix * ChartDisplayFactor)
    const gridLeftPix = Math.ceil(colWidthPix * GridLeftFactor)

    const legendLeftPix = colWidthPix - LegendWidthPix - legendMarginPix
    const gridWidthPix =
        showingLegend ?
            colWidthPix - gridLeftPix - LegendWidthPix - legendMarginPix * 2
        :   colWidthPix - gridLeftPix * 2

    return { gridLeftPix, gridWidthPix, legendLeftPix }
}

export const getResponsiveGridDefs = (showingWind, placement, bgColor) => {
    const syzygyTop = '15%'
    const syzygyHeight = '5%'
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
