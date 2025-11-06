import './css/AddressPopup.css'
import { useEffect, useEffectEvent, useState } from 'react'
import Modal from 'react-bootstrap/Modal'
import { Form } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import useGeocode from './useGeocode'
import { useQueryClient } from '@tanstack/react-query'

export default function AddressPopup({ onClose, setAddressMarker, station }) {
    const queryClient = useQueryClient()
    const [addressValue, setAddressValue] = useState('')

    const { isPending, data, error } = useGeocode(station, addressValue)

    const onQueryFinished = useEffectEvent(() => {
        if (!isPending) {
            // Force useQuery to not use cache for future queries.
            queryClient.removeQueries({ queryKey: ['geocode'] })
        }
    })

    useEffect(() => {
        onQueryFinished()
    }, [error?.message]) // TODO: Not sure why this works

    useEffect(() => {
        if (data) {
            setAddressMarker({ lat: Number(data.lat), lng: Number(data.lon) })
            onClose()
        }
    }, [data, setAddressMarker, onClose])

    const handleSubmit = (e) => {
        e.preventDefault()
        setAddressValue(e.currentTarget.addressLookup.value)
    }

    return (
        <Modal show={true} onHide={onClose}>
            <Modal.Header className='address-header' closeButton>
                <Modal.Title className='address-body'>Address Lookup</Modal.Title>
            </Modal.Header>
            <Modal.Body className='address-body'>
                <Form onSubmit={(e) => handleSubmit(e)}>
                    <Form.Group className='mb-3' controlId='addressLookup'>
                        {isPending && !!addressValue ? (
                            <Spinner animation='border' variant='primary' />
                        ) : (
                            <p className='text-white'>{error?.message}</p>
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
                    <Button
                        variant='custom-primary'
                        type='submit'
                        disabled={isPending && !!addressValue}>
                        Search
                    </Button>
                </Form>
            </Modal.Body>
        </Modal>
    )
}
