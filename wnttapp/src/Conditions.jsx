import './css/Conditions.css'
import { Spinner } from 'react-bootstrap'
import { Link } from './Links'
import { Months, degreesToDir, roundTo } from './utils'
import { SyzygyConfig } from './Syzygy'
import { AppContext } from './AppContext'
import { useContext } from 'react'
import ErrorBlock from './ErrorBlock'

export default function Conditions({ data, error }) {
    const ctx = useContext(AppContext)
    const noData = '--'

    // Convert iso date string into 'Aug 5 10:05 PM' format. Don't need year here. Ah, javascript.
    const format_dt = (dts) => {
        const dt = new Date(dts)
        const re = /:\d\d /
        const tm = dt.toLocaleTimeString('en-US').replace(re, ' ')
        return `${Months[dt.getMonth()]} ${dt.getDate()} ${tm}`
    }

    // Same as format_dt but only time portion
    const format_tm = (dts) => {
        const dt = new Date(dts)
        const re = /:\d\d /
        const tm = dt.toLocaleTimeString('en-US').replace(re, ' ')
        return tm
    }

    if (error) {
        return (
            <>
                <ErrorBlock error={error} />
            </>
        )
    }

    if (!data) {
        return (
            <div className='text-center'>
                <Spinner animation='border' variant='primary' />
            </div>
        )
    }

    const now = format_dt(new Date())
    const inches = data.next_tide_surge_str ? Number(data.next_tide_surge_str) * 12 : null
    const wind_dir_str = degreesToDir(data.wind_dir_deg)

    return (
        <div className='cond-container'>
            <div className='cond-col-header'>Metric</div>
            <div className='cond-col-header'>Value</div>
            <div className='cond-col-header'>As of</div>
            <div className='horizontal-line'></div>

            {/* current tide */}
            <div className='cond-label'>Water Level</div>
            <div className='cond-data'>
                {data.tide_dir ? `${data.tide} ft MLLW ${data.tide_dir}` : noData}
            </div>
            {/* this is observation time */}
            <div className='cond-time'>{data.tide_time ? format_dt(data.tide_time) : noData}</div>

            {/* next high tide level */}
            <div className='cond-label'>
                Next High Tide<sup>*</sup>
            </div>
            <div className='cond-data'>
                {data.next_tide_str ? `${data.next_tide_str} ft MLLW` : noData}
            </div>
            <div className='cond-time'>{now}</div>

            {/* next tide time and type */}
            <div className='cond-label'>Time</div>
            <div className='cond-data'>
                {data.next_tide_dt ? `${format_tm(data.next_tide_dt)}` : noData}
            </div>
            <div className='cond-time'>{now}</div>

            {/* storm surge */}
            <div className='cond-label'>
                Storm Surge<sup>*</sup>
            </div>
            <div className='cond-data'>
                {data.next_tide_surge_str ?
                    `${data.next_tide_surge_str} ft (${roundTo(inches, 1)} in)`
                :   noData}
            </div>
            <div className='cond-time'>{format_dt(data.surge_time)}</div>

            {/* wind speed */}

            <div className='cond-label'>Wind Speed</div>
            <div className='cond-data'>
                {data.wind_speed == null ? noData : `${data.wind_speed} mph from ${wind_dir_str}`}
            </div>
            <div className='cond-time'>{data.wind_time ? format_dt(data.wind_time) : noData}</div>

            {/* wind gust */}
            <div className='cond-label'>Wind Gust</div>
            <div className='cond-data'>
                {data.wind_gust == null ? noData : `${data.wind_gust} mph`}
            </div>
            <div className='cond-time'>{data.wind_time ? format_dt(data.wind_time) : noData}</div>

            {/* water temp */}
            <div className='cond-label'>Water Temp</div>
            <div className='cond-data'>{data.temp ? `${data.temp}º F` : noData}</div>
            <div className='cond-time'>{data.temp_time ? format_dt(data.temp_time) : noData}</div>

            {/* current moon phase */}
            <div className='cond-label'>Moon Phase</div>
            <div className='cond-data'>
                {data.phase ? `${SyzygyConfig[data.phase].name}` : noData}
            </div>
            <div className='cond-time'>{data.phase_dt ? format_dt(data.phase_dt) : noData}</div>

            {/* next moon phase */}
            <div className='cond-label'>Next Phase</div>
            <div className='cond-data'>
                {data.next_phase ? `${SyzygyConfig[data.next_phase].name}` : noData}
            </div>
            <div className='cond-time'>
                {data.next_phase_dt ? format_dt(data.next_phase_dt) : noData}
            </div>
            <div className='horizontal-line'></div>
            <div className='footnotes'>
                <sup>*</sup>Next Tide Level does not include Storm Surge.
            </div>
            <div className='footnotes'>
                Source of this data:&nbsp; &nbsp;
                <Link
                    href={`https://cdmo.baruch.sc.edu/pwa/index.html?stationCode=${ctx.station.id}`}
                    text='Water'
                />
                &nbsp; &nbsp;
                <Link
                    href={`https://cdmo.baruch.sc.edu/pwa/index.html?stationCode=${ctx.station.weatherStationId}`}
                    text='Weather'
                />
            </div>
        </div>
    )
}
