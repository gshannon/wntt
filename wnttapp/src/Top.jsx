import './css/Top.css'
import { Activity, useContext, useState } from 'react'
import Container from 'react-bootstrap/Container'
import { Row, Col } from 'react-bootstrap'
import NavbarBrand from 'react-bootstrap/NavbarBrand'
import NavDropdown from 'react-bootstrap/NavDropdown'
import Nav from 'react-bootstrap/Nav'
import NavLink from 'react-bootstrap/NavLink'
import { MediumBase, Page } from './utils'
import Logo from './images/wr-logo.png'
import Wave from './images/util/wave.png'
import Hamburger from './images/util/hamburger.png'
import ConditionsPopup from './ConditionsPopup'
import Overlay from './Overlay'
import { AppContext } from './AppContext'

export default function Top({ page, gotoPage }) {
    const ctx = useContext(AppContext)

    const [showConditions, setShowConditions] = useState(false)

    const onModalClose = () => {
        setShowConditions(false)
    }

    const stationSelected = ctx.station != null

    const expandedMenu = (
        <Col className='expanded-menu px-1'>
            <Nav>
                <NavLink onClick={() => gotoPage(Page.Home)} active={page === Page.Home}>
                    Home
                </NavLink>
                <NavLink
                    className={stationSelected ? '' : 'disabled'}
                    onClick={() => gotoPage(Page.Graph)}
                    active={page === Page.Graph}>
                    Graph
                </NavLink>
                <NavLink
                    className={stationSelected ? '' : 'disabled'}
                    onClick={() => gotoPage(Page.Map)}
                    active={page === Page.Map}>
                    Map
                </NavLink>
                <NavLink onClick={() => gotoPage(Page.About)} active={page === Page.About}>
                    About
                </NavLink>
                <NavDropdown
                    title='Help'
                    active={[Page.Glossary, Page.HelpSyzygy, Page.Tutorials].includes(page)}>
                    <HelpItems page={page} gotoPage={gotoPage} />
                </NavDropdown>
            </Nav>
        </Col>
    )

    const pulldownMenu = (
        <Col className='hamburger-menu px-1'>
            <NavDropdown className='pe-1' title={<img width={35} src={Hamburger} alt='Menu' />}>
                <NavDropdown.Item onClick={() => gotoPage(Page.Home)} active={page === Page.Home}>
                    Home
                </NavDropdown.Item>
                <NavDropdown.Item
                    className={stationSelected ? '' : 'disabled'}
                    onClick={() => gotoPage(Page.Graph)}
                    active={page === Page.Graph}>
                    Graph
                </NavDropdown.Item>
                <NavDropdown.Item
                    className={stationSelected ? '' : 'disabled'}
                    onClick={() => gotoPage(Page.Map)}
                    active={page === Page.Map}>
                    Map
                </NavDropdown.Item>
                <NavDropdown.Item onClick={() => gotoPage(Page.About)} active={page === Page.About}>
                    About
                </NavDropdown.Item>
                <NavDropdown.Divider />
                <NavDropdown.Item disabled={true}>Help</NavDropdown.Item>
                <HelpItems page={page} gotoPage={gotoPage} />
            </NavDropdown>
        </Col>
    )

    return (
        <div className='app-box-top'>
            <Container className=' my-0'>
                <Row className='nav-container align-items-center'>
                    <Col className='pe-1'>
                        <NavbarBrand
                            className='main-title mx-1'
                            onClick={() => gotoPage(Page.Home)}>
                            <div>Wells Reserve</div>
                            <div className='tide-tracker'>Tide Tracker</div>
                        </NavbarBrand>
                    </Col>
                    <Activity mode={window.innerWidth >= MediumBase ? 'visible' : 'hidden'}>
                        {expandedMenu}
                    </Activity>
                    <Activity mode={window.innerWidth < MediumBase ? 'visible' : 'hidden'}>
                        {pulldownMenu}
                    </Activity>
                    <Col className='px-1'>
                        <Overlay
                            text='Popup that shows current weather and tide data.'
                            placement='bottom'
                            contents={
                                <div
                                    className='conditions-container mx-md-2'
                                    onClick={() => setShowConditions(ctx.station != null)}>
                                    <img
                                        className='conditions-img'
                                        src={Wave}
                                        width={75}
                                        alt='Latest conditions'
                                    />
                                    <div className='conditions-centered'>Latest Conditions</div>
                                </div>
                            }
                        />
                    </Col>
                    <Col className='px-1'>
                        <Overlay
                            text='View the Wells Reserve web site'
                            placement='bottom'
                            contents={
                                <a
                                    target='_blank'
                                    rel='noopener noreferrer'
                                    href='https://wellsreserve.org'>
                                    <img
                                        className='logo'
                                        src={Logo}
                                        width={130}
                                        alt='Wells Reserve Logo'
                                    />
                                </a>
                            }
                        />
                    </Col>
                </Row>
            </Container>
            {ctx.special && ctx.station ? (
                <Row className='current-station justify-content-center py-1 my-0 mx-0'>
                    Station: {ctx.station.reserveName}, {ctx.station.waterStationName}
                </Row>
            ) : null}
            {showConditions && <ConditionsPopup station={ctx.station} onClose={onModalClose} />}
        </div>
    )
}

const HelpItems = ({ page, gotoPage }) => {
    return (
        <>
            <NavDropdown.Item
                className={page === Page.Glossary ? 'active' : ''}
                onClick={() => gotoPage(Page.Glossary)}>
                Glossary
            </NavDropdown.Item>
            <NavDropdown.Item
                className={page === Page.HelpSyzygy ? 'active' : ''}
                onClick={() => gotoPage(Page.HelpSyzygy)}>
                Sun, Moon & Tides
            </NavDropdown.Item>
            <NavDropdown.Item
                className={page === Page.Tutorials ? 'active' : ''}
                onClick={() => gotoPage(Page.Tutorials)}>
                Tutorials
            </NavDropdown.Item>
        </>
    )
}
