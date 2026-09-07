import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import Station, { type StationJson } from './Station'
import * as storage from './storage'
import { handleQueryError } from './queryError'

// Fetch station selection data from the server, and keep it cached for the app lifetime.
export default function useStations() {
    const mainStore = storage.getMainStorage()

    return useQuery({
        queryKey: ['station-all'],
        retry: false,
        // Prevent it ever refetching after an error. User must reload.
        refetchInterval: false,
        queryFn: async ({ signal }) => {
            return await axios
                .post<{ stations: Record<string, StationJson>; banner: string }>(
                    import.meta.env.VITE_API_STATIONS_URL,
                    {
                        version: import.meta.env.VITE_APP_VERSION,
                        // For logging...
                        uid: mainStore.uid ?? 'NONE',
                        session: mainStore.session,
                        started: mainStore.started,
                        screenWidth: window.innerWidth,
                    },
                    { signal },
                )
                .then((res) => {
                    const asArray = Object.entries(res.data.stations).map(([id, stn]) => [
                        id,
                        Station.fromJson(id, stn),
                    ])
                    return { stations: Object.fromEntries(asArray), banner: res.data.banner }
                })
                .catch((error) =>
                    handleQueryError(error, {
                        operation: import.meta.env.VITE_API_STATIONS_URL,
                        mainStore,
                    }),
                )
        },
        staleTime: Infinity,
        gcTime: Infinity,
    })
}
