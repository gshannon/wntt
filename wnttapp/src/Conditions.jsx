import './css/Conditions.css'
import { Spinner } from 'react-bootstrap'
import { Link } from './Links'
import { apiErrorResponse, Months, SyzygyInfo } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

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
        return <div className='text-center text-white'>{apiErrorResponse(error)}</div>
    }

    if (!data) {
        return (
            <div className='text-center'>
                <Spinner animation='border' variant='primary' />
            </div>
        )
    }

    return (
        <div className='cond-container'>
            <div className='cond-col-header'>Metric</div>
            <div className='cond-col-header'>Value</div>
            <div className='cond-col-header'>As of</div>
            <div className='horizontal-line'></div>
            <div className='cond-label'>Tide Level</div>
            <div className='cond-data'>
                {data.tide_dir ? `${data.tide} ft MLLW ${data.tide_dir}` : noData}
            </div>
            <div className='cond-time'>{data.tide_time ? format_dt(data.tide_time) : noData}</div>

            <div className='cond-label'>Next Tide</div>
            <div className='cond-data'>
                {data.next_tide_dt
                    ? `${format_tm(data.next_tide_dt)} (${
                          data.next_tide_type === 'H' ? 'High' : 'Low'
                      })`
                    : noData}
            </div>
            <div className='cond-time'>{format_dt(new Date())}</div>

            <div className='cond-label'>Wind Speed</div>
            <div className='cond-data'>
                {data.wind_speed == null ? noData : `${data.wind_speed} mph from ${data.wind_dir}`}
            </div>
            <div className='cond-time'>{data.wind_time ? format_dt(data.wind_time) : noData}</div>

            <div className='cond-label'>Wind Gust</div>
            <div className='cond-data'>
                {data.wind_gust == null ? noData : `${data.wind_gust} mph`}
            </div>
            <div className='cond-time'>{data.wind_time ? format_dt(data.wind_time) : noData}</div>

            <div className='cond-label'>Water Temp</div>
            <div className='cond-data'>{data.temp ? `${data.temp}º F` : noData}</div>
            <div className='cond-time'>{data.temp_time ? format_dt(data.temp_time) : noData}</div>

            <div className='cond-label'>Moon Phase</div>
            <div className='cond-data'>
                {data.phase ? `${SyzygyInfo[data.phase].name}` : noData}
            </div>
            <div className='cond-time'>{data.phase_dt ? format_dt(data.phase_dt) : noData}</div>

            <div className='cond-label'>Next Phase</div>
            <div className='cond-data'>
                {data.next_phase ? `${SyzygyInfo[data.next_phase].name}` : noData}
            </div>
            <div className='cond-time'>
                {data.next_phase_dt ? format_dt(data.next_phase_dt) : noData}
            </div>
            <div className='horizontal-line'></div>
            <div className='links'>
                Source of this data, plus more data:&nbsp; &nbsp;
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
