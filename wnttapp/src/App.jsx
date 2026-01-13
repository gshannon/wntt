// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import * as Sentry from '@sentry/react'
import { useEffect, useEffectEvent, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import axios from 'axios'
import Top from './Top'
import Control from './Control'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import * as storage from './storage'
import { AppContext } from './AppContext'
import { Page } from './utils'
import Station from './Station'
import { NotAcceptable, stringify } from './utils'

const WELLS_STATION_ID = 'welinwq'
const WELLS_BG_CLASS = 'wells-bg'
const OTHER_BG_CLASS = 'other-bg'

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
    const isSpecial = import.meta.env.VITE_SPECIAL ?? '0' === '1'
    const [special, setSpecial] = useState(isSpecial) // temporary dev hack
    const [fatalError, setFatalError] = useState(null)
    const [curPage, setCurPage] = useState(Page.Home)
    const [returnPage, setReturnPage] = useState(null)

    // Initial station will be the one stored, or null by default.
    const main = storage.getMainStorage()
    // In multi-reserve mode, there is no default station.
    const [stationId, setStationId] = useState(
        main.stationId ?? (isSpecial ? null : WELLS_STATION_ID)
    )
    const [station, setStation] = useState(null)
    // For now we have 1 background for Wells, and 1 for all others.
    const [bgClass, setBgClass] = useState(
        stationId === WELLS_STATION_ID ? WELLS_BG_CLASS : OTHER_BG_CLASS
    )
    const [customElevationNav, setCustomElevationNav] = useState(undefined)
    const userId = main.uid ?? crypto.randomUUID().substring(0, 13)
    if (!main.uid) {
        storage.setMainStorage({ ...main, uid: userId, since: stringify(new Date()) })
    } else if (!main.since) {
        storage.setMainStorage({ ...main, since: stringify(new Date()) })
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

    //////////////////////////////////
    // Effects

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_APP_VERSION}`)
        Sentry.logger.info('Startup', {
            main: storage.getMainStorage(),
        })
    }, [])

    useEffect(() => {
        if (stationId) {
            axios
                .post(import.meta.env.VITE_API_STATION_DATA_URL, {
                    uid: userId,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: stationId,
                })
                .then((res) => {
                    setStation(Station.fromJson(stationId, res.data))
                    setBgClass(stationId === WELLS_STATION_ID ? WELLS_BG_CLASS : OTHER_BG_CLASS)
                    const main = storage.getMainStorage()
                    storage.setMainStorage({
                        ...main,
                        stationId: stationId,
                    })
                })
                .catch((error) => {
                    if (error.status === NotAcceptable) {
                        setFatalError(error)
                    } else if (error.name !== 'CanceledError') {
                        console.log(error.message, error.response?.data?.detail)
                    }
                })
        }
    }, [stationId, userId])

    const onCustomChange = useEffectEvent((newElevation) => {
        if (newElevation !== undefined && station != null) {
            const storedOptions = storage.getPermanentStorage(station.id)
            const options = station.stationOptionsWithDefaults(storedOptions)
            storage.setPermanentStorage(station.id, {
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
                    userId: userId,
                    station: station,
                    setStationId: setStationId,
                    bgClass: bgClass,
                    gotoPage: gotoPage,
                    customElevationNav: customElevationNav,
                    setCustomElevationNav: setCustomElevationNav,
                    fatalError: fatalError,
                    setFatalError: setFatalError,
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
