/* eslint-disable */
import { useContext, useState, useRef } from 'react'
import { AppContext } from './AppContext'
import { calcWindspeedTickInterval, formatDate, isTouchScreen, isSmallScreen } from './utils'
import * as storage from './storage'
import ReactECharts from 'echarts-for-react'
import { format } from 'date-fns'
import Spinner from 'react-bootstrap/Spinner'
import { Dimension, LegendId, buildLocalDataSet, getResponsiveGridDefs } from './ChartBuilder'
import SyzygyPopup from './SyzygyPopup'
import { SyzygyConfig } from './Syzygy'
import ErrorBlock from './ErrorBlock'
import BlueArrow from './images/util/arrow-blue.png?inline'
import GreenArrow from './images/util/arrow-green.png?inline'
import BlackArrow from './images/util/arrow-black.png?inline'

const CustomElevationColor = '#17becf'
const RecordTideColor = '#d62728'
const ProjectedStormTideColor = '#e377c2'
const ObservedTideColor = '#2ca02c'
const PredictedTideColor = '#0b7dcc'
const RecordedStormSurgeColor = '#bcbd22'
const ProjectedStormSurgeColor = '#9467bd'
const WindGustColor = '#0b7dcc'
const WindSpeedColor = '#17becf'
const PlotBgColor = '#f3f2f2'
const ForecastWindSpeedColor = '#8D89A6'

const PredictedTideTitle = 'Predicted Tide'
const RecordedStormSurgeTitle = 'Recorded Storm Surge'
const ObservedTideTitle = 'Observed Tide'
const ProjectedStormTideTitle = 'Projected Storm Tide'
const ProjectedStormSurgeTitle = 'Projected Storm Surge'
const WindSpeedTitle = 'Wind Speed'
const WindGustTitle = 'Wind Gust'
const ForecastWindSpeedTitle = 'Forecast Wind Speed'
const xAxisFormat = '{hh}:{mm} {A}\n{MMM} {d}'

// These values must match the AuxDataType enum in the back end.
const AuxDataKeys = Object.freeze({
    HistTideHilo: 'HL', // for observed tide, '(High)' or '(Low)'
    AstroTideHilo: 'AHL', // same, for predicted tides
    WindDir: 'WD', // Int, wind direction 0-360
    WindDirStr: 'WDS', // direction label, e.g. 'N', 'SW', 'SSE'
    ForecastWindDir: 'FWD', // Int, wind direction 0-360
    ForecastWindDirStr: 'FWDS', // direction label
})

/*
 * Contents of data:
 * 'timeline' : array of datetimes to define all x axes.
 * 'blob' : data for all non-constant plots, array of arrays. Essentially provides an ordered list of "dimensions" (y) for each
 *     time value (x). Values in inner arrays must correlate to data.dimensions, where [0] is always the datetime, and [1...]
 *     represent values to be graphed, or null if that time has no data for that dimension.
 * 'dimensions' : array of dimension names/keys used to identify discrete data herein. See the Dimensions object for defintions.
 * 'aux_data': object keyed by datetime, for each time a charted value has any additional data for labels, etc.
 *     Values are objects with key of AuxDataKeys and value for use in graph.
 * 'syzygy' : object with data for sun/moon symbols may be empty. Key is datetime from timeline, value is code: e.g. 'NM' for new moon
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
    const customElevationTitle = 'Custom Elevation' + (isNarrow ? '' : `(${customElevationMllw})`)

    const legendData = [{ name: recordTideTitle, legendId: LegendId.RecordTide }]

    const legendIdToTitle = (legendId) => {
        for (const obj of legendData) {
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
                const dtstr = p.data[0]
                if ([Dimension.WindGusts, Dimension.WindSpeeds].includes(dimName)) {
                    buffer += `${val} mph from ${data.aux_data[dtstr]?.[AuxDataKeys.WindDirStr] ?? ''}`
                } else if (dimName === Dimension.ForecastWindSpeeds) {
                    buffer += `${val} mph from ${data.aux_data[dtstr]?.[AuxDataKeys.ForecastWindDirStr] ?? ''}`
                } else if (dimName === Dimension.HistTides) {
                    buffer += `${val} ${data.aux_data[dtstr]?.[AuxDataKeys.HistTideHilo] ?? ''}`
                } else if (dimName === Dimension.AstroTides) {
                    buffer += `${val} ${data.aux_data[dtstr]?.[AuxDataKeys.AstroTideHilo] ?? ''}`
                } else {
                    buffer += val
                }
            }
        }
        return buffer ? format(dt, 'ccc, MMM d, yyyy h:mm aaa') + buffer : ''
    }

    const series = [
        {
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 1,
            name: recordTideTitle,
            encode: { x: Dimension.DateTime, y: Dimension.RecordTide },
            symbol: 'none',
            color: RecordTideColor,
            tooltip: { show: isNarrow },
        },
        ...(data.syzygy ?
            [
                {
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
                },
            ]
        :   []),
    ]

    if (customElevationMllw != null) {
        series.push({
            // If they are showing a custom elevation, insert it into the plot data, so that the
            // 1st 3 items are in descending order.
            type: 'line',
            xAxisIndex: 1,
            yAxisIndex: 1,
            datasetIndex: 1,
            // Series name is used to display on tooltip AND to map to legend.data. Since this one is not in the tooltip,
            // and is formatted in the legend, we'll just use the dimension key for convenience.
            name: customElevationTitle,
            encode: { x: Dimension.DateTime, y: Dimension.CustomElevation },
            // smooth: true,
            symbol: 'none',
            color: CustomElevationColor,
            tooltip: { show: isNarrow },
        })
        legendData.push({ name: customElevationTitle, legendId: LegendId.CustomElevation })
    }

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
        legendData.push({ name: ObservedTideTitle, legendId: LegendId.ObservedTide })
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
        legendData.push({ name: PredictedTideTitle, legendId: LegendId.PredictedTide })
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
        legendData.push({ name: RecordedStormSurgeTitle, legendId: LegendId.RecordedStormSurge })
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
        legendData.push({ name: ProjectedStormTideTitle, legendId: LegendId.ProjectedStormTide })
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
        legendData.push({ name: ProjectedStormSurgeTitle, legendId: LegendId.ProjectedStormSurge })
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
            symbolRotate: (_, params) => {
                const dtstr = params.data[0]
                const deg = data.aux_data[params.data[0]]?.[AuxDataKeys.WindDir] ?? 0
                // echarts uses 0 ... -180 for 0 ... 180, and 0 ... 179 for 359 ... 181
                return deg <= 180 ? -deg : 360 - deg
            },
        })
        legendData.push({
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
            symbolRotate: (_, params) => {
                const deg = data.aux_data[params.data[0]]?.[AuxDataKeys.WindDir] ?? 0
                // echarts uses 0 ... -180 for 0 ... 180, and 0 ... 179 for 359 ... 181
                return deg <= 180 ? -deg : 360 - deg
            },
        })
        legendData.push({
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
            symbolRotate: (_, params) => {
                const dtstr = params.data[0]
                const deg = data.aux_data[params.data[0]]?.[AuxDataKeys.ForecastWindDir] ?? 0
                // echarts uses 0 ... -180 for 0 ... 180, and 1 ... 179 for 359 ... 181
                return deg <= 180 ? -deg : 360 - deg
            },
            color: ForecastWindSpeedColor,
        })
        legendData.push({
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
                for (const leg of legendData) {
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
        customElevationMllw,
    )

    let xAxesForZoom = [1]
    if (data.syzygy) xAxesForZoom = [0, ...xAxesForZoom]
    if (showingWind) xAxesForZoom = [...xAxesForZoom, 2]

    const options = {
        backgroundColor: PlotBgColor,
        grid: getResponsiveGridDefs(showingWind),
        title: { text: `Tides at ${ctx.station.waterStationName}`, subtext: data.subtitle },
        tooltip: {
            trigger: 'axis',
            formatter: formatTooltip,
        },
        legend: {
            top: '20%',
            right: '2%',
            orient: 'vertical',
            borderWidth: 1,
            data: !isNarrow ? legendData : [],
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
                        color: '#ccc',
                        type: 'solid',
                    },
                },
                axisLabel: { formatter: showingWind ? '' : xAxisFormat },
                min: minDate,
            },
            ...(showingWind ?
                [
                    {
                        type: 'time',
                        gridIndex: 2,
                        axisLabel: { formatter: xAxisFormat },
                        splitLine: {
                            show: true,
                            lineStyle: {
                                color: '#ccc',
                                type: 'solid',
                            },
                        },
                        min: minDate,
                    },
                ]
            :   []),
        ],
        yAxis: [
            {
                // This is for the Syzygy symbols.
                type: 'value',
                // name: '',
                gridIndex: 0,
                min: 1,
                max: 1,
                interval: 0,
                // axisTick: { show: false },
                // splitLine: { show: false },
                // splitNumber: 1,
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
                        color: '#ccc',
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
                        // interval: calcWindspeedTickInterval(ctx.station),
                    },
                ]
            :   []),
        ],
        dataset: [{ source: data.blob, dimensions: data.dimensions }, localDataset],
        series: series,
        dataZoom: [{ type: 'slider', xAxisIndex: xAxesForZoom }],

        toolbox: [
            {
                show: true,
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
