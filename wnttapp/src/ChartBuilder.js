import NewMoonImg from './images/util/moon-new.png'
import FirstQuarterImg from './images/util/moon-1q.png'
import FullMoonImg from './images/util/moon-full.png'
import LastQuarterImg from './images/util/moon-3q.png'
import PerigeeImg from './images/util/perigee.png'
import PerihelionImg from './images/util/perihelion.png'
import { ScreenSize, getScreenSize } from './utils'

// These must be kept in sync with the API
export const NewMoon = 'NM'
export const FirstQuarter = 'FQ'
export const FullMoon = 'FM'
export const LastQuarter = 'LQ'
export const Perigee = 'PG'
export const Perihelion = 'PH'

export const Dimension = Object.freeze({
    DateTime: 'dt',
    RecordTide: 'rec',
    HighestAnnual: 'highann',
    Syzygy: 'syzygy',
    SyzygyUrl: 'syurl',
    CustomElevation: 'custom-elevation',
    MeanHighWater: 'mean-high-water',
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
})

// For uniquely identifying traces in event handling. Order doesn't matter, so long as they are unique.
export const LegendId = Object.freeze({
    RecordTide: 1,
    HighestAnnualPredicted: 2,
    MeanHighWater: 3,
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
    highestAnnualPrediction,
    station,
    customElevationMllw,
) => {
    // Build a second dataset for data that's better built here than the backend.
    const localDims = [
        { name: Dimension.DateTime, type: 'time' },
        { name: Dimension.RecordTide, type: 'number' },
        { name: Dimension.HighestAnnual, type: 'number' },
        { name: Dimension.MeanHighWater, type: 'number' },
        ...(customElevationMllw ? [Dimension.CustomElevation] : []),
        ...(syzygyData ? [Dimension.Syzygy, Dimension.SyzygyUrl] : []),
    ]
    const localBlob = timeline.map((dt) => {
        const row = [
            dt,
            station.recordTideMllw(),
            highestAnnualPrediction,
            station.meanHighWaterMllw,
        ]
        if (customElevationMllw) {
            row.push(customElevationMllw)
        }
        if (syzygyData) {
            if (dt in syzygyData) {
                const code = syzygyData[dt][0]
                row.push(...[1, getSyzygyUrl(code)])
            } else {
                row.push(...[null, null])
            }
        }
        return row
    })

    return { source: localBlob, dimensions: localDims }
}

export const getSyzygyUrl = (code) => {
    const prefix = 'image://'
    switch (code) {
        case NewMoon:
            return prefix + NewMoonImg
        case FirstQuarter:
            return prefix + FirstQuarterImg
        case FullMoon:
            return prefix + FullMoonImg
        case LastQuarter:
            return prefix + LastQuarterImg
        case Perigee:
            return prefix + PerigeeImg
        case Perihelion:
            return prefix + PerihelionImg
        default:
            return null
    }
}

export const getResponsiveGridDefs = (showingWind) => {
    const screenSize = getScreenSize()

    const syzygyTop = '15%'
    const syzygyHeight = '5%'
    const tideGridTop = '20%'
    const windGridTop = '54%'
    const windGridHeight = '25%'
    const leftMargin = '8%'

    var gridWidth
    switch (screenSize) {
        case ScreenSize.Small:
            gridWidth = '87%'
            break
        case ScreenSize.Medium:
            gridWidth = '55%'
            break
        case ScreenSize.Large:
            gridWidth = '62%'
            break
        case ScreenSize.XLarge:
            gridWidth = '67%'
            break
        case ScreenSize.XXLarge:
            gridWidth = '70%'
            break
        default: // xsmall
            gridWidth = '87%'
    }
    const tideGridHeight = showingWind ? '30%' : '57%'
    const grid = [
        // The top section of the grid is only for the moon/sun symbols
        { left: leftMargin, top: syzygyTop, width: gridWidth, height: syzygyHeight },
        { left: leftMargin, top: tideGridTop, width: gridWidth, height: tideGridHeight },
        ...(showingWind ?
            [{ left: leftMargin, top: windGridTop, width: gridWidth, height: windGridHeight }]
        :   []),
    ]
    return grid
}
