import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { buildCacheKey } from './utils'
import * as storage from './storage'

export default function useGraphData(station, startDate, endDate, hiloMode) {
    const mainStore = storage.getMainStorage()
    // The main graph data api call.
    return useQuery({
        retry: false,
        queryKey: buildCacheKey(station.id, startDate, endDate, hiloMode),
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_GRAPH_URL, {
                    signal,
                    uid: mainStore.uid,
                    session: mainStore.session,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: station.id,
                    start: startDate,
                    end: endDate,
                    hilo: hiloMode,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError') {
                        console.error(
                            error.message,
                            error.response?.status,
                            error.response?.data?.detail
                        )
                    }
                    throw error
                })
        },
        staleTime: 10_000,
        gcTime: 10_000,
    })
}
