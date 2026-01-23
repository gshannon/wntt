import { useEffect } from 'react'
import { Col, Row } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import axios from 'axios'
import * as Sentry from '@sentry/react'

// We're using 406-NotAcceptable on the backend to indicate we need to update.  This happens
// when the a change was made on either end that effects the other, or just to force users
// to update to get new functionality.
const NotAcceptable = 406 // version out of date

// Display an error message in a div. error param can be:
// 1) string
// 2) AxiosError with status NotAcceptable, and a page reload will be forced
// 3) any other AxiosError, and a generic message is displayed.
export default function ErrorBlock({ error }) {
    const isUpgrade =
        axios.isAxiosError(error) && (error.response?.status ?? null) === NotAcceptable
    const upgradeSeconds = 10

    // If we're upgrading, force it with an effect.
    useEffect(() => {
        if (isUpgrade) {
            const timer = setTimeout(() => {
                window.location.reload()
            }, upgradeSeconds * 1000)

            return () => {
                // do it here also in case they navigated away before the timer was up
                window.location.reload()
                clearTimeout(timer)
            }
        }
        return
    }, [isUpgrade])

    if (error == null) {
        Sentry.logger.error('Error is NULL!')
        return ''
    }
    if (isUpgrade) {
        return (
            <>
                <Row>
                    <Col className='d-flex justify-content-center text-dark bg-light pt-3'>
                        A new version was detected. Click to update, or the app will automatically
                        update in {upgradeSeconds} seconds.
                    </Col>
                </Row>
                <Row>
                    <Col className='d-flex justify-content-center text-dark bg-light py-3'>
                        <Button
                            variant='info'
                            className='mb-3'
                            onClick={() => window.location.reload()}>
                            Get New Version
                        </Button>
                    </Col>
                </Row>
            </>
        )
    } else {
        const msg =
            typeof error === 'string'
                ? error
                : 'There was a problem fetching the data. Please try again later.'
        return (
            <Row>
                <Col className='d-flex justify-content-center text-warning bg-dark py-3'>{msg}</Col>
            </Row>
        )
    }
}
