import { useQuery } from '@tanstack/react-query'
import { GeocodeUrl } from './utils'
import axios from 'axios'

const isInBounds = (mapBounds, lat, lon) => {
    const minLat = Math.min(mapBounds[0][0], mapBounds[1][0])
    const minLon = Math.min(mapBounds[0][1], mapBounds[1][1])
    const maxLat = Math.max(mapBounds[0][0], mapBounds[1][0])
    const maxLon = Math.max(mapBounds[0][1], mapBounds[1][1])
    return lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon
}

export default function useGeocode(station, search) {
    const lookupValue = search + ' USA'
    const encoded = lookupValue.replace(/\s+/gi, '+')
    const url = GeocodeUrl + '/search?q=' + encoded + '&api_key=' + import.meta.env.VITE_GEOCODE_KEY

    const { isPending, data, error } = useQuery({
        retry: false,
        enabled: !!search,
        queryKey: ['geocode'],
        queryFn: async () => {
            const res = await axios.get(url).then((res) => {
                if (res.data !== undefined && res.data[0] !== undefined) {
                    const lat = res.data[0].lat
                    const lon = res.data[0].lon
                    if (!isInBounds(station.mapBounds, lat, lon)) {
                        throw new Error('That address does not appear to be in the local area')
                    }
                    return res.data[0]
                } else {
                    throw new Error('That appears to be an invalid address')
                }
            })
            return res
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
    return { isPending, data, error }
}
