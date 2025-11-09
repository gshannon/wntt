import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export default function useGeocode(search) {
    const address = search + ' USA'
    const encoded = address.replace(/\s+/gi, '+')
    const subKey = search ?? 'X'

    const { isLoading, data, error } = useQuery({
        retry: false,
        enabled: !!search,
        queryKey: ['geocode', subKey],
        queryFn: async () => {
            const res = await axios
                .post(import.meta.env.VITE_API_ADDRESS_URL, {
                    search: encoded,
                    app_version: import.meta.env.VITE_BUILD_NUM,
                })
                .then((res) => {
                    console.log(res)
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
                })
                .catch((error) => {
                    // It'll be canceled if user clicks another point before this finishes, so
                    // that's not considered an error, and nothing to do.
                    if (error.name === 'CanceledError') {
                        console.log('CANCELED')
                        return null
                    }
                    console.log(`with [${subKey}]: `, error)
                    throw error
                })
            return res
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
    return { isLoading, data, error }
}
