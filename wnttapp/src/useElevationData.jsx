import { useQuery } from '@tanstack/react-query'
import { EpqsUrl, roundTo } from './utils'
import axios from 'axios'

export default function useElevationData(pendingMarkerLocation) {
    // We want the key to be different so it doesn't use cached data from previous query.
    const subKey = pendingMarkerLocation
        ? `${pendingMarkerLocation.lat},${pendingMarkerLocation.lng}`
        : 'x'
    const { data, error, isLoading } = useQuery({
        retry: false,
        enabled: !!pendingMarkerLocation,
        queryKey: ['marker', subKey],
        queryFn: async () => {
            const res = await axios
                // We'll allow 30 seconds to handle connection-related timeouts.
                // If it times out, we'll get code of "ECONNABORTED", message "timeout of xxx exceeded"
                .get(
                    `${EpqsUrl}?x=${pendingMarkerLocation.lng}&y=${pendingMarkerLocation.lat}` +
                        `&units=Feet&wkid=4326&includeDate=False`,
                    { timeout: 30000 }
                )
                .then((res) => {
                    return roundTo(parseFloat(res.data.value), 2)
                })
                .catch((error) => {
                    // It'll be canceled if user clicks another point before this finishes, so
                    // that's not considered an error, and nothing to do.
                    if (error.name === 'CanceledError') {
                        console.log('CANCELED')
                        return null
                    }
                    throw error
                })
            return res
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })

    return { data, error, isLoading }
}
