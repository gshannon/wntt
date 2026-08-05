import './css/Graph.css'
import { useContext, useEffect, useEffectEvent, useReducer, useState } from 'react'
import { Col, Row } from 'react-bootstrap'
import { AppContext } from './AppContext'
import GetDates from './GetDates'
import Chart from './EChart'
import Overlay from './Overlay'
import useGraphData from './useGraphData'
import { addDays, differenceInDays } from 'date-fns'
import {
    buildCacheKey,
    MediumBase,
    getScreenBase,
    stringify,
    isSmallScreen,
    getMaxNumDays,
    maxGraphDate,
} from './utils'
import * as storage from './storage'
import prevButton from './images/util/previous.png?inline'
import nextButton from './images/util/next.png?inline'
import { useQueryClient } from '@tanstack/react-query'
import Map from './Map'

export default function Graph() {
    const ctx = useContext(AppContext)

    // TODO: Not handling race condition where ctx has no station.  Cannot put
    // a short circuit here because of React errors.
    const [defaultStartDate, defaultEndDate] = getDefaultRange()

    /////////////////
    // start date, end date, hilo mode, screen size
    const stationDaily = storage.getDailyStorage(ctx.station?.id || null)

    // these strings drive what's in the screen start/end date text box controls.
    const [startDate, setStartDate] = useState(new Date(stationDaily.start ?? defaultStartDate))
    const [endDate, setEndDate] = useState(new Date(stationDaily.end ?? defaultEndDate))
    const [isHiloMode, setIsHiloMode] = useState(stationDaily.hiloMode ?? isSmallScreen())
    const [showMap, setShowMap] = useState(false)
    // The user can refresh the graph using the same date range. but it seems React has no native support
    // for forcing a re-render without state change, so I'm doing this hack. Calling a reducer triggers re-render.
    const [, forceRerender] = useReducer((x) => x + 1, 0)

    const [startCtl, setStartCtl] = useState({
        min: ctx.station.minGraphDate(),
        start: startDate,
        max: maxGraphDate(),
    })

    const [endCtl, setEndCtl] = useState({
        min: startDate,
        end: endDate,
        max: addDays(startDate, getMaxNumDays() - 1),
    })

    const onDateChange = useEffectEvent((start, end, hiloMode) => {
        storage.setDailyStorage(ctx.station.id, {
            ...stationDaily,
            start: stringify(start),
            end: stringify(end),
            hiloMode: hiloMode,
            screenBase: getScreenBase(),
        })
    })

    useEffect(() => {
        onDateChange(startDate, endDate, isHiloMode)
    }, [startDate, endDate, isHiloMode])

    const queryClient = useQueryClient()
    const daysShown = differenceInDays(endDate, startDate) + 1

    const setDateRange = (newStartDate, newEndDate, forceRefresh) => {
        setStartDate(newStartDate)

        setEndDate(newEndDate)
        // If this query's already in cache, remove it first, else it won't refetch even if stale.
        if (forceRefresh) {
            const key = buildCacheKey(
                ctx.station.id,
                stringify(newStartDate),
                stringify(newEndDate),
                isHiloMode,
            )
            queryClient.removeQueries({ queryKey: key, exact: true })
        }
        forceRerender() // If the dates have changed, this isn't necessary, but it's harmless.
    }

    const toggleHiloMode = () => {
        setIsHiloMode(!isHiloMode)
    }

    const onMapClose = () => {
        setShowMap(false)
    }

    const onMapRequest = () => {
        setShowMap(true)
    }

    const setJumpDates = (directionFactor) => {
        const daysToShow = Math.min(daysShown, getMaxNumDays())
        const newStart =
            directionFactor > 0 ?
                ctx.station.limitGraphDate(addDays(endDate, 1))
            :   ctx.station.limitGraphDate(addDays(startDate, daysToShow * directionFactor))
        const newEnd = ctx.station.limitGraphDate(addDays(newStart, daysToShow - 1))
        setStartCtl({ ...startCtl, start: newStart })
        setEndCtl({
            min: newStart,
            end: newEnd,
            max: ctx.station.limitGraphDate(addDays(newStart, getMaxNumDays() - 1)),
        })
        setDateRange(newStart, newEnd, false)
    }

    // Reset the date controls to use the default range, as if entering app for the first time with no storage values.
    const resetDateControls = () => {
        const [defaultStartDate, defaultEndDate] = getDefaultRange()
        setStartCtl({
            min: ctx.station.minGraphDate(),
            start: defaultStartDate,
            max: maxGraphDate(),
        })
        setEndCtl({
            min: defaultStartDate,
            end: defaultEndDate,
            max: addDays(defaultStartDate, getMaxNumDays() - 1),
        })
        setDateRange(defaultStartDate, defaultEndDate, false)
        // Also reset the plot visibility states. Remove the legendOnly object, force a re-init.
        const daily = storage.getDailyStorage(ctx.station.id)
        delete daily.legendOnly
        storage.setDailyStorage(ctx.station.id, daily)
    }

    const handlePreviousClick = (e) => {
        e.preventDefault()
        setJumpDates(-1)
    }

    const handleNextClick = (e) => {
        e.preventDefault()
        setJumpDates(1)
    }

    const {
        isPending: loading,
        data,
        error,
    } = useGraphData(ctx.station, startDate, endDate, isHiloMode, ctx.special)

    const numDaysText = daysShown > 1 ? `${daysShown} days` : 'day'

    return (
        <>
            <GetDates
                startCtl={startCtl}
                setStartCtl={setStartCtl}
                endCtl={endCtl}
                setEndCtl={setEndCtl}
                setDateRange={setDateRange}
                isHiloMode={isHiloMode}
                onMapRequest={onMapRequest}
                onMapClose={onMapClose}
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
            {showMap && <Map key={ctx.station?.id} onMapClose={onMapClose} />}
        </>
    )
}

const JumpDates = (props) => {
    if (props.errorOrLoading) {
        return <Col className='col-1' />
    }
    // Disable these if out of range
    const anchorClass =
        (
            (props.dir === 'back' && props.start <= props.station.minGraphDate()) ||
            (props.dir === 'forward' && props.end >= maxGraphDate())
        ) ?
            'disable-pointer'
        :   'pointer'
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

const getDefaultRange = () => {
    const today = new Date()
    const defaultDays = window.innerWidth >= MediumBase ? 4 : 1
    return [today, addDays(today, defaultDays - 1)]
}
