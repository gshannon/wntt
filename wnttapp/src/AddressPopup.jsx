import './css/AddressPopup.css'
import { useState, useEffect, useEffectEvent } from 'react'
import Modal from 'react-bootstrap/Modal'
import { Form } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import useGeocode from './useGeocode'
import * as mu from './mapUtils'
import { apiErrorResponse } from './utils'

export default function AddressPopup({ setPendingMarkerLocation, onClose, station }) {
    const [addressValue, setAddressValue] = useState('') // persist between renders

    const { isLoading, data: location, error } = useGeocode(addressValue)

    let markerLocation = null
    let errorMessage = ''

    if (!isLoading) {
        if (error) {
            errorMessage = apiErrorResponse(error)
        } else {
            if (location?.lat && location?.lng) {
                if (mu.isInBounds(station.mapBounds, location)) {
                    markerLocation = {
                        lat: Number(location.lat),
                        lng: Number(location.lng),
                    }
                } else {
                    console.log(`(${location.lat},${location.lng}) is  not in map bounds`)
                    errorMessage = 'That address does not appear to be within the map bounds.'
                }
            } else if (addressValue && !error) {
                console.log('No error, but no data so must be invalid address')
                errorMessage = 'That appears to be an invalid address.'
            }
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        setAddressValue(e.currentTarget.addressLookup.value)
    }

    const onLocationSet = useEffectEvent(() => {
        setPendingMarkerLocation(markerLocation)
        onClose()
    })

    useEffect(() => {
        if (markerLocation?.lat && markerLocation?.lng) {
            onLocationSet()
        }
    }, [markerLocation?.lat, markerLocation?.lng])

    return (
        <Modal show={true} onHide={onClose}>
            <Modal.Header className='address-header' closeButton>
                <Modal.Title className='address-body'>Address Lookup</Modal.Title>
            </Modal.Header>
            <Modal.Body className='address-body'>
                <Form onSubmit={(e) => handleSubmit(e)}>
                    <Form.Group className='mb-3' controlId='addressLookup'>
                        {isLoading ? (
                            <Spinner animation='border' variant='primary' />
                        ) : (
                            <p className='text-white'>{errorMessage}</p>
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
                    <Button variant='custom-primary' type='submit' disabled={isLoading}>
                        Search
                    </Button>
                </Form>
            </Modal.Body>
        </Modal>
    )
}
