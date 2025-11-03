// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useEffectEvent, useRef, useState } from 'react'
import Top from './Top'
import Control from './Control'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import axios from 'axios'
import * as storage from './storage'
import { AppContext } from './AppContext'
import { DefaultMapZoom, EpqsUrl, Page, roundTo } from './utils'
import { getStationConfig } from './stations'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function App() {
    const abortControllerRef = useRef(null)

    /////////////////////////////////////////////
    // Set up state.
    const [special, setSpecial] = useState(import.meta.env.VITE_SPECIAL ?? '0' === '1') // temporary dev hack
    const [curPage, setCurPage] = useState(Page.Home)
    const [returnPage, setReturnPage] = useState(null)

    // Initial station will be the one stored, or Wells by default.
    const main = storage.getGlobalPermanentStorage()
    const [station, setStation] = useState(getStationConfig(main.stationId ?? 'welinwq'))
    const stationOptions = getStationOptions(station)

    // All the station options need to be in their own state variable so we can save them as they're updated.
    const [markerElevationError, setMarkerElevationError] = useState(false) // this one's operational only
    const [markerElevationNav, setMarkerElevationNav] = useState(stationOptions.markerElevationNav)
    const [customElevationNav, setCustomElevationNav] = useState(stationOptions.customElevationNav)
    const [mapType, setMapType] = useState(stationOptions.mapType)
    const [markerLocation, setMarkerLocation] = useState(stationOptions.markerLocation)
    const [mapCenter, setMapCenter] = useState(stationOptions.mapCenter)
    const [zoom, setZoom] = useState(stationOptions.zoom)

    /////////////////////////////////////////////
    // Action handlers

    /**
     * Handles user selecting a different station. Writes the selected id to storage.
     * @param {string} id : id of selected station, e.g. 'welinwq'
     */
    const setStationId = (id) => {
        if (id !== station.id) {
            const s = getStationConfig(id)
            storage.setGlobalPermanentStorage({
                stationId: id,
            })
            setStation(s) // This will trigger a render and effect.
        }
    }

    // temporary dev hack
    const toggleSpecial = () => {
        setSpecial(!special)
    }

    // All navigation is done with this.
    const gotoPage = (page, returnPage) => {
        setCurPage(page)
        setReturnPage(returnPage || null)
    }

    // Set the map marker location lat/long, but limit to 7 digits of precision, which is good to ~1cm.
    const setMarkerLatLng = (latlng) => {
        if (!latlng) {
            setMarkerLocation(null)
        } else {
            const { lat, lng } = latlng
            setMarkerLocation({ lat: Number(lat.toFixed(7)), lng: Number(lng.toFixed(7)) })
        }
    }

    //////////////////////////////////
    // Effects

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    /**
     * After a station change, we update the state variables for the selected station.
     * I had to put this in useEffectEvent. If I did this in useEffect, I got:
     * "Error: Calling setState synchronously within an effect can trigger cascading renders."
     * Note that setting this state will trigger another render that saves it to storage, which is
     * not necessary, but I don't know how to prevent that, and it results in no screen update.
     */
    const onStationChange = useEffectEvent(() => {
        const options = getStationOptions(station)
        setCustomElevationNav(options.markerElevationNav)
        setMarkerLocation(options.markerLocation)
        setMarkerElevationNav(options.markerElevationNav)
        setMapCenter(options.mapCenter)
        setMapType(options.mapType)
        setZoom(options.zoom)
    })

    useEffect(() => {
        onStationChange()
    }, [station.id])

    /**
     * Effect to keep the local storage of permanent station options in sync.
     */
    useEffect(() => {
        storage.setStationPermanentStorage(station.id, {
            customElevationNav,
            markerLocation,
            markerElevationNav,
            mapCenter,
            mapType,
            zoom,
        })
    }, [
        station.id,
        customElevationNav,
        markerLocation,
        markerElevationNav,
        mapCenter,
        mapType,
        zoom,
    ])

    useEffect(() => {
        // We only fetch elevation if markerLocation is set and markerElevationNav is not set.
        // That avoids a superfluous lookup during mount, when both values are set from the previous
        // session, which is the only time this code is executed when markerElevationNav is already known.
        if (markerLocation && !markerElevationNav) {
            const url =
                `${EpqsUrl}?x=${markerLocation.lng}&y=${markerLocation.lat}` +
                `&units=Feet&wkid=4326&includeDate=False`

            // If there's a call still running, abort it.
            abortControllerRef.current?.abort()
            abortControllerRef.current = new AbortController()
            axios
                // We'll allow 15 seconds to handle connection-related timeouts.
                .get(url, { timeout: 15000, signal: abortControllerRef.current.signal })
                .then((response) => {
                    setMarkerElevationError(false)
                    setMarkerElevationNav(roundTo(parseFloat(response.data.value), 2))
                })
                .catch((error) => {
                    // It'll be canceled if user clicks another point before this finishes, so
                    // that's not considered an error.
                    if (error.name !== 'CanceledError') {
                        console.error(`ERROR fetching elevation: ${error.name}`)
                        setMarkerElevationError(true)
                    }
                })
        }
    }, [markerLocation, markerElevationNav])

    return (
        <QueryClientProvider client={queryClient}>
            <AppContext.Provider
                value={{
                    station: station,
                    setStationId: setStationId,
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
                    special: special,
                    toggleSpecial: toggleSpecial,
                }}>
                <div className='App app-box'>
                    <Top page={curPage} gotoPage={gotoPage} />
                    <Control page={curPage} returnPage={returnPage} gotoPage={gotoPage} />
                </div>
            </AppContext.Provider>
            {/* <ReactQueryDevtools initialIsOpen={false} buttonPosition='top-right' position='right' /> */}
        </QueryClientProvider>
    )
}

const getStationOptions = (station) => {
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
