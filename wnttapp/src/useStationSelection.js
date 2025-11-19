import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import useClientIp from './useClientIp'

// Fetch station selection data from the server, and keep it cached for the app lifetime.
export default function useStationSelection(enabled) {
    const { data: clientIp } = useClientIp()
    return useQuery({
        enabled: enabled,
        queryKey: ['station-selection'],
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
                    if (error.name !== 'CanceledError') {
                        console.log(error)
                    }
                    throw error
                })
        },
        staleTime: 'static',
    })
}
