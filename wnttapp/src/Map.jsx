/* eslint-disable */
import './css/Map.css'
import { useEffect, useEffectEvent, useMemo, useRef, useContext, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Tooltip as LeafletTooltip } from 'react-leaflet'
import { Form } from 'react-bootstrap'
import BarLoader from 'react-spinners/BarLoader'
import Container from 'react-bootstrap/Container'
import { Col, Row } from 'react-bootstrap'
import { RedPinIcon } from './MarkerIcon'
import Button from 'react-bootstrap/Button'
import { AppContext } from './AppContext'
import * as mu from './mapUtils'
import * as storage from './storage'
import useElevationData from './useElevationData'
import ErrorBlock from './ErrorBlock'
import AddressForm from './AddressForm'

const WaterStationEmoji = '\u{1F53B}'
const WeatherStationEmoji = '\u{1F536}'

export default function Map({ onMapClose, saveMapRef }) {
    const ctx = useContext(AppContext)

    const storedOptions = storage.getPermanentStorage(ctx.station.id)
    const stationOptions = ctx.station.stationOptionsWithDefaults(storedOptions)

    // Pending values are used when user clicks on the map or finds by address, before they add it to the graph.
    const [pendingMarkerLocation, setPendingMarkerLocation] = useState(null)
    const [pendingElevationNav, setPendingElevationNav] = useState(null)
    const [mapType, setMapType] = useState(stationOptions.mapType)
    const mapTile = mapType === 'basic' ? mu.openMap : mu.satelliteMap
    const [mapCenter, setMapCenter] = useState(stationOptions.mapCenter)
    const [zoom, setZoom] = useState(stationOptions.zoom)

    const markerRef = useRef(null)
    const mapRef = useRef(null)

    // If they've selected a new location or done address lookup, get the elevation.
    const {
        isLoading,
        data: elevation,
        error: queryError,
    } = useElevationData(pendingMarkerLocation)

    if (elevation != null && elevation !== pendingElevationNav) {
        setPendingElevationNav(elevation)
        setMapCenter(pendingMarkerLocation) // recenter on looked up location
        // TODO: Consider zooming in also, but only after address lookup, not after map click/drag.
    }

    const addtoGraph = () => {
        ctx.onCustomElevationSet(pendingElevationNav, pendingMarkerLocation)
        resetPending()
        onMapClose()
    }

    const cancel = () => {
        resetPending()
        onMapClose()
    }

    const removeMarker = () => {
        ctx.onCustomElevationSet(null, null)
        resetPending()
        onMapClose()
    }

    const resetPending = () => {
        setPendingElevationNav(null)
        setPendingMarkerLocation(null)
    }

    const handleMapTypeToggle = (event) => {
        setMapType(mapType === 'basic' ? 'sat' : 'basic')
    }

    // Set the map marker location lat/long, but limit to 7 digits of precision, which is good to ~1cm.
    const setMarkerLatLng = (latlngStrs) => {
        if (latlngStrs) {
            const { lat, lng } = latlngStrs
            setPendingMarkerLocation({ lat: Number(lat.toFixed(7)), lng: Number(lng.toFixed(7)) })
        }
    }

    const markerEventHandlers = useMemo(
        () => ({
            dragend() {
                const marker = markerRef.current
                if (marker != null) {
                    setMarkerLatLng(marker.getLatLng())
                }
            },
        }),
        [],
    )

    const MapClickHandler = () => {
        useMapEvents({
            click: (e) => {
                setMarkerLatLng(e.latlng)
            },
            zoomend: (e) => {
                setZoom(e.target.getZoom())
            },
            dragend: (e) => {
                setMapCenter(e.target.getCenter())
            },
        })
        return null
    }

    // Keep the local storage of permanent station options in sync.
    // We own all the values except the 2 custom* fields, so we leave them alone.
    const onValueChange = useEffectEvent(() => {
        const storedOptions = storage.getPermanentStorage(ctx.station.id)
        const curOptions = ctx.station.stationOptionsWithDefaults(storedOptions)
        storage.setPermanentStorage(ctx.station.id, {
            ...curOptions,
            mapCenter,
            mapType,
            zoom,
        })
    })

    useEffect(() => {
        onValueChange()
    }, [mapCenter, mapType, zoom])

    useEffect(() => {
        if (mapRef.current) {
            saveMapRef(mapRef.current)
        }
    }, [mapRef, saveMapRef])

    const toolTipCfg = mu.buildTooltipLocations(ctx.station)

    const stationMarker = (key, loc, symbol, title) => {
        return (
            <Marker draggable={false} position={loc} icon={mu.stationIcon(symbol)}>
                <LeafletTooltip
                    permanent
                    opacity={0.65}
                    direction={toolTipCfg[key]['dir']}
                    offset={toolTipCfg[key]['offset']}>
                    {title}
                </LeafletTooltip>
            </Marker>
        )
    }

    // A way to recenter and apply zoom when those things change. The MapContainer is not recreated on rerender
    // so when this child component is mounted it can reset the view settings to current values.
    const ChangeView = () => {
        useMap().setView(mapCenter, zoom)
    }

    const ErrorSection = () => {
        if (queryError) {
            return (
                <Row>
                    <Col className='d-flex justify-content-center text-warning bg-dark'>
                        <ErrorBlock error={queryError} />
                    </Col>
                </Row>
            )
        } else {
            return <></>
        }
    }

    return (
        <Container>
            <Row className='py-2'>
                <Col className='col-6 px-0 d-flex flex-column justify-content-center align-items-center'>
                    <div className='instructions-container text-start mx-2'>
                        {
                            <Instructions
                                isLoading={isLoading}
                                pendingElevationNav={pendingElevationNav}
                            />
                        }
                    </div>
                    <div className='text-center'>
                        <Button
                            variant='custom-primary'
                            className='mt-2 mb-0 mx-1'
                            onClick={() => addtoGraph()}
                            disabled={
                                !pendingElevationNav ||
                                pendingElevationNav > ctx.station.maxCustomElevationNavd88()
                            }>
                            Graph
                        </Button>
                        <Button
                            variant='custom-primary'
                            className='mt-2 mb-0 mx-1'
                            onClick={() => removeMarker()}
                            disabled={!ctx.customElevationNav}>
                            Clear
                        </Button>
                        <Button
                            variant='custom-primary'
                            className='mt-2 mb-0 mx-1'
                            onClick={() => cancel()}>
                            Cancel
                        </Button>
                    </div>
                </Col>
                <Col className='px-0 align-self-center flex-column'>
                    <div className='address-container'>
                        <AddressForm
                            setPendingMarkerLocation={setPendingMarkerLocation}
                            station={ctx.station}
                        />
                    </div>
                    <div className='mx-0'>
                        <Form.Switch
                            type='switch'
                            label='Satellite View'
                            checked={mapType === 'sat'}
                            onChange={handleMapTypeToggle}
                        />
                    </div>
                </Col>
            </Row>
            <ErrorSection />
            <Row className='justify-content-center mt-1'>
                <MapContainer
                    center={mapCenter}
                    boundsOptions={{ maxZoom: mu.MaxZoom }}
                    zoom={zoom}
                    ref={mapRef}>
                    <TileLayer attribution={mapTile.attrib} url={mapTile.url} />
                    <ChangeView center={mapCenter} zoom={zoom} />
                    <MapClickHandler />
                    {stationMarker('wq', ctx.station.swmpLocation, WaterStationEmoji, 'Tide Gauge')}
                    {stationMarker(
                        'met',
                        ctx.station.weatherLocation,
                        WeatherStationEmoji,
                        'Weather Station',
                    )}
                    {(pendingMarkerLocation || ctx.customLocation) && (
                        <Marker
                            draggable={true}
                            position={pendingMarkerLocation || ctx.customLocation}
                            icon={RedPinIcon}
                            eventHandlers={markerEventHandlers}
                            ref={markerRef}>
                            <LeafletTooltip
                                permanent
                                opacity={0.75}
                                direction={'right'}
                                offset={[30, -27]}>
                                Custom Location:{' '}
                                {isLoading ?
                                    '-'
                                :   ctx.station.navd88ToMllw(
                                        pendingElevationNav || ctx.customElevationNav,
                                    ) + ' ft'
                                }
                            </LeafletTooltip>
                        </Marker>
                    )}
                </MapContainer>
            </Row>
        </Container>
    )
}

function Instructions({ pendingElevationNav, isLoading }) {
    const ctx = useContext(AppContext)
    const Cleartext = () => {
        return (
            <>
                Click <b>Clear</b> to stop showing a custom location on the graph.
            </>
        )
    }
    if (isLoading) {
        return <BarLoader loading={true} color={'green'} />
    }

    if (pendingElevationNav) {
        const elevMllw = ctx.station.navd88ToMllw(pendingElevationNav)
        if (pendingElevationNav > ctx.station.maxCustomElevationNavd88()) {
            return (
                <>
                    <p>
                        The selected location is at <b>{elevMllw} ft</b>, which is above the maximum
                        elevation to be included on the graph (
                        {ctx.station.maxCustomElevationMllw()} ft).
                    </p>
                    {ctx.customElevationNav && <Cleartext />}
                </>
            )
        } else {
            return (
                <>
                    <p>
                        The selected location is at <b>{elevMllw} ft</b>.{' '}
                    </p>
                    Click the <b>Graph</b> button to add this to the graph as &quot;Custom
                    Location&quot;. {ctx.customElevationNav && <Cleartext />}
                </>
            )
        }
    } else if (ctx.customElevationNav) {
        return (
            <>
                <p>
                    Your chosen elevation is{' '}
                    <b>{ctx.station.navd88ToMllw(ctx.customElevationNav)} ft</b>. You may change it
                    by <b>clicking on the map</b>, <b>dragging the pin</b>, or{' '}
                    <b>looking up an address</b>.
                </p>{' '}
                Click <b>Clear</b> to stop showing a custom location on the graph.
            </>
        )
    } else {
        return (
            <>
                <b>Click on the map</b> or <b>look up by address</b> to find a location whose
                elevation can be included on the graph.
            </>
        )
    }
}
