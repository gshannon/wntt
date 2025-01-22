import './css/Home.css'
import banner from './images/aerial-4.jpg'
import { Page } from './utils'
import { Col, Row, Stack } from 'react-bootstrap'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import useLatestData from './useLatestData'

export default function Home() {
    const appContext = useContext(AppContext)

    const noData = '--'
    let windSpeedStr = noData
    let windGustStr = noData
    let tideStr = noData
    let tempStr = noData

    const { data, error } = useLatestData()

    if (error) {
        console.error(error)
    } else if (data) {
        windSpeedStr = `${data.wind_speed} mph from ${data.wind_dir}`
        windGustStr = `${data.wind_gust} mph`
        tideStr = `${data.tide} ft MLLW`
        tempStr = `${data.temp}º F`
    }

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
                    &nbsp;page and use the Graph Tutorial button, or watch this{' '}
                    <a
                        target='_blank'
                        rel='noopener noreferrer'
                        href='https://www.youtube.com/embed/0RbrZBbK9B8?si=oUzyDw3XgZ59KZZw'>
                        tutorial video
                    </a>{' '}
                    on Youtube.
                </p>
            </div>
            <div className='latest'>
                <Row className='align-items-center'>
                    <Col className='mx-1 px-1'>
                        <Stack>
                            <div className='label'>Wind Speed</div>
                            <div className='data'>{windSpeedStr}</div>
                        </Stack>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Stack>
                            <div className='label'>Wind Gust</div>
                            <div className='data'>{windGustStr}</div>
                        </Stack>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Stack>
                            <div className='label'>Tide Level</div>
                            <div className='data'>{tideStr}</div>
                        </Stack>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Stack>
                            <div className='label'>Water Temperature</div>
                            <div className='data'>{tempStr}</div>
                        </Stack>
                    </Col>
                </Row>
            </div>
        </div>
    )
}
