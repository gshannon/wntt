export const EpqsUrl = 'https://epqs.nationalmap.gov/v1/json'
export const ClientIpUrl = 'https://api.ipify.org/?format=json'
export const GeocodeUrl = 'https://geocode.maps.co'
export const MapBounds = [
    [44.01, -70.73],
    [43.01, -69.8],
]
export const DefaultMapCenter = { lat: 43.3201432976, lng: -70.5639195442 }
export const DefaultMapZoom = 13
export const MaxCustomElevationMllw = 25 // Prevents the graph scale from getting skewed

// Are we on a touch screen?
export const isTouchScreen =
    'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0

// This will allow handling of smart phones or other narrow screen devices.
export const isSmallScreen = () => window.matchMedia(`(max-width: ${MediumBase - 1}px)`).matches

export const Months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
]

// CSS Pixel (Logical Pixel) width of Bootstrap's responsive width breakpoints.  Note this is different
// from Device Pixels (Physical) Pixels, which are usually 2 or 3 times as bigger. See DPR (Device Pixel Ratio).
// These values match Bootstrap's responsive breakpoints.
export const SmallBase = 576
export const MediumBase = 768
export const LargeBase = 992
export const XLBase = 1200
export const XXLBase = 1400

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
// Note that the graph API has the same limits, so these should be kept in sync.
export const minGraphDate = () => {
    const year = new Date().getFullYear()
    return new Date(`1/1/${year - 2}`)
}
export const maxGraphDate = () => {
    const year = new Date().getFullYear()
    return new Date(`12/31/${year + 2}`)
}

export const Page = Object.freeze({
    Home: 1,
    Graph: 2,
    Map: 3,
    Glossary: 4,
    About: 5,
    Help: 6,
})

// Round a floating point value to n digits of precision
export const roundTo = (value, digits) => Number(value.toFixed(digits))

export const navd88ToMllw = (navd88) => {
    if (navd88 == null) {
        return null
    }
    return roundTo(navd88 + parseFloat(import.meta.env.VITE_NAVD88_MLLW_CONVERSION), 2)
}

export const mllwToNavd88 = (mllw) => {
    if (mllw == null) {
        return null
    }
    return roundTo(mllw - parseFloat(import.meta.env.VITE_NAVD88_MLLW_CONVERSION), 2)
}

export const maxCustomElevationNavd88 = () => mllwToNavd88(MaxCustomElevationMllw)

// Provide a consistent string version of a date as MM/DD/YYYY for convenience.
export const stringify = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${month}/${day}/${year}`
}

// Build the cache key to use for a given date range.
export function buildCacheKey(startDate, endDate, hiloMode) {
    return ['graph', startDate + ':' + endDate, hiloMode ? 'hilo' : 'normal']
}

// Give a Date or a string.  Days may be negative. Returns Date.
export const addDays = (date, days) => {
    const copy = new Date(date)
    copy.setDate(copy.getDate() + days)
    return copy
}

// Pass dates as Dates or string in any order.
export const dateDiff = (date1, date2) => {
    const d1 = new Date(date1)
    const d2 = new Date(date2)
    const oneDay = 24 * 60 * 60 * 1000 // millis in a normal day
    return Math.round(Math.abs((d2 - d1) / oneDay)) // round to account for DST change
}

// Pass a Date or string. Returns same, within min/max settings.
export const limitDate = (date) => {
    const d1 = new Date(date)
    const d2 = new Date(Math.max(d1, minGraphDate()))
    return new Date(Math.min(d2, maxGraphDate()))
}

// Compute the default date range for the graph. Returns mm/dd/yyyy strings.
export const getDefaultDateStrings = () => {
    const today = new Date()
    const defaultDays = window.innerWidth >= MediumBase ? 4 : 1
    return {
        defaultStartStr: stringify(today),
        defaultEndStr: stringify(addDays(today, defaultDays - 1)),
    }
}
