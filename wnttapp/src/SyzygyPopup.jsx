import './css/Syzygy.css'
import Row from 'react-bootstrap/Row'
import Container from 'react-bootstrap/Container'
import Modal from 'react-bootstrap/Modal'
import { useContext } from 'react'
import { Page, SyzygyInfo } from './utils'
import { AppContext } from './AppContext'

export default function SyzygyPopup({ code, onClose }) {
    const ctx = useContext(AppContext)
    return (
        <Modal id='syzygy-modal' show={true} size='md' onHide={onClose}>
            <Modal.Header
                className='py-2 syzygy-header text-white'
                closeButton
                closeVariant='white'>
                {SyzygyInfo[code].name}
            </Modal.Header>
            <Modal.Body className='px-4 py-4'>
                <Container>
                    <Row className='justify-content-start mx-0 mb-3'>
                        <Content code={code} gotoPage={ctx.gotoPage} />
                    </Row>
                </Container>
            </Modal.Body>
        </Modal>
    )
}

const Help = ({ gotoPage }) => {
    return (
        <p>
            <a href='#' className='my-1' onClick={() => gotoPage(Page.HelpSyzygy, Page.Graph)}>
                More details...
            </a>{' '}
        </p>
    )
}

const Content = ({ code, gotoPage }) => {
    if (code === 'NM' || code === 'FM') {
        return (
            <>
                <p>
                    When the Sun, Moon & Earth are in alignment, the pull of the Sun and Moon are
                    combined, causing higher high tides and lower low tides. This occurs at every
                    Full Moon and New Moon, and results in a <b>spring tide</b>. If this coincides
                    with the Moon in <b>perigee</b>, there will be a <b>supermoon</b> and we get a{' '}
                    <b>perigean spring tide</b>, also known as a <b>king tide</b>.
                </p>
                <Help gotoPage={gotoPage} />
            </>
        )
    } else if (code === 'FQ' || code === 'LQ') {
        return (
            <>
                <p>
                    When the Sun and Moon are at a 90º angle from Earth, as happens at First Quarter
                    and Last Quarter, we have a <b>neap tide</b>. In this case, the Sun&apos;s
                    gravity partially cancels out that of the Moon, and the tide range will be
                    smaller -- lower highs and higher lows.
                </p>
                <Help gotoPage={gotoPage} />
            </>
        )
    } else if (code === 'PG') {
        return (
            <>
                <p>
                    <b>Perigee</b> is the point in the Moon&apos;s orbit where it is closest to the
                    Earth, and will therefore have its greatest tidal influence. That influence will
                    be either enhanced or reduced depending on the Earth-Moon-Sun alignment and
                    distance of the Sun. If perigee coincides with New Moon or Full Moon, we will
                    have a <b>perigean spring tide</b>, also known as a <b>king tide</b>.
                </p>
                <Help gotoPage={gotoPage} />
            </>
        )
    } else if (code === 'PH') {
        return (
            <>
                <p>
                    During the Earth&apos;s orbit around the Sun, the nearest point is called{' '}
                    <b>perihelion</b>, and it occurs just <b>once per year</b>, two weeks after the
                    Winter Solstice. Here, the Sun&apos;s gravity has its most profound effect. If
                    close to a New or Full Moon, the Sun will enhance the Moon&apos;s pull. At First
                    or Last Quarter, it will partially cancel out the Moon&apos;s pull.
                </p>
                <Help gotoPage={gotoPage} />
            </>
        )
    }
}
