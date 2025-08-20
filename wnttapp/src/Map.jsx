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
import { YellowPin, RedPin } from './MarkerIcon'
import Button from 'react-bootstrap/Button'
import AddressPopup from './AddressPopup'
import { MapBounds, maxCustomElevationNavd88, navd88ToMllw, Page } from './utils'
import { AppContext } from './AppContext'
import Tutorial from './Tutorial'
import Overlay from './Overlay'
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
        appContext.setCustomElevationNav(appContext.markerElevationNav)
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
        appContext.setMarkerLatLng(latlng)
        appContext.setMarkerElevationNav(null) // the old elevation is invalid now
        appContext.setMapCenter(latlng)
    }
    const removeMarker = () => {
        appContext.setMarkerLatLng(null)
        appContext.setMarkerElevationNav(null)
        appContext.setCustomElevationNav(null)
    }

    const handleChange = (event) => {
        appContext.setMapType(event.target.value)
    }

    const markerEventHandlers = useMemo(
        () => ({
            dragend() {
                const marker = markerRef.current
                if (marker != null) {
                    appContext.setMarkerLatLng(marker.getLatLng())
                    appContext.setMarkerElevationNav(null) // the old elevation is invalid now
                }
            },
        }),
        [appContext]
    )

    const MapClickHandler = () => {
        useMapEvents({
            click: (e) => {
                appContext.setMarkerLatLng(e.latlng)
                appContext.setMarkerElevationNav(null)
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

    const elevationContent = () => {
        if (appContext.markerElevationNav) {
            return <>{navd88ToMllw(appContext.markerElevationNav) + ' ft MLLW'}</>
        } else if (appContext.markerElevationError) {
            return <>Error, please try again later.</>
        } else if (appContext.markerLocation) {
            return <BarLoader loading={true} color={'green'} />
        }
    }

    return (
        <Container>
            <Row className='py-2'>
                <Col className='px-0 d-flex justify-content-center align-items-center'>
                    <Table>
                        <tbody>
                            <tr>
                                <td>Latitude:</td>
                                <td className='nowrap'>
                                    {appContext.markerLocation
                                        ? appContext.markerLocation.lat.toFixed(6) + ' º'
                                        : '-'}
                                </td>
                            </tr>
                            <tr>
                                <td>Longitude:</td>
                                <td className='nowrap'>
                                    {appContext.markerLocation
                                        ? appContext.markerLocation.lng.toFixed(6) + ' º'
                                        : '-'}
                                </td>
                            </tr>
                            <tr>
                                <td>Elevation:</td>
                                <td>{elevationContent()}</td>
                            </tr>
                        </tbody>
                    </Table>
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
                                        className='m-2'
                                        onClick={() => addtoGraph()}
                                        disabled={
                                            !appContext.markerElevationNav ||
                                            appContext.markerElevationNav ===
                                                appContext.customElevationNav ||
                                            appContext.markerElevationNav >
                                                maxCustomElevationNavd88()
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
                                        className='m-2'
                                        onClick={() => removeMarker()}
                                        disabled={!appContext.markerLocation}>
                                        Remove Marker
                                    </Button>
                                }></Overlay>
                        </Col>
                    </Row>
                    <Row>
                        <Col className='text-center fw-bold'>Map Style</Col>
                    </Row>
                    <Row className='mx-1'>
                        <Col className='col-6 text-end'>
                            <Form.Check
                                inline
                                type='radio'
                                label='Basic'
                                value='basic'
                                checked={appContext.mapType === 'basic'}
                                onChange={handleChange}
                            />
                        </Col>
                        <Col className='col-6'>
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
                <Col className='d-flex justify-content-center align-items-center'>
                    <Row>
                        <Col className='map-vertical-buttons'>
                            <a href='#' onClick={() => setShowAddressPopup(true)}>
                                Address&nbsp;Lookup
                            </a>
                            <a
                                href='#'
                                className='my-1'
                                onClick={() => appContext.gotoPage(Page.Graph)}>
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
                                Elevation: {navd88ToMllw(appContext.markerElevationNav) ?? '-'}
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
