import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { buildCacheKey, stringify } from './utils'
import * as storage from './storage'
import { handleQueryError } from './queryError'
import type Station from './Station'

export default function useGraphData(
    station: Station,
    startDate: Date,
    endDate: Date,
    hiloMode: boolean,
    special: boolean,
) {
    const mainStore = storage.getMainStorage()
    const permStore = storage.getPermanentStorage(station.id)
    const startDateStr = stringify(startDate)
    const endDateStr = stringify(endDate)
    // The main graph data api call.
    return useQuery({
        retry: false,
        queryKey: buildCacheKey(station.id, startDateStr, endDateStr, hiloMode),
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_GRAPH_URL, {
                    signal,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: station.id,
                    start: startDateStr,
                    end: endDateStr,
                    hilo: hiloMode,
                    // These fields are for logging
                    uid: mainStore.uid ?? 'NONE',
                    session: mainStore.session,
                    started: mainStore.started,
                    screenWidth: window.innerWidth,
                    customNav: permStore.customElevationNav ?? null,
                    special: special,
                })
                .then((res) => res.data)
                .catch((error) =>
                    handleQueryError(error, {
                        operation: import.meta.env.VITE_API_GRAPH_URL,
                        mainStore,
                        extra: { start: startDateStr, end: endDateStr },
                    }),
                )
        },
        staleTime: 10_000,
        gcTime: 10_000,
    })
}
