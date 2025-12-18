import { useState } from 'react'
import { useContext } from 'react'
import Dropdown from 'react-bootstrap/Dropdown'
import { AppContext } from './AppContext'
import useStationSelection from './useStationSelection'
import { apiErrorResponse } from './utils'

const StationSelection = ({ error, children }) => {
    return error ? (
        <div className='text-warning bg-dark'>{apiErrorResponse(error)}</div>
    ) : (
        <>{children}</>
    )
}

export default function ReserveSelect() {
    const ctx = useContext(AppContext)
    const [stationSelectionData, setStationSelectionData] = useState([])
    const { data, error } = useStationSelection(stationSelectionData.length == 0)

    if (data != null && stationSelectionData.length == 0) {
        setStationSelectionData(data)
    }
    return (
        <StationSelection error={error}>
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
        </StationSelection>
    )
}
