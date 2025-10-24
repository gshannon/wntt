import '../css/Graph.css'
import graphControl1 from '../images/graph-control-1.jpg'
import graphControl2 from '../images/graph-control-2.jpg'
import popup from '../images/graph-popup.jpg'

import img03 from '../images/gtut03.jpg'
import img04 from '../images/gtut04.jpg'
import img07 from '../images/gtut07.jpg'
import toggle from '../images/toggle.jpg'
import download from '../images/download.jpg'
import zoomArea from '../images/zoom-area.jpg'
import panMode from '../images/pan-mode.jpg'
import reset from '../images/reset.jpg'
import zoomMode from '../images/zoom-mode.jpg'
import panning from '../images/panning.jpg'
import elevation from '../images/elevation.jpg'
import { isSmallScreen, isTouchScreen } from '../utils'

export const getData = (station) => {
    const clickOrTap = isTouchScreen ? 'tap' : 'click'
    const clickOrTapCap = isTouchScreen ? 'Tap' : 'Click'
    return [
        {
            img: graphControl1,
            cls: 'pic-width-90',
            render: () => {
                return (
                    <span>
                        Here you are seeing a graph of past and predicted tide levels for the
                        selected date range, as measured from the Wells Harbor. To see other dates,
                        change the Start and/or End Date, then {clickOrTap} the <b>Refresh</b>{' '}
                        button. You can also {clickOrTap} <b>Reset</b> at any time to return to the
                        default date settings.
                    </span>
                )
            },
        },
        {
            img: graphControl2,
            cls: 'pic-width-90',
            render: () => {
                return (
                    <span>
                        You can turn on the <b>Highs/Lows</b> checkbox to see only the high and low
                        tides, and not the other values in between. On small screens, this option is
                        mandatory.
                    </span>
                )
            },
        },
        {
            img: img07,
            render: () => {
                return (
                    <span>
                        {clickOrTapCap} the large left and right arrows to scroll back or forward in
                        time.
                    </span>
                )
            },
        },
        {
            img: popup,
            cls: 'pic-width-60-90',
            render: () => {
                return (
                    <span>
                        When you {clickOrTap} on a data point, you&apos;ll see a popup that shows
                        the data values. All terms are defined in the <b>Glossary</b> page, which
                        you can reach from the <b>Help</b> menu.
                    </span>
                )
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
                        tide predictions. If you have set a custom elevation, that is shown also.
                        This helps you visualize the potential risk posed by the tides.
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
        ...(!isSmallScreen()
            ? [
                  {
                      img: toggle,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  In the legend, {clickOrTap} any data line to toggle its
                                  visibility.
                              </span>
                          )
                      },
                  },
              ]
            : []),
        {
            img: elevation,
            render: () => {
                return (
                    <span>
                        To add a custom elevation to the graph, navigate to the Map page with the
                        Edit button, or the Map tab on the menu bar, and follow the instructions
                        there. This will allow you to compare the elevation of your home, business
                        or other point of interest to the predicted tides. Only elevations less than{' '}
                        {station.maxCustomElevationMllw()} feet MLLW may be added to the graph, to
                        avoid skewing the graph scale.
                    </span>
                )
            },
        },
        ...(!isSmallScreen()
            ? [
                  {
                      img: download,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  {clickOrTapCap} the camera icon to download a printable graph
                                  image file.
                              </span>
                          )
                      },
                  },
              ]
            : []),
        ...(!isSmallScreen() && !isTouchScreen
            ? [
                  {
                      img: zoomArea,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  To zoom into the graph, {clickOrTap} and drag over an area, or use
                                  the scroll wheel or touch pad.
                              </span>
                          )
                      },
                  },
                  {
                      img: panMode,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  When zoomed, you can {clickOrTap} the Pan Mode button to pan.
                              </span>
                          )
                      },
                  },
                  {
                      img: panning,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  In Pan mode, {clickOrTap} and drag up or down in the graph to pan.
                              </span>
                          )
                      },
                  },
                  {
                      img: zoomMode,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  In Pan mode, you can {clickOrTap} the Zoom button to zoom more.
                              </span>
                          )
                      },
                  },
                  {
                      img: reset,
                      cls: 'pic-width-60-90',
                      render: () => {
                          return (
                              <span>
                                  To reset the graph to its original state, {clickOrTap} the Reset
                                  icon.
                              </span>
                          )
                      },
                  },
              ]
            : []),
    ]
}
