// Wraps an html anchor link that opens in a new window/tab, where display text is the URL.
export function SimpleLink({ href }) {
    return (
        <a target='_blank' rel='noopener noreferrer' href={href}>
            {href}
        </a>
    )
}

// Wraps an html anchor link that opens in a new window/tab, where display text is different from the URL.
export function Link({ href, text }) {
    return (
        <a target='_blank' rel='noopener noreferrer' href={href}>
            {text}
        </a>
    )
}
