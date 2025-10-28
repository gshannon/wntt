import Home from './Home'
import Graph from './Graph'
import Map from './Map'
import About from './About'
import Help from './Help'
import HelpSyzygy from './HelpSyzygy'
import { Page } from './utils'
import Glossary from './Glossary'

export default function Control({ page, returnPage, gotoPage }) {
    return (
        <div className='app-box-bottom'>
            {page === Page.Home && <Home />}
            {page === Page.Graph && <Graph />}
            {page === Page.Map && <Map />}
            {page === Page.About && <About />}
            {page === Page.Glossary && <Glossary />}
            {page === Page.Tutorials && <Help />}
            {page === Page.HelpSyzygy && <HelpSyzygy gotoPage={gotoPage} returnPage={returnPage} />}
        </div>
    )
}
