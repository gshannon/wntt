import img01 from '../images/gtut01.jpg'
import img02 from '../images/gtut02.jpg'
import img03 from '../images/gtut03.jpg'
import img04 from '../images/gtut04.jpg'
import img05 from '../images/gtut05.jpg'
import img06 from '../images/gtut06.jpg'
import img07 from '../images/gtut07.jpg'
import toggle from '../images/toggle.jpg'
import download from '../images/download.jpg'
import zoomArea from '../images/zoom-area.jpg'
import panMode from '../images/pan-mode.jpg'
import reset from '../images/reset.jpg'
import zoomMode from '../images/zoom-mode.jpg'
import panning from '../images/panning.jpg'
import set from '../images/set.jpg'
import { MaxCustomElevation } from '../utils'

export const getData = () => {
    return [
        {
            img: img01,
            cls: 'pic-width-70-90',
            render: () => {
                return (
                    <span>
                        Here you are seeing a graph of past and predicted tide levels for the
                        selected date range, as measured from the Wells Harbor. As you move your
                        mouse over the graph, you will see popup text showing the values for each
                        point on the graph.
                    </span>
                )
            },
        },
        {
            img: img06,
            render: () => {
                return (
                    <span>
                        You may change the start and end dates at any time, then click Refresh to
                        update the graph.
                    </span>
                )
            },
        },
        {
            img: img07,
            render: () => {
                return (
                    <span>
                        Or click the large left and right arrows to scroll back or forward in time.
                    </span>
                )
            },
        },
        {
            img: img02,
            render: () => {
                return (
                    <span>
                        Match the line colors to the key on the right to see what each line means.
                        You can find full explanations on the <b>Glossary</b> page.
                    </span>
                )
            },
        },
        {
            img: toggle,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>Click any data line to toggle its visibility.</span>
            },
        },
        {
            img: img03,
            cls: 'pic-width-70-90',
            render: () => {
                return (
                    <span>
                        For dates in the past, you see Predicted Tide, Observed Tide, and wind data.
                        Recorded Storm Surge is the difference between Predicted Tide and Observed
                        Tide, and is an indication of how much the weather affected the astronomical
                        tide predictions.
                    </span>
                )
            },
        },
        {
            img: img04,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        For several days in the the future, you will see the Projected Storm Tide
                        value, which is the sum of the Predicted Tide (astronomical) and the
                        Projected Storm Surge. This surge value comes from an experimental project
                        by NOAA, and is the best known estimate for the Wells harbor, updated every
                        6 hours.
                    </span>
                )
            },
        },
        {
            img: img05,
            render: () => {
                return (
                    <span>
                        For any date range, there are flat lines at the top which represent key
                        benchmarks: Record Tide, Highest Annual Predicted Tide and Mean High Water.
                        If you have set a custom elevation, that is shown also. These help you
                        visualize the potential risk posed by the tides.
                    </span>
                )
            },
        },
        {
            img: set,
            render: () => {
                return (
                    <span>
                        To add a custom elevation to the graph, navigate to the Map page with the
                        Set button, or the Map tab on the menu bar, and follow the instructions
                        there. This will allow you to compare the elevation of your home, business
                        or other point of interest to the predicted tides. Only elevations of{' '}
                        {MaxCustomElevation} feet or less are will be added to the graph, to avoid
                        skewing the graph scale.
                    </span>
                )
            },
        },
        {
            img: download,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>Click the camera icon to download a printable graph image file.</span>
            },
        },
        {
            img: zoomArea,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        To zoom into the graph, click and drag over an area, or use the scroll wheel
                        or touch pad.
                    </span>
                )
            },
        },
        {
            img: panMode,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>When zoomed, you can click the Pan Mode button to pan.</span>
            },
        },
        {
            img: panning,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>In Pan mode, click and drag up or down in the graph to pan.</span>
            },
        },
        {
            img: zoomMode,
            cls: 'pic-width-60-90',
            render: () => {
                return <span>In Pan mode, you can click the Zoom button to zoom more.</span>
            },
        },
        {
            img: reset,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        To reset the graph to its original state, double-click anywhere in the graph
                        or click the Reset icon.
                    </span>
                )
            },
        },
    ]
}
