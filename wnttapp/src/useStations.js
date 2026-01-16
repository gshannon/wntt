import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'
import Station from './Station'

// Fetch station selection data from the server, and keep it cached for the app lifetime.
export default function useStations() {
    const ctx = useContext(AppContext)
    return useQuery({
        queryKey: ['station-all'],
        retry: false,
        // Prevent it ever refetching after an error. User must reload.
        refetchInterval: false,
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_STATIONS_URL, {
                    signal,
                    uid: ctx.userId,
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
                    if (error.name !== 'CanceledError' && error.status != NotAcceptable) {
                        console.log(error.message, error.response?.data?.detail)
                    }
                    throw error
                })
        },
        staleTime: Infinity,
        gcTime: Infinity,
    })
}
