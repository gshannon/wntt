import './css/Top.css'
import { useState } from 'react'
import Container from 'react-bootstrap/Container'
import Navbar from 'react-bootstrap/Navbar'
import NavbarBrand from 'react-bootstrap/NavbarBrand'
import NavbarToggle from 'react-bootstrap/NavbarToggle'
import NavbarCollapse from 'react-bootstrap/NavbarCollapse'
import NavDropdown from 'react-bootstrap/NavDropdown'
import Nav from 'react-bootstrap/Nav'
import NavLink from 'react-bootstrap/NavLink'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import { Page } from './utils'
import Logo from './images/wr-logo.png'
import Wave from './images/util/wave.png'
import HelpButton from './images/util/help.png'
import Conditions from './Conditions'

export default function Top(props) {
    const page = props.page
    const gotoPage = props.gotoPage
    const [showConditions, setShowConditions] = useState(false)

    const onModalClose = () => {
        setShowConditions(false)
    }

    return (
        <>
            <Navbar className='my-0' expand='md'>
                <Container>
                    <NavbarBrand onClick={() => gotoPage(Page.Home)}>
                        Wells Reserve <br />
                        <i>
                            <b>Tide Tracker</b>
                        </i>
                    </NavbarBrand>
                    <NavbarToggle />
                    <NavbarCollapse className='me-1'>
                        <Nav>
                            <NavLink
                                onClick={() => gotoPage(Page.Home)}
                                active={page === Page.Home}>
                                Home
                            </NavLink>
                            <NavLink
                                onClick={() => gotoPage(Page.Graph)}
                                active={page === Page.Graph}>
                                Graph
                            </NavLink>
                            <NavLink onClick={() => gotoPage(Page.Map)} active={page === Page.Map}>
                                Map
                            </NavLink>
                            <NavLink
                                onClick={() => gotoPage(Page.About)}
                                active={page === Page.About}>
                                About
                            </NavLink>
                        </Nav>
                    </NavbarCollapse>
                    <NavbarBrand>
                        <OverlayTrigger
                            placement='bottom'
                            overlay={
                                <Tooltip id='id-cond-button'>
                                    Popup that shows current weather and tide data.
                                </Tooltip>
                            }>
                            <NavLink
                                className='px-sm-2 px-lg-4'
                                onClick={() => setShowConditions(true)}>
                                <img
                                    className='conditions-menu object-fit-contain'
                                    src={Wave}
                                    width={50}
                                    alt='Current conditions'
                                />
                            </NavLink>
                        </OverlayTrigger>
                    </NavbarBrand>
                    <NavDropdown
                        className='ps-sm-2 pe-sm-4'
                        title={
                            <img
                                className='object-fit-contain'
                                src={HelpButton}
                                width={50}
                                alt='Help'
                            />
                        }>
                        <NavDropdown.Item onClick={() => gotoPage(Page.Glossary)}>
                            Glossary
                        </NavDropdown.Item>
                        <NavDropdown.Item onClick={() => gotoPage(Page.Help)}>
                            Help
                        </NavDropdown.Item>
                    </NavDropdown>
                    <NavbarBrand>
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://wellsreserve.org'>
                            <img
                                className='object-fit-contain'
                                src={Logo}
                                width={165}
                                alt='Wells Reserve Logo'
                            />
                        </a>
                    </NavbarBrand>
                </Container>
                {showConditions && <Conditions onClose={onModalClose} />}
            </Navbar>
        </>
    )
}
