import { useContext, useState, useRef } from 'react'
import { AppContext } from './AppContext'
import { degreesToDir, formatDate, isSmallScreen, toEchartDegrees } from './utils'
import * as storage from './storage'
import ReactECharts from 'echarts-for-react'
import { format } from 'date-fns'
import Spinner from 'react-bootstrap/Spinner'
import {
    Dimension,
    LegendId,
    buildLocalDataSet,
    getOptimalPlacement,
    getResponsiveGridDefs,
} from './ChartBuilder'
import SyzygyPopup from './SyzygyPopup'
import { SyzygyConfig } from './Syzygy'
import ErrorBlock from './ErrorBlock'
import BlueArrow from './images/util/arrow-blue.png?inline'
import GreenArrow from './images/util/arrow-green.png?inline'
import BlackArrow from './images/util/arrow-black.png?inline'

const CustomElevationColor = '#17becf'
const RecordTideColor = '#d62728'
const HighestAnnualPredictedColor = '#ff7f0e'
const ProjectedStormTideColor = '#e377c2'
const ObservedTideColor = '#2ca02c'
const PredictedTideColor = '#0b7dcc'
const RecordedStormSurgeColor = '#bcbd22'
const ProjectedStormSurgeColor = '#9467bd'
const WindGustColor = '#0b7dcc'
const WindSpeedColor = '#17becf'
const PlotBgColor = '#f3f2f2'
const ForecastWindSpeedColor = '#8D89A6'
const gridLineDarkColor = '#3c3941'
const gridLineLightColor = '#ccc'

const PredictedTideTitle = 'Predicted Tide'
const RecordedStormSurgeTitle = 'Recorded Storm Surge'
const ObservedTideTitle = 'Observed Tide'
const ProjectedStormTideTitle = 'Projected Storm Tide'
const ProjectedStormSurgeTitle = 'Projected Storm Surge'
const WindSpeedTitle = 'Wind Speed'
const WindGustTitle = 'Wind Gust'
const ForecastWindSpeedTitle = 'Forecast Wind Speed'
const xAxisFormat = '{hh}:{mm} {A}\n{MMM} {d}'

/*
 * Contents of data:
 * 'timeline' : array of datetimes to define all x axes.
 * 'blob' : data for all non-constant plots, array of arrays. Essentially provides an ordered list of "dimensions" (y) for each
 *     time value (x). Values in inner arrays must correlate to data.dimensions, where [0] is always the datetime, and [1...]
 *     represent values to be graphed, or null if that time has no data for that dimension.
 * 'dimensions' : array of dimension names/keys used to identify discrete data herein. See the Dimensions object for defintions.
 * 'syzygy' : object with data for sun/moon symbols may be empty. Key is datetime from timeline, value is code: e.g. 'NM' for new moon
 * 'subtitle' : date range subtitle for graph
 * 'highest_annual_prediction' : highest predicted astro tide for the year in mllw
 */

export default function Chart({ error, loading, hiloMode, data }) {
    const ctx = useContext(AppContext)
    const customElevationNav = ctx.customElevationNav
    const showElevation =
        customElevationNav && customElevationNav <= ctx.station.maxCustomElevationNavd88()
    const customElevationMllw = showElevation ? ctx.station.navd88ToMllw(customElevationNav) : null
    // If display isn't wide enough, we won't show the legend or the mode bar, and disallow zoom/pan.
    const isNarrow = isSmallScreen()
    const tideMarkerSize = 10
    const [syzygyHelpCode, setSyzygyHelpCode] = useState(null)
    const chartRef = useRef(null)

    const onModalClose = () => {
        setSyzygyHelpCode(null)
    }

    // Recall or initialize the set of traces that should not be visible in the graph.
    const getOrInitializeDaily = () => {
        const daily = storage.getDailyStorage(ctx.station.id)
        if (daily.legendOnly) {
            return daily
        }
        // Not there yet, so initialize it.
        storage.setDailyStorage(ctx.station.id, {
            ...daily,
            legendOnly: [],
        })
        return storage.getDailyStorage(ctx.station.id)
    }

    const stationDaily = getOrInitializeDaily()

    if (error) {
        return (
            <>
                <ErrorBlock error={error} />
            </>
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

    // We only include the values in parens when in non-narrow screen. In narrow mode, title is shown in tooltip and values are redundant.
    const recordTideTitle =
        `Record Tide ${formatDate(new Date(ctx.station.recordTideDate))}` +
        (isNarrow ? '' : ` (${ctx.station.recordTideMllw()})`)
    const highestAnnualTitle =
        'Highest Annual Predicted' + (isNarrow ? '' : ` (${data.highest_annual_prediction})`)
    const customElevationTitle = 'Custom Elevation ' + (isNarrow ? '' : `(${customElevationMllw})`)

    const legendIdToTitle = (legendId) => {
        for (const obj of legend) {
            if (obj.legendId === legendId) {
                return obj.name
            }
        }
        return null
    }

    const formatTooltip = (params) => {
        // There's a param for each tooltip-enabled series that contains data associated with the Y axis under the cursor.
        // I hate building every possible tooltip with one function, but if I define the tooltips
        // at the series level, then I can't find a way to format the datetime.
        // First, some ugliness to pull the datetime for this point in the chart. Could use any param.
        const dt = new Date(params[0].data[0]) // technically s/b params[0].data[params[0].encode.x[0]]
        var buffer = ''
        for (const p of params) {
            // p.data is an array where [0] is the y value (dt) and others are the values under the cursor on the yaxis, in series order.
            // p.encode is an object with keys for x and y. Here we only care about y[0], which is the index of the dimension
            // for which we are building a tooltip. This means it's also the index into p.data for the value of that dimension.
            const dimIndex = p.encode.y[0]
            const val = p.data[dimIndex] // data[0] is the datetime, and data[1...] are the values for the dimensions.
            if (val != null) {
                buffer += `<br/>${p.marker} ${p.seriesName}: `
                const dimName = p.dimensionNames[dimIndex]
                if ([Dimension.WindGusts, Dimension.WindSpeeds].includes(dimName)) {
                    const deg = p.data[data.dimensions.indexOf(Dimension.WindDir)]
                    buffer += `${val} mph from ${deg ? degreesToDir(deg) : ''}`
                } else if (dimName === Dimension.ForecastWindSpeeds) {
                    const deg = p.data[data.dimensions.indexOf(Dimension.ForecastWindDir)]
                    buffer += `${val} mph from ${deg ? degreesToDir(deg) : ''}`
                } else if (dimName === Dimension.HistTides) {
                    const label = p.data[data.dimensions.indexOf(Dimension.HistTidesLabels)]
                    buffer += `${val} ${label ?? ''}`
                } else if (dimName === Dimension.AstroTides) {
                    const label = p.data[data.dimensions.indexOf(Dimension.AstroTidesLabels)]
                    buffer += `${val} ${label ?? ''}`
                } else {
                    buffer += val
                }
            }
        }
        return buffer ? format(dt, 'ccc, MMM d, yyyy h:mm aaa') + buffer : ''
    }

    const series = []
    const legend = []

    if (data.syzygy) {
        series.push({
            type: 'scatter',
            xAxisIndex: 0,
            yAxisIndex: 0,
            datasetIndex: 1,
            name: 'syzygy', // for this one, name is only needed for click handling
            encode: { x: Dimension.DateTime, y: Dimension.Syzygy },
            symbol: (values, params) => {
                // values is the array containing all values for x in this dataset. Elements with
                // the value 1 indicate a symbol, and the image url will be present also
                if (values[params.encode.y[0]]) {
                    const urlIndex = params.dimensionNames.indexOf(Dimension.SyzygyUrl)
                    return values[urlIndex]
                } else {
                    return null
                }
            },
            symbolSize: 30,
            tooltip: {
                trigger: 'item',
                // For these events we pull the data from the syzygy object using the x datetime value.
                // It's an array with the event code (e.g. FM) and the actual datetime, not aligned with timeline.
                formatter: (param) => {
                    const dt = param.data[0] // timeline datetime
                    const code = data.syzygy[dt]
                    const dtStr = format(new Date(dt), 'ccc, MMM d, yyyy h:mm aaa')
                    return `${SyzygyConfig[code].name}: ${dtStr}<br>Click symbol for more.`
                },
            },
        })
    }

    series.push({
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        datasetIndex: 1,
        name: recordTideTitle,
        encode: { x: Dimension.DateTime, y: Dimension.RecordTide },
        symbol: 'none',
        color: RecordTideColor,
        tooltip: { show: isNarrow },
        sortValue: ctx.station.recordTideMllw(),
    })
    legend.push({
        name: recordTideTitle,
        legendId: LegendId.RecordTide,
        sortValue: ctx.station.recordTideMllw(),
    })

    series.push({
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        datasetIndex: 1,
        name: highestAnnualTitle,
        encode: { x: Dimension.DateTime, y: Dimension.HighestAnnualPredicted },
        symbol: 'none',
        color: HighestAnnualPredictedColor,
        tooltip: { show: isNarrow },
        sortValue: data.highest_annual_prediction,
    })
    legend.push({
        name: highestAnnualTitle,
        legendId: LegendId.HighestAnnualPredicted,
        sortValue: data.highest_annual_prediction,
    })

    if (customElevationMllw != null) {
        series.push({
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 1,
            name: customElevationTitle,
            encode: { x: Dimension.DateTime, y: Dimension.CustomElevation },
            symbol: 'none',
            color: CustomElevationColor,
            tooltip: { show: isNarrow },
            sortValue: customElevationMllw,
        })
        legend.push({
            name: customElevationTitle,
            legendId: LegendId.CustomElevation,
            sortValue: customElevationMllw,
        })
    }

    // series order drives tooltip display order and legend order drives legend display order,
    // so sort the unpredictable ones now, high-to-low. The rest are in a logical permanent order.
    series.sort((a, b) => b.sortValue - a.sortValue)
    legend.sort((a, b) => b.sortValue - a.sortValue)

    if (data.dimensions.includes(Dimension.HistTides)) {
        series.push({
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 0,
            name: ObservedTideTitle,
            encode: { x: Dimension.DateTime, y: Dimension.HistTides },
            smooth: true,
            symbol: hiloMode ? 'circle' : 'none',
            connectNulls: true, // avoid gaps for syzygy events, which rarely align with other data
            symbolSize: tideMarkerSize,
            color: ObservedTideColor,
        })
        legend.push({ name: ObservedTideTitle, legendId: LegendId.ObservedTide })
    }
    if (data.dimensions.includes(Dimension.AstroTides)) {
        series.push({
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 0,
            name: PredictedTideTitle,
            encode: { x: Dimension.DateTime, y: Dimension.AstroTides },
            smooth: true,
            symbol: hiloMode ? 'circle' : 'none',
            connectNulls: true,
            symbolSize: tideMarkerSize,
            color: PredictedTideColor,
        })
        legend.push({ name: PredictedTideTitle, legendId: LegendId.PredictedTide })
    }
    if (data.dimensions.includes(Dimension.RecordedStormSurge)) {
        series.push({
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 0,
            name: RecordedStormSurgeTitle,
            encode: { x: Dimension.DateTime, y: Dimension.RecordedStormSurge },
            smooth: true,
            symbol: 'none',
            connectNulls: true,
            color: RecordedStormSurgeColor,
        })
        legend.push({ name: RecordedStormSurgeTitle, legendId: LegendId.RecordedStormSurge })
    }
    if (data.dimensions.includes(Dimension.ProjectedStormTide)) {
        series.push({
            type: 'line',
            lineStyle: { type: 'dashed' },
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 0,
            name: ProjectedStormTideTitle,
            encode: { x: Dimension.DateTime, y: Dimension.ProjectedStormTide },
            smooth: true,
            symbol: 'none',
            connectNulls: true,
            color: ProjectedStormTideColor,
        })
        legend.push({ name: ProjectedStormTideTitle, legendId: LegendId.ProjectedStormTide })
    }
    if (data.dimensions.includes(Dimension.ProjectedStormSurge)) {
        series.push({
            type: 'line',
            lineStyle: { type: 'dashed' },
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 0,
            name: ProjectedStormSurgeTitle,
            encode: { x: Dimension.DateTime, y: Dimension.ProjectedStormSurge },
            smooth: true,
            symbol: 'none',
            connectNulls: true,
            color: ProjectedStormSurgeColor,
        })
        legend.push({ name: ProjectedStormSurgeTitle, legendId: LegendId.ProjectedStormSurge })
    }
    if (data.dimensions.includes(Dimension.WindGusts)) {
        series.push({
            type: 'scatter',
            xAxisIndex: 2,
            yAxisIndex: 2,
            datasetIndex: 0,
            name: WindGustTitle,
            encode: { x: Dimension.DateTime, y: Dimension.WindGusts },
            symbol: `image://${BlueArrow}`,
            color: WindGustColor,
            symbolRotate: (_, params) =>
                toEchartDegrees(params.data[data.dimensions.indexOf(Dimension.WindDir)]),
        })
        legend.push({
            name: WindGustTitle,
            icon: 'image://' + BlueArrow,
            legendId: LegendId.WindGust,
        })
    }
    if (data.dimensions.includes(Dimension.WindSpeeds)) {
        series.push({
            type: 'scatter',
            xAxisIndex: 2,
            yAxisIndex: 2,
            datasetIndex: 0,
            name: WindSpeedTitle,
            encode: { x: Dimension.DateTime, y: Dimension.WindSpeeds },
            symbol: 'image://' + GreenArrow,
            color: WindSpeedColor,
            symbolRotate: (_, params) =>
                toEchartDegrees(params.data[data.dimensions.indexOf(Dimension.WindDir)]),
        })
        legend.push({
            name: WindSpeedTitle,
            icon: 'image://' + GreenArrow,
            legendId: LegendId.WindSpeed,
        })
    }
    if (data.dimensions.includes(Dimension.ForecastWindSpeeds)) {
        series.push({
            type: 'scatter',
            xAxisIndex: 2,
            yAxisIndex: 2,
            datasetIndex: 0,
            name: ForecastWindSpeedTitle,
            encode: { x: Dimension.DateTime, y: Dimension.ForecastWindSpeeds },
            symbol: 'image://' + BlackArrow,
            symbolRotate: (_, params) =>
                toEchartDegrees(params.data[data.dimensions.indexOf(Dimension.ForecastWindDir)]),
            color: ForecastWindSpeedColor,
        })
        legend.push({
            name: ForecastWindSpeedTitle,
            icon: 'image://' + BlackArrow,
            legendId: LegendId.WindForecast,
        })
    }

    const onEvents = {
        click: (param) => {
            if (param.componentType === 'series') {
                if (param.seriesName === 'syzygy') {
                    // Put the selected code (e.g. FM) in state to trigger the modal popup.
                    setSyzygyHelpCode(data.syzygy[param.data[0]])
                }
            } else if (param.componentType === 'legend') {
                var legendId = 0
                for (const leg of legend) {
                    if (leg.name === param.value) {
                        legendId = leg.legendId
                        break
                    }
                }
                if (legendId > 0) {
                    const stationDaily = getOrInitializeDaily()
                    if (!stationDaily.legendOnly.includes(legendId)) {
                        stationDaily.legendOnly.push(legendId)
                    } else {
                        stationDaily.legendOnly = stationDaily.legendOnly.filter(
                            (v) => v !== legendId,
                        )
                    }
                    storage.setDailyStorage(ctx.station.id, stationDaily)
                }
            }
        },
    }

    const onReady = () => {
        const chart = chartRef.current?.getEchartsInstance()
        if (chart) {
            for (const legendId of stationDaily.legendOnly) {
                chart.dispatchAction({
                    type: 'legendUnSelect',
                    name: legendIdToTitle(legendId),
                })
            }
        }
    }

    const showingWind =
        data.dimensions.includes(Dimension.WindSpeeds) ||
        data.dimensions.includes(Dimension.ForecastWindSpeeds)
    // this helps the 2 or 3 grids to line up on the x axis
    const minDate = data.blob.length > 0 ? data.blob[0][0] : null // first datetime in the blob

    const localDataset = buildLocalDataSet(
        data.timeline,
        data.syzygy,
        ctx.station,
        data.highest_annual_prediction,
        customElevationMllw,
    )

    let xAxesForZoom = [1]
    if (data.syzygy) xAxesForZoom = [0, ...xAxesForZoom]
    if (showingWind) xAxesForZoom = [...xAxesForZoom, 2]

    const placement = getOptimalPlacement(!isNarrow)
    const gridDef = getResponsiveGridDefs(showingWind, placement)

    const options = {
        backgroundColor: PlotBgColor,
        grid: gridDef,
        title: [
            {
                text: `Tides at ${ctx.station.waterStationName}`,
                subtext: data.subtitle,
                subtextStyle: { fontWeight: 'bolder' },
            },
            ...(!isNarrow ?
                [
                    {
                        text: 'Click lines below to toggle visibility.',
                        left: placement.legendLeftPix,
                        top: '20%',
                        textStyle: { fontSize: '.8em', fontWeight: 'bold' },
                    },
                ]
            :   []),
        ],
        tooltip: {
            trigger: 'axis',
            formatter: formatTooltip,
            order: 'seriesAsc',
        },

        legend: {
            top: '25%',
            left: placement.legendLeftPix,
            orient: 'vertical',
            borderWidth: 2,
            data: !isNarrow ? legend : [],
            triggerEvent: true,
            formatter: (name) => {
                if (name.startsWith('Wind ')) {
                    return `${name} (points to direction)`
                }
                return name
            },
        },
        xAxis: [
            {
                type: 'time',
                gridIndex: 0,
                splitLine: {
                    show: false,
                },
                axisLabel: { formatter: '' }, // do not show the labels for the syzygy symbols
                min: minDate,
            },
            {
                type: 'time',
                gridIndex: 1,
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: gridLineDarkColor,
                        type: 'solid',
                    },
                },
                axisLabel: { hideOverlap: true, formatter: showingWind ? '' : xAxisFormat },
                minorTick: { show: true, splitNumber: 2, length: 0 },
                minorSplitLine: { show: true, lineStyle: { color: gridLineLightColor } },
                min: minDate,
            },
            ...(showingWind ?
                [
                    {
                        type: 'time',
                        gridIndex: 2,
                        axisLabel: {
                            hideOverlap: true,
                            formatter: xAxisFormat,
                        },
                        splitLine: {
                            show: true,
                            lineStyle: {
                                color: gridLineDarkColor,
                                type: 'solid',
                            },
                        },
                        minorTick: { show: true, splitNumber: 2, length: 0 },
                        minorSplitLine: { show: true, lineStyle: { color: gridLineLightColor } },
                        min: minDate,
                    },
                ]
            :   []),
        ],
        yAxis: [
            {
                // This is for the Syzygy symbols.
                type: 'value',
                gridIndex: 0,
                min: 1,
                max: 1,
                interval: 0,
            },
            {
                type: 'value',
                name: 'Tide Level (MLLW feet)',
                nameLocation: 'center',
                nameRotate: 90,
                nameTextStyle: { fontWeight: 'bold' },
                gridIndex: 1,
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: gridLineDarkColor,
                        type: 'solid',
                    },
                },
            },
            ...(showingWind ?
                [
                    {
                        type: 'value',
                        name: 'Wind Speed (MPH)',
                        nameLocation: 'center',
                        nameRotate: 90,
                        nameTextStyle: { fontWeight: 'bold' },
                        gridIndex: 2,
                        min: 0,
                        splitLine: {
                            show: true, // Optional: make vertical lines dark too
                            lineStyle: {
                                color: gridLineDarkColor,
                                width: 1,
                            },
                        },
                    },
                ]
            :   []),
        ],
        dataset: [{ source: data.blob, dimensions: data.dimensions }, localDataset],
        series: series,
        dataZoom: [{ type: 'slider', xAxisIndex: xAxesForZoom, show: !isNarrow }],

        toolbox: [
            {
                show: !isNarrow,
                feature: {
                    restore: {},
                    saveAsImage: {
                        show: true,
                        // Optional: Customize the button's tooltip title
                        title: 'Save as Image',
                        name: `tides_${format(new Date(), 'yyyyMMddHHmmss')}`,
                        type: 'png',
                    },
                    magicType: {
                        type: ['line', 'bar'], // allow conversion to bar graph
                    },
                },
            },
        ],
    }

    return (
        <>
            <ReactECharts
                ref={chartRef}
                option={options}
                onEvents={onEvents}
                onChartReady={onReady}
                style={{ height: '65vh' }}
                notMerge={true}
                initopts={{
                    renderer: 'canvas', // or 'svg'
                    locale: 'EN',
                }}
            />
            <p style={{ fontSize: '.95em', fontWeight: 700, textAlign: 'center' }}>
                Times are shown in station local time ({ctx.station.timeZone}).
                <br />
                Tide and wind observation data may be missing due to equipment maintenance,
                equipment failure or power failure.
            </p>
            {syzygyHelpCode && <SyzygyPopup code={syzygyHelpCode} onClose={onModalClose} />}
        </>
    )
}
