import './css/Conditions.css'
import { Row, Col, Spinner } from 'react-bootstrap'
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
                <div className='cond-container'>
                    <div className='cond-label'>Wind Speed</div>
                    <div className='cond-data'>
                        {data.wind_speed ? `${data.wind_speed} mph from ${data.wind_dir}` : noData}
                    </div>
                    <div className='cond-time'>{data.wind_time}</div>

                    <div className='cond-label'>Wind Gust</div>
                    <div className='cond-data'>
                        {data.wind_gust ? `${data.wind_gust} mph` : noData}
                    </div>
                    <div className='cond-time'>{data.wind_time}</div>

                    <div className='cond-label'>Tide Level</div>
                    <div className='cond-data'>
                        {data.tide_dir ? `${data.tide} ft MLLW ${data.tide_dir}` : noData}
                    </div>
                    <div className='cond-time'>{data.tide_time}</div>

                    <div className='cond-label'>Water Temp</div>
                    <div className='cond-data'>{data.temp ? `${data.temp}º F` : noData}</div>

                    <div className='cond-time'>{data.temp_time}</div>
                </div>
            )
        }
    }

    return (
        <Modal show={true} size='md' onHide={props.onClose}>
            <Modal.Header className='py-2 cond-header text-white' closeButton closeVariant='white'>
                Latest Conditions
            </Modal.Header>
            <Modal.Body className='px-4 py-4'>{getContent()}</Modal.Body>
        </Modal>
    )
}
