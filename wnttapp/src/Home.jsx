import './css/Home.css'
import { Page } from './utils'
import { Col, Row, Stack } from 'react-bootstrap'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import Overlay from './Overlay'
import useLatestData from './useLatestData'

export default function Home() {
    const appContext = useContext(AppContext)

    const noData = '--'

    const { data, error } = useLatestData()

    if (error) {
        console.error(error)
    }

    const windSpeedStr = data?.wind_speed ? `${data.wind_speed} mph from ${data.wind_dir}` : noData
    const windGustStr = data?.wind_gust ? `${data.wind_gust} mph` : noData
    const tideStr = data?.tide ? `${data.tide} ft MLLW ${data.tide_dir}` : noData
    const tempStr = data?.temp ? `${data.temp}º F` : noData
    const windTime = data?.wind_time ?? noData
    const tideTime = data?.tide_time ?? noData
    const tempTime = data?.temp_time ?? noData

    return (
        <div className='home'>
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
            <Row className='conditions text-center mb-1 px-0'>
                <Col className='col-12 title mb-1'>Latest Conditions</Col>
                <Col className='mx-2 px-1 offset-2'>
                    <Overlay
                        text={`As of ${windTime}`}
                        placement='top'
                        enable={windSpeedStr != noData}
                        contents={
                            <Stack>
                                <div className='label'>Wind Speed</div>
                                <div>{windSpeedStr}</div>
                            </Stack>
                        }></Overlay>
                </Col>
                <Col className='mx-1 px-1'>
                    <Overlay
                        text={`As of ${windTime}`}
                        placement='top'
                        enable={windGustStr != noData}
                        contents={
                            <Stack>
                                <div className='label'>Wind Gust</div>
                                <div>{windGustStr}</div>
                            </Stack>
                        }></Overlay>
                </Col>
                <Col className='mx-1 px-1'>
                    <Overlay
                        text={`As of ${tideTime}`}
                        placement='top'
                        enable={tideStr != noData}
                        contents={
                            <Stack>
                                <div className='label'>Tide Level</div>
                                <div>{tideStr}</div>
                            </Stack>
                        }></Overlay>
                </Col>
                <Col className='mx-1 px-1'>
                    <Overlay
                        text={`As of ${tempTime}`}
                        placement='top'
                        enable={tempStr != noData}
                        contents={
                            <Stack>
                                <div className='label'>Water Temp</div>
                                <div>{tempStr}</div>
                            </Stack>
                        }></Overlay>
                </Col>
            </Row>
        </div>
    )
}
