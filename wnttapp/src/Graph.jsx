import './css/Graph.css'
import { useContext, useEffect, useReducer, useState } from 'react'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import { Col, Row } from 'react-bootstrap'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import GetDates from './GetDates'
import Plot from 'react-plotly.js'
import useGraphData from './useGraphData'
import {
    addDays,
    buildCacheKey,
    getDefaultDateStrings,
    MediumBase,
    stringify,
    dateDiff,
    widthGreaterOrEqual,
    limitDate,
    getMaxNumDays,
    maxCustomElevationNavd88,
    minGraphDate,
    maxGraphDate,
    navd88ToMllw,
} from './utils'
import { getDailyLocalStorage, setDailyLocalStorage } from './localStorage'
import { AppContext } from './AppContext'
import prevButton from './images/util/previous.png'
import nextButton from './images/util/next.png'
import { useQueryClient } from '@tanstack/react-query'

const PlotBgColor = '#f3f2f2'
const CustomElevationColor = '#17becf'
const RecordTideColor = '#d62728'
const HighestAnnualPredictionColor = '#ff7f0e'
const MeanHighWaterColor = '#8c564b'
const ProjectedStormTideColor = '#e377c2'
const ObservedTideColor = '#2ca02c'
const PredictedTideColor = '#0b7dcc'
const RecordedStormSurgeColor = '#bcbd22'
const ProjectedStormSurgeColor = '#9467bd'
const WindGustColor = '#0b7dcc'
const WindSpeedColor = '#17becf'

export default function Graph() {
    const appContext = useContext(AppContext)
    const customElevationNav = appContext.customElevationNav
    const showElevation = customElevationNav && customElevationNav <= maxCustomElevationNavd88()
    const customElevationMllw = showElevation ? navd88ToMllw(customElevationNav) : null
    // If display isn't wide enough, we won't show the legend or the mode bar, and disallow zoom/pan.
    const isWideEnough = widthGreaterOrEqual(MediumBase)
    // Never allow touchscreen zoom/pan, because it causes problems with the hover text.
    const isTouchScreen =
        'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0
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

    // For constants which do not appear on hover text, we only need the first and last value,
    // but must have a value for every timeline point, so we put nulls in between.
    const expandConstant = (value, count) => {
        return [value].concat(Array(count - 2).fill(null)).concat(value)
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
            `DatesStorage is empty, resetting range from ${startDateStr}=${endDateStr} to default.`
        )
        resetDateControls()
    }

    const { isPending: loading, data, error } = useGraphData(startDateStr, endDateStr)

    const MyPlot = () => {
        if (error) {
            console.error(error)
            return (
                <div>
                    <br />
                    <br />
                    <br />
                    Sorry, we are unable to generate the graph just now. There may have been a
                    problem fetching data.
                    <br /> {error.message}
                    <br />
                    <Button variant='warning' onClick={() => window.location.reload()}>
                        Try again
                    </Button>
                    <br />
                    <br />
                    <br />
                </div>
            )
        } else if (loading) {
            return (
                <div style={{ textAlign: 'center' }}>
                    <br />
                    <br />
                    <br />
                    <Spinner animation='border' variant='primary' />
                    <br />
                    <br />
                    <br />
                </div>
            )
        }

        const includingWindData = data.wind_speeds !== null
        const graph1_max = 1
        const graph1_min = includingWindData ? 0.52 : 0.1
        const graph2_max = 0.48
        const graph2_min = 0

        const layout = {
            showlegend: isWideEnough,
            height: 420,
            template: 'plotly',
            plot_bgcolor: PlotBgColor,
            title: {
                text:
                    'Wells Harbor Tides' +
                    (data.wind_speeds !== null ? ' & Wind Data' : '') +
                    '<br>',
                font: { size: 18 },
                subtitle: {
                    text: data.start_date + ' - ' + data.end_date,
                    font: { size: 15 },
                },
            },
            hovermode: 'x unified',
            // hoverlabel must be extra wide due to issue created by hoverdistance (see below)
            hoverlabel: { namelength: 22 },
            /* hoverdistance controls how many pixels to the left or right of the cursor it will look for data when
            trying to show hover text for a plot that has a None for the time the cursor is over. While this is
            an essential feature, since otherwise you'd have to hover exactly over a data point to see the
            hover text, it has a serious drawback: with "x unified" hovermode, it will perform this logic on each plot 
            independently. This means that if the closest non-null data for some plots are to the left, and others are
            to the right, it will identify the x axis (time) based on on (probably the first it finds), and then 
            show data from a different time for other plots, with the actual datetime in parens. This makes the display
            much wider.  What I want is for it to skip those plots that have no data for the time displayed on the hover, 
            but that seems to be impossible. */
            hoverdistance: 1,
            hoversubplots: 'axis', // to include wind hovers in upper graph
            legend: {
                groupclick: 'toggleitem',
                title: {
                    text: '<b>Click lines below to toggle visibility.<br>See Help for details.</b>',
                },
            },
            margin: { t: 60, b: 50, l: 65 }, // overriding defaults t: 100, b/l/r: 80
            // Override default date format to more readable, with 12-hour clock.
            xaxis: { gridcolor: 'black', hoverformat: '%b %d, %Y %I:%M %p' },
            xaxis2: { gridcolor: 'black' },
            yaxis: {
                title: {
                    text: 'Tide feet (MLLW)',
                    font: { color: 'black', size: 15 },
                },
                domain: [graph1_min, graph1_max],
                gridcolor: 'black',
            },
            yaxis2: {
                title: { text: 'Wind MPH', font: { size: 15 } },
                domain: [graph2_min, graph2_max],
                gridcolor: 'black',
            },
            grid: {
                rows: 2,
                columns: 1,
                subplots: [['xy'], ['xy2']],
                roworder: 'top to bottom',
            },
            dragmode: isWideEnough && !isTouchScreen ? 'zoom' : false,
        }

        // Build hover format for future astro tides, to include High/Low labels.
        const astro_hover = data.timeline.map((dt) => {
            const i = data.astro_hilo_dts.indexOf(dt)
            if (i < 0) {
                return '%{y}'
            } else {
                const val = data.astro_hilo_vals[i]
                if (val == 'H') {
                    return '%{y} (HIGH)'
                } else {
                    return '%{y} (LOW)'
                }
            }
        })

        // Build hover format for recorded tides, to include High/Low labels.
        const hist_hover = data.timeline.map((dt) => {
            const i = data.hist_hilo_dts.indexOf(dt)
            if (i < 0) {
                return '%{y}'
            } else {
                const val = data.hist_hilo_vals[i]
                if (val == 'H') {
                    return '%{y} (HIGH)'
                } else {
                    return '%{y} (LOW)'
                }
            }
        })

        // TODO: Order 1st 2 items by level desc
        const plotData = [
            ...(showElevation
                ? [
                      {
                          x: data.timeline,
                          // We need this one filled across cuz it appears on the hover text.
                          y: Array(data.timeline.length).fill(customElevationMllw),
                          legendgroup: 'grp1',
                          type: 'scatter',
                          name: `Custom Elevation (${customElevationMllw})`,
                          text: `Custom Elevation: ${customElevationMllw}`,
                          hoverinfo: 'text', // tells it to use 'text' in hover
                          mode: 'Lines',
                          line: { color: CustomElevationColor },
                      },
                  ]
                : []),
            {
                x: data.timeline,
                y: Array(data.timeline.length).fill(data.record_tide),
                type: 'scatter',
                legendgroup: 'grp1',
                name: `Record Tide, ${data.record_tide_date} (${data.record_tide})`,
                mode: 'lines',
                line: { color: RecordTideColor },
                // We want hover text only for small screens, otherwise it clutters the hover.
                hoverinfo: isWideEnough ? 'skip' : 'all',
                // hovertemplate overrides hoverinfo, so must set to empty if we want no hover text.
                // Otherwise must override default template of "{name} : %{y}".
                hovertemplate: isWideEnough
                    ? ''
                    : `Record (${data.record_tide_date}) : %{y}<extra></extra>`,
            },
            {
                x: data.timeline,
                y: data.highest_annual_predictions,
                type: 'scatter',
                legendgroup: 'grp1',
                name: 'Highest Annual Predicted (' + data.highest_annual_predictions[0] + ')',
                mode: 'Lines',
                line: { color: HighestAnnualPredictionColor },
                // Again, hover text only on small screens
                hoverinfo: isWideEnough ? 'skip' : 'all',
                hovertemplate: isWideEnough ? '' : `Highest Annual Predicted: %{y}<extra></extra>`,
            },
            {
                x: data.timeline,
                y: expandConstant(data.mean_high_water, data.timeline.length),
                type: 'scatter',
                legendgroup: 'grp1',
                mode: 'lines',
                visible: 'legendonly', // Initially not shown
                line: { color: MeanHighWaterColor },
                name: `Mean High Water (${data.mean_high_water})`,
                connectgaps: true,
                hoverinfo: 'skip',
            },
            ...(data.future_tide !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.future_tide,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          name: 'Projected Storm Tide',
                          mode: 'lines',
                          line: { dash: 'dash', color: ProjectedStormTideColor },
                      },
                  ]
                : []),
            ...(data.hist_tides !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.hist_tides,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          name: 'Observed Tide',
                          mode: 'lines',
                          line: { color: ObservedTideColor },
                          hovertemplate: hist_hover,
                      },
                  ]
                : []),
            {
                x: data.timeline,
                y: data.astro_tides,
                legendgroup: 'grp1',
                type: 'scatter',
                mode: 'lines',
                line: { color: PredictedTideColor },
                name: 'Predicted Tide',
                hovertemplate: astro_hover,
            },
            ...(data.past_surge !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.past_surge,
                          legendgroup: 'grp1',
                          type: 'scatter',
                          name: 'Recorded Storm Surge',
                          mode: 'lines',
                          line: { color: RecordedStormSurgeColor },
                      },
                  ]
                : []),
            ...(data.future_surge !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.future_surge,
                          legendgroup: 'grp1',
                          type: 'scatter',
                          name: 'Projected Storm Surge',
                          mode: 'lines',
                          line: { dash: 'dash', color: ProjectedStormSurgeColor },
                      },
                  ]
                : []),
            ...(includingWindData
                ? [
                      {
                          x: data.timeline,
                          y: data.wind_gusts,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          mode: 'markers',
                          marker: {
                              color: WindGustColor,
                              size: 10,
                              symbol: 'arrow',
                              angle: data.wind_dir,
                          },
                          name: 'Wind Gusts',
                          yaxis: 'y2',
                          hovertemplate: '%{y:.1f} mph from %{hovertext}',
                          hovertext: data['wind_dir_hover'],
                      },
                  ]
                : []),
            ...(includingWindData
                ? [
                      {
                          x: data.timeline,
                          y: data.wind_speeds,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          mode: 'markers',
                          marker: {
                              color: WindSpeedColor,
                              size: 10,
                              symbol: 'arrow',
                              angle: data.wind_dir,
                          },
                          name: 'Wind Speed',
                          yaxis: 'y2',
                          hovertemplate: '%{y:.1f} mph from %{hovertext}',
                          hovertext: data['wind_dir_hover'],
                      },
                  ]
                : []),
        ]
        return (
            <>
                <Plot
                    data={plotData}
                    layout={layout}
                    useResizeHandler={true}
                    style={{ width: '100%', height: '100%' }}
                    config={{
                        responsive: isWideEnough, // accept clicks?
                        scrollZoom: isWideEnough, // zoom with mouse wheel?
                        displayModeBar: isWideEnough, // show mode bar at all?
                        modeBarButtonsToRemove: [
                            'select2d',
                            'lasso2d',
                            'autoscale2d',
                            'zoomIn2d',
                            'zoomOut2d',
                        ],
                        displaylogo: false, // hide the plotly link in the mode bar
                    }}
                />
                <p style={{ fontSize: '.95em', textAlign: 'center' }}>
                    Tide and wind observation data may be missing due to equipment maintenance,
                    equipment failure or power failure.
                </p>
            </>
        )
    }

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
                    <MyPlot />
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
