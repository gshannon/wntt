import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useClientIp } from './useClientIp'

export default function useLatestData() {
    const oneMinute = 60_000
    const { clientIp, ipError } = useClientIp()

    const { data, error } = useQuery({
        retry: false,
        queryKey: ['latest'],
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_LATEST_URL, {
                ip: clientIp ?? 'unknown',
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        enabled: !!clientIp || !!ipError,
        staleTime: oneMinute * 5,
        gcTime: oneMinute * 5, // gcTime should be >= staleTime in case they move off the page and return
    })
    return { data, error }
}
