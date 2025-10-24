import { Activity } from 'react'
import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import Help from './Help'
import HelpSyzygy from './HelpSyzygy'
import { Page } from './utils'
import Glossary from './Glossary'

export default function Control({ page, returnPage, gotoPage }) {
    // I'm only using the Activity approach (new to React 19.2) for the Graph page, when it might be
    // more valuable to avoid unmount/remount.  For the others, mounting is not particularly expensive
    // and also the call to setView in Map is throwing an error when that page is hidden rather than
    // unmounted.
    return (
        <div className='app-box-bottom'>
            {page === Page.Home && <Home />}
            <Activity mode={page === Page.Graph ? 'visible' : 'hidden'}>
                <Graph />
            </Activity>
            {page === Page.Map && <Map />}
            {page === Page.About && <About />}
            {page === Page.Glossary && <Glossary />}
            {page === Page.Tutorials && <Help />}
            {page === Page.HelpSyzygy && <HelpSyzygy gotoPage={gotoPage} returnPage={returnPage} />}
        </div>
    )
}
