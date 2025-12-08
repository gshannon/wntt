import { daysBetween, formatDatetime, SyzygyInfo, Perihelion } from './utils'

export const Overlap_pixel_shift = 15
export const Overlap_x_millis = 1000 * 60 * 15 // 15 minutes

/*
hovertemplate: If given, hoverinfo is ignored. 
If not given & hoverinfo is 'all', the default template will be '<name> : {%y}' where %y is the y value. 
If given, only applies to the '{%y}' portion of the default, unless '<extra></extra>' is included,
  in which case it defines the entire hover line (this is how you show a different name). (yoiks!)
*/
export const buildPlot = ({
    name,
    x,
    y,
    legendOnly = false,
    lineType = null, // null means no lines
    markerSize = null, // 0 means no markers (this forces lines)
    markerSymbol = 'circle', // ignored if markerSize=0
    markerAngle = null, // ignored if markerSize=0
    color = 'black',
    hoverinfo = 'all', // 'all', 'skip' or 'text'; ignored if hovertemplate is provided
    hovertext = null, // ignored unless referred to in hovertemplate
    hovertemplate = null, // if given, hoverinfo is ignored.
    yaxis = 'y', // use 'y2' for 2nd graph (wind)
    disableToggle = false, // for use by event handlers
    connectgaps = true,
} = {}) => {
    const p = {
        name: name,
        x: x,
        y: y,
        disableToggle: disableToggle,
        visible: legendOnly ? 'legendonly' : true,
        type: 'scatter',
        legendgroup: 'grp1',
        connectgaps: connectgaps,
        hoverinfo: hoverinfo,
        // hovertemplate overrides hoverinfo, so we must set it to empty if we want no hover text.
        // Otherwise we can use it to override the default template of "{name} : %{y}".
        hovertemplate: hovertemplate,
        hovertext: hovertext,
        yaxis: yaxis,
    }
    let mode = 'lines'
    if (lineType && markerSize) {
        mode += '+markers'
    } else if (markerSize) {
        mode = 'markers'
    }
    p.mode = mode
    if (lineType) {
        p.line = { dash: lineType, color: color, shape: 'spline' }
    }
    if (markerSize) {
        p.marker = { color: color, size: markerSize, symbol: markerSymbol, angle: markerAngle }
    }
    // console.log(p)
    return p
}

export const calculate_overlap_minutes = (timeline, screen_width) => {
    const days = daysBetween(timeline.at(-1), timeline[0])
    console.log(days, screen_width)
}

// syzygy is an Array of objects with 2 fields. "dt": datetime string & "code" of event, like NM, FQ, etc.
export const buildSyzygyAnnotations = (syzygy, timeline) => {
    const annotations = []
    const annotationInfo = [] // This will parallel the layout annotations, so we can popup help on each.

    for (const item of syzygy) {
        const info = SyzygyInfo[item.code]
        const annotation = {
            text: info.display,
            font: { size: item.code == Perihelion ? 30 : 24 },
            x: item.dt,
            yref: 'paper', // We'll put this at the top of the graph, sticking out a bit
            y: 1.05,
            showarrow: false,
            hoverlabel: { bgcolor: 'black', font: { color: 'white' } },
            hovertext: `${info.name}: ${formatDatetime(
                new Date(item.dt)
            )}<br>Click symbol for more.`,
        }
        annotations.push(annotation)
        annotationInfo.push(item.code)
    }

    // TESTING ONLY
    // if (annotations.length > 1) {
    //     annotations[1].x = annotations[0].x
    //     if (annotations.length > 2) {
    //         annotations[2].x = annotations[0].x
    //     }
    // }

    space_annotations(annotations, timeline)

    return [annotations, annotationInfo]
}

// Avoid collisions
// TODO: This needs work
export const space_annotations = (annos, timeline) => {
    if (annos.length > 1) {
        // const left_margin = annos[1].x - new Date(timeline.at(0))
        const right_margin = new Date(timeline.at(-1)) - annos.at(-1).x

        // If A & B are too close, move A left or B right
        if (annos[1].x - annos[0].x < Overlap_x_millis) {
            if (right_margin < Overlap_x_millis) {
                annos[0].xshift = -Overlap_pixel_shift
            } else {
                annos[1].xshift = Overlap_pixel_shift
            }
        }
        if (annos.length == 3) {
            // If A & B are too close, move A left or B right
            if (annos[2].x - annos[1].x < Overlap_x_millis) {
                if (right_margin < Overlap_x_millis) {
                    if (annos[0].xshift) {
                        annos[0].xshift -= Overlap_pixel_shift // increase the shift of A
                    }
                    annos[1].xshift = -Overlap_pixel_shift
                } else {
                    // if (annos[1].xshift) {
                    //     annos[1].xshift += pixels // increase the shift of A
                    // }
                    annos[2].xshift = Overlap_pixel_shift + (annos[1].xshift ?? 0)
                }
            }
        }
    }
}
