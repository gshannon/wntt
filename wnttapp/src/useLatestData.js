import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import useClientIp from './useClientIp'

export default function useLatestData(station) {
    // We'll try to get the client IP address for logging, but it's not critical.
    const { data: clientIp, error: ipError } = useClientIp()

    const { isLoading, data, error } = useQuery({
        retry: false,
        queryKey: [station.id, 'latest'],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_LATEST_URL, {
                    signal,
                    ip: clientIp ?? 'unknown',
                    station_id: station.id,
                    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    app_version: import.meta.env.VITE_BUILD_NUM,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError') {
                        console.log(error)
                    }
                    throw error
                })
        },
        // This query will be run on the Home page, so we'd like to have the client ip for logging.
        // Client query is fast but will generally not finish before this query is run, so we wait
        // for it. However, an error getting the ip should not stop the app.
        enabled: !!clientIp || !!ipError,
        staleTime: 30_000, // 30 seconds. Allows for frequent checks without hammering the server.
        gcTime: 30_000, // gcTime should be >= staleTime in case they move off the page and return
    })

    return { isLoading, data, error }
}
