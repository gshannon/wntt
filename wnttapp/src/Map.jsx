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
import AddressPopup from './AddressPopup'
import { Page, apiErrorResponse } from './utils'
import { AppContext } from './AppContext'
import Tutorial from './Tutorial'
import Overlay from './Overlay'
import { getData } from './tutorials/map'
import * as mu from './mapUtils'
import * as storage from './storage'
import useElevationData from './useElevationData'

const WaterStationEmoji = '\u{1F537}'
const WeatherStationEmoji = '\u{1F536}'
const NoaaStationEmoji = '\u{1F53B}'

export default function Map() {
    const ctx = useContext(AppContext)

    const stationOptions = mu.getStationOptions(ctx.station)

    // This is used when user clicks on the map, while we look up the elevation.
    const [pendingMarkerLocation, setPendingMarkerLocation] = useState(null)
    const [markerLocation, setMarkerLocation] = useState(stationOptions.markerLocation)
    const [markerElevationNav, setMarkerElevationNav] = useState(stationOptions.markerElevationNav)
    const [mapType, setMapType] = useState(stationOptions.mapType)
    const [mapCenter, setMapCenter] = useState(stationOptions.mapCenter)
    const [zoom, setZoom] = useState(stationOptions.zoom)

    const [showAddressPopup, setShowAddressPopup] = useState(false)
    const [showTut, setShowTut] = useState(false)
    const markerRef = useRef(null)

    const { isLoading, data, error: queryError } = useElevationData(pendingMarkerLocation)

    if (data) {
        setMarkerLocation(pendingMarkerLocation)
        setPendingMarkerLocation(null)
        setMarkerElevationNav(data)
    }

    const addtoGraph = () => {
        ctx.setCustomElevationNav(markerElevationNav)
        ctx.gotoPage(Page.Graph) // start tracking elevation, goto graph
    }

    const mapTile = mapType === 'basic' ? mu.openMap : mu.satelliteMap

    const removeMarker = () => {
        ctx.setCustomElevationNav(null)
        setMarkerLocation(null)
        setMarkerElevationNav(null)
        setPendingMarkerLocation(null)
    }

    const handleMapTypeChange = (event) => {
        setMapType(event.target.value)
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
        []
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

    const onModalClose = () => {
        setShowAddressPopup(false)
        setShowTut(false)
    }

    const elevationLabelContent = () => {
        if (isLoading) {
            return <BarLoader loading={true} color={'green'} />
        }
        if (markerElevationNav) {
            return <>{ctx.station.navd88ToMllw(markerElevationNav) + ' ft MLLW'}</>
        }
        return <>-</>
    }

    // Keep the local storage of permanent station options in sync.
    // We own all the values except customElevationNav, so we leave that alone.
    const onValueChange = useEffectEvent(() => {
        const curOptions = mu.getStationOptions(ctx.station)
        storage.setStationPermanentStorage(ctx.station.id, {
            ...curOptions,
            markerLocation,
            markerElevationNav,
            mapCenter,
            mapType,
            zoom,
        })
    })

    useEffect(() => {
        onValueChange()
    }, [markerLocation, markerElevationNav, mapCenter, mapType, zoom])

    const toolTipCfg = mu.buildTooltipLocations(ctx.station)

    const stationMarker = (key, loc, symbol, title, name, id) => {
        return (
            <Marker draggable={false} position={loc} icon={mu.stationIcon(symbol)}>
                <LeafletTooltip
                    permanent
                    opacity={0.65}
                    direction={toolTipCfg[key]['dir']}
                    offset={toolTipCfg[key]['offset']}>
                    {title}
                    <br />
                    {name} ({id})
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
                        {apiErrorResponse(queryError)}
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
                <Col className='px-0 d-flex justify-content-center align-items-center'>
                    <div className='loc-container'>
                        <div className='loc-label'>Latitude:</div>
                        <div className='loc-data nowrap'>
                            {markerLocation ? markerLocation.lat.toFixed(6) + ' º' : '-'}
                        </div>
                        <div className='loc-label'>Longitude:</div>
                        <div className='loc-data nowrap'>
                            {markerLocation ? markerLocation.lng.toFixed(6) + ' º' : '-'}
                        </div>
                        <div className='loc-label'>Elevation:</div>
                        <div className='loc-data'>{elevationLabelContent()}</div>
                    </div>
                </Col>
                <Col className='px-0 align-self-center'>
                    <Row className='mx-0'>
                        <Col className='col-12 text-center'>
                            <Overlay
                                text='Add or replace your custom elevation to the graph and return
                                        to the Graph.'
                                placement='top'
                                contents={
                                    <Button
                                        variant='custom-primary'
                                        className='mt-2 mb-0 mx-1'
                                        onClick={() => addtoGraph()}
                                        disabled={
                                            !markerElevationNav ||
                                            markerElevationNav === ctx.customElevationNav ||
                                            markerElevationNav >
                                                ctx.station.maxCustomElevationNavd88()
                                        }>
                                        Add to Graph
                                    </Button>
                                }></Overlay>
                            <Overlay
                                text='Remove your custom marker from the map and the graph.'
                                placement='top'
                                contents={
                                    <Button
                                        variant='custom-primary'
                                        className='mt-2 mb-0'
                                        onClick={() => removeMarker()}
                                        disabled={!markerLocation}>
                                        Remove Marker
                                    </Button>
                                }></Overlay>
                        </Col>
                    </Row>
                    <Row className='mx-0'>
                        <Col className='text-center fw-bold'>Map Style</Col>
                    </Row>
                    <Row className='mx-0'>
                        <Col className='col-6 text-end'>
                            <Form.Check
                                inline
                                type='radio'
                                label='Basic'
                                value='basic'
                                checked={mapType === 'basic'}
                                onChange={handleMapTypeChange}
                            />
                        </Col>
                        <Col className='col-6'>
                            <Form.Check
                                inline
                                type='radio'
                                label='Satellite'
                                value='sat'
                                checked={mapType === 'sat'}
                                onChange={handleMapTypeChange}
                            />
                        </Col>
                    </Row>
                </Col>
                <Col className='d-flex justify-content-center align-items-center'>
                    <Row>
                        <Col className='map-vertical-buttons'>
                            <a href='#' onClick={() => setShowAddressPopup(true)}>
                                Address&nbsp;Lookup
                            </a>
                            <a href='#' className='my-1' onClick={() => ctx.gotoPage(Page.Graph)}>
                                Return&nbsp;to Graph
                            </a>
                            <Overlay
                                text='Open the Map page tutorial in a popup window.'
                                placement='top'
                                contents={
                                    <Button
                                        variant='primary'
                                        className='my-1'
                                        onClick={() => setShowTut(true)}>
                                        Map Tutorial
                                    </Button>
                                }></Overlay>
                        </Col>
                    </Row>
                </Col>
            </Row>
            <ErrorSection />
            <Row className='justify-content-center mt-1'>
                <MapContainer
                    center={mapCenter}
                    maxBounds={ctx.station.mapBounds}
                    zoom={zoom}
                    minZoom={mu.MinZoom}
                    maxZoom={mu.MaxZoom}
                    className='map-container'>
                    <ChangeView center={mapCenter} zoom={zoom} />
                    <TileLayer attribution={mapTile.attrib} url={mapTile.url} />
                    <MapClickHandler />
                    {stationMarker(
                        'wq',
                        ctx.station.swmpLocation,
                        WaterStationEmoji,
                        'Water Quality Station:',
                        ctx.station.waterStationName,
                        ctx.station.id
                    )}
                    {stationMarker(
                        'met',
                        ctx.station.weatherLocation,
                        WeatherStationEmoji,
                        'Meteorological Station:',
                        ctx.station.weatherStationName,
                        ctx.station.weatherStationId
                    )}
                    {stationMarker(
                        'noaa',
                        ctx.station.noaaStationLocation,
                        NoaaStationEmoji,
                        'NOAA Station:',
                        ctx.station.noaaStationName,
                        ctx.station.noaaStationId
                    )}
                    {markerLocation && (
                        <Marker
                            draggable={true}
                            position={markerLocation}
                            icon={RedPinIcon}
                            eventHandlers={markerEventHandlers}
                            ref={markerRef}>
                            <LeafletTooltip opacity={0.75} direction={'right'} offset={[30, -27]}>
                                Custom Elevation:{' '}
                                {markerElevationNav
                                    ? ctx.station.navd88ToMllw(markerElevationNav)
                                    : '-'}
                            </LeafletTooltip>
                        </Marker>
                    )}
                </MapContainer>
            </Row>
            {showAddressPopup && (
                <AddressPopup
                    setPendingMarkerLocation={setPendingMarkerLocation}
                    onClose={onModalClose}
                    station={ctx.station}
                />
            )}
            {showTut && (
                <Tutorial onClose={onModalClose} data={getData(ctx.station)} title='Map Tutorial' />
            )}
        </Container>
    )
}
