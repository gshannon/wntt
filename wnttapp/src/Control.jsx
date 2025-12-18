import { useContext } from 'react'
import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import Help from './Help'
import HelpSyzygy from './HelpSyzygy'
import { Page } from './utils'
import Glossary from './Glossary'
import { AppContext } from './AppContext'

export default function Control({ page, returnPage, gotoPage }) {
    const ctx = useContext(AppContext)

    // Changing the "key" prop forces unmount/mount in cases where the station is changed
    // while on that page.
    return (
        <div className='app-box-bottom'>
            {page === Page.Home && <Home />}
            {page === Page.Graph && <Graph key={ctx.station.id} />}
            {page === Page.Map && <Map key={ctx.station.id} />}
            {page === Page.About && <About />}
            {page === Page.Glossary && <Glossary />}
            {page === Page.Tutorials && <Help />}
            {page === Page.HelpSyzygy && <HelpSyzygy gotoPage={gotoPage} returnPage={returnPage} />}
        </div>
    )
}
