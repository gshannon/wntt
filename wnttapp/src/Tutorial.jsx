import './css/Tutorial.css'
import { useRef } from 'react'
import Modal from 'react-bootstrap/Modal'
import Carousel from 'react-bootstrap/Carousel'
import Col from 'react-bootstrap/Col'
import Row from 'react-bootstrap/Row'
import arrowLeft from './images/util/arrow-left.png'
import arrowRight from './images/util/arrow-right.png'

export default function Tutorial(props) {
    const carouselRef = useRef(null)

    const onPrevClick = () => {
        carouselRef && carouselRef.current.prev()
    }
    const onNextClick = () => {
        carouselRef && carouselRef.current.next()
    }

    return (
        <Modal show={true} size='lg' onHide={props.onClose}>
            <Modal.Header className='py-2 tut-header text-white' closeButton>
                {props.title}
            </Modal.Header>
            <Modal.Body className='px-3 py-0'>
                <Row className='align-items-center'>
                    <Col xs={1}>
                        <a href='#' onClick={onPrevClick}>
                            <img src={arrowLeft} width={25} height={31} />
                        </a>
                    </Col>
                    <Col xs={10}>
                        <Carousel
                            ref={carouselRef}
                            variant='dark'
                            keyboard={true}
                            wrap={false}
                            controls={false}
                            indicators={true}
                            interval={null}>
                            {props.data.map((obj, index) => (
                                <Carousel.Item key={index}>
                                    <Row className='tut-top'>
                                        <Col className='text-center'>
                                            <img
                                                className={'m-3 ' + (obj.cls ?? 'pic-width-90')}
                                                src={obj.img}
                                                alt=''
                                            />
                                        </Col>
                                    </Row>
                                    <Row className='tut-bottom'>
                                        <Col className='tut-text text-center'>{obj.render()}</Col>
                                    </Row>
                                </Carousel.Item>
                            ))}
                        </Carousel>
                    </Col>
                    <Col xs={1}>
                        <a href='#' onClick={onNextClick}>
                            <img src={arrowRight} width={25} height={31} />
                        </a>
                    </Col>
                </Row>
            </Modal.Body>
        </Modal>
    )
}
