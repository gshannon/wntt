// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useEffectEvent, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Top from './Top'
import Control from './Control'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import * as storage from './storage'
import { AppContext } from './AppContext'
import { Page } from './utils'
import Station from './Station'
import axios from 'axios'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function App() {
    /////////////////////////////////////////////
    // Set up state.
    const [special, setSpecial] = useState(import.meta.env.VITE_SPECIAL ?? '0' === '1') // temporary dev hack
    const [curPage, setCurPage] = useState(Page.Home)
    const [returnPage, setReturnPage] = useState(null)

    // Initial station will be the one stored, or Wells by default.
    const main = storage.getGlobalPermanentStorage()
    const [stationId, setStationId] = useState(main.stationId ?? 'welinwq')
    const [station, setStation] = useState(null)
    const [customElevationNav, setCustomElevationNav] = useState(undefined)

    // temporary dev hack
    const toggleSpecial = () => {
        setSpecial(!special)
    }

    // All navigation is done with this.
    const gotoPage = (page, returnPage) => {
        setCurPage(page)
        setReturnPage(returnPage || null)
    }

    //////////////////////////////////
    // Effects

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    useEffect(() => {
        axios
            .post(import.meta.env.VITE_API_STATION_DATA_URL, {
                app_version: import.meta.env.VITE_BUILD_NUM,
                station_id: stationId,
            })
            .then((res) => {
                setStation(Station.fromJson(res.data))
            })
        storage.setGlobalPermanentStorage({
            stationId: stationId,
        })
    }, [stationId])

    const onCustomChange = useEffectEvent((newElevation) => {
        if (newElevation !== undefined && station != null) {
            const storedOptions = storage.getStationPermanentStorage(station.id)
            const options = station.stationOptionsWithDefaults(storedOptions)
            storage.setStationPermanentStorage(station.id, {
                ...options,
                customElevationNav: newElevation,
            })
        }
    })

    useEffect(() => {
        onCustomChange(customElevationNav)
    }, [customElevationNav])

    return (
        <QueryClientProvider client={queryClient}>
            <AppContext.Provider
                value={{
                    station: station,
                    setStationId: setStationId,
                    gotoPage: gotoPage,
                    customElevationNav: customElevationNav,
                    setCustomElevationNav: setCustomElevationNav,
                    special: special,
                    toggleSpecial: toggleSpecial,
                }}>
                <div className='App app-box'>
                    <Top page={curPage} gotoPage={gotoPage} />
                    <Control page={curPage} returnPage={returnPage} gotoPage={gotoPage} />
                </div>
            </AppContext.Provider>
            {/* <ReactQueryDevtools
                initialIsOpen={false}
                buttonPosition='top-right'
                position='bottom'
            /> */}
        </QueryClientProvider>
    )
}
