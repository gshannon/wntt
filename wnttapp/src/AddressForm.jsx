import './css/AddressForm.css'
import { useState } from 'react'
import { Form } from 'react-bootstrap'
import { Col, Row, Alert } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import useAddressLookup from './useAddressLookup'
import * as mu from './mapUtils'

export default function AddressForm({ setPendingMarkerLocation, station }) {
    const [addressValue, setAddressValue] = useState('') // persist between renders
    const [errorMessage, setErrorMessage] = useState(null)
    const [doLookup, setDoLookup] = useState(false)

    const { isLoading, data: location, error } = useAddressLookup(addressValue)

    if (doLookup && !isLoading) {
        if (error) {
            setErrorMessage(error)
        } else {
            if (location?.lat && location?.lng) {
                if (mu.isInBounds(station.mapBounds, location)) {
                    setPendingMarkerLocation({
                        lat: Number(location.lat),
                        lng: Number(location.lng),
                    })
                } else {
                    setErrorMessage('That address does not appear to be within the map bounds.')
                }
            } else if (addressValue && !error) {
                // No error, but no data so must be invalid address
                setErrorMessage('That appears to be an invalid address.')
            }
        }
        setDoLookup(false)
    }

    const closeError = () => {
        setErrorMessage(null)
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        setAddressValue(e.currentTarget.addressLookup.value)
        setDoLookup(true)
    }

    return (
        <>
            {errorMessage != null && (
                <MyAlert errorMessage={errorMessage} closeError={closeError} />
            )}

            {errorMessage == null && (
                <Form className='address-body' onSubmit={(e) => handleSubmit(e)}>
                    <Row className='mx-0 mt-2'>
                        <Col>
                            <Form.Group controlId='addressLookup'>
                                <Form.Control
                                    name='addr'
                                    type='text'
                                    required={true}
                                    autoFocus={true}
                                    controlId='addressLookup'
                                    placeholder='Enter address'
                                    defaultValue={addressValue}
                                />
                            </Form.Group>
                        </Col>
                    </Row>
                    <Row className='align-items-end mx-0'>
                        <Form.Text style={{ color: 'white' }}>
                            Must be in the local area. Include city and state.
                        </Form.Text>
                    </Row>
                    <Row className='mx-0 my-1 justify-content-end'>
                        <Col className='flex-grow-0'>
                            {isLoading ?
                                <Spinner animation='grow' variant='light' />
                            :   <Button
                                    variant='custom-primary'
                                    size='md'
                                    type='submit'
                                    disabled={isLoading}>
                                    Search
                                </Button>
                            }
                        </Col>
                    </Row>
                </Form>
            )}
        </>
    )
}

function MyAlert({ errorMessage, closeError }) {
    return (
        <Alert show={errorMessage != null} className='py-1 my-1' variant='secondary'>
            <div>{errorMessage}</div>
            <div className='d-flex justify-content-end'>
                <Button onClick={() => closeError()} className='my-1' variant='secondary'>
                    OK
                </Button>
            </div>
        </Alert>
    )
}
