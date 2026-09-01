// Any image that can be downloaded with the graph must be inlined to prevent CORS errors.
import NewMoonImg from './images/util/moon-new.png?inline'
import FirstQuarterImg from './images/util/moon-first.png?inline'
import FullMoonImg from './images/util/moon-full.png?inline'
import LastQuarterImg from './images/util/moon-last.png?inline'
import PerigeeImg from './images/util/perigee.png?inline'
import PerihelionImg from './images/util/perihelion.png?inline'

// These values must be kept in sync with the API

export const SyzygyCodes = {
    NewMoon: 'NM',
    FirstQuarter: 'FQ',
    FullMoon: 'FM',
    LastQuarter: 'LQ',
    Perigee: 'PG',
    Perihelion: 'PH',
} as const

// Use the standard idiom for "the union of values of a const object" — the modern stand-in for a string enum.
export type SyzygyCode = (typeof SyzygyCodes)[keyof typeof SyzygyCodes]

const syzygyCodeValues = new Set<string>(Object.values(SyzygyCodes))

// Guard function
export const isSyzygyCode = (x: unknown): x is SyzygyCode =>
    typeof x === 'string' && syzygyCodeValues.has(x)

const prefix = 'image://'

export const SyzygyConfig: Record<SyzygyCode, { name: string; url: string }> = {
    [SyzygyCodes.NewMoon]: { name: 'New Moon', url: prefix + NewMoonImg },
    [SyzygyCodes.FirstQuarter]: { name: 'First Quarter', url: prefix + FirstQuarterImg },
    [SyzygyCodes.FullMoon]: { name: 'Full Moon', url: prefix + FullMoonImg },
    [SyzygyCodes.LastQuarter]: { name: 'Last Quarter', url: prefix + LastQuarterImg },
    [SyzygyCodes.Perigee]: { name: 'Perigee', url: prefix + PerigeeImg },
    [SyzygyCodes.Perihelion]: { name: 'Perihelion', url: prefix + PerihelionImg },
}
