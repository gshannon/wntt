import jsonData from './stations.json'
import Station from './Station'

const AllStations = {}

// Build javascript Station data from json file contents
for (const key in jsonData) {
    AllStations[key] = new Station(jsonData[key])
}

// Get the Station instance for this id, e.g. 'welinwq'
export const getStation = (water_station_id) => {
    return AllStations[water_station_id]
}
