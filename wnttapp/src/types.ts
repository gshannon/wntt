// Shared domain types used across modules.
import type { ReactNode } from 'react'
import { SyzygyCode } from './Syzygy'

export type LatLng = { lat: number; lng: number }

// Navigation callback threaded through the component tree (see App.tsx).
export type GotoPage = (page: number, returnPage?: number | null) => void

// The start/end date picker control state (Graph <-> GetDates).
export interface StartDateCtl {
    min: Date
    start: Date
    max: Date
}
export interface EndDateCtl {
    min: Date
    end: Date
    max: Date
}

// One slide of the Map/Graph walkthrough (see src/tutorials/*).
export interface TutorialSlide {
    img: string
    cls?: string
    render: () => ReactNode
}

// The /latest/ endpoint payload (current conditions). All fields nullable —
// the API returns null for anything not currently available.
export interface LatestConditions {
    temp: number | null
    tide: number | null
    tide_dir: string | null
    tide_time: string | null
    next_high_tide: number | null
    next_tide_dt: string | null
    next_tide_surge: number | null
    surge_time: string | null
    wind_speed: number | null
    wind_gust: number | null
    wind_dir_deg: number | null
    wind_time: string | null
    phase: SyzygyCode | null
    phase_dt: string | null
    next_phase: SyzygyCode | null
    next_phase_dt: string | null
}

// [[south-west lat, lng], [north-east lat, lng]] — a Leaflet-style bounds pair.
export type MapBounds = [[number, number], [number, number]]

// The graph API returns columnar data: one row per dimension, each row an
// array whose first entry is an ISO datetime string and the rest numbers
// (or null for gaps). See wnttapi graph payload.
export type BlobRow = (string | number | null)[]
export type Blob = BlobRow[]

// A moon/sun event as delivered in the graph payload's syzygy data.
export interface SyzygyEvent {
    code: SyzygyCode
    real_dt: string
}

// The /graph/ endpoint payload consumed by EChart / ChartBuilder.
export interface GraphData {
    dimensions: string[]
    blob: Blob
    syzygy?: SyzygyEvent[] | null
    subtitle?: string
    highest_annual_prediction: number
}
