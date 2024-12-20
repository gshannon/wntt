import L from 'leaflet'
import userMarker from './images/util/yellow-pin.png'
import tideGauge from './images/util/red-pin.png'

export const YellowPin = new L.Icon({
    iconUrl: userMarker,
    iconSize: [29, 32],
    iconAnchor: [2, 32],
    popupAnchor: undefined,
    shadowUrl: undefined,
    shadowSize: undefined,
    shadowAnchor: undefined,
    className: 'leaflet-div-icon',
})

export const RedPin = new L.Icon({
    iconUrl: tideGauge,
    iconSize: [29, 32],
    iconAnchor: [2, 32],
    popupAnchor: undefined,
    shadowUrl: undefined,
    shadowSize: undefined,
    shadowAnchor: undefined,
    className: 'leaflet-div-icon',
})
