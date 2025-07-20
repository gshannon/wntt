import { useQuery } from '@tanstack/react-query'
import { useClientIp } from './useClientIp'
import { buildCacheKey } from './utils'
import { getDailyLocalStorage, setDailyLocalStorage } from './localStorage'
import axios from 'axios'

export default function useGraphData(startDate, endDate, hiloMode) {
    // Using useQuery here so we can have dependent queries.
    const ourVersion = import.meta.env.VITE_BUILD_NUM
    const oneMinute = 60_000

    const { clientIp, ipError } = useClientIp()

    // Compare our version to the version on the server and force a reload if they don't match.
    // This prevents clients from becoming stale.
    const { data: version, error: verError } = useQuery({
        queryKey: ['version'],
        queryFn: async () => {
            // Using a fake parameter in the url here to defeat any caching
            const resp = await axios.get(`/signature.json?${Date.now()}`)
            const json = await resp.data
            if (json.version !== ourVersion) {
                console.warn(
                    `${new Date().toLocaleTimeString()} : update required, latest: ${
                        json.version
                    }, ours: ${ourVersion}`
                )
                const daily = getDailyLocalStorage('misc-daily') ?? {}
                setDailyLocalStorage('misc-daily', { ...daily, upgraded: true })
                window.location.reload()
            }
            return json.version
        },
        staleTime: oneMinute,
        gcTime: oneMinute,
    })

    if (verError) {
        console.error(verError)
    }

    // The main graph data api call.
    const { isPending, data, error } = useQuery({
        retry: false,
        queryKey: buildCacheKey(startDate, endDate),
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_GRAPH_URL, {
                start_date: startDate,
                end_date: endDate,
                hilo_mode: hiloMode,
                ip: clientIp ?? 'unknown',
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        // Query is dependent, so if reload is forced it happens before this fetch, and we always have the IP
        // IP is not critical to proceed, but we do want to wait until both queries have returned.
        enabled: !!version && (!!clientIp || !!ipError),
        // I want to avoid memory building with lots of old queries lying around, so setting gcTime low.
        // But allow longer fresh period. As long as they spend less than gcTime on other pages between
        // hitting the graph page, no refetch is needed, as gc timer is reset when you return to graph
        // and stale timer is still running.
        staleTime: 10_000,
        gcTime: 1_000,
    })

    return { isPending, data, error }
}
