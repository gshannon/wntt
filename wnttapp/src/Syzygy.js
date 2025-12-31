// These must be kept in sync with the API
export const NewMoon = 'NM'
export const FirstQuarter = 'FQ'
export const FullMoon = 'FM'
export const LastQuarter = 'LQ'
export const Perigee = 'PG'
export const Perihelion = 'PH'

export const SyzygyConfig = {
    [NewMoon]: { name: 'New Moon', fontSize: 24, display: '\u{1F31A}' }, // 🌚
    [FirstQuarter]: { name: 'First Quarter', fontSize: 24, display: '\u{1F313}' }, // 🌓
    [FullMoon]: { name: 'Full Moon', fontSize: 24, display: '\u{1F31D}' }, // 🌝
    [LastQuarter]: { name: 'Last Quarter', fontSize: 24, display: '\u{1F317}' }, // 🌗
    [Perigee]: { name: 'Perigee', fontSize: 24, display: '\u{1F535}' }, //  🔵 \u{1F53B} 🔻 \u{1F53A} 🔺
    [Perihelion]: { name: 'Perihelion', fontSize: 28, display: '\u{2600}\u{fe0f}' }, // ☀️
}

export const getSyzygyEvent = (apiData) => {
    return {
        dt: apiData.dt,
        code: apiData.code,
        config: SyzygyConfig[apiData.code],
    }
}
