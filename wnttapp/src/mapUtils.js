import L from 'leaflet'
import * as storage from './storage'

export const DefaultMapZoom = 13
export const MinZoom = 8
export const MaxZoom = 18

export const getStationOptions = (station) => {
    // Get station-specific fields from storage.  Will be {} if it's a first time user or storage was cleared.
    const options = storage.getStationPermanentStorage(station.id)
    // If we got {} back, fill in defaults.
    if (Object.keys(options).length === 0) {
        options.markerElevationNav = null
        options.customElevationNav = null
        options.markerLocation = null
        options.mapCenter = station.swmpLocation
        options.mapType = 'basic'
        options.zoom = DefaultMapZoom
    }
    return options
}

export const stationIcon = (emoji) => {
    return L.divIcon({
        className: 'my-icon',
        html: emoji,
        iconAnchor: [8, 16],
    })
}

export const openMap = {
    attrib: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
}
export const satelliteMap = {
    attrib: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
}

// Intelligently place the station marker tooltips to reduce the chance of overlap.
export const buildTooltipLocations = (station) => {
    const offsets = {
        top: [9, -10],
        left: [-10, 5],
        right: [10, -5],
        bottom: [9, 30],
    }
    // These are the locations of the 3 station markers.
    const locs = [
        { key: 'wq', val: station.swmpLocation },
        { key: 'noaa', val: station.noaaStationLocation },
        { key: 'met', val: station.weatherLocation },
    ]
    // We sort them by latitude, high to low (would be low to high in southern hemisphere)
    locs.sort((a, b) => b.val.lat - a.val.lat)
    const data = {}
    // Highest latitude gets tooltip on top.
    data[locs[0].key] = { dir: 'top', offset: offsets.top }
    // Middle latitude gets tooltip on right if its longitude is greater (eastward), else left
    const startRight = locs[1].val.lng > locs[0].val.lng
    data[locs[1].key] = startRight
        ? { dir: 'right', offset: offsets.right }
        : { dir: 'left', offset: offsets.left }
    // Lowest latitude gets tooltop on bottom.
    data[locs[2].key] = { dir: 'bottom', offset: offsets.bottom }
    return data
}

export const isInBounds = (mapBounds, loc) => {
    const minLat = Math.min(mapBounds[0][0], mapBounds[1][0])
    const minLng = Math.min(mapBounds[0][1], mapBounds[1][1])
    const maxLat = Math.max(mapBounds[0][0], mapBounds[1][0])
    const maxLng = Math.max(mapBounds[0][1], mapBounds[1][1])
    const flag = loc.lat >= minLat && loc.lat <= maxLat && loc.lng >= minLng && loc.lng <= maxLng
    return flag
}
