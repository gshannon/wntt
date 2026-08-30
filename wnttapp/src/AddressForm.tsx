import './css/AddressForm.css'
import { type Dispatch, type FormEvent, type SetStateAction, useState, useEffect } from 'react'
import { Form } from 'react-bootstrap'
import { Col, Row, Alert } from 'react-bootstrap'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import useAddressLookup from './useAddressLookup'
import ErrorBlock from './ErrorBlock'
import * as mu from './mapUtils'
import type Station from './Station'
import type { LatLng } from './types'

export default function AddressForm({
    setPendingMarkerLocation,
    station,
}: {
    setPendingMarkerLocation: Dispatch<SetStateAction<LatLng | null>>
    station: Station
}) {
    const [addressValue, setAddressValue] = useState('') // persist between renders
    const [errorMessage, setErrorMessage] = useState<string | Error | null>(null)
    const [doLookup, setDoLookup] = useState(false)
    const [searchLocation, setSearchLocation] = useState<LatLng | null>(null)

    const { isLoading, data: location, error } = useAddressLookup(addressValue, doLookup)

    if (doLookup && !isLoading) {
        if (error) {
            setErrorMessage(error)
        } else {
            if (location?.lat && location?.lng) {
                if (mu.isInBounds(station.mapBounds, location)) {
                    setSearchLocation({
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

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        const input = e.currentTarget.elements.namedItem('addressLookup') as HTMLInputElement
        setAddressValue(input.value)
        setDoLookup(true)
    }

    useEffect(() => {
        setPendingMarkerLocation(searchLocation)
    }, [setPendingMarkerLocation, searchLocation])

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
                                    placeholder='Enter address'
                                    defaultValue={addressValue}
                                />
                            </Form.Group>
                        </Col>
                    </Row>
                    <Row className='align-items-end mx-0'>
                        <Form.Text style={{ color: 'white' }}>
                            Must be in the local area. Include city.
                        </Form.Text>
                    </Row>
                    <Row className='mx-0 my-1 justify-content-end'>
                        <Col className='flex-grow-0'>
                            {isLoading ?
                                <Spinner animation='grow' variant='light' />
                            :   <Button
                                    variant='custom-primary'
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

function MyAlert({
    errorMessage,
    closeError,
}: {
    errorMessage: string | Error | null
    closeError: () => void
}) {
    return (
        <Alert show={errorMessage != null} className='py-1 my-1' variant='secondary'>
            <ErrorBlock error={errorMessage} />
            <div className='d-flex justify-content-end'>
                <Button onClick={() => closeError()} className='my-1' variant='secondary'>
                    OK
                </Button>
            </div>
        </Alert>
    )
}
