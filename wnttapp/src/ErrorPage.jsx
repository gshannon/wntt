import { NotAcceptable } from './utils'

export default function ErrorPage({ error }) {
    const message =
        error.status === NotAcceptable
            ? 'Oops. It looks like your version is out of date. Please reload the page.'
            : `Oops. We&apos;re having a problem. Please try again later. (code ${error.status})`
    return (
        <>
            <br />
            <br />
            <div className='text-center fs-5'>{message}</div>
        </>
    )
}
