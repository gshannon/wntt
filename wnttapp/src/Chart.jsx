import { AppContext } from './AppContext'
import { isTouchScreen, maxCustomElevationNavd88, navd88ToMllw, isSmallScreen } from './utils'
import Plot from 'react-plotly.js'
import Spinner from 'react-bootstrap/Spinner'
import Button from 'react-bootstrap/Button'
import { buildSyzygyAnnotations, buildPlot } from './ChartBuilder'
import SyzygyPopup from './SyzygyPopup'
import { useContext, useState } from 'react'

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
const PlotBgColor = '#f3f2f2'

export default function Chart({ error, loading, hiloMode, data, forceUpdate }) {
    const appContext = useContext(AppContext)
    const customElevationNav = appContext.customElevationNav
    const showElevation = customElevationNav && customElevationNav <= maxCustomElevationNavd88()
    const customElevationMllw = showElevation ? navd88ToMllw(customElevationNav) : null
    // If display isn't wide enough, we won't show the legend or the mode bar, and disallow zoom/pan.
    const isNarrow = isSmallScreen()
    const tideMarkerSize = 8
    const windMarkerSize = 11
    const [showHelp, setShowHelp] = useState(-1)

    const onModalClose = () => {
        setShowHelp(-1)
    }

    if (error) {
        console.error(error)
        return (
            <div>
                <br />
                <br />
                <br />
                Sorry, we are unable to generate the graph just now. There may have been a problem
                fetching data.
                <br /> {error.message}
                <br />
                <Button variant='warning' onClick={() => forceUpdate()}>
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
    const graph1_min = data.wind_speeds !== null ? 0.52 : 0.1
    const graph2_max = 0.48
    const graph2_min = 0

    const layout = {
        showlegend: !isNarrow,
        height: 420,
        template: 'plotly',
        plot_bgcolor: PlotBgColor,
        title: {
            text: 'Wells Harbor Tides',
            subtitle: {
                text: data.start_date + ' - ' + data.end_date,
            },
        },
        hovermode: 'x unified',
        // hoverlabel can get pretty wide thanks to the hoverdistance problem (see below), so for narrow screens,
        // we slightly decrease font size.
        hoverlabel: { namelength: 22, font: { size: isNarrow ? 12 : 13 } },
        /* hoverdistance controls how many pixels to the left or right of the cursor it will look for data when
            trying to show hover text for a plot that has a None for the time the cursor is over. While this is
            an essential feature, since otherwise you'd have to hover exactly over a data point to see the
            hover text, it has a serious drawback: with "x unified" hovermode, it will perform this logic on each plot 
            independently. This means that if the closest non-null data for some plots are to the left, and others are
            to the right, it will identify the x axis (time) based on only one (probably the first it finds), and then 
            show data from a nearby time for other plots, with the actual datetime in parens. I can see where this
            might be useful for some, but they don't give a way to suppress this behavior. Here, I want to show hover text for 
            only plots that have a value for the selected time.  Worse, when it shows this "nearby" data, it ends up
            being quite wide, messing up the display on narrow screens. In hilo mode, we could set a higher value, like 10,
            for user convenience, but when there's a high or low value very close to the start or end of the graph,
            where the hover for the midnight would bring in the nearby high or low, it can look ugly.
            So we use a happy middle ground of around 5 pixels.
             */
        hoverdistance: hiloMode ? 5 : 1,
        hoversubplots: 'axis', // to include wind hovers in upper graph
        legend: {
            groupclick: 'toggleitem',
            title: {
                text: '<b>Click lines below to toggle visibility.<br>See Help for details.</b>',
            },
        },
        margin: { t: 70, b: 50, l: 65 }, // overriding defaults t: 100, b/l/r: 80
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
            // For tide, we will use 1-ft intervals for tick marks if not showing wind and
            // total range is low enough to avoid being too cluttered.
            dtick:
                data.wind_speeds === null &&
                Math.max(data.record_tide, customElevationMllw ?? 0) < 16
                    ? 1
                    : 2,
        },
        yaxis2: {
            title: { text: 'Wind MPH', font: { size: 15 } },
            domain: [graph2_min, graph2_max],
            gridcolor: 'black',
            // For wind, we prefer a tick interval of 2, for greater precistion, but if the range
            // is too high, it gets very cluttered, so we bump it to 5.
            dtick:
                data.wind_speeds !== null &&
                Math.max(...data.wind_gusts) - Math.min(...data.wind_speeds) < 18
                    ? 2
                    : 5,
        },
        grid: {
            rows: 2,
            columns: 1,
            subplots: [['xy'], ['xy2']],
            roworder: 'top to bottom',
        },
        // Don't allow zoom dragging on small or touch screens.
        dragmode: isNarrow || isTouchScreen ? false : 'zoom',
    }

    // Add annotations for moon, sun data.
    const [annotations, displayedCodes] = buildSyzygyAnnotations(data.syzygy, data.timeline)
    layout.annotations = annotations

    const expandConstant = (value) => {
        return Array(data.timeline.length).fill(value)
    }

    // Building the plot data, we are aware that the order in the array determines the display order
    // in the legend and the hover text. We start with record tide, followed by highest annual prediction, which
    // should be the highest 2 values. If there's a custom elevation, that will be inserted in the proper place
    // so the 1st 3 are in descending order. After that, the precise order could vary by time, so we just make our
    // best guess here.

    // Hack: Plotly uses the 1st element of wind_dir array to control the direction of the marker in the legend.
    // Unfortunately it doesn't use the first non-null value.  So if the 1st element is null, as is normally the
    // case in hilo mode, it will show wind speed & wind gust in the legend with NO MARKER.. So we cheat a little.
    // This does not cause the false value to appear in the graph, since the speed & gust values are null.
    if (data.wind_dir !== null && data.wind_dir.length > 0 && data.wind_dir[0] === null) {
        data.wind_dir[0] = 0
    }

    const plotData = [
        buildPlot({
            name: `Record Tide, ${data.record_tide_date} (${data.record_tide})`,
            x: data.timeline,
            // We need this one filled across cuz it may appear on the hover text.
            y: expandConstant(data.record_tide),
            lineType: 'solid',
            color: RecordTideColor,
            // We want hover text only for small screens, otherwise it clutters the hover.
            hoverinfo: isNarrow ? 'all' : 'skip',
            // hovertemplate overrides hoverinfo, so must set to empty if we want no hover text.
            // Otherwise must override default template of "{name} : %{y}".
            hovertemplate: isNarrow
                ? `Record (${data.record_tide_date}) : %{y}<extra></extra>`
                : null,
        }),
        buildPlot({
            name: 'Highest Annual Predicted (' + data.highest_annual_prediction + ')',
            x: data.timeline,
            y: expandConstant(data.highest_annual_prediction),
            lineType: 'solid',
            color: HighestAnnualPredictionColor,
            hoverinfo: isNarrow ? 'all' : 'skip',
            hovertemplate: isNarrow ? 'Highest Annual Predicted: %{y}<extra></extra>' : '',
        }),
        buildPlot({
            name: `Mean High Water (${data.mean_high_water})`,
            x: data.timeline,
            y: expandConstant(data.mean_high_water),
            legendOnly: true,
            lineType: 'solid',
            color: MeanHighWaterColor,
            hoverinfo: 'skip',
        }),
        ...(data.hist_tides !== null
            ? [
                  buildPlot({
                      name: 'Observed Tide',
                      x: data.timeline,
                      y: data.hist_tides,
                      lineType: 'solid',
                      markerSize: hiloMode ? tideMarkerSize : 0,
                      color: ObservedTideColor,
                      hovertext: data.hist_hilo_labels,
                      hovertemplate: '%{y} %{hovertext}',
                  }),
              ]
            : []),
        buildPlot({
            name: 'Predicted Tide',
            x: data.timeline,
            y: data.astro_tides,
            lineType: 'solid',
            markerSize: hiloMode ? tideMarkerSize : 0,
            color: PredictedTideColor,
            hovertext: data.astro_hilo_labels,
            hovertemplate: '%{y} %{hovertext}',
        }),
        ...(data.past_surge !== null
            ? [
                  buildPlot({
                      name: 'Recorded Storm Surge',
                      x: data.timeline,
                      y: data.past_surge,
                      lineType: 'solid',
                      markerSize: hiloMode ? tideMarkerSize : 0,
                      color: RecordedStormSurgeColor,
                  }),
              ]
            : []),
        ...(data.future_tide !== null
            ? [
                  buildPlot({
                      name: 'Projected Storm Tide',
                      x: data.timeline,
                      y: data.future_tide,
                      lineType: 'dash',
                      markerSize: hiloMode ? tideMarkerSize : 0,
                      color: ProjectedStormTideColor,
                  }),
              ]
            : []),
        ...(data.future_surge !== null
            ? [
                  buildPlot({
                      name: 'Projected Storm Surge',
                      x: data.timeline,
                      y: data.future_surge,
                      lineType: 'dash',
                      markerSize: hiloMode ? tideMarkerSize : 0,
                      color: ProjectedStormSurgeColor,
                  }),
              ]
            : []),
        ...(data.wind_speeds !== null
            ? [
                  buildPlot({
                      name: 'Wind Gusts',
                      x: data.timeline,
                      y: data.wind_gusts,
                      markerSize: windMarkerSize,
                      markerSymbol: 'arrow',
                      markerAngle: data.wind_dir,
                      color: WindGustColor,
                      yaxis: 'y2',
                      hovertemplate: '%{y:.1f} mph from %{hovertext}',
                      hovertext: data.wind_dir_hover,
                  }),
                  buildPlot({
                      name: 'Wind Speed',
                      x: data.timeline,
                      y: data.wind_speeds,
                      markerSize: windMarkerSize,
                      markerSymbol: 'arrow',
                      markerAngle: data.wind_dir,
                      color: WindSpeedColor,
                      yaxis: 'y2',
                      hovertemplate: '%{y:.1f} mph from %{hovertext}',
                      hovertext: data.wind_dir_hover,
                  }),
              ]
            : []),
    ]

    if (customElevationMllw != null) {
        // If they are showing a custom elevation, insert it into the plot data, so that the
        // 1st 3 items are in descending order.
        const index =
            customElevationMllw >= data.record_tide
                ? 0
                : customElevationMllw >= data.highest_annual_prediction
                ? 1
                : 2
        plotData.splice(
            index,
            0,
            buildPlot({
                name: `Custom Elevation (${customElevationMllw})`,
                x: data.timeline,
                // We need this one filled across cuz it may appear on the hover text.
                y: expandConstant(customElevationMllw),
                lineType: 'solid',
                color: CustomElevationColor,
                hovertemplate: 'Custom Elevation: %{y}<extra></extra>',
            })
        )
    }

    return (
        <>
            <Plot
                data={plotData}
                layout={layout}
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
                config={{
                    responsive: !isNarrow, // accept clicks?
                    scrollZoom: !isNarrow, // zoom with mouse wheel?
                    displayModeBar: !isNarrow, // show mode bar at all?
                    // For touch screens, zoom & pan don't work. Remove all but the camera option.
                    modeBarButtonsToRemove: [
                        'select2d',
                        'lasso2d',
                        'autoscale2d',
                        'zoomIn2d',
                        'zoomOut2d',
                        ...(isTouchScreen ? ['zoom2d', 'pan2d', 'resetScale2d'] : []),
                    ],
                    displaylogo: false, // hide the plotly link in the mode bar
                }}
                onClickAnnotation={(data) => {
                    // data.index will be 0-based index into displayedCodes[]
                    setShowHelp(data.index)
                }}
            />
            <p style={{ fontSize: '.95em', fontWeight: 700, textAlign: 'center' }}>
                Tide and wind observation data may be missing due to equipment maintenance,
                equipment failure or power failure.
            </p>
            {showHelp >= 0 && (
                <SyzygyPopup code={displayedCodes[showHelp]} onClose={onModalClose} />
            )}
        </>
    )
}
