// Importing this here ensures that the CSS is applied globally.
import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useState } from 'react'
import Top from './Top'
import Control from './Control'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Page } from './utils'
import { getDailyLocalStorage, setDailyLocalStorage } from './localStorage'

// Page management needs to be here because it's needed by both child components.

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function App() {
    // Since the version detection only happens on the graph page, if we're upgrading we return there instead of home.
    const daily = getDailyLocalStorage('misc-daily') ?? {}
    const upgraded = daily.upgraded ?? false
    if (upgraded) {
        console.log(`Auto upgrade detected, will start at graph page`)
    }
    setDailyLocalStorage('misc-daily', { ...daily, upgraded: false }) // always reset the upgraded flag

    const [curPage, setCurPage] = useState(upgraded ? Page.Graph : Page.Home)

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    const gotoPage = (opt) => {
        setCurPage(opt)
    }

    return (
        <QueryClientProvider client={queryClient}>
            <div className='App app-box'>
                <Top page={curPage} gotoPage={gotoPage} />
                <Control page={curPage} gotoPage={gotoPage} />
            </div>
            {/* <ReactQueryDevtools initialIsOpen={false} buttonPosition='top-right' position='right' /> */}
        </QueryClientProvider>
    )
}
