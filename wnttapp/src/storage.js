import * as Sentry from '@sentry/react'
import { stringify } from './utils'

// This is a facade for Local Storage on the browser. There are 2 storage object types used:
// 1. A "main.<version>" which contains any global values for the app. get/setMainStorage()
// 2. "<stationid>.<version>": 1 for each station the user has viewed.  This object has 2 sections:
//    - "daily" : properties that will be used only on the same calendar day, then removed. get/setDailyStorage()
//    - "perm" : properties that last indefinitely. get/setPermanentStorage()
// The fact that the daily and permanent station-specific properties are actually stored under the same local
// storage key is an implementation detail, and not relevant to callers.

const StorageVersion = '003'

const storageKey = (key) => {
    return `${StorageVersion}.${key}`
}

// Store a non-station-specific object in local storage.
export const setMainStorage = (value) => {
    try {
        localStorage.setItem(storageKey('main'), JSON.stringify(value))
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
    }
}

// Retrieve a non-station-specific object with no expiration from local storage.
// Returns an empty object if the key does not exist.
export const getMainStorage = () => {
    try {
        const data = localStorage.getItem(storageKey('main'))
        return data ? JSON.parse(data) : {}
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
        return {}
    }
}

// Store a station-specific permanent object in local storage.
export const setPermanentStorage = (stationId, value) => {
    const key = storageKey(stationId)
    try {
        const raw = localStorage.getItem(key)
        const data = raw ? JSON.parse(raw) : { daily: {} }
        localStorage.setItem(storageKey(stationId), JSON.stringify({ ...data, perm: value }))
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
    }
}

// Retrieve the station-specific permanent object from local storage, which is the "perm" property of the stored object.
// Returns an empty object if the key does not exist.
export const getPermanentStorage = (stationId) => {
    if (!stationId) {
        return {}
    }
    const key = storageKey(stationId)
    try {
        const raw = localStorage.getItem(key)
        const data = raw ? JSON.parse(raw) : {}
        return data.perm ?? {}
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
        return {}
    }
}

// Store a station-specific daily object in local storage.
export const setDailyStorage = (stationId, value, date = new Date()) => {
    const key = storageKey(stationId)
    try {
        const raw = localStorage.getItem(key)
        const data = raw ? JSON.parse(raw) : { perm: {} }
        const newDaily = { day: stringify(date), ...value }
        localStorage.setItem(storageKey(stationId), JSON.stringify({ ...data, daily: newDaily }))
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
    }
}

// Retrieve the station-specific daily object from local storage.  Returns an empty object if the
// key does not exist. Deletes the stored data and returns {} if it is expired.
export const getDailyStorage = (stationId) => {
    if (!stationId) {
        return {}
    }
    const key = storageKey(stationId)
    const todayStr = stringify(new Date())
    try {
        const raw = localStorage.getItem(key)
        const data = raw ? JSON.parse(raw) : {}

        if (data.daily?.day === todayStr) {
            return data.daily
        }
        if (data.daily) {
            // The daily fields have expired, so remove them.
            localStorage.setItem(key, JSON.stringify({ ...data, daily: {} }))
        }
        return {}
    } catch (error) {
        console.error(error.message)
        Sentry.captureException(error)
        return {}
    }
}
