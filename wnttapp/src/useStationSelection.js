import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import useClientIp from './useClientIp'
import { NotAcceptable } from './utils'

// Fetch station selection data from the server, and keep it cached for the app lifetime.
export default function useStationSelection(enabled) {
    const { data: clientIp } = useClientIp()
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
                    ip: clientIp ?? 'unknown',
                    app_version: import.meta.env.VITE_APP_VERSION,
                })
                .then((res) => {
                    return res.data
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status != NotAcceptable) {
                        console.log(error.message)
                        Sentry.captureException(error.message)
                    }
                    throw error
                })
        },
        staleTime: 'static',
    })
}
