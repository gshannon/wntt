import './css/Map.css'
import { useMemo, useRef, useContext, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Tooltip as LeafletTooltip } from 'react-leaflet'
import { Form } from 'react-bootstrap'
import BarLoader from 'react-spinners/BarLoader'
import Container from 'react-bootstrap/Container'
import Table from 'react-bootstrap/Table'
import { Col, Row } from 'react-bootstrap'
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import { YellowPin, RedPin } from './MarkerIcon'
import Button from 'react-bootstrap/Button'
import AddressPopup from './AddressPopup'
import { MapBounds, MaxCustomElevation, Page } from './utils'
import { AppContext } from './AppContext'
import Tutorial from './Tutorial'
import { getData } from './tutorials/map'

const WellsStationLocation = {
    lat: '43.320089',
    lng: '-70.563442',
}

const MinZoom = 8
const MaxZoom = 18

export default function Map() {
    const appContext = useContext(AppContext)

    const [showAddressPopup, setShowAddressPopup] = useState(false)
    const [showTut, setShowTut] = useState(false)
    const markerRef = useRef(null)

    const addtoGraph = () => {
        appContext.setCustomElevation(appContext.markerElevation)
        appContext.gotoPage(Page.Graph) // start tracking elevation, goto graph
    }

    const openMap = {
        attrib: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    }
    const satelliteMap = {
        attrib: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    }
    const mapTile = appContext.mapType === 'basic' ? openMap : satelliteMap

    const setAddressMarker = (latlng) => {
        appContext.setMarkerLocation(latlng)
        appContext.setMarkerElevation(null) // the old elevation is invalid now
        appContext.setMapCenter(latlng)
    }
    const removeMarker = () => {
        appContext.setMarkerLocation(null)
        appContext.setMarkerElevation(null)
        appContext.setCustomElevation(null)
    }

    const handleChange = (event) => {
        appContext.setMapType(event.target.value)
    }

    const markerEventHandlers = useMemo(
        () => ({
            dragend() {
                const marker = markerRef.current
                if (marker != null) {
                    appContext.setMarkerLocation(marker.getLatLng())
                    appContext.setMarkerElevation(null) // the old elevation is invalid now
                }
            },
        }),
        [appContext]
    )

    const MapClickHandler = () => {
        useMapEvents({
            click: (e) => {
                appContext.setMarkerLocation(e.latlng)
                appContext.setMarkerElevation(null)
            },
            zoomend: (e) => {
                appContext.setZoom(e.target.getZoom())
            },
            dragend: (e) => {
                appContext.setMapCenter(e.target.getCenter())
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
        useMap().setView(appContext.mapCenter, appContext.zoom)
    }

    return (
        <Container>
            <Row className='py-2'>
                <Col xs={4} className='d-flex justify-content-center align-items-center'>
                    <Table>
                        <tbody>
                            <tr>
                                <td>Latitude:</td>
                                <td>
                                    {appContext.markerLocation
                                        ? appContext.markerLocation.lat.toFixed(5) + ' º'
                                        : '-'}
                                </td>
                            </tr>
                            <tr>
                                <td>Longitude:</td>
                                <td>
                                    {appContext.markerLocation
                                        ? appContext.markerLocation.lng.toFixed(5) + ' º'
                                        : '-'}
                                </td>
                            </tr>
                            <tr>
                                <td>Elevation:</td>
                                <td>
                                    {appContext.markerElevation ? (
                                        appContext.markerElevation + ' ft MLLW'
                                    ) : appContext.markerLocation ? (
                                        <BarLoader loading={true} color={'blue'} />
                                    ) : (
                                        '-'
                                    )}
                                </td>
                            </tr>
                        </tbody>
                    </Table>
                </Col>
                <Col xs={4} className='align-self-center'>
                    <Row>
                        <Col className='text-center'>
                            <OverlayTrigger
                                overlay={
                                    <Tooltip id='id-set-button'>
                                        Add or replace your custom elevation to the graph and return
                                        to the Graph.
                                    </Tooltip>
                                }>
                                <Button
                                    variant='custom-primary'
                                    className='m-2'
                                    onClick={() => addtoGraph()}
                                    disabled={
                                        !appContext.markerElevation ||
                                        appContext.markerElevation > MaxCustomElevation ||
                                        appContext.markerElevation === appContext.customElevation
                                    }>
                                    Add to Graph
                                </Button>
                            </OverlayTrigger>
                            <OverlayTrigger
                                overlay={
                                    <Tooltip id='id-set-button'>
                                        Remove your custom marker from the map and the graph.
                                    </Tooltip>
                                }>
                                <Button
                                    variant='custom-primary'
                                    className='m-2'
                                    onClick={() => removeMarker()}
                                    disabled={!appContext.markerLocation}>
                                    Remove&nbsp;Marker
                                </Button>
                            </OverlayTrigger>
                        </Col>
                    </Row>
                    <Row>
                        <Col className='text-center fw-bold'>Map Style</Col>
                    </Row>
                    <Row>
                        <Col xs={4} className='offset-2'>
                            <Form.Check
                                inline
                                type='radio'
                                label='Basic'
                                value='basic'
                                checked={appContext.mapType === 'basic'}
                                onChange={handleChange}
                            />
                        </Col>
                        <Col xs={4}>
                            <Form.Check
                                inline
                                type='radio'
                                label='Satellite'
                                value='sat'
                                checked={appContext.mapType === 'sat'}
                                onChange={handleChange}
                            />
                        </Col>
                    </Row>
                </Col>
                <Col xs={4} className='d-flex justify-content-center align-items-center'>
                    <Row>
                        <Col className='map-vertical-buttons'>
                            <OverlayTrigger
                                overlay={
                                    <Tooltip id='id-set-button'>
                                        Find a location by entering a physical address.
                                    </Tooltip>
                                }>
                                <a href='#' onClick={() => setShowAddressPopup(true)}>
                                    Address&nbsp;Lookup
                                </a>
                            </OverlayTrigger>
                            <OverlayTrigger
                                overlay={
                                    <Tooltip id='id-set-button'>Return to the Graph page.</Tooltip>
                                }>
                                <a
                                    href='#'
                                    className='my-1'
                                    onClick={() => appContext.gotoPage(Page.Graph)}>
                                    Return&nbsp;to Graph
                                </a>
                            </OverlayTrigger>
                            <OverlayTrigger
                                trigger='hover'
                                overlay={
                                    <Tooltip id='id-set-button'>
                                        Open the Map page tutorial in a popup window.
                                    </Tooltip>
                                }>
                                <Button
                                    variant='primary'
                                    className='my-1'
                                    onClick={() => setShowTut(true)}>
                                    Map Tutorial
                                </Button>
                            </OverlayTrigger>
                        </Col>
                    </Row>
                </Col>
            </Row>
            <Row className='justify-content-center mt-1'>
                <MapContainer
                    center={appContext.mapCenter}
                    maxBounds={MapBounds}
                    zoom={appContext.zoom}
                    minZoom={MinZoom}
                    maxZoom={MaxZoom}
                    className='map-container'>
                    <ChangeView center={appContext.mapCenter} zoom={appContext.zoom} />
                    <TileLayer attribution={mapTile.attrib} url={mapTile.url} />
                    <MapClickHandler />
                    <Marker draggable={false} position={WellsStationLocation} icon={YellowPin}>
                        <LeafletTooltip
                            permanent
                            opacity={0.75}
                            direction={'right'}
                            offset={[30, -27]}>
                            Wells Tide Gauge
                        </LeafletTooltip>
                    </Marker>
                    {appContext.markerLocation && (
                        <Marker
                            draggable={true}
                            position={appContext.markerLocation}
                            icon={RedPin}
                            eventHandlers={markerEventHandlers}
                            ref={markerRef}>
                            <LeafletTooltip
                                permanent
                                opacity={0.75}
                                direction={'right'}
                                offset={[30, -27]}>
                                Custom: {appContext.markerElevation}
                            </LeafletTooltip>
                        </Marker>
                    )}
                </MapContainer>
            </Row>
            {showAddressPopup && (
                <AddressPopup setAddressMarker={setAddressMarker} onClose={onModalClose} />
            )}
            {showTut && <Tutorial onClose={onModalClose} data={getData()} title='Map Tutorial' />}
        </Container>
    )
}
