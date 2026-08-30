import { createContext } from 'react'

// This is in its own file instead of in App.jsx to quiet the
// "Fast refresh only works when a file only exports components" warning from vite.

export const AppContext = createContext({})
