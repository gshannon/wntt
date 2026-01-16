import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

export default function useAddressLookup(search) {
    const ctx = useContext(AppContext)
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
                    uid: ctx.userId,
                    version: import.meta.env.VITE_APP_VERSION,
                    search: encoded,
                })
                .then((res) => {
                    return { lat: res.data.lat ?? null, lng: res.data.lng ?? null }
                })
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message, error.response?.data?.detail)
                    }
                    throw error
                })
        },
        staleTime: 0,
        cacheTime: 0,
        gcTime: 0,
    })
}
