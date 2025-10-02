import { Col, Row, Stack } from 'react-bootstrap'
import Container from 'react-bootstrap/Container'
import { Link } from './Links'

const Entry = (props) => {
    return (
        <Row>
            <Col sm={2} className='border-end border-2'>
                <b>{props.title}</b>
            </Col>
            <Col>{props.children}</Col>
        </Row>
    )
}

export default function Glossary() {
    return (
        <Container>
            <Stack gap={3} className='py-3'>
                <Entry title='Wells Reserve SWMP'>
                    The{' '}
                    <Link
                        href='https://www.wellsreserve.org/research/environmental-monitoring'
                        text='System-Wide Monitoring Program'
                    />{' '}
                    at the Wells Reserve. This data is made available by the{' '}
                    <Link
                        href='https://cdmo.baruch.sc.edu'
                        text='Centralized Data Management Office'
                    />{' '}
                    of the{' '}
                    <Link
                        href='https://www.nerra.org'
                        text='National Estuarine Research Reserve System'
                    />
                    .
                </Entry>
                <Entry title='MLLW (Mean Lower Low Water)'>
                    When we say a tide is <i>9.5 feet MLLW</i>, we mean its height is 9.5 feet
                    higher than{' '}
                    <Link
                        href='https://tidesandcurrents.noaa.gov/datum_options.html#MLLW'
                        text='Mean Lower Low Water'
                    />
                    , which is the tidal{' '}
                    <Link href='https://oceanservice.noaa.gov/facts/datum.html' text='datum' />{' '}
                    (point of reference) used by this application for all land and sea elevations.
                    MLLW is the average of all lowest daily tides observed over the{' '}
                    <b>National Tidal Datum Epoch</b>. Another commonly used datum is{' '}
                    <Link
                        href='https://en.wikipedia.org/wiki/North_American_Vertical_Datum_of_1988'
                        text='NAVD88'
                    />
                    , and during the current <b>National Tidal Datum Epoch</b>, MLLW is{' '}
                    {import.meta.env.VITE_NAVD88_MLLW_CONVERSION} feet higher than NAVD88 (
                    <i>MLLW = NAVD88 + {import.meta.env.VITE_NAVD88_MLLW_CONVERSION}</i>). See{' '}
                    <Link
                        href='https://tidesandcurrents.noaa.gov/datums.html?id=8419317'
                        text='here'
                    />{' '}
                    for more information about datums.
                </Entry>
                <Entry title='Custom Elevation'>
                    The elevation relative to MLLW of the selected location on the Map page. This is
                    an elevation you are interested in showing on the graph for purposes of
                    comparison to tide data. If you enter an address to look up, it is sent to{' '}
                    <Link href='https://geocode.maps.co' text='Geocode' /> to get a
                    latitude/longitude. The elevation is determined by sending the selected
                    latitude/longitude coordinates to{' '}
                    <Link
                        href='https://apps.nationalmap.gov/epqs/'
                        text='The National Map Elevation Point Query Service'
                    />
                    , provided by the United States Geological Service, to obtain the elevation of
                    that point relative to NAVD88, which is then converted to MLLW.
                </Entry>
                <Entry title='Record Tide<'>
                    This is the highest recorded tide at Wells. Source: <b>Wells Reserve SWMP</b>
                </Entry>
                <Entry title='Highest Annual Predicted'>
                    The highest predicted astronomical tide for the requested year, relative to
                    MLLW.
                </Entry>
                <Entry title='MHW (Mean High Water)'>
                    The average of all the high water heights, relative to MLLW, observed over the{' '}
                    <b>National Tidal Datum Epoch</b>, i.e. between 1983 and 2001. Source:{' '}
                    <Link
                        href='https://tidesandcurrents.noaa.gov/datums.html?id=8419317'
                        text='https://tidesandcurrents.noaa.gov/datums.html?id=8419317'
                    />
                </Entry>
                <Entry title='Observed Tide'>
                    Recorded tide level relative to MLLW. Data is captured every 15 minutes, and
                    there is generally a delay of less than one hour between data collection and
                    availability of the data for display. Source: <b>Wells Reserve SWMP</b>
                </Entry>
                <Entry title='Predicted Tide'>
                    The predicted astronomical tide level relative to MLLW based on the gravity of
                    the Moon and the relative motion of the Earth, Sun and Moon, as published by{' '}
                    <Link
                        href='https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317'
                        text='NOAA'
                    />
                    . Such predictions do not consider any atmospheric or meteorological events.
                </Entry>
                <Entry title='Recorded Storm Surge'>
                    The difference between the Observed Tide and the Predicted Tide. This generally
                    represents the effects of wind, rain and other meteorological factors such as
                    storms. For example, if the Predicted Tide was 11.5 feet and the Observed Tide
                    was 12 feet, the Recorded Storm Surge would be 0.5 feet for that observation
                    time.
                </Entry>
                <Entry title='Projected Storm Surge'>
                    A computer model-generated estimate of adjustments to Predicted Tide levels in
                    the near future (about 4 days), based on NOAA&apos;s{' '}
                    <Link
                        href='https://slosh.nws.noaa.gov/etsurge2.0/index.php?stid=8419317&datum=MLLW&show=0-0-1-1-0'
                        text='Probabilistic Extra-Tropical Storm Surge'
                    />{' '}
                    data.{' '}
                    <b>This is an EXPERIMENTAL project and is not to be considered a forecast</b>.
                    The data is refreshed four times a day. Please read NOAA&apos;s disclaimer{' '}
                    <Link href='https://slosh.nws.noaa.gov/etsurge2.0/disclaimer.php' text='here' />
                    .
                </Entry>
                <Entry title='Projected Storm Tide'>
                    The sum of Predicted Tide and Projected Storm Surge.
                </Entry>
                <Entry title='Wind Gusts'>
                    The highest wind speed detected during the 15-minute sample period at the Wells
                    meteorological station. Samples are taken every five seconds. Source:{' '}
                    <b>Wells Reserve SWMP</b>
                </Entry>
                <Entry title='Wind Speed'>
                    The average wind speed detected during the 15-minute sample period at the Wells
                    meteorological station. Samples are taken every five seconds. Source:{' '}
                    <b>Wells Reserve SWMP</b>
                </Entry>
                <Entry title='National Tidal Datum Epoch'>
                    The specific{' '}
                    <Link
                        href='https://tidesandcurrents.noaa.gov/datum-updates/ntde/'
                        text='19-year period'
                    />{' '}
                    adopted by NOAA&apos;s National Ocean Service as the time segment over which
                    tide observations are taken in order to obtain tidal datums, e.g. MLLW. The
                    present NTDE uses data from 1983 through 2001, and is expected to be replaced by
                    a new NTDE representing 2002 - 2020, sometime after 2026.
                </Entry>
            </Stack>
        </Container>
    )
}
