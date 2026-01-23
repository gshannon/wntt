import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import { EpqsUrl, roundTo } from './utils'

export default function useElevationData(pendingMarkerLocation) {
    // We want the key to be different so it doesn't use cached data from previous query.
    const subKey = pendingMarkerLocation
        ? `${pendingMarkerLocation.lat},${pendingMarkerLocation.lng}`
        : 'x'
    return useQuery({
        retry: false,
        enabled: !!pendingMarkerLocation,
        queryKey: ['marker', subKey],
        queryFn: async ({ signal }) => {
            return await axios
                // We'll allow 30 seconds to handle connection-related timeouts.
                // If it times out, we'll get code of "ECONNABORTED", message "timeout of xxx exceeded"
                .get(
                    `${EpqsUrl}?x=${pendingMarkerLocation.lng}&y=${pendingMarkerLocation.lat}` +
                        `&units=Feet&wkid=4326&includeDate=False`,
                    { timeout: 30000, signal }
                )
                .then((res) => {
                    return roundTo(parseFloat(res.data.value), 2)
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError') {
                        console.error(
                            error.message,
                            error.response?.status,
                            error.response?.data?.detail
                        )
                        // This endpoint is not part of our backend, so we'll log exceptions here.
                        Sentry.captureException(error)
                    }
                    throw error
                })
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
}
