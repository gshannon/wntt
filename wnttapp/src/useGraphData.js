import { useQuery } from '@tanstack/react-query'
import useClientIp from './useClientIp'
import * as Sentry from '@sentry/react'
import axios from 'axios'
import { buildCacheKey, NotAcceptable } from './utils'

export default function useGraphData(station, startDate, endDate, hiloMode) {
    const { data: clientIp } = useClientIp()

    // The main graph data api call.
    return useQuery({
        retry: false,
        queryKey: buildCacheKey(station.id, startDate, endDate, hiloMode),
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_GRAPH_URL, {
                    signal,
                    start_date: startDate,
                    end_date: endDate,
                    hilo_mode: hiloMode,
                    station_id: station.id,
                    ip: clientIp ?? 'unknown',
                    app_version: import.meta.env.VITE_APP_VERSION,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message)
                        Sentry.captureException(error.message)
                    }
                    throw error
                })
        },
        staleTime: 10_000,
        gcTime: 10_000,
    })
}
