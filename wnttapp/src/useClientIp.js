import { useQuery } from '@tanstack/react-query'
import { ClientIpUrl } from './utils'

export default function useClientIp() {
    const { isLoading, data, error } = useQuery({
        queryKey: ['clientip'],
        queryFn: async ({ signal }) => {
            const resp = await fetch(ClientIpUrl, { signal })
            if (!resp.ok) {
                console.log(resp)
            }
            const data = await resp.json()
            return data.ip
        },
        staleTime: 'static',
    })
    return { isLoading, data, error }
}
