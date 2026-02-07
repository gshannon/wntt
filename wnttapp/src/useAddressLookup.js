import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import * as storage from './storage'

export default function useAddressLookup(search) {
    const mainStore = storage.getMainStorage()
    const address = search + ' USA'
    const encoded = address.replace(/\s+/gi, '+')
    const subKey = search ?? 'X'

    return useQuery({
        retry: false,
        enabled: !!search,
        queryKey: ['geocode', subKey],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_ADDRESS_URL, {
                    signal,
                    uid: mainStore.uid,
                    session: mainStore.session,
                    version: import.meta.env.VITE_APP_VERSION,
                    search: encoded,
                })
                .then((res) => {
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError') {
                        console.error(
                            error.message,
                            error.response?.status,
                            error.response?.data?.detail,
                        )
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
