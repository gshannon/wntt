import './css/Home.css'
import { useState } from 'react'
import { Row, Col } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import Dropdown from 'react-bootstrap/Dropdown'
import { Activity, useContext } from 'react'
import { AppContext } from './AppContext'
import { Link } from './Links'
import Conditions from './Conditions'
import useLatestData from './useLatestData'
import useStationSelection from './useStationSelection'
import { apiErrorResponse, Page } from './utils'

export default function Home() {
    const ctx = useContext(AppContext)
    const [stationSelectionData, setStationSelectionData] = useState(null)
    const { data, error } = useStationSelection(stationSelectionData == null)

    if (data != null && stationSelectionData == null) {
        setStationSelectionData(data)
    }

    const stationItems = stationSelectionData
        ? stationSelectionData.map((stn) => (
              <Dropdown.Item
                  className='pointer'
                  key={stn.id}
                  disabled={stn.id === ctx.station?.id}
                  onClick={() => {
                      ctx.setStationId(stn.id)
                  }}>
                  {stn.reserveName}, {stn.waterStationName}
              </Dropdown.Item>
          ))
        : ''

    const stationSelectionSection = error ? (
        <div className='text-warning bg-dark'>{apiErrorResponse(error)}</div>
    ) : (
        <Dropdown>
            <Dropdown.Toggle variant='primary' id='dropdown-basic'>
                Select Station
            </Dropdown.Toggle>
            <Dropdown.Menu>{stationItems}</Dropdown.Menu>
        </Dropdown>
    )

    const text1 = () => {
        if (ctx.special) {
            return (
                <>
                    Here you can view historical tide and wind data, as well as predicted tides and
                    storm surge, for certain members of the{' '}
                    <Link
                        href='https://coast.noaa.gov/nerrs/'
                        text='National Estuarine Research Reserve System'
                    />
                    . You can also obtain the elevation of any location in general vicinity of the
                    reserve in order to assess the flood risk at that location.
                </>
            )
        } else {
            return (
                <>
                    Here you can view historical tide and wind data, as well as predicted tides and
                    storm surge. You can also obtain the elevation of any location within our
                    boundaries (Kennebunk to Ogunquit), to assess the flood risk at that location.
                </>
            )
        }
    }

    return (
        <div id='home' className='home'>
            <div className='welcome p-2 my-3'>
                <p>
                    Welcome to the Wells National Estuarine Research Reserve Tide Tracker. {text1()}{' '}
                    To learn more, watch this{' '}
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
                    <Col className='align-content-center'>{stationSelectionSection}</Col>
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
            {ctx.station && <ConditionsSection station={ctx.station} />}
        </div>
    )
}

const ConditionsSection = ({ station }) => {
    const { data, error } = useLatestData(station)

    return (
        <div className='conditions'>
            <div className='title'>Latest Conditions -- {station.reserveName}</div>
            <Conditions data={data} error={error} />
        </div>
    )
}
