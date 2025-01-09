import './css/Top.css'
import Container from 'react-bootstrap/Container'
import Navbar from 'react-bootstrap/Navbar'
import NavbarBrand from 'react-bootstrap/NavbarBrand'
import NavbarToggle from 'react-bootstrap/NavbarToggle'
import NavbarCollapse from 'react-bootstrap/NavbarCollapse'
import Nav from 'react-bootstrap/Nav'
import NavLink from 'react-bootstrap/NavLink'
import { Page } from './utils'
import Logo from './images/wr-logo.png'

export default function Top(props) {
    let page = props.page
    let gotoPage = props.gotoPage

    return (
        <>
            <Navbar className='my-0' expand='sm'>
                <Container>
                    <NavbarBrand onClick={() => gotoPage(Page.Home)}>
                        <h4>Wells Reserve Tide Tracker</h4>
                    </NavbarBrand>
                    <NavbarToggle />
                    <NavbarCollapse>
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
                                onClick={() => gotoPage(Page.Glossary)}
                                active={page === Page.Glossary}>
                                Glossary
                            </NavLink>
                            <NavLink
                                onClick={() => gotoPage(Page.About)}
                                active={page === Page.About}>
                                About
                            </NavLink>
                        </Nav>
                    </NavbarCollapse>
                    <NavbarBrand>
                        <a
                            target='_blank'
                            rel='noopener noreferrer'
                            href='https://wellsreserve.org'>
                            <img src={Logo} width={165} height={55} alt='Wells Reserve Logo' />
                        </a>
                    </NavbarBrand>
                </Container>
            </Navbar>
        </>
    )
}
