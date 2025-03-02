export const MinDate = new Date(import.meta.env.VITE_MIN_DATE)
export const MaxDate = new Date(import.meta.env.VITE_MAX_DATE)
export const MaxNumDays = 7 // This could be as high as 10, to support 10 full days of CDMO 15-min data.
export const EpqsUrl = 'https://epqs.nationalmap.gov/v1/json'
export const ClientIpUrl = 'https://api.ipify.org/?format=json'
export const GeocodeUrl = 'https://geocode.maps.co'
export const MaxCustomElevation = 25
export const DefaultNumDays = 4
export const MapBounds = [
    [44.01, -70.73],
    [43.01, -69.8],
]
export const DefaultMapCenter = { lat: 43.3201432976, lng: -70.5639195442 }
export const DefaultMapZoom = 13

export const Page = Object.freeze({
    Home: 1,
    Graph: 2,
    Map: 3,
    Help: 4,
    About: 5,
})

// Provide a consistent string version of a date as MM/DD/YYYY for convenience.
export const stringify = (date) => {
    const year = date.getUTCFullYear()
    const month = String(date.getUTCMonth() + 1).padStart(2, '0')
    const day = String(date.getUTCDate()).padStart(2, '0')
    return `${month}/${day}/${year}`
}
// Build the cache key to use for a given date range.
export function buildCacheKey(startDate, endDate) {
    return ['graph', startDate + ':' + endDate]
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
    const d2 = new Date(Math.max(d1, MinDate))
    return new Date(Math.min(d2, MaxDate))
}

// Compute the default date range for the graph.
export const getDefaultDates = () => {
    const today = new Date()
    return {
        defaultStart: today,
        defaultEnd: addDays(today, DefaultNumDays - 1),
    }
}
