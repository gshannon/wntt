import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

// Fetch station selection data from the server, and keep it cached for the app lifetime.
export default function useStationSelection(enabled) {
    const ctx = useContext(AppContext)
    return useQuery({
        enabled: enabled,
        queryKey: ['station-selection'],
        retry: false,
        // Prevent it ever refetching after an error. User must reload.
        refetchInterval: false,
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_STATION_SELECTION_URL, {
                    signal,
                    bid: ctx.browserId,
                    version: import.meta.env.VITE_APP_VERSION,
                })
                .then((res) => {
                    return res.data
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
