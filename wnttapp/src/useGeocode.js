import { useQuery } from '@tanstack/react-query'
import { GeocodeUrl } from './utils'
import axios from 'axios'

export default function useGeocode(station, search) {
    const lookupValue = search + ' USA'
    const encoded = lookupValue.replace(/\s+/gi, '+')
    const url = GeocodeUrl + '/search?q=' + encoded + '&api_key=' + import.meta.env.VITE_GEOCODE_KEY
    const subKey = search ?? 'X'

    const { isLoading, data, error } = useQuery({
        retry: false,
        enabled: !!search,
        queryKey: ['geocode', subKey],
        queryFn: async () => {
            const res = await axios
                .get(url, { timeout: 30000 })
                .then((res) => {
                    return { lat: res.data[0]?.lat ?? null, lng: res.data[0]?.lon ?? null }
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
