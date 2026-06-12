// Any image that can be downloaded with the graph must be inlined to prevent CORS errors.
import NewMoonImg from './images/util/moon-new.png?inline'
import FirstQuarterImg from './images/util/moon-first.png?inline'
import FullMoonImg from './images/util/moon-full.png?inline'
import LastQuarterImg from './images/util/moon-last.png?inline'
import PerigeeImg from './images/util/perigee.png?inline'
import PerihelionImg from './images/util/perihelion.png?inline'

// These values must be kept in sync with the API
export const SyzygyCode = Object.freeze({
    NewMoon: 'NM',
    FirstQuarter: 'FQ',
    FullMoon: 'FM',
    LastQuarter: 'LQ',
    Perigee: 'PG',
    Perihelion: 'PH',
})

export const SyzygyConfig = {
    [SyzygyCode.NewMoon]: { name: 'New Moon' },
    [SyzygyCode.FirstQuarter]: { name: 'First Quarter' },
    [SyzygyCode.FullMoon]: { name: 'Full Moon' },
    [SyzygyCode.LastQuarter]: { name: 'Last Quarter' },
    [SyzygyCode.Perigee]: { name: 'Perigee' },
    [SyzygyCode.Perihelion]: { name: 'Perihelion' },
}

export const getSyzygyUrl = (code) => {
    const prefix = 'image://'
    switch (code) {
        case SyzygyCode.NewMoon:
            return prefix + NewMoonImg
        case SyzygyCode.FirstQuarter:
            return prefix + FirstQuarterImg
        case SyzygyCode.FullMoon:
            return prefix + FullMoonImg
        case SyzygyCode.LastQuarter:
            return prefix + LastQuarterImg
        case SyzygyCode.Perigee:
            return prefix + PerigeeImg
        case SyzygyCode.Perihelion:
            return prefix + PerihelionImg
        default:
            return null
    }
}
