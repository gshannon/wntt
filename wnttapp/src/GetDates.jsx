import './css/GetDates.css'
import { useContext, useState } from 'react'
import Button from 'react-bootstrap/Button'
import { Col, Form, FormLabel, FormText, Row } from 'react-bootstrap'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import { DatePicker } from 'reactstrap-date-picker'
import Container from 'react-bootstrap/Container'
import {
    addDays,
    dateDiff,
    limitDate,
    stringify,
    getMaxNumDays,
    minGraphDate,
    maxGraphDate,
    navd88ToMllw,
    Page,
} from './utils'
import Tutorial from './Tutorial'
import { AppContext } from './AppContext'
import { getData } from './tutorials/graph'

// Allow users to set start/end date range for the graph.

export default function GetDates({
    startCtl,
    setStartCtl,
    endCtl,
    setEndCtl,
    setDateRangeStrings,
    resetDateControls,
}) {
    const appContext = useContext(AppContext)
    const [showTut, setShowTut] = useState(false)

    const months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
    ]
    const minDate = minGraphDate()
    const maxDate = maxGraphDate()
    const rangeMin = `${months[minDate.getMonth()]} ${minDate.getFullYear()}`
    const rangeMax = `${months[maxDate.getMonth()]} ${maxDate.getFullYear()}`

    const handleSubmit = (e) => {
        // The form has 2 submit buttons -- refresh & reset, so handle them both here.
        e.preventDefault()
        const clickedButton = e.nativeEvent.submitter

        if (clickedButton.name === 'refresh') {
            // This will force a re-render even if the dates are the same as before
            setDateRangeStrings(stringify(startCtl.start), stringify(endCtl.end))
        } else if (clickedButton.name === 'reset') {
            resetDateControls() // Let parent reset the date controls, and the appContext.
        }
    }

    const handleStartChange = (formatted) => {
        // When they change start date, we automatically change end date also, to match the previously
        // selected number of days shown, if possible.
        // Datepicker won't call this if date is invalid or outside min/max, but it calls it if
        // they empty it out or click Today when date is already today, so we will ignore those.
        if (formatted && formatted !== stringify(startCtl.start)) {
            const daysShown = dateDiff(startCtl.start, endCtl.end) + 1
            const newStart = new Date(formatted)
            const newEnd = limitDate(addDays(newStart, daysShown - 1))
            setStartCtl({ ...startCtl, start: newStart })
            setEndCtl({
                min: newStart,
                // Set the end date to honor the numDays from previous settings, limited by overall max.
                end: newEnd,
                max: limitDate(addDays(newStart, getMaxNumDays() - 1)),
            })
        }
    }

    const handleEndChange = (formatted) => {
        // When they change the end date, it has no effect on the start date. Since the date control
        // won't allow a date out of range, we can skip range checking here.
        // Note we must do nothing if the date did not change, as that would cause no re-rendering.
        if (formatted && formatted !== stringify(endCtl.end)) {
            const newEnd = new Date(formatted)
            setEndCtl({ ...endCtl, end: newEnd })
        }
    }

    const onModalClose = () => {
        setShowTut(false)
    }

    return (
        <Container className='my-2'>
            <Row className='align-items-center'>
                <Col sm={9}>
                    <Form onSubmit={handleSubmit}>
                        <Row className='align-items-center'>
                            <Col className='col-4 align-self-start'>
                                <FormLabel>Start Date: </FormLabel>
                                <DatePicker
                                    id='start-datepicker'
                                    showClearButton={false}
                                    showTodayButton={true}
                                    dateFormat='MM/DD/YYYY'
                                    value={stringify(startCtl.start)}
                                    minDate={stringify(startCtl.min)}
                                    maxDate={stringify(startCtl.max)}
                                    onChange={(_, f) => handleStartChange(f)}
                                />
                                <FormText muted>
                                    Range: {rangeMin} - {rangeMax}
                                </FormText>
                            </Col>
                            <Col className='col-4 align-self-start'>
                                <FormLabel>End Date: </FormLabel>
                                <DatePicker
                                    id='end-datepicker'
                                    showClearButton={false}
                                    dateFormat='MM/DD/YYYY'
                                    value={stringify(endCtl.end)}
                                    minDate={stringify(endCtl.min)}
                                    maxDate={stringify(endCtl.max)}
                                    onChange={(_, f) => handleEndChange(f)}
                                />
                                <FormText muted>Maximum {getMaxNumDays()} day range</FormText>
                            </Col>

                            <Col className='col-4'>
                                <Row className='mx-1'>
                                    <Col className='d-flex align-items-center justify-content-center'>
                                        <OverlayTrigger
                                            trigger={['hover', 'hover']}
                                            overlay={
                                                <Tooltip id='id-refresh-button'>
                                                    Redraw the graph with the latest data using the
                                                    selected date range.
                                                </Tooltip>
                                            }>
                                            <Button
                                                variant='custom-primary'
                                                className='px-2 m-1'
                                                type='submit'
                                                name='refresh'>
                                                Refresh
                                            </Button>
                                        </OverlayTrigger>
                                        <OverlayTrigger
                                            trigger={['hover', 'hover']}
                                            overlay={
                                                <Tooltip id='id-reset-button'>
                                                    Return to the default date range and refresh the
                                                    graph.
                                                </Tooltip>
                                            }>
                                            <Button
                                                variant='custom-primary'
                                                className='px-2 m-1'
                                                type='submit'
                                                name='reset'>
                                                Reset
                                            </Button>
                                        </OverlayTrigger>
                                    </Col>
                                    <Col className='d-flex align-items-center justify-content-center'>
                                        <OverlayTrigger
                                            trigger={['hover', 'hover']}
                                            overlay={
                                                <Tooltip id='id-set-button'>
                                                    Open the Graph page tutorial in a popup window.
                                                </Tooltip>
                                            }>
                                            <Button
                                                variant='primary'
                                                className='px-2 my-1'
                                                onClick={() => setShowTut(true)}>
                                                Graph Tutorial
                                            </Button>
                                        </OverlayTrigger>
                                    </Col>
                                </Row>
                                <Row></Row>
                            </Col>
                        </Row>
                    </Form>
                </Col>
                <Col sm={3}>
                    <Row className='custom-elevation mx-0 py-3 align-items-center'>
                        <Col xs={7} className='text-center flex-grow-1'>
                            Custom Elevation:{' '}
                            {appContext.customElevationNav ? (
                                <strong>
                                    {navd88ToMllw(appContext.customElevationNav)}&nbsp;ft
                                </strong>
                            ) : (
                                '-'
                            )}
                        </Col>
                        <Col className='text-center'>
                            <OverlayTrigger
                                overlay={
                                    <Tooltip id='id-set-button'>
                                        Go to Map page to manage your custom elevation.
                                    </Tooltip>
                                }>
                                <Button
                                    variant='custom-primary'
                                    className='py-0'
                                    onClick={() => appContext.gotoPage(Page.Map)}>
                                    Edit
                                </Button>
                            </OverlayTrigger>
                        </Col>
                    </Row>
                </Col>
            </Row>
            {showTut && <Tutorial onClose={onModalClose} data={getData()} title='Graph Tutorial' />}
        </Container>
    )
}
