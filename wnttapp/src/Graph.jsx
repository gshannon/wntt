import './css/Graph.css'
import { useContext, useEffect, useEffectEvent, useReducer, useState } from 'react'
import { Col, Row } from 'react-bootstrap'
import { AppContext } from './AppContext'
import GetDates from './GetDates'
import Chart from './Chart'
import Overlay from './Overlay'
import useGraphData from './useGraphData'
import {
    addDays,
    buildCacheKey,
    getDefaultDateStrings,
    getScreenBase,
    stringify,
    daysBetween,
    isSmallScreen,
    limitDate,
    getMaxNumDays,
    maxGraphDate,
} from './utils'
import * as storage from './storage'
import prevButton from './images/util/previous.png'
import nextButton from './images/util/next.png'
import { useQueryClient } from '@tanstack/react-query'

export default function Graph() {
    const ctx = useContext(AppContext)

    // TODO: Not handling race condition where ctx has no station.  Cannot put
    // a short circuit here because of React errors.

    /* 
    Start & end dates are strings in format mm/dd/yyyy with 0-padding.  See utils.stringify.
    Javascript new Date() returns a date/time in the local time zone, so users should get the 
    right date whatever timezone they're in. 
    */
    const { defaultStartStr, defaultEndStr } = getDefaultDateStrings()

    /////////////////
    // start date, end date, hilo mode, screen size
    const stationDaily = storage.getStationDailyStorage(ctx.station?.id || null)

    // these strings drive what's in the screen start/end date text box controls.
    const [startDateStr, setStartDateStr] = useState(stationDaily.start ?? defaultStartStr)
    const [endDateStr, setEndDateStr] = useState(stationDaily.end ?? defaultEndStr)
    const [isHiloMode, setIsHiloMode] = useState(stationDaily.hiloMode ?? isSmallScreen())
    // The user can refresh the graph using the same date range. but it seems React has no native support
    // for forcing a re-render without state change, so I'm doing this hack. Calling a reducer triggers re-render.
    const [, forceUpdate] = useReducer((x) => x + 1, 0)

    const [startCtl, setStartCtl] = useState({
        min: ctx.station.minGraphDate(),
        start: new Date(startDateStr),
        max: maxGraphDate(),
    })

    const [endCtl, setEndCtl] = useState({
        min: new Date(startDateStr),
        end: new Date(endDateStr),
        max: addDays(new Date(startDateStr), getMaxNumDays() - 1),
    })

    const onDateChange = useEffectEvent((start, end, hiloMode) => {
        storage.setStationDailyStorage(ctx.station.id, {
            start: start,
            end: end,
            hiloMode: hiloMode,
            screenBase: getScreenBase(),
        })
    })

    useEffect(() => {
        onDateChange(startDateStr, endDateStr, isHiloMode)
    }, [startDateStr, endDateStr, isHiloMode])

    const queryClient = useQueryClient()
    const daysShown = daysBetween(startDateStr, endDateStr) + 1

    const setDateRangeStrings = (newStartDateStr, newEndDateStr) => {
        setStartDateStr(newStartDateStr)

        setEndDateStr(newEndDateStr)
        // If this query's already in cache, remove it first, else it won't refetch even if stale.
        const key = buildCacheKey(ctx.station.id, newStartDateStr, newEndDateStr, isHiloMode)
        queryClient.removeQueries({ queryKey: key, exact: true })
        forceUpdate() // If the dates have changed, this isn't necessary, but it's harmless.
    }

    const toggleHiloMode = () => {
        setIsHiloMode(!isHiloMode)
    }

    const setJumpDates = (directionFactor) => {
        const daysToShow = Math.min(daysShown, getMaxNumDays())
        const newStart =
            directionFactor > 0
                ? limitDate(addDays(endDateStr, 1), ctx.station)
                : limitDate(addDays(startDateStr, daysToShow * directionFactor), ctx.station)
        const newEnd = limitDate(addDays(newStart, daysToShow - 1), ctx.station)
        setStartCtl({ ...startCtl, start: newStart })
        setEndCtl({
            min: newStart,
            end: newEnd,
            max: limitDate(addDays(newStart, getMaxNumDays() - 1), ctx.station),
        })
        setDateRangeStrings(stringify(newStart), stringify(newEnd))
    }

    // Reset the date controls to use the default range, as if entering app for the first time with no storage values.
    const resetDateControls = () => {
        const { defaultStartStr, defaultEndStr } = getDefaultDateStrings()
        setStartCtl({
            min: ctx.station.minGraphDate(),
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
        stationDaily.start == undefined &&
        (startDateStr, endDateStr) != (defaultStartStr, defaultEndStr)
    ) {
        console.log(
            `stationDaily is empty, resetting range from (${startDateStr}-${endDateStr}) to default.`
        )
        resetDateControls()
    }

    // The user changing their screen width doesn't trigger a rerender, only a DOM redraw, which doesn't
    // execute our code. So if we detect that here, we need to set some state that normally is set
    // only on initial render, or when user does something to trigger it.
    if (stationDaily.screenBase != getScreenBase()) {
        if (isSmallScreen() && !isHiloMode) {
            // This is normally forced only on initial render.
            setIsHiloMode(true)
        }
        // We probably need to adjust the date range. We'll adjust the max, and also the selected
        // end date if it is now too late.
        const newMax = limitDate(addDays(startDateStr, getMaxNumDays() - 1), ctx.station)
        const newEnd = new Date(Math.min(newMax, endCtl.end))
        if (newEnd != endCtl.end) {
            // If we're shortening the selected range, update state and trigger refetch.
            setEndCtl({
                min: new Date(startDateStr),
                end: newEnd,
                max: newMax,
            })
            setEndDateStr(stringify(newEnd))
        }
        // This avoids an endless loop on rerender.
        storage.setStationDailyStorage(ctx.station.id, {
            ...stationDaily,
            screenBase: getScreenBase(),
        })
    }

    const {
        isPending: loading,
        data,
        error,
    } = useGraphData(ctx.station, startDateStr, endDateStr, isHiloMode)

    const numDaysText = daysShown > 1 ? `${daysShown} days` : 'day'

    return (
        <>
            <GetDates
                startCtl={startCtl}
                setStartCtl={setStartCtl}
                endCtl={endCtl}
                setEndCtl={setEndCtl}
                setDateRangeStrings={setDateRangeStrings}
                isHiloMode={isHiloMode}
                toggleHiloMode={toggleHiloMode}
                resetDateControls={resetDateControls}
            />
            {/*
            Note we are not using Container because it sets left & right margin to auto, and this
            doesn't allow enough horizontal space to be used when in between 2 breakpoints. That means setting row's x margins 
            to 0, to override the default of -12.
            */}
            <Row className='justify-content-center align-items-center mx-0'>
                <JumpDates
                    hoverText={`Previous ${numDaysText}`}
                    action={handlePreviousClick}
                    image={prevButton}
                    dir='back'
                    start={startCtl.start}
                    end={endCtl.end}
                    station={ctx.station}
                    errorOrLoading={error || loading}
                />
                <Col className='col-10 px-0'>
                    <Chart loading={loading} error={error} hiloMode={isHiloMode} data={data} />
                </Col>
                <JumpDates
                    hoverText={`Next ${numDaysText}`}
                    action={handleNextClick}
                    image={nextButton}
                    dir='forward'
                    start={startCtl.start}
                    end={endCtl.end}
                    station={ctx.station}
                    errorOrLoading={error || loading}
                />
            </Row>
        </>
    )
}

const JumpDates = (props) => {
    if (props.errorOrLoading) {
        return <Col className='col-1' />
    }
    // Disable these if out of range
    const anchorClass =
        (props.dir === 'back' && props.start <= props.station.minGraphDate()) ||
        (props.dir === 'forward' && props.end >= maxGraphDate())
            ? 'disable-pointer'
            : 'pointer'
    return (
        <Col className='col-1 px-0 jumpdate'>
            <Overlay
                text={props.hoverText}
                placement='top'
                contents={
                    <a onClick={props.action} className={anchorClass}>
                        <img className='pic' src={props.image} alt={props.hoverText} />
                    </a>
                }></Overlay>
        </Col>
    )
}
