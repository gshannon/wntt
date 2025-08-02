import './css/Conditions.css'
import { Container, Row, Col, Spinner } from 'react-bootstrap'
import Table from 'react-bootstrap/Table'
import Modal from 'react-bootstrap/Modal'
import useLatestData from './useLatestData'

export default function Conditions(props) {
    const noData = '--'

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
                            <td className='cond-data'>
                                {data.wind_speed
                                    ? `${data.wind_speed} mph from ${data.wind_dir}`
                                    : noData}
                            </td>
                            <td className='cond-data'>
                                {data.wind_gust ? `${data.wind_gust} mph` : noData}
                            </td>
                            <td className='cond-data'>
                                {data.tide_dir ? `${data.tide} ft MLLW ${data.tide_dir}` : noData}
                            </td>
                            <td className='cond-data'>{data.temp ? `${data.temp}º F` : noData}</td>
                        </tr>
                        <tr className='text-center'>
                            <td className='cond-time'>{data.wind_time}</td>
                            <td className='cond-time'>{data.wind_time}</td>
                            <td className='cond-time'>{data.tide_time}</td>
                            <td className='cond-time'>{data.temp_time}</td>
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
