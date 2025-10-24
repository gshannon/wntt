import './css/About.css'
import { Container } from 'react-bootstrap'
import Accordion from 'react-bootstrap/Accordion'
import { SimpleLink, Link } from './Links'
// import { AppContext } from './AppContext'
// import { useContext } from 'react'

export default function About() {
    // const ctx = useContext(AppContext)
    // const toggle = () => {
    //     alert('Special mode is now ' + (ctx.special ? 'OFF' : 'ON'))
    //     ctx.toggleSpecial()
    // }
    return (
        <Container>
            <Accordion alwaysOpen defaultActiveKey={['0']}>
                <Accordion.Item eventKey='0'>
                    <Accordion.Header>DISCLAIMER</Accordion.Header>
                    <Accordion.Body>
                        <div className='fw-bold'>
                            This web application gathers and collates publicly available information
                            from the best available trusted data sources, listed below. It does not
                            generate or create predictions of future tide levels. The reliability of
                            the data is only as good as the sources. Furthermore, actual water level
                            at any given location may differ from the measured tide level due to
                            variations of terrain and wave activity. As always, the local{' '}
                            <Link
                                href='https://forecast.weather.gov/MapClick.php?lat=43.3223&lon=-70.5809'
                                text='National Weather Service'
                            />{' '}
                            should be consulted for official storm surge forecasts and any watches
                            or warnings.
                        </div>
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='1'>
                    <Accordion.Header>Who is this for?</Accordion.Header>
                    <Accordion.Body>
                        This is intended for the residents and property owners in the surrounding
                        communities of the reserves in the National Estuarine Research Reserve
                        System, particularly those with properties at lower elevations near the
                        shore. Do you know the elevation of your property? If there were a storm
                        coming, would you know how to get the relevant tide and storm surge
                        predictions? And would you know how to ensure that those predictions and
                        your property elevation were relative to the same vertical <i>datum</i>, so
                        you are comparing apples to apples? If not, this is for you.
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='2'>
                    <Accordion.Header>Why do we need this?</Accordion.Header>
                    <Accordion.Body>
                        <p>
                            January 13, 2024 saw a record breaking storm event hit the coast of
                            Maine, causing hundreds of millions of dollars in damages and breaking
                            water level records going back to the 1990’s. How can we get the most
                            reliable predictions about future storm tides, and most importantly,
                            relate that to the elevation of our homes, businesses or points of
                            interest?
                        </p>
                        <p>
                            You can find historical tides on one web site, predicted astronomical
                            tides on another, and storm surge predictions on yet another. And with a
                            little work, you can find your property elevation. Of course, all these
                            values must be relative to the same vertical datum, or else they cannot
                            be compared in any meaningful way. Then you might like to see all that
                            data on a graph so you can quickly visualize it over time.
                        </p>
                        <p>
                            This application solves the problem by aggregating and presenting
                            graphical tide data alongside an optional user-configured elevation
                            based on a map location. It includes wind data, observed tide levels,
                            astronomical tide predictions, and the projected storm surge for four
                            days into the future. All data is presented using the same vertical
                            datum (point of reference), so that observations, predictions,
                            estimations and elevations may be displayed on a single graph for
                            accurate comparison.
                        </p>
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='3'>
                    <Accordion.Header>Sources</Accordion.Header>
                    <Accordion.Body>
                        <ol className='list-group list-group-numbered'>
                            <li className='list-group-item d-flex justify-content-between align-items-start'>
                                <div className='ms-2 me-auto'>
                                    <div className='fw-bold'>Historical tides and wind data</div>
                                    <div>
                                        National Estuarine Research Reserve System, Centralized Data
                                        Management Office (Web Services):{' '}
                                        <SimpleLink href='https://cdmo.baruch.sc.edu' />{' '}
                                    </div>
                                </div>
                            </li>
                            <li className='list-group-item d-flex justify-content-between align-items-start'>
                                <div className='ms-2 me-auto'>
                                    <div className='fw-bold'>Astronomical Tide Predictions</div>
                                    <div>
                                        Main site:{' '}
                                        <SimpleLink href='https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317' />
                                    </div>
                                    <div>
                                        API:{' '}
                                        <SimpleLink href='https://api.tidesandcurrents.noaa.gov/api/prod/' />
                                    </div>
                                </div>
                            </li>
                            <li className='list-group-item d-flex justify-content-between align-items-start'>
                                <div className='ms-2 me-auto'>
                                    <div className='fw-bold'>Future Storm Surge</div>
                                    <div>
                                        Main site:{' '}
                                        <SimpleLink href='https://slosh.nws.noaa.gov/etsurge2.0/index.php?stid=8419317&datum=MLLW&show=0-0-1-1-0' />
                                    </div>
                                    <div>
                                        Disclaimer:{' '}
                                        <SimpleLink href='https://slosh.nws.noaa.gov/etsurge2.0/disclaimer.php' />
                                    </div>
                                </div>
                            </li>
                            <li className='list-group-item d-flex justify-content-between align-items-start'>
                                <div className='ms-2 me-auto'>
                                    <div className='fw-bold'>
                                        The National Map Elevation Point Query Service
                                    </div>
                                    <div>
                                        Main Site:{' '}
                                        <SimpleLink href='https://apps.nationalmap.gov/epqs/' />
                                    </div>
                                    <div>
                                        Accuracy Information:{' '}
                                        <SimpleLink href='https://www.usgs.gov/faqs/how-accurate-are-elevations-generated-elevation-point-query-service-national-map' />
                                    </div>
                                </div>
                            </li>
                            <li className='list-group-item d-flex justify-content-between align-items-start'>
                                <div className='ms-2 me-auto'>
                                    <div className='fw-bold'>Moon phase data</div>
                                    <div>
                                        U.S. Navy Astronomical Applications Department:{' '}
                                        <SimpleLink href='https://aa.usno.navy.mil/data/api' />
                                    </div>
                                </div>
                            </li>
                        </ol>
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='4'>
                    <Accordion.Header>More Information</Accordion.Header>
                    <Accordion.Body>
                        Want to see more information about sea level rise in Maine? Try these links.
                        <ul>
                            <li>
                                <Link
                                    href='https://coast.noaa.gov/sealevelcalculator/'
                                    text='NOAA Sea Level Calculator'
                                />
                            </li>
                            <li>
                                <Link
                                    href='https://www.maine.gov/dacf/mgs/hazards/slr_ticker/slr_dashboard.html'
                                    text='Maine Geological Survey Sea Level Rise Dashboard'
                                />
                            </li>
                            <li>
                                <Link
                                    href='https://www.maine.gov/climateplan/climate-impacts/climate-data'
                                    text='Maine Climate Science Dashboard'
                                />
                            </li>
                            <li>
                                <Link
                                    href='https://www.maine.gov/future/sites/maine.gov.future/files/inline-files/STS_EXSUM_2024.pdf'
                                    text='Scientific Assessment of Climate Change and Its Effects in Maine (pdf)'
                                />
                            </li>
                        </ul>
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>

            <div className='p-3' style={{ fontSize: '.7em', float: 'right' }}>
                {/* <a href='#' onClick={() => toggle()}> */}
                Version {/* </a>{' '} */}
                {import.meta.env.VITE_BUILD_NUM ?? '?'} W{window.innerWidth}.{window.outerWidth} H
                {window.innerHeight}.{window.outerHeight}
            </div>
        </Container>
    )
}
