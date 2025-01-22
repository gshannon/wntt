import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export default function useLatestData() {
    const { data, error } = useQuery({
        retry: false,
        queryKey: ['latest'],
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_LATEST_URL, {
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        staleTime: 60_000 * 5, // keep it fresh for 5 minutes
        gcTime: 60_000 * 5, // gcTime should be >= staleTime in case they move off the page and return
    })
    return { data, error }
}
