import img01 from '../images/mtut01.jpg'
import img02 from '../images/mtut02.jpg'
import img03 from '../images/mtut03.jpg'
import img04 from '../images/mtut04.jpg'
import img05 from '../images/mtut05.jpg'
import img05a from '../images/mtut05a.jpg'
import img06 from '../images/mtut06.jpg'
import img07 from '../images/mtut07.jpg'
import img08 from '../images/mtut08.jpg'
import { MaxCustomElevationMllw } from '../utils'

export const getData = () => {
    return [
        {
            img: img01,
            cls: 'pic-width-70-90',
            render: () => {
                return (
                    <span>
                        Here you have the opportunity to add the elevation of your home, business,
                        or place of interest to the graph. You&apos;ll do this by either finding the
                        location on the map through navigation, or by searching for an address. If
                        the elevation is less than {MaxCustomElevationMllw} feet MLLW, you can
                        choose to show it on the tide graph. (Higher elevations would lessen the
                        usefulness of the graph.) Let&apos;s go through the steps...
                    </span>
                )
            },
        },
        {
            img: img04,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>You can choose between a basic map, or a satellite image.</span>
            },
        },
        {
            img: img02,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        In the upper left corner there&apos;s a zoom control. Use this to zoom in or
                        out. The buttons will become disabled when you&apos;re reached the minimum
                        or maximum zoom level. You can also zoom with the scroll wheel or touch pad.
                    </span>
                )
            },
        },
        {
            img: img03,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        To pan, click and hold your mouse button, then move the mouse in the
                        direction you want to push the map.
                    </span>
                )
            },
        },
        {
            img: img07,
            render: () => {
                return (
                    <span>
                        One way to select a location is to search by address. Click on{' '}
                        <b>Address Lookup</b> and enter an address, including the street number and
                        town. Then click the <b>Search</b> button.
                    </span>
                )
            },
        },
        {
            img: img05,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        Another way is to pan and zoom inside the map, and click on the desired
                        spot. A blue marker will appear. To change it, you can just click somewhere
                        else, or you can drag the marker to a new location. Each time the marker
                        changes, the system will determine the latitude/longitude, then use that to
                        retrieve the elevation. When you are ready, if the elevation is less than{' '}
                        {MaxCustomElevationMllw} ft, you can click the <b>Add to Graph</b> button,
                        and you will be returned to the graph.
                    </span>
                )
            },
        },
        {
            img: img05a,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        The map can only be zoomed in so far and terrain variations can be difficult
                        to interpret from above. Since the resolution of the elevation data is 1
                        square meter on land, but up to 10 square meters in intertidal areas,
                        it&apos;s a good idea to try a few spots near the spot you are interested
                        in, and see how the elevations vary.
                    </span>
                )
            },
        },
        {
            img: img06,
            cls: 'pic-width-70-90',
            render: () => {
                return (
                    <span>
                        Now you can see your custom elevation on the graph, and you can compare it
                        to the past and predicted tide levels.
                    </span>
                )
            },
        },
        {
            img: img08,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        If you want to remove the location at any time, just navigate back to the
                        map page and click the <b>Remove Marker</b> button. If you want to use a
                        different location from the one that&apos;s already on the graph, move the
                        marker to a new location, and click <b>Add to Graph</b> again.
                    </span>
                )
            },
        },
    ]
}
