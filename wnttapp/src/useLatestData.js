import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useClientIp } from './useClientIp'

export default function useLatestData(station) {
    const { clientIp, ipError } = useClientIp()

    const { data, error } = useQuery({
        retry: false,
        queryKey: [station.id, 'latest'],
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_LATEST_URL, {
                ip: clientIp ?? 'unknown',
                water_station: station.id,
                weather_station: station.weatherStationId,
                noaa_station_id: station.noaaStationId,
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        enabled: !!clientIp || !!ipError,
        staleTime: 30_000, // 30 seconds. Allows for frequent checks without hammering the server.
        gcTime: 30_000, // gcTime should be >= staleTime in case they move off the page and return
    })
    return { data, error }
}
