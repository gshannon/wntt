import { useQueryClient } from '@tanstack/react-query'
import { Page } from './utils'

// Custom hook to prevent the graph query cache from excessive memory pressure.
// If the number of graph queries in the cache exceeds a certain threshhold,
// we just clear them all.

const minSaneMax = 1
const maxSaneMax = 8
const defaultMax = 3

export const useCache = (page) => {
    const queryClient = useQueryClient()
    let maxQueries = import.meta.env.VITE_MAX_GRAPH_QUERIES_IN_CACHE ?? defaultMax
    maxQueries = Math.max(maxQueries, minSaneMax)
    maxQueries = Math.min(maxQueries, maxSaneMax)

    if (page === Page.Graph) {
        const cache = queryClient.getQueryCache()
        const graphQueries = cache
            .findAll()
            .filter((q) => q.queryKey[0] === 'graph' && q.state?.data?.timeline !== undefined)

        const cnt = graphQueries.length

        if (cnt > maxQueries) {
            console.log(`Max graph queries is ${maxQueries}. Found ${cnt}, removing them.`)
            queryClient.removeQueries({ queryKey: ['graph'], exact: false })
        }
    }
}
