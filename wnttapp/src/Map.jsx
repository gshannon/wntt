import './css/Map.css'
import { useEffect, useEffectEvent, useMemo, useRef, useContext, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Tooltip as LeafletTooltip } from 'react-leaflet'
import { RecenterIcon1, RecenterIcon2, CloseBox } from './Icons'
import Overlay from './Overlay'
import Modal from 'react-bootstrap/Modal'
import { Form } from 'react-bootstrap'
import BeatLoader from 'react-spinners/BeatLoader'
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

export default function Map({ onMapClose }) {
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
    const closeRef = useRef(null)

    // If they've selected a new location or done address lookup, get the elevation.
    const {
        isLoading,
        data: elevation,
        error: queryError,
    } = useElevationData(pendingMarkerLocation)

    if (!isLoading && !!elevation && elevation !== pendingElevationNav) {
        setPendingElevationNav(elevation)
        setMapCenter(pendingMarkerLocation) // recenter on looked up location
        // TODO: Consider zooming in also, but only after address lookup, not after map click/drag.
    }

    const addtoGraph = () => {
        ctx.onCustomElevationSet(pendingElevationNav, pendingMarkerLocation)
        clearPending()
        onMapClose()
    }

    const cancel = () => {
        clearPending()
        onMapClose()
    }

    const removeMarker = () => {
        ctx.onCustomElevationSet(null, null)
        clearPending()
        onMapClose()
    }

    const clearPending = () => {
        setPendingElevationNav(null)
        setPendingMarkerLocation(null)
    }

    const handleMapTypeToggle = () => {
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

    const handleRecenterToMarker = () => {
        setMapCenter(pendingMarkerLocation || ctx.customLocation)
    }

    const handleRecenterToDefault = () => {
        setMapCenter(ctx.station.swmpLocation)
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

    // After initial render, we want to keep focus off the address field b/c on phones, that brings up the keyboard
    // and most people probably won't do address lookups, at least initially.
    useEffect(() => {
        if (closeRef.current) {
            closeRef.current.focus()
        }
    }, [])

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
        <Modal id='map-modal' show={true} size='xl' onHide={onMapClose}>
            <Modal.Body className='px-0 py-0'>
                <div>
                    <div className='close-box'>
                        <button ref={closeRef} onClick={onMapClose}>
                            <CloseBox />
                        </button>
                    </div>
                    <div className='header-grid'>
                        <div className='instructions-container px-2 py-2'>
                            {isLoading ?
                                <BeatLoader className='loading' loading={true} color={'green'} />
                            :   <div className='text-start mx-3'>
                                    {instructions(ctx, pendingElevationNav)}
                                </div>
                            }
                        </div>
                        <div className='map-address mx-2 my-1'>
                            <AddressForm
                                setPendingMarkerLocation={setPendingMarkerLocation}
                                station={ctx.station}
                            />
                        </div>
                        <div className='map-buttons py-1'>
                            <Button
                                variant='custom-primary'
                                onClick={() => addtoGraph()}
                                disabled={
                                    !pendingElevationNav ||
                                    pendingElevationNav > ctx.station.maxCustomElevationNavd88()
                                }>
                                Graph
                            </Button>
                            <Button
                                variant='custom-primary'
                                onClick={() => removeMarker()}
                                disabled={!ctx.customElevationNav}>
                                Clear
                            </Button>
                            <Button variant='custom-primary' onClick={() => cancel()}>
                                Cancel
                            </Button>
                        </div>
                        <div className='map-view pe-2'>
                            <Overlay
                                text='Center on marker'
                                contents={
                                    <button
                                        disabled={!pendingMarkerLocation && !ctx.customLocation}
                                        onClick={handleRecenterToMarker}>
                                        <RecenterIcon1 />
                                    </button>
                                }
                            />
                            <Overlay
                                text='Center on Tide Guage'
                                contents={
                                    <button onClick={handleRecenterToDefault}>
                                        <RecenterIcon2 />
                                    </button>
                                }
                            />
                            <Form.Switch
                                type='switch'
                                label='Satellite'
                                checked={mapType === 'sat'}
                                onChange={handleMapTypeToggle}
                            />
                        </div>
                    </div>

                    <ErrorSection />
                    <Row className='justify-content-center mt-0 mx-1 mx-sm-2'>
                        <MapContainer
                            center={mapCenter}
                            boundsOptions={{ maxZoom: mu.MaxZoom }}
                            zoom={zoom}>
                            <TileLayer attribution={mapTile.attrib} url={mapTile.url} />
                            <ChangeView center={mapCenter} zoom={zoom} />
                            <MapClickHandler />
                            {stationMarker(
                                'wq',
                                ctx.station.swmpLocation,
                                WaterStationEmoji,
                                'Tide Gauge',
                            )}
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
                </div>
            </Modal.Body>
        </Modal>
    )
}

const instructions = (ctx, pendingElevationNav) => {
    const cleartext = () => {
        return (
            <>
                Click <b>Clear</b> to stop showing a custom location on the graph.
            </>
        )
    }
    if (pendingElevationNav) {
        const elevMllw = ctx.station.navd88ToMllw(pendingElevationNav)
        if (pendingElevationNav > ctx.station.maxCustomElevationNavd88()) {
            return (
                <>
                    <p>
                        The selected location is at <b>{elevMllw} ft</b> MLLW, which is above the
                        maximum elevation to be included on the graph (
                        {ctx.station.maxCustomElevationMllw()} ft).
                    </p>
                    {ctx.customElevationNav && cleartext()}
                </>
            )
        } else {
            return (
                <>
                    <p>
                        The selected location is at <b>{elevMllw} ft</b> MLLW.{' '}
                    </p>
                    Click the <b>Graph</b> button to add this to the graph as &quot;Custom
                    Location&quot;. {ctx.customElevationNav && cleartext()}
                </>
            )
        }
    } else if (ctx.customElevationNav) {
        return (
            <>
                <p>
                    Your chosen elevation is{' '}
                    <b>{ctx.station.navd88ToMllw(ctx.customElevationNav)} ft</b> MLLW. You may
                    change it by <b>clicking on the map</b>, <b>dragging the pin</b>, or{' '}
                    <b>looking up an address</b>.
                </p>{' '}
                {cleartext()}
            </>
        )
    } else {
        return (
            <>
                <p>
                    <b>Click on the map</b> or <b>enter an address</b> to get the elevation of a
                    location.{' '}
                </p>
                You can then add that to the graph, and that can help you assess the flooding risk
                at that location.
            </>
        )
    }
}
