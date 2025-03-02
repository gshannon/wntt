import { Col, Row, Stack } from 'react-bootstrap'
import Container from 'react-bootstrap/Container'

export default function Glossary() {
    return (
        <Container>
            <Stack gap={3} className='py-3'>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Wells Reserve SWMP</b>
                    </Col>
                    <Col>
                        The{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://www.wellsreserve.org/research/environmental-monitoring'>
                            System-Wide Monitoring Program
                        </a>{' '}
                        at the Wells Reserve. This data is made available by the{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://cdmo.baruch.sc.edu'>
                            Centralized Data Management Office
                        </a>{' '}
                        of the{' '}
                        <a target='_blank' rel='noopener noreferrer' href='https://www.nerra.org'>
                            National Estuarine Research Reserve System
                        </a>
                        .
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>
                            MLLW
                            <br />
                            Mean Lower Low Water
                        </b>
                    </Col>
                    <Col>
                        When we say a tide is <i>9.5 feet MLLW</i>, we mean its height is 9.5 feet
                        higher than{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://tidesandcurrents.noaa.gov/datum_options.html#MLLW'>
                            Mean Lower Low Water
                        </a>
                        , which is the tidal{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://oceanservice.noaa.gov/facts/datum.html'>
                            datum
                        </a>{' '}
                        (point of reference) used by this application for all land and sea
                        elevations. MLLW is the average of all lowest daily tides observed over the{' '}
                        <b>National Tidal Datum Epoch</b>. Another commonly used datum is{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://en.wikipedia.org/wiki/North_American_Vertical_Datum_of_1988'>
                            NAVD88
                        </a>
                        , and during the current <b>National Tidal Datum Epoch</b>, MLLW is{' '}
                        {import.meta.env.VITE_NAVD88_MLLW_CONVERSION} feet higher than NAVD88 (
                        <i>MLLW = NAVD88 + {import.meta.env.VITE_NAVD88_MLLW_CONVERSION}</i>). See{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://tidesandcurrents.noaa.gov/datums.html?id=8419317'>
                            here
                        </a>{' '}
                        for more information about datums.
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Custom Elevation</b>
                    </Col>
                    <Col>
                        The elevation relative to MLLW of the selected location on the Map page.
                        This is an elevation you are interested in showing on the graph for purposes
                        of comparison to tide data. If you enter an address to look up, it is sent
                        to{' '}
                        <a target='_blank' rel='noopener noreferrer' href='https://geocode.maps.co'>
                            Geocode
                        </a>{' '}
                        to get a latitude/longitude. The elevation is determined by sending the
                        selected latitude/longitude coordinates to{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://apps.nationalmap.gov/epqs/'>
                            The National Map Elevation Point Query Service
                        </a>
                        , provided by the United States Geological Service, to obtain the elevation
                        of that point relative to NAVD88, which is then converted to MLLW.
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Record Tide</b>
                    </Col>
                    <Col>
                        This is the highest recorded tide at Wells. Source:{' '}
                        <b>Wells Reserve SWMP</b>
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Highest Annual Predicted</b>
                    </Col>
                    <Col>
                        The highest predicted astronomical tide for the requested year, relative to
                        MLLW.
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>
                            MHW
                            <br />
                            Mean High Water
                        </b>
                    </Col>
                    <Col>
                        The average of all the high water heights, relative to MLLW, observed over
                        the <b>National Tidal Datum Epoch</b>, i.e. between 1983 and 2001. Source:{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://tidesandcurrents.noaa.gov/datums.html?id=8419317'>
                            https://tidesandcurrents.noaa.gov/datums.html?id=8419317
                        </a>
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Observed Tide</b>
                    </Col>
                    <Col>
                        Recorded tide level relative to MLLW. Data is captured every 15 minutes, and
                        there is generally a delay of less than one hour between data collection and
                        availability of the data for display. Source: <b>Wells Reserve SWMP</b>
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Predicted Tide</b>
                    </Col>
                    <Col>
                        The predicted astronomical tide level relative to MLLW based on the gravity
                        of the Moon and the relative motion of the Earth, Sun and Moon, as published
                        by{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317'>
                            NOAA
                        </a>
                        . Such predictions do not consider any atmospheric or meteorological events.
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Recorded Storm Surge</b>
                    </Col>
                    <Col>
                        The difference between the Observed Tide and the Predicted Tide. This
                        generally represents the effects of wind, rain and other meteorological
                        factors such as storms. For example, if the Predicted Tide was 11.5 feet and
                        the Observed Tide was 12 feet, the Recorded Storm Surge would be 0.5 feet
                        for that observation time.
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Projected Storm Surge</b>
                    </Col>
                    <Col>
                        A computer model-generated estimate of adjustments to Predicted Tide levels
                        in the near future (about 4 days), based on NOAA&apos;s{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://slosh.nws.noaa.gov/etsurge2.0/index.php?stid=8419317&datum=MLLW&show=0-0-1-1-0'>
                            Probabilistic Extra-Tropical Storm Surge
                        </a>{' '}
                        data.{' '}
                        <b>
                            This is an EXPERIMENTAL project and is not to be considered a forecast
                        </b>
                        . The data is refreshed four times a day. Please read NOAA&apos;s disclaimer{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://slosh.nws.noaa.gov/etsurge2.0/disclaimer.php'>
                            here
                        </a>
                        .
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Projected Storm Tide</b>
                    </Col>
                    <Col>The sum of Predicted Tide and Projected Storm Surge.</Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Wind Gusts</b>
                    </Col>
                    <Col>
                        The highest wind speed detected during the 15-minute sample period at the
                        Wells meteorological station. Samples are taken every five seconds. Source:{' '}
                        <b>Wells Reserve SWMP</b>
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>Wind Speed</b>
                    </Col>
                    <Col>
                        The average wind speed detected during the 15-minute sample period at the
                        Wells meteorological station. Samples are taken every five seconds. Source:{' '}
                        <b>Wells Reserve SWMP</b>
                    </Col>
                </Row>
                <Row>
                    <Col sm={2} className='border-end border-2'>
                        <b>National Tidal Datum Epoch</b>
                    </Col>
                    <Col>
                        The specific{' '}
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://tidesandcurrents.noaa.gov/datum-updates/ntde/'>
                            19-year period
                        </a>{' '}
                        adopted by NOAA&apos;s National Ocean Service as the time segment over which
                        tide observations are taken in order to obtain tidal datums, e.g. MLLW. The
                        present NTDE uses data from 1983 through 2001, and is expected to be
                        replaced by a new NTDE representing 2002 - 2020, sometime after 2026.
                    </Col>
                </Row>
            </Stack>
        </Container>
    )
}
