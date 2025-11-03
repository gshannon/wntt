import { useQuery } from '@tanstack/react-query'
import { ClientIpUrl } from './utils'

export default function useClientIp() {
    const { data: clientIp, error: ipError } = useQuery({
        queryKey: ['clientip'],
        queryFn: async () => {
            const resp = await fetch(ClientIpUrl)
            const data = await resp.json()
            return data.ip
        },
        // This could only change if they switch VPNs maybe
        staleTime: 'static',
    })

    if (ipError) {
        console.error(ipError)
    }

    return { clientIp, ipError }
}

export { useClientIp }
