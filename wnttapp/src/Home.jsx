import './css/Home.css'
import banner from './images/aerial-4.jpg'
import { Page } from './utils'
import { Container, Col, Row, Stack } from 'react-bootstrap'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import Overlay from './Overlay'
import useLatestData from './useLatestData'

export default function Home() {
    const appContext = useContext(AppContext)

    const noData = '--'
    let windSpeedStr = noData
    let windGustStr = noData
    let tideStr = noData
    let tempStr = noData
    let windTime = ''
    let tideTime = ''
    let tempTime = ''

    const { data, error } = useLatestData()

    if (error) {
        console.error(error)
    } else if (data) {
        windSpeedStr = `${data.wind_speed} mph from ${data.wind_dir}`
        windGustStr = `${data.wind_gust} mph`
        tideStr = `${data.tide} ft MLLW ${data.tide_dir}`
        tempStr = `${data.temp}º F`
        windTime = data.wind_time
        tideTime = data.tide_time
        tempTime = data.temp_time
    }

    return (
        <div className='home'>
            <img src={banner} alt='Aerial photo of Wells Harbor' />
            <Container className='banner'>
                <Row>
                    <Col xs={10} className='offset-1 welcome'>
                        <p>
                            Welcome to the Wells National Estuarine Research Reserve Tide Tracker.
                            Here you can view historical tide and wind data, as well as predicted
                            tides and storm surge. You can also obtain the elevation of any location
                            within our boundaries (Kennebunk to Ogunquit), to assess the flood risk
                            at that location.
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
                                href='https://www.youtube.com/watch?v=wr2nfjE43Gg'>
                                tutorial video
                            </a>{' '}
                            on Youtube.
                        </p>
                    </Col>
                </Row>
                <Row className='conditions text-center mt-3'>
                    <Col className='mx-2 px-1 offset-2'>
                        <Overlay
                            text={`As of ${windTime}`}
                            placement='top'
                            contents={
                                <Stack>
                                    <div className='label'>Wind Speed</div>
                                    <div className='data'>{windSpeedStr}</div>
                                </Stack>
                            }></Overlay>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Overlay
                            text={`As of ${windTime}`}
                            placement='top'
                            contents={
                                <Stack>
                                    <div className='label'>Wind Gust</div>
                                    <div className='data'>{windGustStr}</div>
                                </Stack>
                            }></Overlay>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Overlay
                            text={`As of ${tideTime}`}
                            placement='top'
                            contents={
                                <Stack>
                                    <div className='label'>Tide Level</div>
                                    <div className='data'>{tideStr}</div>
                                </Stack>
                            }></Overlay>
                    </Col>
                    <Col className='mx-1 px-1'>
                        <Overlay
                            text={`As of ${tempTime}`}
                            placement='top'
                            contents={
                                <Stack>
                                    <div className='label'>Water Temperature</div>
                                    <div className='data'>{tempStr}</div>
                                </Stack>
                            }></Overlay>
                    </Col>
                </Row>
            </Container>
        </div>
    )
}
