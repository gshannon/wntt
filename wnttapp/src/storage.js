import { stringify } from './utils'

const _local_storage_version = '002'
const _local_storage_prefix = 'wntt'

const storageKey = (name) => `${_local_storage_prefix}-${name}-${_local_storage_version}`

export class Storage {
    constructor(name) {
        this.keyName = storageKey(name)
    }
    get = () => {
        try {
            const data = window.localStorage.getItem(this.keyName)
            return data ? JSON.parse(data) : {}
        } catch (error) {
            console.error(error)
            return {}
        }
    }
    save = (data) => {
        try {
            window.localStorage.setItem(this.keyName, JSON.stringify(data))
        } catch (error) {
            console.error(error)
        }
    }
}

export class DailyStorage extends Storage {
    constructor(name) {
        super(name)
    }

    get = () => {
        try {
            const data = window.localStorage.getItem(this.keyName)
            if (data) {
                // The value will be an object with "day" and "value"
                const dateKey = stringify(new Date())
                const { day, value } = JSON.parse(data)
                if (day === dateKey) {
                    return value
                }
                // It's an old value, just remove it
                window.localStorage.removeItem(this.keyName)
                return {}
            } else {
                return {}
            }
        } catch (error) {
            console.error(error)
            return {}
        }
    }

    save = (data) => {
        try {
            const dateKey = stringify(new Date())
            const json = JSON.stringify({ day: dateKey, value: data })
            window.localStorage.setItem(this.keyName, json)
        } catch (error) {
            console.error(error)
        }
    }
}
