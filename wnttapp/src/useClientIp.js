import { useQuery } from '@tanstack/react-query'
import { ClientIpUrl } from './utils'

export default function useClientIp() {
    const oneMinute = 60_000
    const oneHour = oneMinute * 60

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

    return { clientIp, ipError }
}

export { useClientIp }
