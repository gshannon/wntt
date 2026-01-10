import { useQuery } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'
import axios from 'axios'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

export default function useAddressLookup(search) {
    const ctx = useContext(AppContext)
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
                    bid: ctx.browserId,
                    version: import.meta.env.VITE_APP_VERSION,
                    search: encoded,
                })
                .then((res) => {
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message, error.response?.data?.detail)
                        Sentry.captureException(error.message)
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
