import './css/Map.css'
import { useMemo, useRef, useContext, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Tooltip as LeafletTooltip } from 'react-leaflet'
import { Form } from 'react-bootstrap'
import BarLoader from 'react-spinners/BarLoader'
import Container from 'react-bootstrap/Container'
import { Col, Row } from 'react-bootstrap'
import { RedPinIcon } from './MarkerIcon'
import Button from 'react-bootstrap/Button'
import AddressPopup from './AddressPopup'
import { Page } from './utils'
import { AppContext } from './AppContext'
import Tutorial from './Tutorial'
import Overlay from './Overlay'
import { getData } from './tutorials/map'

const MinZoom = 8
const MaxZoom = 18
const WaterStationEmoji = '\u{1F537}'
const WeatherStationEmoji = '\u{1F536}'
const NoaaStationEmoji = '\u{1F53B}'

const stationIcon = (emoji) => {
    return L.divIcon({
        className: 'my-icon',
        html: emoji,
        iconAnchor: [8, 16],
    })
}
// console.log(WaterStationIcon)

export default function Map() {
    const ctx = useContext(AppContext)

    const [showAddressPopup, setShowAddressPopup] = useState(false)
    const [showTut, setShowTut] = useState(false)
    const markerRef = useRef(null)

    const addtoGraph = () => {
        ctx.setCustomElevationNav(ctx.markerElevationNav)
        ctx.gotoPage(Page.Graph) // start tracking elevation, goto graph
    }

    const openMap = {
        attrib: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    }
    const satelliteMap = {
        attrib: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    }
    const mapTile = ctx.mapType === 'basic' ? openMap : satelliteMap

    const setAddressMarker = (latlng) => {
        ctx.setMarkerLatLng(latlng)
        ctx.setMarkerElevationNav(null) // the old elevation is invalid now
        ctx.setMapCenter(latlng)
    }
    const removeMarker = () => {
        ctx.setMarkerLatLng(null)
        ctx.setMarkerElevationNav(null)
        ctx.setCustomElevationNav(null)
    }

    const handleChange = (event) => {
        ctx.setMapType(event.target.value)
    }

    const markerEventHandlers = useMemo(
        () => ({
            dragend() {
                const marker = markerRef.current
                if (marker != null) {
                    ctx.setMarkerLatLng(marker.getLatLng())
                    ctx.setMarkerElevationNav(null) // the old elevation is invalid now
                }
            },
        }),
        [ctx]
    )

    const MapClickHandler = () => {
        useMapEvents({
            click: (e) => {
                ctx.setMarkerLatLng(e.latlng)
                ctx.setMarkerElevationNav(null)
            },
            zoomend: (e) => {
                ctx.setZoom(e.target.getZoom())
            },
            dragend: (e) => {
                ctx.setMapCenter(e.target.getCenter())
            },
        })
        return null
    }

    const onModalClose = () => {
        setShowAddressPopup(false)
        setShowTut(false)
    }

    // A way to recenter and apply zoom when those things change. The MapContainer is not recreated on rerender
    // so when this child component is mounted it can reset the view settings to current values.
    const ChangeView = () => {
        useMap().setView(ctx.mapCenter, ctx.zoom)
    }

    const elevationLabelContent = () => {
        if (ctx.markerElevationNav) {
            return <>{ctx.station.navd88ToMllw(ctx.markerElevationNav) + ' ft MLLW'}</>
        }
        if (ctx.markerElevationError) {
            return <>Error, please try again later.</>
        }
        if (ctx.markerLocation) {
            return <BarLoader loading={true} color={'green'} />
        }
        return <>-</>
    }

    const stationMarker = (loc, symbol, title, name, id) => {
        return (
            <Marker draggable={false} position={loc} icon={stationIcon(symbol)}>
                <LeafletTooltip opacity={0.75} direction={'right'} offset={[10, -15]}>
                    {title}
                    <br />
                    {name} ({id})
                </LeafletTooltip>
            </Marker>
        )
    }

    return (
        <Container>
            <Row className='py-2'>
                <Col className='px-0 d-flex justify-content-center align-items-center'>
                    <div className='loc-container'>
                        <div className='loc-label'>Latitude:</div>
                        <div className='loc-data nowrap'>
                            {ctx.markerLocation ? ctx.markerLocation.lat.toFixed(6) + ' º' : '-'}
                        </div>
                        <div className='loc-label'>Longitude:</div>
                        <div className='loc-data nowrap'>
                            {ctx.markerLocation ? ctx.markerLocation.lng.toFixed(6) + ' º' : '-'}
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
                                            !ctx.markerElevationNav ||
                                            ctx.markerElevationNav === ctx.customElevationNav ||
                                            ctx.markerElevationNav >
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
                                        disabled={!ctx.markerLocation}>
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
                                checked={ctx.mapType === 'basic'}
                                onChange={handleChange}
                            />
                        </Col>
                        <Col className='col-6'>
                            <Form.Check
                                inline
                                type='radio'
                                label='Satellite'
                                value='sat'
                                checked={ctx.mapType === 'sat'}
                                onChange={handleChange}
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
            <Row className='justify-content-center mt-1'>
                <MapContainer
                    center={ctx.mapCenter}
                    maxBounds={ctx.station.mapBounds}
                    zoom={ctx.zoom}
                    minZoom={MinZoom}
                    maxZoom={MaxZoom}
                    className='map-container'>
                    <ChangeView center={ctx.mapCenter} zoom={ctx.zoom} />
                    <TileLayer attribution={mapTile.attrib} url={mapTile.url} />
                    <MapClickHandler />
                    {stationMarker(
                        ctx.station.swmpLocation,
                        WaterStationEmoji,
                        'Water Quality Station:',
                        ctx.station.waterStationName,
                        ctx.station.id
                    )}
                    {stationMarker(
                        ctx.station.weatherLocation,
                        WeatherStationEmoji,
                        'Meteorological Station:',
                        ctx.station.weatherStationName,
                        ctx.station.weatherStationId
                    )}
                    {stationMarker(
                        ctx.station.noaaStationLocation,
                        NoaaStationEmoji,
                        'NOAA Station:',
                        ctx.station.noaaStationName,
                        ctx.station.noaaStationId
                    )}
                    {ctx.markerLocation && (
                        <Marker
                            draggable={true}
                            position={ctx.markerLocation}
                            icon={RedPinIcon}
                            eventHandlers={markerEventHandlers}
                            ref={markerRef}>
                            <LeafletTooltip
                                permanent
                                opacity={0.75}
                                direction={'right'}
                                offset={[30, -27]}>
                                Custom Elevation:{' '}
                                {ctx.markerElevationNav
                                    ? ctx.station.navd88ToMllw(ctx.markerElevationNav)
                                    : '-'}
                            </LeafletTooltip>
                        </Marker>
                    )}
                </MapContainer>
            </Row>
            {showAddressPopup && (
                <AddressPopup
                    setAddressMarker={setAddressMarker}
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
