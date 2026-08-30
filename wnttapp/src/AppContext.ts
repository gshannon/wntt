import { createContext } from 'react'
import type Station from './Station'
import type { GotoPage, LatLng } from './types'

// This is in its own file instead of in App.jsx to quiet the
// "Fast refresh only works when a file only exports components" warning from vite.

export interface AppContextValue {
    sessionId: string
    stationsData: Record<string, Station> | undefined
    station: Station | null
    onStationSelected: (stationId: string) => void
    gotoPage: GotoPage
    customElevationNav: number | null | undefined
    onCustomElevationSet: (navd88Value: number | null, location: LatLng | null) => void
    customLocation: LatLng | null | undefined
    fatalError: Error | null
    special: boolean
    toggleSpecial: () => void
}

export const AppContext = createContext<AppContextValue>({} as AppContextValue)
