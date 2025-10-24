import { ListGroup, Row } from 'react-bootstrap'
import Container from 'react-bootstrap/Container'
import { SimpleLink, Link } from './Links'
import { SyzygyInfo } from './utils'

export default function HelpSyzygy({ gotoPage, returnPage }) {
    const Back = () => {
        return returnPage ? (
            <Row className='justify-content-start my-3'>
                <a
                    href='#'
                    onClick={() => {
                        gotoPage(returnPage)
                    }}>
                    Back to Graph
                </a>
            </Row>
        ) : (
            ''
        )
    }

    return (
        <Container>
            <Back />
            <Row className='justify-content-center fs-4 fw-bold my-3'>
                Tidal Influence of the Sun and Moon
            </Row>
            <Row className='justify-content-start mx-0 mb-3'>
                <p>
                    Tides are caused by the gravitational forces produced by the relative positions
                    of the Sun, Moon and Earth, and the rotation of the Earth. Symbols representing
                    key positions of the Sun ({SyzygyInfo.PH.display}) and Moon (
                    {SyzygyInfo.NM.display} {SyzygyInfo.FQ.display} {SyzygyInfo.FM.display}
                    {SyzygyInfo.LQ.display} {SyzygyInfo.PG.display}) are presented on the tide graph
                    as a way to better understand the tide patterns. While there are other drivers
                    of coastal flooding such as weather, local topography and sea level rise, in the
                    lunar month, the highest tides usually occur around New Moon and Full Moon.
                </p>
                <p>
                    The gravitational pull of the Moon is the primary force, and as it moves along
                    its 27.5 day orbit around the Earth, it pulls the oceans toward it. The
                    Moon&apos;s orbit is ellipitcal, so it isn&apos;t always the same distance from
                    Earth. Once per orbit, it is at the closest distance (
                    <Link
                        href='https://www.timeanddate.com/astronomy/moon/lunar-perigee-apogee.html'
                        text='perigee'
                    />
                    ) , and its pull is at its strongest.
                </p>
                <p>
                    The Sun, despite being much greater in mass, has roughly half the Moon&apos;s
                    gravitational pull due to its great distance from Earth. Once per year, two
                    weeks after the Winter Solstice, Earth is at its closest point to the Sun, or{' '}
                    <Link href='https://simple.wikipedia.org/wiki/Perihelion' text='perihelion' />.
                    Here the Sun it will have its greatest effect, either to enhance or cancel out
                    the Moon&apos;s gravitational pull.
                </p>
                <p>
                    When the Sun, Moon & Earth are in alignment, the pull of the Sun and Moon are
                    combined, causing higher high tides and lower low tides. This occurs at every
                    Full Moon and New Moon, and results in a{' '}
                    <Link
                        href='https://oceanservice.noaa.gov/facts/springtide.html'
                        text='spring tide'
                    />
                    . When perigee coincides with a Full or New Moon, the Moon will appear larger
                    than usual -- a <b>Supermoon</b>, and we get a{' '}
                    <Link
                        href='https://oceanservice.noaa.gov/facts/perigean-spring-tide.html'
                        text='perigean spring tide'
                    />
                    , also known as a{' '}
                    <Link href='https://en.wikipedia.org/wiki/King_tide' text='king tide' />.
                </p>
                <p>
                    A different effect occurs when the Sun and Moon are at a 90º angle from Earth,
                    as happens at First Quarter and Last Quarter. This is a{' '}
                    <Link
                        href='https://oceanservice.noaa.gov/facts/springtide.html'
                        text='neap tide'
                    />
                    . In this case, the Sun&apos;s gravity partially cancels out that of the Moon,
                    and the tide range will be smaller -- lower highs and higher lows. See{' '}
                    <Link
                        href='https://science.nasa.gov/moon/tides/#h-here-comes-the-sun'
                        text='here'
                    />{' '}
                    for a helpful illustration.
                </p>
                <p className='fw-bold'>
                    Given all that, it follows that the highest tides should occur around New Moon
                    or Full Moon, when the Moon is near perigee, and even more so if the Earth is
                    near perihelion.
                </p>
                <p>Sources:</p>
                <ListGroup className='mb-3'>
                    <ListGroup.Item>
                        <SimpleLink href='https://science.nasa.gov/moon/tides/' />
                    </ListGroup.Item>
                    <ListGroup.Item>
                        <SimpleLink href='https://oceanservice.noaa.gov/education/tutorial_tides/tides06_variations.html' />
                    </ListGroup.Item>
                </ListGroup>
            </Row>
            <Back />
        </Container>
    )
}
