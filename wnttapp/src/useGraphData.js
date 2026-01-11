import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { buildCacheKey, NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

export default function useGraphData(station, startDate, endDate, hiloMode) {
    const ctx = useContext(AppContext)

    // The main graph data api call.
    return useQuery({
        retry: false,
        queryKey: buildCacheKey(station.id, startDate, endDate, hiloMode),
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_GRAPH_URL, {
                    signal,
                    bid: ctx.browserId,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: station.id,
                    start: startDate,
                    end: endDate,
                    hilo: hiloMode,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message, error.response?.data?.detail)
                    }
                    throw error
                })
        },
        staleTime: 10_000,
        gcTime: 10_000,
    })
}
