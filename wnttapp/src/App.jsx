// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Top from './Top'
import Control from './Control'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import * as storage from './storage'
import { AppContext } from './AppContext'
import { Page } from './utils'
import { getStationConfig } from './stations'
import * as mu from './mapUtils'

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
    const [station, setStation] = useState(getStationConfig(main.stationId ?? 'welinwq'))
    const stationOptions = mu.getStationOptions(station)
    const [customElevationNav, setCustomElevationNav] = useState(stationOptions.customElevationNav)

    // Each station option needs to be in its own state variable so we can save them as they're updated.

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

    //////////////////////////////////
    // Effects

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    useEffect(() => {
        const curOptions = mu.getStationOptions(station)
        storage.setStationPermanentStorage(station.id, {
            ...curOptions,
            customElevationNav: customElevationNav,
        })
    })

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
