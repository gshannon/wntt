import './css/AddressPopup.css'
import { useEffect, useState } from 'react'
import Modal from 'react-bootstrap/Modal'
import { Form } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import axios from 'axios'
import { MapBounds, GeocodeUrl } from './utils'

const Mode = Object.freeze({
    Ready: 1,
    Loading: 2,
    Error: 3,
})

export default function AddressPopup(props) {
    const onClose = props.onClose
    const setAddressMarker = props.setAddressMarker
    const [mode, setMode] = useState(Mode.Ready)
    const [addressValue, setAddressValue] = useState('')
    const [error, setError] = useState('')

    const isInBounds = (lat, lon) => {
        const minLat = Math.min(MapBounds[0][0], MapBounds[1][0])
        const minLon = Math.min(MapBounds[0][1], MapBounds[1][1])
        const maxLat = Math.max(MapBounds[0][0], MapBounds[1][0])
        const maxLon = Math.max(MapBounds[0][1], MapBounds[1][1])
        return lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon
    }

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
        if (addressValue && /\S/.test(addressValue)) {
            const lookupValue = addressValue + ' Maine USA'
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
    }, [addressValue, setAddressMarker, onClose])

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
                            Must be in the local area. Include city. It is assumed to be Maine.
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
