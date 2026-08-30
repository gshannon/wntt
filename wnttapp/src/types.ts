// Shared domain types used across modules.

export type LatLng = { lat: number; lng: number }

// [[south-west lat, lng], [north-east lat, lng]] — a Leaflet-style bounds pair.
export type MapBounds = [[number, number], [number, number]]
