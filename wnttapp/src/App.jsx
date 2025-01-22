import './css/App.css'
// uncomment to show bootstrap debug
//import './bs-breakpoint.css'
import { useEffect, useState } from 'react'
import Top from './Top'
import Control from './Control'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Page, getLocalStorage, setLocalStorage } from './utils'

// Page management needs to be here because it's needed by both child components.

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function App() {
    const [curPage, setCurPage] = useState(getLocalStorage('page', false) ?? Page.Home)

    useEffect(() => {
        console.log(`WNTT Startup, build ${import.meta.env.VITE_BUILD_NUM}`)
    }, [])

    const gotoPage = (opt) => {
        setLocalStorage('page', opt, false)
        setCurPage(opt)
    }

    return (
        <QueryClientProvider client={queryClient}>
            <div className='App'>
                <Top page={curPage} gotoPage={gotoPage} />
                <Control page={curPage} gotoPage={gotoPage} />
            </div>
            {/* <ReactQueryDevtools initialIsOpen={false} buttonPosition='top-right' position='right' /> */}
        </QueryClientProvider>
    )
}
