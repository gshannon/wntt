import './css/Graph.css'
import { type MouseEvent, useContext, useEffect, useEffectEvent, useReducer, useState } from 'react'
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
import type Station from './Station'

export default function Graph() {
    const ctx = useContext(AppContext)
    // Graph/Map/EChart/GetDates/Conditions only mount once a station is set (see Control.tsx / Home guards).
    const station = ctx.station!

    // TODO: Not handling race condition where ctx has no station.  Cannot put
    // a short circuit here because of React errors.
    const [defaultStartDate, defaultEndDate] = getDefaultRange()

    /////////////////
    // start date, end date, hilo mode, screen size
    const stationDaily = storage.getDailyStorage(station?.id || null)

    // these strings drive what's in the screen start/end date text box controls.
    const [startDate, setStartDate] = useState(new Date(stationDaily.start ?? defaultStartDate))
    const [endDate, setEndDate] = useState(new Date(stationDaily.end ?? defaultEndDate))
    const [isHiloMode, setIsHiloMode] = useState(stationDaily.hiloMode ?? isSmallScreen())
    const [showMap, setShowMap] = useState(false)
    // The user can refresh the graph using the same date range. but it seems React has no native support
    // for forcing a re-render without state change, so I'm doing this hack. Calling a reducer triggers re-render.
    const [, forceRerender] = useReducer((x) => x + 1, 0)

    const [startCtl, setStartCtl] = useState({
        min: station.minGraphDate(),
        start: startDate,
        max: maxGraphDate(),
    })

    const [endCtl, setEndCtl] = useState({
        min: startDate,
        end: endDate,
        max: addDays(startDate, getMaxNumDays() - 1),
    })

    const onDateChange = useEffectEvent((start: Date, end: Date, hiloMode: boolean) => {
        storage.setDailyStorage(station.id, {
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

    const setDateRange = (newStartDate: Date, newEndDate: Date, forceRefresh: boolean) => {
        setStartDate(newStartDate)

        setEndDate(newEndDate)
        // If this query's already in cache, remove it first, else it won't refetch even if stale.
        if (forceRefresh) {
            const key = buildCacheKey(
                station.id,
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

    const setJumpDates = (directionFactor: number) => {
        const daysToShow = Math.min(daysShown, getMaxNumDays())
        const newStart =
            directionFactor > 0 ?
                station.limitGraphDate(addDays(endDate, 1))
            :   station.limitGraphDate(addDays(startDate, daysToShow * directionFactor))
        const newEnd = station.limitGraphDate(addDays(newStart, daysToShow - 1))
        setStartCtl({ ...startCtl, start: newStart })
        setEndCtl({
            min: newStart,
            end: newEnd,
            max: station.limitGraphDate(addDays(newStart, getMaxNumDays() - 1)),
        })
        setDateRange(newStart, newEnd, false)
    }

    // Reset the date controls to use the default range, as if entering app for the first time with no storage values.
    const resetDateControls = () => {
        const [defaultStartDate, defaultEndDate] = getDefaultRange()
        setStartCtl({
            min: station.minGraphDate(),
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
        const daily = storage.getDailyStorage(station.id)
        delete daily.legendOnly
        storage.setDailyStorage(station.id, daily)
    }

    const handlePreviousClick = (e: MouseEvent) => {
        e.preventDefault()
        setJumpDates(-1)
    }

    const handleNextClick = (e: MouseEvent) => {
        e.preventDefault()
        setJumpDates(1)
    }

    const {
        isPending: loading,
        data,
        error,
    } = useGraphData(station, startDate, endDate, isHiloMode, ctx.special)

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
                    station={station}
                    errorOrLoading={error || loading}
                />
                <Col className='col-10 px-0'>
                    {ctx.banner && <MessageBox message={ctx.banner} />}
                    <Chart loading={loading} error={error} hiloMode={isHiloMode} data={data} />
                </Col>
                <JumpDates
                    hoverText={`Next ${numDaysText}`}
                    action={handleNextClick}
                    image={nextButton}
                    dir='forward'
                    start={startCtl.start}
                    end={endCtl.end}
                    station={station}
                    errorOrLoading={error || loading}
                />
            </Row>
            {showMap && <Map key={station?.id} onMapClose={onMapClose} />}
        </>
    )
}

const MessageBox = ({ message }: { message: string }) => {
    return (
        <Row>
            <Col className='d-flex justify-content-center text-warning bg-dark py-1 mx-4 my-2'>
                {message}
            </Col>
        </Row>
    )
}

interface JumpDatesProps {
    errorOrLoading: boolean | Error | null
    dir: 'back' | 'forward'
    start: Date
    end: Date
    station: Station
    hoverText: string
    action: (e: MouseEvent) => void
    image: string
}

const JumpDates = (props: JumpDatesProps) => {
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
