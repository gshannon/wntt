import './css/Conditions.css'
import { Container, Row, Col, Spinner } from 'react-bootstrap'
import Table from 'react-bootstrap/Table'
import Modal from 'react-bootstrap/Modal'
import useLatestData from './useLatestData'

export default function Conditions(props) {
    const noData = '--'
    let windSpeedStr = noData
    let windGustStr = noData
    let tideStr = noData
    let tempStr = noData
    let windTime = ''
    let tideTime = ''
    let tempTime = ''

    const { data, error } = useLatestData()
    if (error) {
        console.error(error)
    }

    const getContent = () => {
        if (error) {
            return (
                <Row>
                    <Col className='text-center'>
                        There was a problem fetching the data. Please try again later.
                    </Col>
                </Row>
            )
        }
        if (!data) {
            return (
                <Row>
                    <Col className='text-center'>
                        <Spinner animation='border' variant='primary' />
                    </Col>
                </Row>
            )
        } else {
            windSpeedStr = `${data.wind_speed} mph from ${data.wind_dir}`
            windGustStr = `${data.wind_gust} mph`
            tideStr = `${data.tide} ft MLLW ${data.tide_dir}`
            tempStr = `${data.temp}º F`
            windTime = data.wind_time
            tideTime = data.tide_time
            tempTime = data.temp_time

            return (
                <Table borderless>
                    <tbody>
                        <tr className='text-center'>
                            <td className='cond-label'>Wind Speed</td>
                            <td className='cond-label'>Wind Gust</td>
                            <td className='cond-label'>Tide Level</td>
                            <td className='cond-label'>Water Temperature</td>
                        </tr>
                        <tr className='text-center'>
                            <td className='cond-data'>{windSpeedStr}</td>
                            <td className='cond-data'>{windGustStr}</td>
                            <td className='cond-data'>{tideStr}</td>
                            <td className='cond-data'>{tempStr}</td>
                        </tr>
                        <tr className='text-center'>
                            <td className='cond-time'>{windTime}</td>
                            <td className='cond-time'>{windTime}</td>
                            <td className='cond-time'>{tideTime}</td>
                            <td className='cond-time'>{tempTime}</td>
                        </tr>
                    </tbody>
                </Table>
            )
        }
    }

    return (
        <Modal show={true} size='lg' onHide={props.onClose}>
            <Modal.Header className='py-2 cond-header text-white' closeButton closeVariant='white'>
                Current Conditions
            </Modal.Header>
            <Modal.Body className='px-4 py-4'>
                <Container>{getContent()}</Container>
            </Modal.Body>
        </Modal>
    )
}
