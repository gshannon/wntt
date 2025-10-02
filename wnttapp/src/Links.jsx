// Wraps an html anchor link that opens in a new window/tab, where display text is the URL.
export function SimpleLink(props) {
    return (
        <a target='_blank' rel='noopener noreferrer' href={props.href}>
            {props.href}
        </a>
    )
}

// Wraps an html anchor link that opens in a new window/tab, where display text is different from the URL.
export function Link(props) {
    return (
        <a target='_blank' rel='noopener noreferrer' href={props.href}>
            {props.text}
        </a>
    )
}
