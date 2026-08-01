import './css/GetDates.css'
import 'react-datepicker/dist/react-datepicker.css'
import { useContext } from 'react'
import HousePic from './images/housepic2.png?inline'
import Button from 'react-bootstrap/Button'
import { Form, FormLabel, FormText } from 'react-bootstrap'
import { DatePicker } from 'react-datepicker'
import { addDays, differenceInDays } from 'date-fns'
import { isSmallScreen, stringify, getMaxNumDays, maxGraphDate } from './utils'
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
    const rangeMin = `${minDate.getFullYear()}`
    const rangeMax = `${maxDate.getFullYear()}`

    const handleHiloToggle = () => {
        toggleHiloMode()
    }

    const handleRefresh = () => {
        // This will force a re-render even if the dates are the same as before
        setDateRangeStrings(stringify(startCtl.start), stringify(endCtl.end), true)
    }

    const handleReset = () => {
        resetDateControls() // Let parent reset the date controls, and the appContext.
    }

    const handleStartChange = (dt) => {
        // When they change start date, we automatically change end date also, to match the previously
        // selected number of days shown, if possible.
        // Datepicker won't call this if date is invalid or outside min/max, but it calls it if
        // they empty it out or click Today when date is already today, so we will ignore those.
        if (dt && dt !== startCtl.start) {
            const daysShown = differenceInDays(endCtl.end, startCtl.start) + 1
            const newStart = new Date(dt)
            const newEnd = ctx.station.limitGraphDate(addDays(newStart, daysShown - 1))
            setStartCtl({ ...startCtl, start: newStart })
            setEndCtl({
                min: newStart,
                // Set the end date to honor the numDays from previous settings, limited by overall max.
                end: newEnd,
                max: ctx.station.limitGraphDate(addDays(newStart, getMaxNumDays() - 1)),
            })
        }
    }

    const handleEndChange = (dt) => {
        // When they change the end date, it has no effect on the start date. Since the date control
        // won't allow a date out of range, we can skip range checking here.
        // Note we must do nothing if the date did not change, as that would cause no re-rendering.
        if (dt && dt !== endCtl.end) {
            const newEnd = new Date(dt)
            setEndCtl({ ...endCtl, end: newEnd })
        }
    }

    return (
        <div id='get-dates'>
            <div className='get-dates-range'>
                <div>
                    <FormLabel>Start Date: </FormLabel>
                    <div>
                        <DatePicker
                            showIcon
                            toggleCalendarOnIconClick
                            id='start-datepicker'
                            selected={startCtl.start}
                            minDate={startCtl.min}
                            maxDate={startCtl.max}
                            onChange={handleStartChange}
                        />
                    </div>
                    <FormText muted>
                        Range: {rangeMin} - {rangeMax}
                    </FormText>
                </div>
                <div>
                    <FormLabel>End Date: </FormLabel>
                    {/* We set the time to noon on min/max dates to compensate for DatePicker bug. */}
                    <div>
                        <DatePicker
                            id='end-datepicker'
                            showIcon
                            toggleCalendarOnIconClick
                            allowSameDay
                            selected={endCtl.end}
                            minDate={endCtl.min}
                            maxDate={endCtl.max}
                            onChange={handleEndChange}
                        />
                    </div>
                    <FormText muted>Maximum {getMaxNumDays()} day range</FormText>
                </div>
            </div>

            <div className='get-dates-ctl'>
                <div className='get-dates-buttons'>
                    <Overlay
                        text='Redraw the graph with the latest data using the selected date range.'
                        placement='top'
                        contents={
                            <Button variant='custom-primary' onClick={handleRefresh}>
                                Refresh
                            </Button>
                        }></Overlay>
                    <Overlay
                        text='Return to the default date range and refresh the graph.'
                        placement='top'
                        contents={
                            <Button variant='custom-primary' onClick={handleReset}>
                                Reset
                            </Button>
                        }></Overlay>
                </div>
                <div className='hilo-box'>
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
                </div>
            </div>
            <Overlay
                text='Add the elevation of your place of interest to the graph.'
                placement='top'
                contents={
                    <div className='get-dates-custom pointer'>
                        <img
                            src={HousePic}
                            width={50}
                            alt='Map popup'
                            onClick={() => onMapRequest()}
                        />
                        <div className='map-label' onClick={() => onMapRequest()}>
                            Find my house!
                        </div>
                    </div>
                }></Overlay>
        </div>
    )
}
