import { useQuery } from '@tanstack/react-query'
import { useClientIp } from './useClientIp'
import { buildCacheKey } from './utils'
import axios from 'axios'

export default function useGraphData(station, startDate, endDate, hiloMode) {
    const { clientIp } = useClientIp()

    // The main graph data api call.
    const { isPending, data, error } = useQuery({
        retry: false,
        queryKey: buildCacheKey(station.id, startDate, endDate, hiloMode),
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_GRAPH_URL, {
                start_date: startDate,
                end_date: endDate,
                hilo_mode: hiloMode,
                water_station: station.id,
                weather_station: station.weatherStationId,
                noaa_station_id: station.noaaStationId,
                ip: clientIp ?? 'unknown',
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        staleTime: 10_000,
        gcTime: 10_000,
    })

    return { isPending, data, error }
}
