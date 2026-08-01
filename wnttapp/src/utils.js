import { format } from 'date-fns'

export const WELLS_STATION_ID = 'welinwq'
export const EpqsUrl = 'https://epqs.nationalmap.gov/v1/json'
export const GeocodeUrl = 'https://geocode.maps.co'
export const OpenMeteoUrl = 'https://open-meteo.com'
export const TidesCurrentsUrl = 'https://tidesandcurrents.noaa.gov/tide_predictions.html'
export const TidesCurrentsStationUrl = 'https://tidesandcurrents.noaa.gov/stationhome.html?id='
export const TidesCurrentsDatumsUrl = 'https://tidesandcurrents.noaa.gov/datum_options.html'
export const SurgeUrl =
    'https://slosh.nws.noaa.gov/etsurge2.0/index.php?glat=All&display=0&type=stormtide&base=USGSTopo'
export const getSurgeStationUrl = (noaaStationId) => {
    return `https://slosh.nws.noaa.gov/etsurge2.0/index.php?stid=${noaaStationId}&datum=MLLW&show=0-0-1-1-0`
}

export const HttpNotAcceptableCode = 406 // version out of date

// CSS Pixel (Logical Pixel) width of Bootstrap's responsive width breakpoints.  Note this is different
// from Device Pixels (Physical) Pixels, which are usually 2 or 3 times as bigger. See DPR (Device Pixel Ratio).
// These values match Bootstrap's responsive breakpoints.
export const SmallBase = 576
export const MediumBase = 768
export const LargeBase = 992
export const XLBase = 1200
export const XXLBase = 1400

export const ScreenSize = Object.freeze({
    XSmall: 'xsmall',
    Small: 'small',
    Medium: 'medium',
    Large: 'large',
    XLarge: 'xlarge',
    XXLarge: 'xxlarge',
})

export const getScreenSize = () => {
    const width = window.innerWidth
    if (width >= XXLBase) {
        return ScreenSize.XXLarge
    }
    if (width >= XLBase) {
        return ScreenSize.XLarge
    }
    if (width >= LargeBase) {
        return ScreenSize.Large
    }
    if (width >= MediumBase) {
        return ScreenSize.Medium
    }
    if (width >= SmallBase) {
        return ScreenSize.Small
    }
    return ScreenSize.XSmall
}

// This will allow handling of smart phones or other narrow screen devices.
export const isSmallScreen = () => window.matchMedia(`(max-width: ${MediumBase - 1}px)`).matches

// Are we on a touch screen?
export const isTouchScreen =
    'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0

// Returns the maximnum number of days to allow on the graph. We limit this based on viewport width, so that
// there are at least as many pixels in the graph as data points (96 per day). If not, some data points would
// be skipped.
export const getMaxNumDays = () => {
    const width = window.innerWidth
    if (width >= XLBase) {
        return 7
    }
    if (width >= LargeBase) {
        return 6
    }
    if (width >= MediumBase) {
        return 4
    }
    if (width >= SmallBase) {
        return 3
    }
    return 2
}

export const getScreenBase = () => {
    const width = window.innerWidth
    if (width >= XXLBase) {
        return XXLBase
    }
    if (width >= XLBase) {
        return XLBase
    }
    if (width >= LargeBase) {
        return LargeBase
    }
    if (width >= MediumBase) {
        return MediumBase
    }
    if (width >= SmallBase) {
        return SmallBase
    }
    return 0
}

// We compute the min/max dates based on current year, rather than hardcoding them. We must
// compute them every time they are requested, in case the year changes while the app is running.
// The graph API has the same limits, so these should be kept in sync.
export const defaultMinGraphDate = () => {
    return new Date(`1/1/${new Date().getFullYear() - 2}`)
}

export const maxGraphDate = () => {
    const year = new Date().getFullYear()
    return new Date(`12/31/${year + 2}`)
}

export const Page = Object.freeze({
    Home: 1,
    Graph: 2,
    About: 3,
    Glossary: 4,
    HelpSyzygy: 5,
})

// Round a floating point value string to n digits of precision
export const roundTo = (value, digits) => Number(value.toFixed(digits))

// Provide a consistent string version of a date as MM/DD/YYYY for convenience.
export const stringify = (date) => {
    return format(date, 'MM/dd/yyyy')
}

// Build the cache key to use for a given date range.
export function buildCacheKey(stationId, startDateStr, endDateStr, hiloMode) {
    return ['graph', stationId, `${startDateStr}:${endDateStr}`, hiloMode ? 'hilo' : 'all']
}

// Calculate a reasonable tick interval for wind graphs so it's
// just the right amount of clutter.
export const calcWindspeedTickInterval = (gusts, forecasts) => {
    let interval = 10
    if (gusts !== null || forecasts !== null) {
        const range = gusts ? Math.max(...gusts) : Math.max(...forecasts)
        if (range < 20) {
            interval = 3
        } else if (range < 30) {
            interval = 5
        }
    }
    return interval
}

export const degreesToDir = (degrees) => {
    let direction

    if (degrees <= 11) direction = 'N'
    else if (degrees <= 33) direction = 'NNE'
    else if (degrees <= 56) direction = 'NE'
    else if (degrees <= 78) direction = 'ENE'
    else if (degrees <= 101) direction = 'E'
    else if (degrees <= 123) direction = 'ESE'
    else if (degrees <= 146) direction = 'SE'
    else if (degrees <= 168) direction = 'SSE'
    else if (degrees <= 191) direction = 'S'
    else if (degrees <= 213) direction = 'SSW'
    else if (degrees <= 236) direction = 'SW'
    else if (degrees <= 258) direction = 'WSW'
    else if (degrees <= 281) direction = 'W'
    else if (degrees <= 303) direction = 'WNW'
    else if (degrees <= 326) direction = 'NW'
    else if (degrees <= 348) direction = 'NNW'
    else direction = 'N'
    return direction
}

// echarts uses 0 ... -180 for 0 ... 180, and 1 ... 179 for 359 ... 181
export const toEchartDegrees = (deg) => (deg <= 180 ? -deg : 360 - deg)
