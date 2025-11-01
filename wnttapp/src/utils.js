export const EpqsUrl = 'https://epqs.nationalmap.gov/v1/json'
export const ClientIpUrl = 'https://api.ipify.org/?format=json'
export const GeocodeUrl = 'https://geocode.maps.co'
export const DefaultMapZoom = 13

// Are we on a touch screen?
export const isTouchScreen =
    'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0

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

// These must be kept in sync with the API
export const NewMoon = 'NM'
export const FirstQuarter = 'FQ'
export const FullMoon = 'FM'
export const LastQuarter = 'LQ'
export const Perigee = 'PG'
// export const Apogee = 'AG'
export const Perihelion = 'PH'
// export const Aphelion = 'AH'

export const SyzygyInfo = {}
SyzygyInfo[NewMoon] = { name: 'New Moon', display: '\u{1F31A}' } // 🌚
SyzygyInfo[FirstQuarter] = { name: 'First Quarter', display: '\u{1F313}' } // 🌓
SyzygyInfo[FullMoon] = { name: 'Full Moon', display: '\u{1F31D}' } // 🌝
SyzygyInfo[LastQuarter] = { name: 'Last Quarter', display: '\u{1F317}' } // 🌗
SyzygyInfo[Perigee] = { name: 'Perigee', display: '\u{1F535}' } //  🔵 \u{1F53B} 🔻 \u{1F53A} 🔺
// SyzygyInfo[Apogee] = { name: 'Apogee', display: '?' }
SyzygyInfo[Perihelion] = { name: 'Perihelion', display: '\u{2600}\u{fe0f}' } // ☀️
// SyzygyInfo[Aphelion] = { name: 'Aphelion', display: '?' }

// Format a Date object for display. Output: "Jan 3, 2026 04:08 PM"
export const formatDatetime = (dt) => {
    if (!dt) {
        return null
    }
    const month = Months[dt.getMonth()]
    const hours = dt.getHours() == 12 ? 12 : (dt.getHours() % 12).toString()
    const minutes = dt.getMinutes().toString().padStart(2, '0')
    const ampm = dt.getHours() >= 12 ? 'PM' : 'AM'
    const formatted = `${month} ${dt.getDate()}, ${dt.getFullYear()} ${hours}:${minutes} ${ampm}`
    return formatted
}

// Format a Date object for display. Output: "Jan 3, 2026"
export const formatDate = (dt) => {
    if (!dt) {
        return null
    }
    const month = Months[dt.getMonth()]
    const formatted = `${month} ${dt.getDate()}, ${dt.getFullYear()}`
    return formatted
}

// CSS Pixel (Logical Pixel) width of Bootstrap's responsive width breakpoints.  Note this is different
// from Device Pixels (Physical) Pixels, which are usually 2 or 3 times as bigger. See DPR (Device Pixel Ratio).
// These values match Bootstrap's responsive breakpoints.
export const SmallBase = 576
export const MediumBase = 768
export const LargeBase = 992
export const XLBase = 1200
export const XXLBase = 1400

// This will allow handling of smart phones or other narrow screen devices.
export const isSmallScreen = () => window.matchMedia(`(max-width: ${MediumBase - 1}px)`).matches

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
    Map: 3,
    About: 4,
    Glossary: 5,
    HelpSyzygy: 6,
    Tutorials: 7,
})

// Round a floating point value to n digits of precision
export const roundTo = (value, digits) => Number(value.toFixed(digits))

// Provide a consistent string version of a date as MM/DD/YYYY for convenience.
export const stringify = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${month}/${day}/${year}`
}

// Build the cache key to use for a given date range.
export function buildCacheKey(stationId, startDate, endDate, hiloMode) {
    return ['graph', `${stationId}:${startDate}:${endDate}`, hiloMode ? 'hilo' : 'all']
}

// Give a Date or a string.  Days may be negative. Returns Date.
export const addDays = (date, days) => {
    const copy = new Date(date)
    copy.setDate(copy.getDate() + days)
    return copy
}

// Pass dates as Dates or string in any order.
export const daysBetween = (date1, date2) => {
    const d1 = new Date(date1)
    const d2 = new Date(date2)
    const oneDay = 24 * 60 * 60 * 1000 // millis in a normal day
    return Math.round(Math.abs((d2 - d1) / oneDay)) // round to account for DST change
}

// Pass a Date or string. Returns same, within min/max settings.
// TODO: This should be moved to Station class
export const limitDate = (date, station) => {
    const d1 = new Date(date)
    const d2 = new Date(Math.max(d1, station.minGraphDate()))
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

export const NotAcceptable = 406 // version out of date
// Use when a call to the API fails.
export const apiErrorResponse = (status) => {
    return status === NotAcceptable
        ? 'It looks like your version may be out of date. Please reload the page.'
        : 'There was a problem fetching the data. Please try again later.'
}
