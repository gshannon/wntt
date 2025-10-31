import L from 'leaflet'
import tideGauge from './images/util/red-pin.png'

export const RedPinIcon = new L.Icon({
    iconUrl: tideGauge,
    iconSize: [29, 32],
    iconAnchor: [2, 32],
    popupAnchor: undefined,
    shadowUrl: undefined,
    shadowSize: undefined,
    shadowAnchor: undefined,
    className: 'leaflet-div-icon',
})
