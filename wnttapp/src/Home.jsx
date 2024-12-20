import './css/Home.css'
import banner from './images/aerial-4.jpg'
import { Page } from './utils'
import { useContext } from 'react'
import { AppContext } from './AppContext'

export default function Home() {
    const appContext = useContext(AppContext)
    return (
        <div className='home'>
            <img src={banner} alt='Aerial photo of Wells Harbor' />
            <div className='welcome'>
                <p>
                    Welcome to the Wells National Estuarine Research Reserve Tide Tracker. Here you
                    can view historical tide and wind data, as well as predicted tides and storm
                    surge. You can also obtain the elevation of any location within our boundaries
                    (Kennebunk to Ogunquit), and assess the flood risk at that location.
                </p>
                <p>
                    To get started, open the{' '}
                    <a href='#' onClick={() => appContext.gotoPage(Page.Graph)}>
                        Graph
                    </a>
                    &nbsp;page and use the Graph Tutorial button.
                </p>
            </div>
        </div>
    )
}
