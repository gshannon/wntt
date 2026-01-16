// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import * as Sentry from '@sentry/react'
import { useEffect, useState } from 'react'
import Top from './Top'
import Control from './Control'
import * as storage from './storage'
import { AppContext } from './AppContext'
import { Page, WELLS_STATION_ID } from './utils'
// import Station from './Station'
import useStations from './useStations'
import { stringify } from './utils'

export default function App() {
    /////////////////////////////////////////////
    // Set up state.
    const isSpecial = import.meta.env.VITE_SPECIAL ?? '0' === '1'
    const [special, setSpecial] = useState(isSpecial) // temporary dev hack
    const [curPage, setCurPage] = useState(Page.Home)
    const [returnPage, setReturnPage] = useState(null)

    // Initial station will be the one stored, or null by default.
    const mainStore = storage.getMainStorage()

    // In multi-reserve mode, there is no default station.
    const stationId = mainStore.stationId ?? (isSpecial ? null : WELLS_STATION_ID)

    // Note this will usually be loading and return null data on the very 1st pass.
    // When fetch is done, it will trigger rerender on this component, and we'll get it that time.
    const { data: stationsData, error: fatalError } = useStations()

    const [station, setStation] = useState(null)
    const [customElevationNav, setCustomElevationNav] = useState(undefined)
    const userId = mainStore.uid ?? crypto.randomUUID().substring(0, 13) // unique enough for our purpose
    if (!mainStore.uid) {
        storage.setMainStorage({ ...mainStore, uid: userId, since: stringify(new Date()) })
    } else if (!mainStore.since) {
        storage.setMainStorage({ ...mainStore, since: stringify(new Date()) })
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

    // handler for user selecting a station
    const onStationSelected = (sid) => {
        setStation(stationsData[sid])
        storage.setMainStorage({ ...mainStore, stationId: sid })
    }

    // handler for user setting custom elevation
    const onCustomElevationSet = (navd88Value) => {
        if (navd88Value !== undefined && station != null) {
            setCustomElevationNav(navd88Value)
            const storedOptions = storage.getPermanentStorage(station.id)
            const options = station.stationOptionsWithDefaults(storedOptions)
            storage.setPermanentStorage(station.id, {
                ...options,
                customElevationNav: navd88Value,
            })
        }
    }

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_APP_VERSION}`)
        Sentry.logger.info('Startup', {
            main: storage.getMainStorage(),
        })
    }, [])

    // Set the station if we have the id and have loaded the station configs.  Should only happen
    // during initial renders.
    if (stationId && station == null && stationsData != null) {
        onStationSelected(stationId)
    }

    return (
        <AppContext.Provider
            value={{
                userId,
                stationsData,
                station,
                onStationSelected,
                gotoPage,
                customElevationNav,
                onCustomElevationSet,
                fatalError,
                special,
                toggleSpecial,
            }}>
            <div className='App app-box'>
                <Top page={curPage} gotoPage={gotoPage} />
                <Control page={curPage} returnPage={returnPage} gotoPage={gotoPage} />
            </div>
        </AppContext.Provider>
    )
}
