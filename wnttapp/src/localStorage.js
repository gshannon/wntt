import { stringify } from './utils'

// change this when necessary after changes to prevent reading old values
const _local_storage_version = '001'
const _local_storage_prefix = 'wntt'

const storageKey = (name) => `${_local_storage_prefix}-${name}-${_local_storage_version}`

// Store an object in localStorage.
export const setLocalStorage = (key, value) => {
    try {
        window.localStorage.setItem(storageKey(key), JSON.stringify(value))
    } catch (error) {
        console.error(error)
    }
}

// Store an object with "day" and "value" keys, with the day set to today's date.
// This is used for values that should only be valid for today. Value should be
// retrieved with getDailyLocalStorage, which will return the value only if
// the stored date matches today's date.
// The date param is for testing only, so it can be set to any date.
export const setDailyLocalStorage = (key, value, date = new Date()) => {
    try {
        const dateKey = stringify(date)
        const json = JSON.stringify({ day: dateKey, value: value })
        window.localStorage.setItem(storageKey(key), json)
    } catch (error) {
        console.error(error)
    }
}

// Retrieve an object from localStorage, which was stored with setLocalStorage. Returns
// an empty object if the key does not exist.
export const getLocalStorage = (key) => {
    try {
        const data = window.localStorage.getItem(storageKey(key))
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

// Retrieve an object from localStorage, which was stored with setDailyLocalStorage.
// If the key does not exist, returns an empty object.  If key exists but the stored date does not
// match today's date, it will delete the object with that key and return an empty object.
export const getDailyLocalStorage = (key, date = new Date()) => {
    const lsKey = storageKey(key)
    try {
        const data = window.localStorage.getItem(lsKey)
        if (data) {
            // The value will be an object with "day" and "value"
            const dateKey = stringify(date)
            const { day, value } = JSON.parse(data)
            if (day === dateKey) {
                return value
            } else {
                // It's an old value, just remove it
                window.localStorage.removeItem(lsKey)
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
