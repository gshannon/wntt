import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import { HttpNotAcceptableCode } from './utils'
import * as storage from './storage'

export default function useAddressLookup(search, doLookup) {
    const mainStore = storage.getMainStorage()
    const address = search + ' USA'
    const encoded = address.replace(/\s+/gi, '+')
    const subKey = search ?? 'X'

    return useQuery({
        retry: false,
        enabled: doLookup && !!search,
        queryKey: ['geocode', subKey],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_ADDRESS_URL, {
                    signal,
                    uid: mainStore.uid,
                    session: mainStore.session,
                    started: mainStore.started,
                    version: import.meta.env.VITE_APP_VERSION,
                    search: encoded,
                })
                .then((res) => {
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
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
                            tags: { operation: import.meta.env.VITE_API_ADDRESS_URL },
                            user: {
                                uid: mainStore.uid,
                                session: mainStore.session,
                                started: mainStore.started,
                            },
                            extra: { search: encoded },
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
