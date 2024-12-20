import { useEffect, useState } from 'react'
import axios from 'axios'
import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import {
    addDays,
    DefaultMapCenter,
    DefaultMapZoom,
    DefaultNumDays,
    EpqsUrl,
    stringify,
    getLocalStorage,
    setLocalStorage,
    Page,
} from './utils'
import Glossary from './Glossary'
import { AppContext } from './AppContext'
import { useCache } from './useCache'

export default function Control(props) {
    const page = props.page
    const gotoPage = props.gotoPage

    /* 
    Start & end dates are strings in format mm/dd/yyyy with 0-padding.  See utils.stringify.
    Javascript new Date() returns a date/time in the local time zone, so users should get the 
    right date whatever timezone they're in. 
    */
    const defaultStart = stringify(new Date())
    const defaultEnd = stringify(addDays(defaultStart, DefaultNumDays - 1))
    const datesStorage = getLocalStorage('dates', true)
    const mainStorage = getLocalStorage('main', false)
    const [startDate, setStartDate] = useState(datesStorage?.start ?? defaultStart)
    const [endDate, setEndDate] = useState(datesStorage?.end ?? defaultEnd)
    const [markerElevation, setMarkerElevation] = useState(mainStorage?.markerElevation)
    const [customElevation, setCustomElevation] = useState(mainStorage?.customElevation ?? null)
    const [mapType, setMapType] = useState(mainStorage?.mapType ? mainStorage?.mapType : 'basic')
    const [markerLocation, setMarkerLocation] = useState(mainStorage?.markerLocation)
    const [mapCenter, setMapCenter] = useState(mainStorage?.mapCenter || DefaultMapCenter)
    const [zoom, setZoom] = useState(mainStorage?.zoom ? mainStorage?.zoom : DefaultMapZoom)

    useCache(page) // make sure cache isn't getting too big

    const setDateStorage = (start, end) => {
        setLocalStorage(
            'dates',
            {
                start: start,
                end: end,
            },
            true
        )
    }

    useEffect(() => {
        setLocalStorage(
            'main',
            {
                customElevation: customElevation,
                markerLocation: markerLocation,
                markerElevation: markerElevation,
                mapCenter: mapCenter,
                mapType: mapType,
                zoom: zoom,
            },
            false
        )
    }, [customElevation, markerLocation, markerElevation, mapCenter, mapType, zoom])

    useEffect(() => {
        setDateStorage(startDate, endDate)
    }, [startDate, endDate])

    const setDateRange = (startDate, endDate) => {
        setStartDate(startDate)
        setEndDate(endDate)
    }

    useEffect(() => {
        const convert = (navd88) => navd88 + parseFloat(import.meta.env.VITE_NAVD88_MLLW_CONVERSION)
        // We only fetch elevation if markerLocation is set and markerElevation is not set.
        // That avoids a superfluous lookup during mount, when both values are set from the previous
        // session, which is the only time this code is executed when markerElevation is already known.
        if (markerLocation && !markerElevation) {
            // prettier-ignore
            const url = EpqsUrl + '?x=' + markerLocation.lng + '&y=' + markerLocation.lat + 
                '&units=Feet&wkid=4326&includeDate=False'
            axios
                .get(url)
                .then((response) => {
                    const navd88_feet = parseFloat(response.data.value)
                    // We get the value in NAVD88 feet, so must convert to MLLW. Then
                    // round it down to 1 digit of precision. Note calling toFixed turns it into a string!
                    setMarkerElevation(Number(convert(navd88_feet).toFixed(1)))
                })
                .catch((err) => {
                    //setError(err);
                    console.error(err)
                })
        }
    }, [markerLocation, markerElevation])

    return (
        <AppContext.Provider
            value={{
                gotoPage: gotoPage,
                startDate: startDate,
                endDate: endDate,
                setDateRange: setDateRange,
                customElevation: customElevation,
                setCustomElevation: setCustomElevation,
                mapType: mapType,
                setMapType: setMapType,
                markerLocation: markerLocation,
                setMarkerLocation: setMarkerLocation,
                mapCenter: mapCenter,
                setMapCenter: setMapCenter,
                markerElevation: markerElevation,
                setMarkerElevation: setMarkerElevation,
                zoom: zoom,
                setZoom: setZoom,
            }}>
            {page === Page.Home && <Home />}
            {page === Page.Graph && <Graph />}
            {page === Page.Map && <Map />}
            {page === Page.About && <About />}
            {page === Page.Glossary && <Glossary />}
        </AppContext.Provider>
    )
}
