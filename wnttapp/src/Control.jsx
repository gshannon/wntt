import { useEffect, useState } from 'react'
import axios from 'axios'
import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import Help from './Help'
import { DefaultMapCenter, DefaultMapZoom, EpqsUrl, Page, roundTo } from './utils'
import { getLocalStorage, setLocalStorage } from './localStorage'
import Glossary from './Glossary'
import { AppContext } from './AppContext'

export default function Control(props) {
    const page = props.page
    const gotoPage = props.gotoPage

    const mainStorage = getLocalStorage('main')
    const [markerElevationNav, setMarkerElevationNav] = useState(mainStorage.markerElevationNav)
    const [customElevationNav, setCustomElevationNav] = useState(mainStorage.customElevationNav)
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
            axios
                .get(url)
                .then((response) => {
                    setMarkerElevationNav(roundTo(parseFloat(response.data.value), 2))
                })
                .catch((err) => {
                    //setError(err);
                    console.error(err)
                })
        }
    }, [markerLocation, markerElevationNav])

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
                    setMarkerLocation: setMarkerLocation,
                    mapCenter: mapCenter,
                    setMapCenter: setMapCenter,
                    markerElevationNav: markerElevationNav,
                    setMarkerElevationNav: setMarkerElevationNav,
                    zoom: zoom,
                    setZoom: setZoom,
                }}>
                {page === Page.Home && <Home />}
                {page === Page.Graph && <Graph />}
                {page === Page.Map && <Map />}
                {page === Page.About && <About />}
                {page === Page.Glossary && <Glossary />}
                {page === Page.Help && <Help />}
            </AppContext.Provider>
        </div>
    )
}
