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
            <Row className='mt-md-5'>
                <Col className='text-center'>
                    <h4>This video covers all the basics of the Tide Tracker:</h4>
                </Col>
            </Row>
            <Row className='my-md-3'>
                <Col className='text-center'>
                    <iframe
                        style={{ border: '1px solid black' }}
                        allow='fullscreen'
                        referrerPolicy='no-referrer'
                        width='560'
                        height='315'
                        src='https://www.youtube.com/embed/0RbrZBbK9B8?autoplay=0'></iframe>
                </Col>
            </Row>
            <Row className='mt-md-5'>
                <Col className='text-center'>
                    <h4>Slide show tutorials:</h4>
                </Col>
            </Row>
            <Row className='my-md-3'>
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
