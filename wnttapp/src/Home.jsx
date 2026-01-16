import './css/Home.css'
import { Row, Col } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import { useContext } from 'react'
import { AppContext } from './AppContext'
import { Link } from './Links'
import Conditions from './Conditions'
import useLatestData from './useLatestData'
import { Page, WELLS_STATION_ID } from './utils'

const WELLS_BG_CLASS = 'wells-bg'
const OTHER_BG_CLASS = 'other-bg'

export default function Home() {
    const ctx = useContext(AppContext)

    const text1 = () => {
        if (ctx.special) {
            return (
                <>
                    This system uses data collected by the{' '}
                    <Link
                        href='https://coast.noaa.gov/nerrs/research/'
                        text='System-Wide Monitoring Program'
                    />{' '}
                    (SWMP) to view historical tide and wind data, as well as predicted tides and
                    storm surge, for certain sites within the{' '}
                    <Link
                        href='https://coast.noaa.gov/nerrs/'
                        text='National Estuarine Research Reserve System'
                    />
                    . You can also obtain the elevation of any location in the general vicinity of
                    the reserve in order to assess the flood risk at that location.
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

    const text2 = () => {
        if (ctx.special) {
            if (ctx.station) {
                return <>You can change the reserve you are interested in at any time.</>
            } else {
                return (
                    <>
                        First, use the Choose Reserve button above to select a reserve. You can
                        change it at any time.
                    </>
                )
            }
        }
    }

    return (
        <div
            id='home'
            className={
                'home ' + (ctx.stationId === WELLS_STATION_ID ? WELLS_BG_CLASS : OTHER_BG_CLASS)
            }>
            <div className='welcome p-2 my-3'>
                <p>
                    Welcome to the {ctx.special ? '' : 'Wells'} National Estuarine Research Reserve
                    Tide Tracker. {text1()} To learn more, watch this{' '}
                    <a
                        target='_blank'
                        rel='noopener noreferrer'
                        href='https://www.youtube.com/watch?v=wr2nfjE43Gg'>
                        tutorial video.
                    </a>{' '}
                    {text2()}
                </p>
            </div>
            <Row>
                {ctx.station != null && (
                    <Col>
                        <Button
                            className='home-screen-btn fw-bold'
                            disabled={ctx.station == null}
                            variant='custom-primary'
                            onClick={() => ctx.gotoPage(Page.Graph)}>
                            {' '}
                            Get Started
                        </Button>
                    </Col>
                )}
            </Row>
            <Row className='mt-3'>{ctx.station && <ConditionsSection station={ctx.station} />}</Row>
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
