import './css/Home.css'
import { Page } from './utils'
import Button from 'react-bootstrap/Button'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import Conditions from './Conditions'
import useLatestData from './useLatestData'

export default function Home() {
    const ctx = useContext(AppContext)

    const { data, error } = useLatestData(ctx.station)

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
                    (Kennebunk to Ogunquit), to assess the flood risk at that location. To learn
                    more, watch this{' '}
                    <a
                        target='_blank'
                        rel='noopener noreferrer'
                        href='https://www.youtube.com/watch?v=wr2nfjE43Gg'>
                        tutorial video
                    </a>{' '}
                    on Youtube, or click the button below.
                </p>
                <p className='mb-1'>
                    <Button
                        className='get-started m-1'
                        variant='custom-primary'
                        onClick={() => ctx.gotoPage(Page.Graph)}>
                        {' '}
                        Get Started
                    </Button>
                </p>
            </div>
            <div className='conditions'>
                <div className='title'>Latest Conditions</div>
                <Conditions data={data} error={error} />
            </div>
        </div>
    )
}
