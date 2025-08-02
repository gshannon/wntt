import './css/Help.css'
import { useState } from 'react'
import { Col, Row } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import Container from 'react-bootstrap/Container'
import { getData as getGraphData } from './tutorials/graph'
import { getData as getMapData } from './tutorials/map'
import Tutorial from './Tutorial'

export default function Help() {
    const [showGraphTut, setShowGraphTut] = useState(false)
    const [showMapTut, setShowMapTut] = useState(false)

    const onModalClose = () => {
        setShowGraphTut(false)
        setShowMapTut(false)
    }

    return (
        <Container>
            <Row>
                <Col className='text-center pt-4 pb-2 titles'>
                    This video covers all the basics of the Tide Tracker.
                </Col>
            </Row>
            <Row>
                <Col className='text-center video'>
                    <iframe
                        className='video'
                        allow='fullscreen'
                        referrerPolicy='no-referrer'
                        src='https://www.youtube.com/embed/wr2nfjE43Gg?autoplay=0'></iframe>
                </Col>
            </Row>
            <Row>
                <Col className='text-center pt-4 pb-2 titles'>Slide show tutorials</Col>
            </Row>
            <Row>
                <Col className='text-center'>
                    <Button
                        variant='primary'
                        className='mx-4 my-2'
                        onClick={() => setShowGraphTut(true)}>
                        Graph Tutorial
                    </Button>
                    <Button
                        variant='primary'
                        className='mx-4 my-2'
                        onClick={() => setShowMapTut(true)}>
                        Map Tutorial
                    </Button>
                </Col>
            </Row>
            {showGraphTut && (
                <Tutorial onClose={onModalClose} data={getGraphData()} title='Graph Tutorial' />
            )}
            {showMapTut && (
                <Tutorial onClose={onModalClose} data={getMapData()} title='Map Tutorial' />
            )}
        </Container>
    )
}
