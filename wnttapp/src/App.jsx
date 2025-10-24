// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useEffectEvent, useState } from 'react'
import Top from './Top'
import Control from './Control'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import axios from 'axios'
import { Storage, DailyStorage } from './storage'
import { AppContext } from './AppContext'
import { DefaultMapZoom, EpqsUrl, Page, roundTo } from './utils'
import { getStation } from './stations'

// Page management needs to be here because it's needed by both child components.

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function App() {
    const [special, setSpecial] = useState(true)
    // Since the version detection only happens on the graph page, if we're upgrading we return there instead of home.
    const miscDailyStorage = new DailyStorage('misc-daily')
    const miscDaily = miscDailyStorage.get()
    const upgraded = miscDaily.upgraded ?? false
    if (upgraded) {
        console.log(`Auto upgrade detected, will start at graph page`)
    }
    const [curPage, setCurPage] = useState(upgraded ? Page.Graph : Page.Home)
    const [returnPage, setReturnPage] = useState(null)
    miscDailyStorage.save({ ...miscDaily, upgraded: false }) // always reset the upgraded flag

    /////////////////
    // stationId
    const mainCache = new Storage('main')
    const main = mainCache.get()
    const [station, setStation] = useState(getStation(main.stationId ?? 'welinwq'))

    /////////////////
    // station-specific fields: zoom, mapCenter, etc
    const stationMainCache = station ? new Storage(station.id) : null
    const stationMain = station ? stationMainCache.get() : null

    // Storage for the selected station. If none, defaults are used. Some of those are null
    const [markerElevationNav, setMarkerElevationNav] = useState(
        stationMain.markerElevationNav ?? null
    )
    const [customElevationNav, setCustomElevationNav] = useState(
        stationMain.customElevationNav ?? null
    )
    const [markerElevationError, setMarkerElevationError] = useState(false)
    const [mapType, setMapType] = useState(stationMain.mapType ?? 'basic')
    const [markerLocation, setMarkerLocation] = useState(stationMain.markerLocation ?? null)
    const [mapCenter, setMapCenter] = useState(
        stationMain.mapCenter || (station?.swmpLocation ?? null)
    )
    const [zoom, setZoom] = useState(stationMain.zoom ?? DefaultMapZoom)

    const onStationChange = useEffectEvent(() => {
        mainCache.save({
            stationId: station.id,
        })
    })

    const onMainCacheChange = useEffectEvent(() => {
        stationMainCache.save({
            customElevationNav: customElevationNav,
            markerLocation: markerLocation,
            markerElevationNav: markerElevationNav,
            mapCenter: mapCenter,
            mapType: mapType,
            zoom: zoom,
        })
    })

    useEffect(() => {
        onStationChange()
    }, [station])

    useEffect(() => {
        onMainCacheChange()
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

    const toggleSpecial = () => {
        setSpecial(!special)
    }

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    const gotoPage = (page, returnPage) => {
        setCurPage(page)
        setReturnPage(returnPage || null)
    }

    return (
        <QueryClientProvider client={queryClient}>
            <AppContext.Provider
                value={{
                    station: station,
                    setStation: setStation,
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
