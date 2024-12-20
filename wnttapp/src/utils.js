export const MinDate = new Date(import.meta.env.VITE_MIN_DATE)
export const MaxDate = new Date(import.meta.env.VITE_MAX_DATE)
export const MaxNumDays = 7 // This could be as high as 10, to support 10 full days of CDMO 15-min data.
export const EpqsUrl = 'https://epqs.nationalmap.gov/v1/json'
export const ClientIpUrl = 'https://api.ipify.org/?format=json'
export const GeocodeUrl = 'https://geocode.maps.co'
export const MaxCustomElevation = 25
export const DefaultNumDays = 7
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
    Glossary: 4,
    About: 5,
})

// Provide a consistent string format of a date. E.g DatePicker
// gives us padded '09/03/2024' while Date.toLocaleDateString() returns '9/3/2024'.
// This avoids having to compare strings by converting to Date, then back to string.
export const stringify = (date) => {
    return date.toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
    })
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
    const oneDay = 24 * 60 * 60 * 1000 // millis in a day
    return Math.round(Math.abs((d2 - d1) / oneDay)) // round to account for DST change
}

// Pass a Date or string. Returns same, within min/max settings.
export const limitDate = (date) => {
    let copy = new Date(date)
    copy = new Date(Math.max(copy, MinDate))
    return new Date(Math.min(copy, MaxDate))
}

// change this when necessary after changes to prevent reading old values
const _local_storage_version = '001'
const _local_storage_prefix = 'wntt'

// If daily is true, we store an object with "day" and "value" keys, with the day
// set to today's date.
export const setLocalStorage = (key, value, daily) => {
    const lsKey = `${_local_storage_prefix}-${key}-${_local_storage_version}`
    try {
        if (daily) {
            const dateKey = stringify(new Date())
            const json = JSON.stringify({ day: dateKey, value: value })
            window.localStorage.setItem(lsKey, json)
        } else {
            window.localStorage.setItem(lsKey, JSON.stringify(value))
        }
    } catch (error) {
        console.error(error)
    }
}

// If daily is true, we expect an object with "day" and "value" keys, and
// return the value only if the day matches the current date.
export const getLocalStorage = (key, daily) => {
    const lsKey = `${_local_storage_prefix}-${key}-${_local_storage_version}`
    try {
        const data = window.localStorage.getItem(lsKey)
        if (data) {
            if (daily) {
                // The value will be an object with "day" and "value"
                const dateKey = stringify(new Date())
                const { day, value } = JSON.parse(data)
                if (day === dateKey) {
                    return value
                } else {
                    // It's an old value, just remove it
                    window.localStorage.removeItem(lsKey)
                    return undefined
                }
            } else {
                return JSON.parse(data)
            }
        } else {
            return undefined
        }
    } catch (error) {
        console.error(error)
        return undefined
    }
}
