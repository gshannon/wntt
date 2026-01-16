import Dropdown from 'react-bootstrap/Dropdown'

export default function ReserveSelect({ ctx }) {
    return (
        <Dropdown id='reserve-dropdown'>
            <Dropdown.Toggle>
                Choose
                <br />
                Reserve
            </Dropdown.Toggle>
            <Dropdown.Menu>
                <Content ctx={ctx} />
            </Dropdown.Menu>
        </Dropdown>
    )
}

// In case we don't have station data loaded yet, just display an empty select list.
const Content = ({ ctx }) => {
    if (!ctx.stationsData) {
        return <></>
    } else {
        return (
            <>
                {Object.entries(ctx.stationsData).map(([id, stn]) => (
                    <Dropdown.Item
                        key={id} // Anything unique
                        disabled={id === ctx.station?.id}
                        onClick={() => {
                            ctx.onStationSelected(stn.id)
                        }}>
                        {stn.reserveName}, {stn.waterStationName}
                    </Dropdown.Item>
                ))}
            </>
        )
    }
}
