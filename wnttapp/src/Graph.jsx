import './css/Graph.css'
import { useEffect, useReducer, useState } from 'react'
import { Col, Row } from 'react-bootstrap'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import GetDates from './GetDates'
import Chart from './Chart'
import useGraphData from './useGraphData'
import {
    addDays,
    buildCacheKey,
    getDefaultDateStrings,
    stringify,
    dateDiff,
    limitDate,
    getMaxNumDays,
    minGraphDate,
    maxGraphDate,
    SmallBase,
    widthLessThan,
} from './utils'
import { getDailyLocalStorage, setDailyLocalStorage } from './localStorage'
import prevButton from './images/util/previous.png'
import nextButton from './images/util/next.png'
import { useQueryClient } from '@tanstack/react-query'

export default function Graph() {
    /* 
    Start & end dates are strings in format mm/dd/yyyy with 0-padding.  See utils.stringify.
    Javascript new Date() returns a date/time in the local time zone, so users should get the 
    right date whatever timezone they're in. 
    */
    const { defaultStartStr, defaultEndStr } = getDefaultDateStrings()
    const datesStorage = getDailyLocalStorage('dates')
    const [startDateStr, setStartDateStr] = useState(datesStorage.start ?? defaultStartStr)
    const [endDateStr, setEndDateStr] = useState(datesStorage.end ?? defaultEndStr)
    // The user can refresh the graph using the same date range. but it seems React has no native support
    // for forcing a re-render without state change, so I'm doing this hack. Calling a reducer triggers re-render.
    // eslint-disable-next-line no-unused-vars
    const [dummy, forceGraphUpdate] = useReducer((x) => x + 1, 0)

    const [startCtl, setStartCtl] = useState({
        min: minGraphDate(),
        start: new Date(startDateStr),
        max: maxGraphDate(),
    })

    const [endCtl, setEndCtl] = useState({
        min: new Date(startDateStr),
        end: new Date(endDateStr),
        max: addDays(new Date(startDateStr), getMaxNumDays() - 1),
    })

    const setDateStorage = (start, end) => {
        setDailyLocalStorage('dates', {
            start: start,
            end: end,
        })
    }

    useEffect(() => {
        setDateStorage(startDateStr, endDateStr)
    }, [startDateStr, endDateStr])

    const queryClient = useQueryClient()
    const daysShown = dateDiff(startDateStr, endDateStr) + 1

    const setDateRangeStrings = (startDateStr, endDateStr) => {
        setStartDateStr(startDateStr)
        setEndDateStr(endDateStr)
        // If this query's already in cache, remove it first, else it won't refetch even if stale.
        const key = buildCacheKey(startDateStr, endDateStr)
        queryClient.removeQueries({ queryKey: key, exact: true })
        forceGraphUpdate() // If the dates have changed, this isn't necessary, but it's harmless.
    }

    const setJumpDates = (directionFactor) => {
        const daysToShow = Math.min(daysShown, getMaxNumDays())
        const newStart = limitDate(addDays(startDateStr, daysToShow * directionFactor))
        const newEnd = limitDate(addDays(newStart, daysToShow - 1))
        setStartCtl({ ...startCtl, start: newStart })
        setEndCtl({
            min: newStart,
            end: newEnd,
            max: limitDate(addDays(newStart, getMaxNumDays() - 1)),
        })
        setDateRangeStrings(stringify(newStart), stringify(newEnd))
    }

    // Reset the date controls to use the default range, as if entering app for the first time with no storage values.
    const resetDateControls = () => {
        const { defaultStartStr, defaultEndStr } = getDefaultDateStrings()
        setStartCtl({
            min: minGraphDate(),
            start: new Date(defaultStartStr),
            max: maxGraphDate(),
        })
        setEndCtl({
            min: new Date(defaultStartStr),
            end: new Date(defaultEndStr),
            max: addDays(new Date(defaultStartStr), getMaxNumDays() - 1),
        })
        setDateRangeStrings(defaultStartStr, defaultEndStr)
    }

    const handlePreviousClick = (e) => {
        e.preventDefault()
        setJumpDates(-1)
    }

    const handleNextClick = (e) => {
        e.preventDefault()
        setJumpDates(1)
    }

    // There is one scenario when we don't want to use the dates in React's state: when the user has
    // left the browser tab open with the graph showing from 1 or more days prior. In this case, we
    // want to ignore state and reset to the default date range. We detect this by checking dateStorage,
    // which is only empty on the very first run, after local storage has been cleared, or when the
    // current date does not match the local storage date. (See utils.getDailyLocalStorage.)
    if (
        datesStorage.start == undefined &&
        (startDateStr, endDateStr) != (defaultStartStr, defaultEndStr)
    ) {
        console.log(
            `DatesStorage is empty, resetting range from (${startDateStr}-${endDateStr}) to default.`
        )
        resetDateControls()
    }

    // If CSS Pixels width is less than Bootstrap's "small" breakpoint, show only highs and lows.
    const hiloMode = widthLessThan(SmallBase)
    const { isPending: loading, data, error } = useGraphData(startDateStr, endDateStr, hiloMode)

    const JumpDates = (props) => {
        if (error || loading) {
            return <Col />
        }
        return (
            <OverlayTrigger overlay={<Tooltip id={props.id}>{props.hoverText}</Tooltip>}>
                <Col xs={1} className='text-center'>
                    <a href='#' onClick={props.action}>
                        <img className='pic' src={props.image} alt={props.hoverText} />
                    </a>
                </Col>
            </OverlayTrigger>
        )
    }

    const numDaysText = daysShown > 1 ? `${daysShown} days` : 'day'

    return (
        <>
            <GetDates
                startCtl={startCtl}
                setStartCtl={setStartCtl}
                endCtl={endCtl}
                setEndCtl={setEndCtl}
                setDateRangeStrings={setDateRangeStrings}
                resetDateControls={resetDateControls}
            />
            {/*
            Note we are not using Container because it sets left & right margin to auto, and this
            doesn't allow enough horizontal space to be used when in between 2 breakpoints.
            For the Row, we must undo the negative margin it carries as compensation for the Container's.
            Otherwise it pushes the Row right and causes a horizontal scrollbar.
            */}
            <Row className='justify-content-center align-items-center me-0'>
                <JumpDates
                    id='id-prev'
                    hoverText={`Previous ${numDaysText}`}
                    action={handlePreviousClick}
                    image={prevButton}
                />
                <Col xs={10} className='px-0'>
                    <Chart loading={loading} error={error} hiloMode={hiloMode} data={data} />
                </Col>
                <JumpDates
                    id='id-next'
                    hoverText={`Next ${numDaysText}`}
                    action={handleNextClick}
                    image={nextButton}
                />
            </Row>
        </>
    )
}
