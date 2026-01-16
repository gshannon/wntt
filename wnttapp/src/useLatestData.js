import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

export default function useLatestData(station) {
    const ctx = useContext(AppContext)

    return useQuery({
        retry: false,
        queryKey: [station.id, 'latest'],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_LATEST_URL, {
                    signal,
                    uid: ctx.userId,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: station.id,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message, error.response?.data?.detail)
                    }
                    throw error
                })
        },
        staleTime: 30_000, // 30 seconds. Allows for frequent checks without hammering the server.
        gcTime: 30_000, // gcTime should be >= staleTime in case they move off the page and return
    })
}
