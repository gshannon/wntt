import './css/Conditions.css'
import Modal from 'react-bootstrap/Modal'
import Conditions from './Conditions'
import useLatestData from './useLatestData'

export default function ConditionsPopup({ station, onClose }) {
    const { data, error } = useLatestData(station)
    if (error) {
        console.error(error)
    }

    return (
        <Modal id='conditions-modal' show={true} size='md' onHide={onClose}>
            <Modal.Header className='py-2 cond-header text-white' closeButton closeVariant='white'>
                Latest Conditions
            </Modal.Header>
            <Modal.Body className='px-4 py-4'>
                <Conditions data={data} error={error} />
            </Modal.Body>
        </Modal>
    )
}
