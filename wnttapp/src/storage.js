import { stringify } from './utils'

const _local_storage_version = '002'
const _local_storage_prefix = 'wntt'

const toStorageKey = (key, daily) => {
    const ifdaily = daily ? 'daily-' : ''
    return `${_local_storage_prefix}-${key}-${ifdaily}${_local_storage_version}`
}

// Store a non-station-specific object in localStorage, with no expiration.
export const setGlobalPermanentStorage = (value) => {
    const key = toStorageKey('main', false)
    try {
        window.localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
        console.error(error)
    }
}

// Store a non-station-specific object in localStorage for today only.
// The date param is for testing only, so it can be set to any date.
export const setGlobalDailyStorage = (value, date = new Date()) => {
    try {
        const dateKey = stringify(date)
        const json = JSON.stringify({ day: dateKey, value: value })
        window.localStorage.setItem(toStorageKey('main', true), json)
    } catch (error) {
        console.error(error)
    }
}

// Store a station-specific object in localStorage, with no expiration.
export const setStationPermanentStorage = (stationId, value) => {
    try {
        window.localStorage.setItem(toStorageKey(stationId, false), JSON.stringify(value))
    } catch (error) {
        console.error(error)
    }
}

// Store a station-specific object in localStorage, for today only.
// The date param is for testing only, so it can be set to any date.
export const setStationDailyStorage = (stationId, value, date = new Date()) => {
    try {
        const dateKey = stringify(date)
        const json = JSON.stringify({ day: dateKey, value: value })
        window.localStorage.setItem(toStorageKey(stationId, true), json)
    } catch (error) {
        console.error(error)
    }
}

// Retrieve a non-station-specific object with no expiration from localStorage.
// Returns an empty object if the key does not exist.
export const getGlobalPermanentStorage = () => {
    try {
        const data = window.localStorage.getItem(toStorageKey('main', false))
        if (data) {
            return JSON.parse(data)
        } else {
            return {}
        }
    } catch (error) {
        console.error(error)
        return {}
    }
}

// Retrieve a non-station-specific object with daily expiration from localStorage.
// If the key does not exist, returns an empty object.  If key exists but the stored date does not
// match today's date, it will delete the object with that key and return an empty object.
export const getGlobalDailyStorage = (date = new Date()) => {
    const key = toStorageKey('main', true)
    try {
        const data = window.localStorage.getItem(key)
        if (data) {
            // The value will be an object with "day" and "value"
            const dateKey = stringify(date)
            const { day, value } = JSON.parse(data)
            if (day === dateKey) {
                return value
            } else {
                // It's an old value, just remove it
                window.localStorage.removeItem(key)
                return {}
            }
        } else {
            return {}
        }
    } catch (error) {
        console.error(error)
        return {}
    }
}

// Retrieve a station-specific object with no expiration from localStorage.
// Returns an empty object if the key does not exist.
export const getStationPermanentStorage = (stationId) => {
    if (!stationId) {
        return {}
    }
    try {
        const data = window.localStorage.getItem(toStorageKey(stationId, false))
        if (data) {
            return JSON.parse(data)
        } else {
            return {}
        }
    } catch (error) {
        console.error(error)
        return {}
    }
}

// Retrieve a station-specific object with daily expiration from localStorage.
// If the key does not exist, returns an empty object.  If key exists but the stored date does not
// match today's date, it will delete the object with that key and return an empty object.
export const getStationDailyStorage = (stationId, date = new Date()) => {
    if (!stationId) {
        return {}
    }
    const key = toStorageKey(stationId, true)
    try {
        const data = window.localStorage.getItem(key)
        if (data) {
            // The value will be an object with "day" and "value"
            const dateKey = stringify(date)
            const { day, value } = JSON.parse(data)
            if (day === dateKey) {
                return value
            } else {
                // It's an old value, just remove it
                window.localStorage.removeItem(key)
                return {}
            }
        } else {
            return {}
        }
    } catch (error) {
        console.error(error)
        return {}
    }
}
