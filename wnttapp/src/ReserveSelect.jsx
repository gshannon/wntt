import { useState } from 'react'
import { useContext } from 'react'
import Dropdown from 'react-bootstrap/Dropdown'
import { useEffect, useEffectEvent } from 'react'
import { AppContext } from './AppContext'
import useStationSelection from './useStationSelection'
import { NotAcceptable } from './utils'

export default function ReserveSelect() {
    const ctx = useContext(AppContext)
    const [stationSelectionData, setStationSelectionData] = useState([])
    const { data, error } = useStationSelection(stationSelectionData.length == 0)

    if (data && stationSelectionData.length == 0) {
        setStationSelectionData(data)
    }

    const errorCheck = useEffectEvent(() => {
        if (error && error.status == NotAcceptable) {
            ctx.setFatalError(error)
        }
    })

    useEffect(() => {
        errorCheck()
    }, [])

    return (
        <Dropdown id='reserve-dropdown'>
            <Dropdown.Toggle>
                Choose
                <br />
                Reserve
            </Dropdown.Toggle>
            <Dropdown.Menu>
                {stationSelectionData.map((stn) => (
                    <Dropdown.Item
                        key={stn.id} // Anything unique
                        disabled={stn.id === ctx.station?.id}
                        onClick={() => {
                            ctx.setStationId(stn.id)
                        }}>
                        {stn.reserveName}, {stn.waterStationName}
                    </Dropdown.Item>
                ))}
            </Dropdown.Menu>
        </Dropdown>
    )
}
