import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import { HttpNotAcceptableCode, EpqsUrl, roundTo } from './utils'
import * as storage from './storage'

export default function useElevationData(pendingMarkerLocation) {
    const mainStore = storage.getMainStorage()
    // We want the key to be different so it doesn't use cached data from previous query.
    const subKey =
        pendingMarkerLocation ? `${pendingMarkerLocation.lat},${pendingMarkerLocation.lng}` : 'x'
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
                    { timeout: 30000, signal },
                )
                .then((res) => {
                    return roundTo(parseFloat(res.data.value), 2)
                })
                .catch((error) => {
                    if (
                        error.name !== 'CanceledError' &&
                        error.response?.status !== HttpNotAcceptableCode
                    ) {
                        console.error(
                            error.message,
                            error.response?.status,
                            error.response?.data?.detail,
                        )
                        Sentry.captureException(error, {
                            tags: { operation: error.request.responseURL },
                            user: {
                                uid: mainStore.uid,
                                session: mainStore.session,
                                started: mainStore.started,
                            },
                        })
                    }
                    throw error
                })
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
}
