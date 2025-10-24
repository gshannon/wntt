import './css/AddressPopup.css'
import { useEffect, useState } from 'react'
import Modal from 'react-bootstrap/Modal'
import { Form } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import axios from 'axios'
import { GeocodeUrl } from './utils'

const Mode = Object.freeze({
    Ready: 1,
    Loading: 2,
    Error: 3,
})

export default function AddressPopup({ onClose, setAddressMarker, station }) {
    const [mode, setMode] = useState(Mode.Ready)
    const [addressValue, setAddressValue] = useState('')
    const [error, setError] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        const val = e.currentTarget.addressLookup.value
        setMode(Mode.Loading)
        setAddressValue(val)
        setError('')
    }

    const handleError = (message) => {
        setError(message)
        setMode(Mode.Error)
    }

    useEffect(() => {
        const isInBounds = (lat, lon) => {
            const minLat = Math.min(station.mapBounds[0][0], station.mapBounds[1][0])
            const minLon = Math.min(station.mapBounds[0][1], station.mapBounds[1][1])
            const maxLat = Math.max(station.mapBounds[0][0], station.mapBounds[1][0])
            const maxLon = Math.max(station.mapBounds[0][1], station.mapBounds[1][1])
            return lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon
        }

        if (addressValue && /\S/.test(addressValue)) {
            const lookupValue = addressValue + ' USA'
            const encoded = lookupValue.replace(/\s+/gi, '+')
            const url =
                GeocodeUrl + '/search?q=' + encoded + '&api_key=' + import.meta.env.VITE_GEOCODE_KEY
            axios
                .get(url)
                .then((res) => {
                    if (res.data !== undefined && res.data[0] !== undefined) {
                        const lat = res.data[0].lat
                        const lon = res.data[0].lon
                        if (isInBounds(lat, lon)) {
                            setAddressMarker({ lat: Number(lat), lng: Number(lon) })
                            onClose()
                        } else {
                            handleError('That address does not appear to be in the local area')
                        }
                    } else {
                        handleError('That appears to be an invalid address')
                    }
                })
                .catch((error) => {
                    console.error(JSON.stringify(error))
                    handleError('An error occurred. Please try again.')
                })
        }
        // TODO: improve these dependencies
    }, [addressValue, setAddressMarker, onClose, station.mapBounds])

    return (
        <Modal show={true} onHide={onClose}>
            <Modal.Header className='address-header' closeButton>
                <Modal.Title className='address-body'>Address Lookup</Modal.Title>
            </Modal.Header>
            <Modal.Body className='address-body'>
                <Form onSubmit={(e) => handleSubmit(e)}>
                    <Form.Group className='mb-3' controlId='addressLookup'>
                        {mode === Mode.Loading ? (
                            <Spinner animation='border' variant='primary' />
                        ) : (
                            <p className='text-danger'>{error}</p>
                        )}
                        <Form.Control
                            name='addr'
                            type='text'
                            required={true}
                            autoFocus={true}
                            placeholder='Enter address to find on map'
                            defaultValue={addressValue}
                        />
                        <Form.Text style={{ color: 'white' }}>
                            Must be in the local area. Include city and state.
                        </Form.Text>
                    </Form.Group>
                    <Button variant='custom-primary' type='submit' disabled={mode === Mode.Loading}>
                        Search
                    </Button>
                </Form>
            </Modal.Body>
        </Modal>
    )
}
