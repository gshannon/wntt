import { defaultMinGraphDate, roundTo } from './utils'

export default class Station {
    constructor({
        id,
        reserveName,
        reserveUrl,
        waterStationName,
        weatherStationId,
        weatherStationName,
        noaaStationId,
        noaaStationName,
        noaaStationUrl,
        navd88ToMllwConversion,
        meanHighWaterMllw,
        mapBounds,
        swmpLocation,
        weatherLocation,
        recordTideNavd88,
        recordTideDate, // string YYYY/MM/DD
        minDateOverride = null, // string YYYY/MM/DD to override default
    }) {
        this.id = id
        this.reserveName = reserveName
        this.reserveUrl = reserveUrl
        this.waterStationName = waterStationName
        this.weatherStationId = weatherStationId
        this.weatherStationName = weatherStationName
        this.noaaStationId = noaaStationId
        this.noaaStationName = noaaStationName
        this.noaaStationUrl = noaaStationUrl
        this.navd88ToMllwConversion = navd88ToMllwConversion
        this.meanHighWaterMllw = meanHighWaterMllw
        this.mapBounds = mapBounds
        this.swmpLocation = swmpLocation
        this.weatherLocation = weatherLocation
        this.recordTideNavd88 = recordTideNavd88
        this.recordTideDate = recordTideDate
        this.minDate = minDateOverride
    }

    recordTideMllw = () => {
        return this.navd88ToMllw(this.recordTideNavd88)
    }

    navd88ToMllw = (navd88) => {
        if (navd88 == null) {
            return null
        }
        return roundTo(navd88 + this.navd88ToMllwConversion, 2)
    }

    mllwToNavd88 = (mllw) => {
        if (mllw == null) {
            return null
        }
        return roundTo(mllw - this.navd88ToMllwConversion, 2)
    }

    maxCustomElevationMllw = () => {
        return roundTo(this.recordTideMllw() + 10, 0)
    }

    maxCustomElevationNavd88 = () => {
        return this.mllwToNavd88(this.maxCustomElevationMllw())
    }

    minGraphDate = () => {
        // If the station has a specific min date, use it unless it's older than the default.
        if (this.minDate) {
            return new Date(Math.max(new Date(this.minDate), defaultMinGraphDate()))
        }
        return defaultMinGraphDate()
    }
}
