import { Modal } from 'react-bootstrap'
import Accordion from 'react-bootstrap/Accordion'
import { MaxCustomElevation } from './utils'

export default function GraphHelp(props) {
    return (
        <Modal show={true} size='lg' onHide={props.onClose}>
            <Modal.Header className='py-2 graph-tips-header' closeButton />
            <Modal.Body className='px-3 py-0 graph-tips-body'></Modal.Body>
            <Accordion defaultActiveKey='0'>
                <Accordion.Item eventKey='0'>
                    <Accordion.Header>What am I looking at?</Accordion.Header>
                    <Accordion.Body>
                        Here you are seeing a graph showing predicted and actual tide levels for the
                        selected date range, as measured from the Wells Harbor in Wells, Maine. As
                        you move your mouse over the graph, you will see popup text showing the
                        exact values for that point on the graph. Match the line colors to the key
                        on the right to see what each line means. Along the top of the graph are
                        straight lines indicating several notable data points such as Record Tide,
                        shown for comparison purposes. This lets you see how close any high tide on
                        the curve comes to that record tide. You may change the start and end dates
                        at any time, then click Refresh to update the graph. All data shown in the
                        graph is described in more detail on the <b>Glossary</b> tab.
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='1'>
                    <Accordion.Header>How does this help me assess my flood risk?</Accordion.Header>
                    <Accordion.Body>
                        For elevations under {MaxCustomElevation} feet, you can add the elevation of
                        your home, business or any location you choose as a <b>new</b> line on the
                        graph! You do this on the Map tab. Follow the instructions there to find
                        your desired location on the map, then return to the Graph. You will then
                        see a new colored line on the graph with the label <b>Custom Elevation. </b>
                        If you set your date range to include today and the next several days,{' '}
                        <b>
                            you will be able to see whether the projected tide comes close to or
                            exceeds this elevation.
                        </b>
                    </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey='2'>
                    <Accordion.Header>
                        Why does future data look different than past data?
                    </Accordion.Header>
                    <Accordion.Body>
                        When the graph is showing past data, you will see recorded tides and wind
                        speed/direction, along with the predicted astronomical tides. For several
                        days in the future, in addition to predicted astronomical tides, (which do
                        not account for the effects of weather), there is the experimental{' '}
                        <b>Projected Storm Surge</b> data, which does consider weather (wind
                        speed/direction). This, added to the astronomical tide, adds up to the
                        overall Projected Storm Tide water levels. This value is meant to be the
                        best available estimate, and, since it is updated every 6 hours, may become
                        more accurate as the tide in question approaches. There are no wind
                        forecasts shown here, but users should bear in mind that high winds,
                        particularly when coming from the east, can drive waves higher than the tide
                        levels. Note that the wind portion of the graph is removed if the date range
                        is entirely in the future.
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </Modal>
    )
}
