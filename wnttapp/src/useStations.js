import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import Station from './Station'
import * as storage from './storage'

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
                .post(import.meta.env.VITE_API_STATIONS_URL, {
                    signal,
                    uid: mainStore.uid,
                    session: mainStore.session,
                    version: import.meta.env.VITE_APP_VERSION,
                })
                .then((res) => {
                    const asArray = Object.entries(res.data).map(([id, stn]) => [
                        id,
                        Station.fromJson(id, stn),
                    ])
                    return Object.fromEntries(asArray)
                })
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
        staleTime: Infinity,
        gcTime: Infinity,
    })
}
