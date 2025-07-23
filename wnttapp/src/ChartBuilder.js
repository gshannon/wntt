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
    connectgaps = false, // connect any gaps in data if using lines
    markerSize = null, // 0 means no markers (this forces lines)
    markerSymbol = 'circle', // ignored if markerSize=0
    markerAngle = null, // ignored if markerSize=0
    color = 'black',
    hoverinfo = 'all', // 'all', 'skip' or 'text'; ignored if hovertemplate is provided
    hovertext = null, // ignored unless referred to in hovertemplate
    hovertemplate = null, // if given, hoverinfo is ignored.
    yaxis = 'y', // use 'y2' for 2nd graph (wind)
} = {}) => {
    const p = {
        name: name,
        x: x,
        y: y,
        visible: legendOnly ? 'legendonly' : true,
        type: 'scatter',
        legendgroup: 'grp1',
        connectgaps: connectgaps,
        hoverinfo: hoverinfo,
        // hovertemplate overrides hoverinfo, so must set to empty if we want no hover text.
        // Otherwise must override default template of "{name} : %{y}".
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
