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
        Sentry.captureException(error.message)
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
        Sentry.captureException(error.message)
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
        Sentry.captureException(error.message)
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
        Sentry.captureException(error.message)
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
        Sentry.captureException(error.message)
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
        Sentry.captureException(error.message)
        return {}
    }
}

// To be called during app startup. TODO: remove this by Spring 2026.
export const manageStorage = () => {
    // If 002 storage exists, convert it to 003.
    const preKeyCount = Object.keys(localStorage).length
    let numConverted = 0
    const converted = []
    for (let i = 0; i < preKeyCount; i++) {
        const key = localStorage.key(i)
        if (key === '003.main') {
            const v3 = JSON.parse(localStorage.getItem(key))
            if ('bid' in v3) {
                // Rename "bid" to "uid"
                converted.push({ [key]: { ...v3 } }) // makes a copy for logging
                v3.uid = v3.bid
                delete v3.bid
                setMainStorage(v3)
                numConverted += 1
            }
        }
        if (key.endsWith('main-002')) {
            console.log('Converting main-002')
            const v2 = JSON.parse(localStorage.getItem(key))
            converted.push({ [key]: v2 })
            setMainStorage(v2)
            numConverted += 1
        } else if (key.endsWith('welinwq-002')) {
            console.log('Converting welinwq-002')
            const v2 = JSON.parse(localStorage.getItem(key))
            converted.push({ [key]: v2 })
            setPermanentStorage('welinwq', v2)
            numConverted += 1
        } else if (key.endsWith('welinwq-daily-002')) {
            console.log('Converting welinwq-daily-002')
            const v2 = JSON.parse(localStorage.getItem(key))
            converted.push({ [key]: v2 })
            setDailyStorage('welinwq', v2.value, new Date(v2.day))
            numConverted += 1
        }
    }
    const removedKeys = []
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key.endsWith('001') || key.endsWith('002')) {
            removedKeys.push(key)
            localStorage.removeItem(key)
        }
    }

    // Lastly, add some info for this app instance.
    const main = getMainStorage()
    setMainStorage({ ...main, session: crypto.randomUUID().substring(0, 6), started: new Date() })

    const finalStorage = []
    const postKeyCount = Object.keys(localStorage).length
    for (let i = 0; i < postKeyCount; i++) {
        const key = localStorage.key(i)
        finalStorage.push({ [key]: JSON.parse(localStorage.getItem(key)) })
    }

    const info = {
        preKeyCount,
        postKeyCount,
        numConverted,
        converted,
        finalStorage,
        removedKeys,
    }

    console.log(info)
    Sentry.logger.info('Local storage', info)
}
