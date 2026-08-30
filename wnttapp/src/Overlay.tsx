import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
import { isTouchScreen } from './utils'

/**
 * Wrapper for OverlayTrigger with Tooltip overlay so we can build these the same way everywhere,
 * and not render them on touch screens, where they don't seem to work well.
 * Props:
 * - text: text to display in the tooltip
 * - placement: placement of the tooltip relative to the contents: 'top', 'bottom', 'left', 'right'
 * - contents: content to display in the overlay
 */

export default function Overlay(props) {
    const { text, placement, contents, enable = true } = props

    if (isTouchScreen || !enable) {
        return <> {contents}</>
    } else {
        return (
            <OverlayTrigger placement={placement} overlay={<Tooltip>{text}</Tooltip>}>
                <span>{contents}</span>
            </OverlayTrigger>
        )
    }
}
