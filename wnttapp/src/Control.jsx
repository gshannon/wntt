import { useEffect, useState } from 'react'
import axios from 'axios'
import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import Help from './Help'
import HelpSyzygy from './HelpSyzygy'
import { DefaultMapCenter, DefaultMapZoom, EpqsUrl, Page, roundTo } from './utils'
import { getLocalStorage, setLocalStorage } from './localStorage'
import Glossary from './Glossary'
import { AppContext } from './AppContext'

export default function Control({ page, returnPage, gotoPage }) {
    const mainStorage = getLocalStorage('main')
    const [markerElevationNav, setMarkerElevationNav] = useState(mainStorage.markerElevationNav)
    const [customElevationNav, setCustomElevationNav] = useState(mainStorage.customElevationNav)
    const [markerElevationError, setMarkerElevationError] = useState(false)
    const [mapType, setMapType] = useState(mainStorage.mapType ? mainStorage.mapType : 'basic')
    const [markerLocation, setMarkerLocation] = useState(mainStorage.markerLocation)
    const [mapCenter, setMapCenter] = useState(mainStorage.mapCenter || DefaultMapCenter)
    const [zoom, setZoom] = useState(mainStorage.zoom ? mainStorage.zoom : DefaultMapZoom)

    useEffect(() => {
        setLocalStorage('main', {
            customElevationNav: customElevationNav,
            markerLocation: markerLocation,
            markerElevationNav: markerElevationNav,
            mapCenter: mapCenter,
            mapType: mapType,
            zoom: zoom,
        })
    }, [customElevationNav, markerLocation, markerElevationNav, mapCenter, mapType, zoom])

    useEffect(() => {
        // We only fetch elevation if markerLocation is set and markerElevationNav is not set.
        // That avoids a superfluous lookup during mount, when both values are set from the previous
        // session, which is the only time this code is executed when markerElevationNav is already known.
        if (markerLocation && !markerElevationNav) {
            const url =
                `${EpqsUrl}?x=${markerLocation.lng}&y=${markerLocation.lat}` +
                `&units=Feet&wkid=4326&includeDate=False`

            // We'll allow 10 seconds to handle connection-related timeouts.
            axios
                .get(url, { timeout: 10000 })
                .then((response) => {
                    setMarkerElevationError(false)
                    setMarkerElevationNav(roundTo(parseFloat(response.data.value), 2))
                })
                .catch((error) => {
                    if (error.code === 'ECONNABORTED') {
                        console.error(`Request timed out: ${url}`)
                    } else {
                        console.error(`ERROR fetching elevation: ${error} URL=${url}`)
                    }
                    setMarkerElevationError(true)
                })
        }
    }, [markerLocation, markerElevationNav])

    // Set the marker location lat/long, but limit to 7 digits of precision, which is good to ~1cm.
    const setMarkerLatLng = (latlng) => {
        if (!latlng) {
            setMarkerLocation(null)
        } else {
            const { lat, lng } = latlng
            setMarkerLocation({ lat: Number(lat.toFixed(7)), lng: Number(lng.toFixed(7)) })
        }
    }

    return (
        <div className='app-box-bottom'>
            <AppContext.Provider
                value={{
                    gotoPage: gotoPage,
                    customElevationNav: customElevationNav,
                    setCustomElevationNav: setCustomElevationNav,
                    mapType: mapType,
                    setMapType: setMapType,
                    markerLocation: markerLocation,
                    setMarkerLatLng: setMarkerLatLng,
                    mapCenter: mapCenter,
                    setMapCenter: setMapCenter,
                    markerElevationNav: markerElevationNav,
                    setMarkerElevationNav: setMarkerElevationNav,
                    markerElevationError: markerElevationError,
                    zoom: zoom,
                    setZoom: setZoom,
                }}>
                {page === Page.Home && <Home />}
                {page === Page.Graph && <Graph />}
                {page === Page.Map && <Map />}
                {page === Page.About && <About />}
                {page === Page.Glossary && <Glossary />}
                {page === Page.Help && <Help />}
                {page === Page.HelpSyzygy && (
                    <HelpSyzygy gotoPage={gotoPage} returnPage={returnPage} />
                )}
            </AppContext.Provider>
        </div>
    )
}
