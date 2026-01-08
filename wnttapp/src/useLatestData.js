import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import * as Sentry from '@sentry/react'
import { NotAcceptable } from './utils'
import { AppContext } from './AppContext'
import { useContext } from 'react'

export default function useLatestData(station) {
    const ctx = useContext(AppContext)

    const { isLoading, data, error } = useQuery({
        retry: false,
        queryKey: [station.id, 'latest'],
        queryFn: async ({ signal }) => {
            return await axios
                .post(import.meta.env.VITE_API_LATEST_URL, {
                    signal,
                    bid: ctx.browserId,
                    version: import.meta.env.VITE_APP_VERSION,
                    station_id: station.id,
                })
                .then((res) => res.data)
                .catch((error) => {
                    if (error.name !== 'CanceledError' && error.status !== NotAcceptable) {
                        console.log(error.message)
                        Sentry.captureException(error.message)
                    }
                    throw error
                })
        },
        staleTime: 30_000, // 30 seconds. Allows for frequent checks without hammering the server.
        gcTime: 30_000, // gcTime should be >= staleTime in case they move off the page and return
    })

    return { isLoading, data, error }
}
