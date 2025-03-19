import { stringify } from './utils'

// change this when necessary after changes to prevent reading old values
const _local_storage_version = '001'
const _local_storage_prefix = 'wntt'

const storageKey = (name) => `${_local_storage_prefix}-${name}-${_local_storage_version}`

// If daily is true, we store an object with "day" and "value" keys, with the day
// set to today's date.
export const setLocalStorage = (key, value) => {
    try {
        window.localStorage.setItem(storageKey(key), JSON.stringify(value))
    } catch (error) {
        console.error(error)
    }
}

// If daily is true, we store an object with "day" and "value" keys, with the day
// set to today's date. The date param is for testing only.
export const setDailyLocalStorage = (key, value, date = new Date()) => {
    try {
        const dateKey = stringify(date)
        const json = JSON.stringify({ day: dateKey, value: value })
        window.localStorage.setItem(storageKey(key), json)
    } catch (error) {
        console.error(error)
    }
}

// If daily is true, we expect an object with "day" and "value" keys, and
// return the value only if the day matches the current date.
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

// If daily is true, we expect an object with "day" and "value" keys, and
// return the value only if the day matches the current date. The date param
// is for testing only.
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
