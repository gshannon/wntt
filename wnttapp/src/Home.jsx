import './css/Home.css'
import { Page } from './utils'
import Button from 'react-bootstrap/Button'
import Dropdown from 'react-bootstrap/Dropdown'
import { Row, Col } from 'react-bootstrap'
import { Activity, useContext } from 'react'
import { AppContext } from './AppContext'
import Conditions from './Conditions'
import useLatestData from './useLatestData'
import { AllStations } from './stations'

export default function Home() {
    const ctx = useContext(AppContext)

    const stationItems = Object.entries(AllStations).map(([id, stn]) => (
        <Dropdown.Item
            href='#'
            key={id}
            disabled={id === ctx.station.id}
            onClick={() => {
                ctx.setStationId(id)
            }}>
            {stn.reserveName}, {stn.waterStationName}
        </Dropdown.Item>
    ))

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
            </div>
            <Row>
                <Activity mode={ctx.special ? 'visible' : 'hidden'}>
                    <Col className='align-content-center'>
                        <Dropdown>
                            <Dropdown.Toggle variant='primary' id='dropdown-basic'>
                                Select SWMP Station
                            </Dropdown.Toggle>
                            <Dropdown.Menu>{stationItems}</Dropdown.Menu>
                        </Dropdown>
                    </Col>
                </Activity>
                <Col className='mb-1'>
                    <Button
                        className='get-started m-1'
                        disabled={ctx.station == null}
                        variant='custom-primary'
                        onClick={() => ctx.gotoPage(Page.Graph)}>
                        {' '}
                        Get Started
                    </Button>
                </Col>
            </Row>
            <Activity mode={ctx.station ? 'visible' : 'hidden'}>
                <ConditionsSection station={ctx.station} />
            </Activity>
        </div>
    )
}

const ConditionsSection = ({ station }) => {
    const { data, error } = useLatestData(station)

    if (error) {
        console.error(error)
    }
    return (
        <div className='conditions'>
            <div className='title'>Latest Conditions -- {station.reserveName}</div>
            <Conditions data={data} error={error} />
        </div>
    )
}
