import './css/GetDates.css'
import { useContext } from 'react'
// import HousePic from './images/housepic1.png'
import HousePic from './images/housepic2.png'
import Button from 'react-bootstrap/Button'
import { Col, Form, FormLabel, FormText, Row } from 'react-bootstrap'
import { DatePicker } from 'reactstrap-date-picker'
import Container from 'react-bootstrap/Container'
import {
    addDays,
    daysBetween,
    isSmallScreen,
    limitDate,
    stringify,
    getMaxNumDays,
    maxGraphDate,
    Months,
} from './utils'
import Overlay from './Overlay'
import { AppContext } from './AppContext'

// Allow users to set start/end date range for the graph.

export default function GetDates({
    startCtl,
    setStartCtl,
    endCtl,
    setEndCtl,
    setDateRangeStrings,
    isHiloMode,
    toggleHiloMode,
    resetDateControls,
    onMapRequest,
}) {
    const ctx = useContext(AppContext)
    const minDate = ctx.station.minGraphDate()
    const maxDate = maxGraphDate()
    const rangeMin = `${Months[minDate.getMonth()]} ${minDate.getFullYear()}`
    const rangeMax = `${Months[maxDate.getMonth()]} ${maxDate.getFullYear()}`

    const handleHiloToggle = () => {
        toggleHiloMode()
    }

    const handleSubmit = (e) => {
        // The form has 2 submit buttons -- refresh & reset, so handle them both here.
        e.preventDefault()
        const clickedButton = e.nativeEvent.submitter

        if (clickedButton.name === 'refresh') {
            // This will force a re-render even if the dates are the same as before
            setDateRangeStrings(stringify(startCtl.start), stringify(endCtl.end), true)
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
            const daysShown = daysBetween(startCtl.start, endCtl.end) + 1
            const newStart = new Date(formatted)
            const newEnd = limitDate(addDays(newStart, daysShown - 1), ctx.station)
            setStartCtl({ ...startCtl, start: newStart })
            setEndCtl({
                min: newStart,
                // Set the end date to honor the numDays from previous settings, limited by overall max.
                end: newEnd,
                max: limitDate(addDays(newStart, getMaxNumDays() - 1), ctx.station),
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

    return (
        <Container className='my-2'>
            <Row className='align-items-center'>
                <Col className='px-0'>
                    <Row className='align-items-center mx-0 date-options'>
                        <Col className='align-self-start'>
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
                        <Col className='align-self-start'>
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

                        <Col>
                            <Row className='mx-0'>
                                <Form onSubmit={handleSubmit}>
                                    <Col className='d-flex align-items-center justify-content-center'>
                                        <Overlay
                                            text='Redraw the graph with the latest data using the selected date range.'
                                            placement='top'
                                            contents={
                                                <Button
                                                    variant='custom-primary'
                                                    className='m-1'
                                                    type='submit'
                                                    name='refresh'>
                                                    Refresh
                                                </Button>
                                            }></Overlay>
                                        <Overlay
                                            text='Return to the default date range and refresh the graph.'
                                            placement='top'
                                            contents={
                                                <Button
                                                    variant='custom-primary'
                                                    className='m-1'
                                                    type='submit'
                                                    name='reset'>
                                                    Reset
                                                </Button>
                                            }></Overlay>
                                    </Col>
                                </Form>
                            </Row>
                            <Row className='mx-0'>
                                <Col className='d-flex align-items-center justify-content-center'>
                                    <Overlay
                                        text='Turn on to show only high and low tides.'
                                        placement='top'
                                        contents={
                                            <Form>
                                                <Form.Check
                                                    type='switch'
                                                    label='Highs/Lows'
                                                    checked={isHiloMode}
                                                    onChange={handleHiloToggle}
                                                    disabled={isSmallScreen()}
                                                />
                                            </Form>
                                        }></Overlay>
                                </Col>
                            </Row>
                        </Col>
                    </Row>
                </Col>
                <Col sm={3} className='mx-0 py-2 text-center'>
                    <Overlay
                        text='Add the elevation of your place of interest to the graph.'
                        placement='top'
                        contents={
                            <div className='mx-md-2 pointer' onClick={() => onMapRequest()}>
                                <img src={HousePic} width={75} alt='Map popup' />
                                <div className='map-label'>Graph my house!</div>
                            </div>
                        }></Overlay>
                </Col>
            </Row>
        </Container>
    )
}
