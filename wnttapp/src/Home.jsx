import './css/Home.css'
import { Page } from './utils'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import Conditions from './Conditions'
import useLatestData from './useLatestData'

export default function Home() {
    const appContext = useContext(AppContext)

    const { data, error } = useLatestData()

    if (error) {
        console.error(error)
    }

    return (
        <div id='home' className='home'>
            <div className='welcome p-2 my-3'>
                <p>
                    Welcome to the Wells National Estuarine Research Reserve Tide Tracker. Here you
                    can view historical tide and wind data, as well as predicted tides and storm
                    surge. You can also obtain the elevation of any location within our boundaries
                    (Kennebunk to Ogunquit), to assess the flood risk at that location.
                </p>
                <p className='mb-1'>
                    To get started, open the{' '}
                    <a href='#' onClick={() => appContext.gotoPage(Page.Graph)}>
                        Graph
                    </a>
                    &nbsp;page and use the Graph Tutorial button, or watch this{' '}
                    <a
                        target='_blank'
                        rel='noopener noreferrer'
                        href='https://www.youtube.com/watch?v=wr2nfjE43Gg'>
                        tutorial video
                    </a>{' '}
                    on Youtube.
                </p>
            </div>
            <div className='conditions'>
                <div className='title'>Latest Conditions</div>
                <Conditions data={data} error={error} />
            </div>
        </div>
    )
}
