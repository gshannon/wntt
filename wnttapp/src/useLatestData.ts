import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as storage from './storage'
import { handleQueryError } from './queryError'
import type Station from './Station'
import { LatestConditions } from './types'
import { isSyzygyCode } from './Syzygy'

export default function useLatestData(station: Station) {
    const mainStore = storage.getMainStorage()

    return useQuery({
        retry: false,
        queryKey: [station.id, 'latest'],
        queryFn: async ({ signal }) => {
            return await axios
                .post(
                    import.meta.env.VITE_API_LATEST_URL,
                    {
                        uid: mainStore.uid,
                        session: mainStore.session,
                        started: mainStore.started,
                        version: import.meta.env.VITE_APP_VERSION,
                        station_id: station.id,
                    },
                    { signal },
                )
                .then((res): LatestConditions => {
                    const d = res.data
                    return {
                        ...d,
                        phase: isSyzygyCode(d.phase) ? d.phase : null,
                        next_phase: isSyzygyCode(d.next_phase) ? d.next_phase : null,
                    }
                })
                .catch((error) =>
                    handleQueryError(error, {
                        operation: import.meta.env.VITE_API_LATEST_URL,
                        mainStore,
                    }),
                )
        },
        staleTime: 300_000, // 5 minutes.
        gcTime: 300_000, // gcTime should be >= staleTime in case they move off the page and return
    })
}
