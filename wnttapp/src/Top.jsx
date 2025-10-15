import './css/Top.css'
import { useState } from 'react'
import Container from 'react-bootstrap/Container'
import { Row, Col } from 'react-bootstrap'
import NavbarBrand from 'react-bootstrap/NavbarBrand'
import NavDropdown from 'react-bootstrap/NavDropdown'
import Nav from 'react-bootstrap/Nav'
import NavLink from 'react-bootstrap/NavLink'
import { Page } from './utils'
import Logo from './images/wr-logo.png'
import Wave from './images/util/wave.png'
import Hamburger from './images/util/hamburger.png'
import HelpButton from './images/util/help.png'
import ConditionsPopup from './ConditionsPopup'
import Overlay from './Overlay'
export default function Top(props) {
    const page = props.page
    const gotoPage = props.gotoPage
    const [showConditions, setShowConditions] = useState(false)

    const onModalClose = () => {
        setShowConditions(false)
    }

    const expandedMenu = (
        <Col className='expanded-menu px-1'>
            <Nav>
                <NavLink onClick={() => gotoPage(Page.Home)} active={page === Page.Home}>
                    Home
                </NavLink>
                <NavLink onClick={() => gotoPage(Page.Graph)} active={page === Page.Graph}>
                    Graph
                </NavLink>
                <NavLink onClick={() => gotoPage(Page.Map)} active={page === Page.Map}>
                    Map
                </NavLink>
                <NavLink onClick={() => gotoPage(Page.About)} active={page === Page.About}>
                    About
                </NavLink>
            </Nav>
        </Col>
    )

    const pulldownMenu = (
        <Col className='hamburger-menu px-1'>
            <NavDropdown className='pe-1' title={<img width={35} src={Hamburger} alt='Menu' />}>
                <NavDropdown.Item onClick={() => gotoPage(Page.Home)} active={page === Page.Home}>
                    Home
                </NavDropdown.Item>
                <NavDropdown.Item onClick={() => gotoPage(Page.Graph)} active={page === Page.Graph}>
                    Graph
                </NavDropdown.Item>
                <NavDropdown.Item onClick={() => gotoPage(Page.Map)} active={page === Page.Map}>
                    Map
                </NavDropdown.Item>
                <NavDropdown.Item onClick={() => gotoPage(Page.About)} active={page === Page.About}>
                    About
                </NavDropdown.Item>
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
                    {/* One of these will be hidden in the CSS */}
                    {expandedMenu}
                    {pulldownMenu}
                    <Col className='px-1'>
                        <Overlay
                            text='Popup that shows current weather and tide data.'
                            placement='bottom'
                            contents={
                                <NavLink
                                    className='px-md-3'
                                    onClick={() => setShowConditions(true)}>
                                    <img
                                        className='conditions-img'
                                        src={Wave}
                                        width={50}
                                        alt='Latest conditions'
                                    />
                                </NavLink>
                            }></Overlay>
                    </Col>
                    <Col className='px-1'>
                        <NavDropdown
                            className='pe-1'
                            title={
                                <img className='help-img' width={40} src={HelpButton} alt='Help' />
                            }>
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
                                className={page === Page.Help ? 'active' : ''}
                                onClick={() => gotoPage(Page.Help)}>
                                Tutorials
                            </NavDropdown.Item>
                        </NavDropdown>
                    </Col>
                    <Col className='px-1'>
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://wellsreserve.org'>
                            <img className='logo' src={Logo} width={130} alt='Wells Reserve Logo' />
                        </a>
                    </Col>
                </Row>
            </Container>
            {showConditions && <ConditionsPopup onClose={onModalClose} />}
        </div>
    )
}
