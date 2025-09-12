import './css/Conditions.css'
import { Spinner } from 'react-bootstrap'
import { Months } from './utils'

export default function Conditions({ data, error }) {
    const noData = '--'

    // Convert iso date string into 'Aug 5 10:05 PM' format. Don't need year here. Ah, javascript.
    const format_dt = (dts) => {
        const dt = new Date(dts)
        const re = /:\d\d /
        const tm = dt.toLocaleTimeString('en-US').replace(re, ' ')
        return `${Months[dt.getMonth()]} ${dt.getDate()} ${tm}`
    }

    if (error) {
        return (
            <div className='text-center'>
                There was a problem fetching the data. Please try again later.
            </div>
        )
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

            <div className='cond-label'>Tide Level</div>
            <div className='cond-data'>
                {data.tide_dir ? `${data.tide} ft MLLW ${data.tide_dir}` : noData}
            </div>
            <div className='cond-time'>{data.tide_time ? format_dt(data.tide_time) : noData}</div>

            <div className='cond-label'>Water Temp</div>
            <div className='cond-data'>{data.temp ? `${data.temp}º F` : noData}</div>
            <div className='cond-time'>{data.temp_time ? format_dt(data.temp_time) : noData}</div>

            <div className='cond-label'>Moon Phase</div>
            <div className='cond-data'>{data.phase ? `${data.phase}` : noData}</div>
            <div className='cond-time'>{data.phase_dt ? format_dt(data.phase_dt) : noData}</div>

            <div className='cond-label'>Next Phase</div>
            <div className='cond-data'>{data.next_phase ? `${data.next_phase}` : noData}</div>
            <div className='cond-time'>
                {data.next_phase_dt ? format_dt(data.next_phase_dt) : noData}
            </div>
        </div>
    )
}
