import './css/Graph.css'
import { useContext, useState } from 'react'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import { Col, Row } from 'react-bootstrap'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import GetDates from './GetDates'
import Plot from 'react-plotly.js'
import useGraphData from './useGraphData'
import { MaxCustomElevation } from './utils'
import { AppContext } from './AppContext'
import { addDays, stringify, dateDiff, limitDate, MinDate, MaxDate, MaxNumDays } from './utils'
import prevButton from './images/util/previous.png'
import nextButton from './images/util/next.png'

export default function Graph() {
    const appContext = useContext(AppContext)
    const customElevation = appContext.customElevation
    const showElevation = customElevation && customElevation <= MaxCustomElevation
    const [startCtl, setStartCtl] = useState({
        min: MinDate,
        start: new Date(appContext.startDate),
        max: MaxDate,
    })
    const [endCtl, setEndCtl] = useState({
        min: new Date(appContext.startDate),
        end: new Date(appContext.endDate),
        max: addDays(new Date(appContext.startDate), MaxNumDays - 1),
    })

    const {
        isPending: loading,
        data,
        error,
    } = useGraphData(appContext.startDate, appContext.endDate)

    const daysShown = dateDiff(appContext.startDate, appContext.endDate) + 1

    const setJumpDates = (directionFactor) => {
        const newStart = limitDate(addDays(appContext.startDate, daysShown * directionFactor))
        const newEnd = limitDate(addDays(newStart, daysShown - 1))
        setStartCtl({ ...startCtl, start: newStart })
        setEndCtl({
            min: newStart,
            end: newEnd,
            max: limitDate(addDays(newStart, MaxNumDays - 1)),
        })
        appContext.setDateRange(stringify(newStart), stringify(newEnd))
    }

    const handlePreviousClick = (e) => {
        e.preventDefault()
        setJumpDates(-1)
    }

    const handleNextClick = (e) => {
        e.preventDefault()
        setJumpDates(1)
    }

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

        const graph1_max = 1
        const graph1_min = 0.52
        const graph2_max = 0.48
        const graph2_min = 0

        const title =
            'Wells Harbor Tides' + (data.wind_speeds !== null ? ' & Wind Data' : '') + ', '
        const layout = {
            height: 500,
            template: 'plotly',
            plot_bgcolor: '#e7e7e7',
            title: {
                text: title + data.start_date + ' - ' + data.end_date,
                font: { size: 20 },
            },
            hovermode: 'x unified',
            /* hoverlabel must be extra wide due to issue created by hoverdistance (see below)
            hoverdistance controls how many pixels to the left or right of the cursor it will look for data when
            trying to show hover text for a plot that has a None for the time the cursor is over. I'd like to
            have this be a high number (default is 20), because swiping around is smoother (no flashing), but then
            when we're on the border between past and future, where there's a data gap, it brings in data from
            left or right-adjacent times, which is not what we want (because it's wrong). So here we make this
            as low a number as we can get away with to compromise, tho even 1 is too high for small displays and 7 days.
            This is a serious shortcoming, IMO. */
            hoverlabel: { namelength: 22 },
            // hoverdistance: 8 - data.num_days,
            hoverdistance: 1, // minimizing the problem, at the cost of flashing popups at high resolution
            hoversubplots: 'axis', // to include wind hovers in upper graph
            legend: { groupclick: 'toggleitem' },
            modebar: {
                remove: ['select2d', 'lasso2d', 'autoscale2d', 'zoomIn2d', 'zoomOut2d'],
            },
            xaxis: { gridcolor: 'black' },
            xaxis2: { gridcolor: 'black' },
            yaxis: {
                title: {
                    text: 'Tide feet (MLLW)',
                    font: { color: 'black', size: 20 },
                },
                domain: [graph1_min, graph1_max],
                gridcolor: 'black',
            },
            yaxis2: {
                title: { text: 'Wind MPH', font: { size: 20 } },
                domain: [graph2_min, graph2_max],
                gridcolor: 'black',
            },
            grid: {
                rows: 2,
                columns: 1,
                subplots: [['xy'], ['xy2']],
                roworder: 'top to bottom',
            },
        }

        const plotData = [
            ...(showElevation
                ? [
                      {
                          x: data.timeline,
                          y: Array(data.timeline.length).fill(customElevation),
                          legendgroup: 'grp1',
                          type: 'scatter',
                          name: `Custom Elevation (${customElevation} ft)`,
                          text: `Custom Elevation: ${customElevation} ft`,
                          hoverinfo: 'text', // tells it to use 'text' in hover
                          mode: 'Lines',
                          line: { color: '#17becf' },
                      },
                  ]
                : []),
            {
                x: data.timeline,
                y: data.record_tide,
                type: 'scatter',
                legendgroup: 'grp1',
                legendgrouptitle: {
                    text: '<b>Click below to toggle visibility.<br>See Glossary for details.</b>',
                },
                mode: 'lines',
                line: { color: '#d62728' },
                name: data.record_tide_title,
                connectgaps: true,
                hoverinfo: 'skip',
            },
            {
                x: data.timeline,
                y: data.highest_annual_predictions,
                type: 'scatter',
                legendgroup: 'grp1',
                name: 'Highest Annual Predicted (' + data.highest_annual_predictions[0] + ')',
                mode: 'Lines',
                line: { color: '#ff7f0e' },
                connectgaps: true,
                hoverinfo: 'skip',
            },
            {
                x: data.timeline,
                y: data.mean_high_water,
                type: 'scatter',
                legendgroup: 'grp1',
                mode: 'lines',
                visible: 'legendonly', // Initially not shown
                line: { color: '#8c564b' },
                name: data.mean_high_water_title,
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
                          name: 'Predicted Storm Tide',
                          mode: 'lines',
                          line: { dash: 'dash', color: '#e377c2' },
                          hovertemplate: '%{y} ft',
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
                          line: { color: '#2ca02c' },
                          hovertemplate: '%{y} ft',
                      },
                  ]
                : []),
            {
                x: data.timeline,
                y: data.astro_tides,
                legendgroup: 'grp1',
                type: 'scatter',
                mode: 'lines',
                line: { color: '#0b7dcc' },
                name: 'Predicted Tide',
                hovertemplate: '%{y} ft',
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
                          line: { color: '#bcbd22' },
                          hovertemplate: '%{y} ft',
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
                          name: 'Predicted Storm Surge',
                          mode: 'lines',
                          line: { dash: 'dash', color: '#9467bd' },
                          hovertemplate: '%{y} ft',
                      },
                  ]
                : []),
            ...(data.wind_gusts !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.wind_gusts,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          mode: 'markers',
                          marker: {
                              color: '#0b7dcc',
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
            ...(data.wind_speeds !== null
                ? [
                      {
                          x: data.timeline,
                          y: data.wind_speeds,
                          type: 'scatter',
                          legendgroup: 'grp1',
                          mode: 'markers',
                          marker: {
                              color: '#17becf',
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
                        responsive: true, // accept clicks
                        scrollZoom: true, // allow zooming via scroll wheel
                        displayModeBar: true, // always show button menu
                        displaylogo: false, // hide the plotly link in the menu bar
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
            />
            <Row className='justify-content-center align-items-center'>
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