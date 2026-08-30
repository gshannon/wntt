import './css/Help.css'
import { useState, useContext } from 'react'
import { Col, Row } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import Container from 'react-bootstrap/Container'
import { getData as getGraphData } from './tutorials/graph'
import { getData as getMapData } from './tutorials/map'
import Tutorial from './Tutorial'
import { AppContext } from './AppContext'

export default function Help() {
    const ctx = useContext(AppContext)
    const [showGraphTut, setShowGraphTut] = useState(false)
    const [showMapTut, setShowMapTut] = useState(false)

    const onModalClose = () => {
        setShowGraphTut(false)
        setShowMapTut(false)
    }

    return (
        <Container>
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
                <Tutorial
                    onClose={onModalClose}
                    data={getGraphData(ctx.station)}
                    title='Graph Tutorial'
                />
            )}
            {showMapTut && (
                <Tutorial
                    onClose={onModalClose}
                    data={getMapData(ctx.station)}
                    title='Map Tutorial'
                />
            )}
        </Container>
    )
}
