import { useContext } from 'react'
import Home from './Home'
import Graph from './Graph'
import About from './About'
import HelpSyzygy from './HelpSyzygy'
import { Page } from './utils'
import Glossary from './Glossary'
import { AppContext } from './AppContext'
import ErrorBlock from './ErrorBlock'

export default function Control({ page, returnPage, gotoPage }) {
    const ctx = useContext(AppContext)

    if (ctx.fatalError) {
        return (
            <div className='app-box-bottom'>
                <ErrorBlock error={ctx.fatalError} />
            </div>
        )
    }

    const pageClass = {
        [Page.Home]: 'home-page',
        [Page.Graph]: 'graph-page',
        [Page.About]: 'about-page',
        [Page.Glossary]: 'glossary-page',
        [Page.HelpSyzygy]: 'help-syzygy-page',
    }

    // Changing the "key" prop forces remount in cases where the station is changed
    // while on that page. Note that to get to Graph or Map, a station must be set in the context.
    return (
        <div className={`app-box-bottom ${pageClass[page]}`}>
            {page === Page.Home && <Home />}
            {page === Page.Graph && <Graph key={ctx.station?.id} />}
            {page === Page.About && <About />}
            {page === Page.Glossary && <Glossary />}
            {page === Page.HelpSyzygy && <HelpSyzygy gotoPage={gotoPage} returnPage={returnPage} />}
        </div>
    )
}
