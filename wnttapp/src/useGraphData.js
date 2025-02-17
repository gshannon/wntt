import { useQuery } from '@tanstack/react-query'
import { ClientIpUrl } from './utils'
import axios from 'axios'

// Using useQuery here so we can have dependent queries.

export default function useGraphData(startDate, endDate) {
    const ourVersion = import.meta.env.VITE_BUILD_NUM
    const oneHour = 60_000 * 60

    const { data: clientIp, error: ipError } = useQuery({
        queryKey: ['clientip'],
        queryFn: async () => {
            const resp = await fetch(ClientIpUrl)
            const data = await resp.json()
            return data.ip
        },
        // We don't need this to run very often -- it's just informational for now.
        staleTime: oneHour,
        gcTime: oneHour,
    })

    if (ipError) {
        console.error(ipError)
    }

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
                window.location.reload()
            }
            return json.version
        },
        staleTime: oneHour,
        gcTime: oneHour,
    })

    if (verError) {
        console.error(verError)
    }

    // The main graph data api call.
    const { isPending, data, error } = useQuery({
        retry: false,
        queryKey: ['graph', startDate + ':' + endDate],
        queryFn: async () => {
            const res = await axios.post(import.meta.env.VITE_API_GRAPH_URL, {
                start_date: startDate,
                end_date: endDate,
                ip: clientIp ?? 'unknown',
                time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                app_version: import.meta.env.VITE_BUILD_NUM,
            })
            return res.data
        },
        // Query is dependent, so if reload is forced it happens before this fetch, and we always have the IP
        // Neither IP nor version is critical to continue if either fail.
        enabled: (!!version || !!verError) && (!!clientIp || !!ipError),
        // I want to avoid memory building with lots of old queries lying around, so setting gcTime low.
        // But allow longish fresh period. As long as they spend less than gcTime on other pages between
        // hitting the graph page, no refetch is needed, as gc timer is reset when you return to graph
        // and stale timer is still running.
        staleTime: 60_000 * 5,
        gcTime: 30_000,
    })

    return { isPending, data, error }
}
