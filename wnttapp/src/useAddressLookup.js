import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export default function useAddressLookup(search) {
    const address = search + ' USA'
    const encoded = address.replace(/\s+/gi, '+')
    const subKey = search ?? 'X'

    const { isLoading, data, error } = useQuery({
        retry: false,
        enabled: !!search,
        queryKey: ['geocode', subKey],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_ADDRESS_URL, {
                    signal,
                    search: encoded,
                    app_version: import.meta.env.VITE_BUILD_NUM,
                })
                .then((res) => {
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError') {
                        console.log(error)
                    }
                    throw error
                })
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
    return { isLoading, data, error }
}
