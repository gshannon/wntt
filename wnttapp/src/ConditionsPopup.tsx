import './css/Conditions.css'
import Modal from 'react-bootstrap/Modal'
import Conditions from './Conditions'
import useLatestData from './useLatestData'
import type Station from './Station'

export default function ConditionsPopup({
    station,
    onClose,
}: {
    station: Station
    onClose: () => void
}) {
    const { data, error } = useLatestData(station)

    return (
        <Modal id='conditions-modal' show={true} onHide={onClose}>
            <Modal.Header className='py-2 cond-header text-white' closeButton closeVariant='white'>
                Latest Conditions - {station.waterStationName}
            </Modal.Header>
            <Modal.Body className='px-0 py-0 px-sm-4 py-sm-4'>
                <Conditions data={data ?? null} error={error} />
            </Modal.Body>
        </Modal>
    )
}
